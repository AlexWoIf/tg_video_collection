import logging
from datetime import datetime

from sqlalchemy import and_, case, distinct, func, or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from models import (Audio, Episode, EpisodeViewRecord, File, KPEpisode,
                    KPSerial, Poster, RequestedNewMovie, Serial, User)


def get_aggregated_view_history(db: Session, user_id: int, limit: int = 10,
                                offset: int = 0):
    """
    Получает агрегированную историю просмотров по сериалам с группировкой по
    последовательным просмотрам с поддержкой пагинации.
    Если limit=0, то возвращает общее количество групп просмотров.
    """
    # Сначала создаем подзапрос, который вычисляет флаг изменения сериала
    subquery = db.query(
        EpisodeViewRecord.user_id,
        EpisodeViewRecord.episode_id,
        EpisodeViewRecord.created_at,
        Serial.id.label('serial_id'),
        Serial.name_rus,
        Serial.name_eng,
        # Вычисляем предыдущий serial_id с помощью LAG
        func.lag(Serial.id).over(
            partition_by=EpisodeViewRecord.user_id,
            order_by=EpisodeViewRecord.created_at
        ).label('prev_serial_id')
    ).join(Episode, EpisodeViewRecord.episode_id == Episode.id) \
     .join(Serial, Episode.serial_id == Serial.id) \
     .filter(EpisodeViewRecord.user_id == user_id) \
     .subquery()

    # Теперь в основном запросе вычисляем группу на основе сравнения с
    # предыдущим serial_id и применяем агрегатную функцию SUM уже к простому
    # полю CASE
    cte_query = db.query(
        subquery.c.user_id,
        subquery.c.episode_id,
        subquery.c.created_at,
        subquery.c.serial_id,
        subquery.c.name_rus,
        subquery.c.name_eng,
        subquery.c.prev_serial_id,
        # Вычисляем группу с помощью SUM и CASE, но уже без оконных функций
        func.sum(
            case(
                (subquery.c.serial_id != subquery.c.prev_serial_id, 1),
                else_=0
            )
        ).over(
            partition_by=subquery.c.user_id,
            order_by=subquery.c.created_at
        ).label('group_number')
    ).subquery()

    # Финальный запрос для агрегации по группам
    query = db.query(
        cte_query.c.name_rus,
        cte_query.c.name_eng,
        func.count().label('consecutive_views'),
        cte_query.c.serial_id,
    ).group_by(
        cte_query.c.user_id,
        cte_query.c.serial_id,
        cte_query.c.group_number
    ).order_by(func.max(cte_query.c.created_at).desc())

    return query.limit(limit).offset(offset).all(), query.count()


def get_alphabet_counts(db, language):
    name_expr = case(
        (language == 'RUS', Serial.name_rus),
        else_=Serial.name_eng
    )

    result = db.query(
        func.upper(func.substr(name_expr, 1, 1)).label('letter'),
        func.count(Serial.id).label('count')
    ).group_by(
        func.upper(func.substr(name_expr, 1, 1))
    ).order_by(
        'letter'
    ).all()

    return result


def get_random_serials(db, limit=10):
    return db.query(
        Serial.name_rus,
        Serial.name_eng,
        Serial.id,
    ).order_by(func.rand()).limit(limit).all()


def get_serial_by_id(db: Session, serial_id: int):
    return db.query(
        Serial.id,
        Serial.name_rus,
        Serial.name_eng,
        Serial.creators,
        Serial.studio,
        Serial.format,
        Serial.actors,
        Serial.descr,
        Serial.imdb,
        Serial.kp_id,
        Poster.file_id,
    ).filter(
        Serial.id == serial_id, Serial.poster_id == Poster.id
    ).one_or_none()


def get_serials_by_namepart(db: Session, name_part: str, limit=10, page=1):
    offset = limit * (page - 1)
    query = db.query(
        Serial.name_rus,
        Serial.name_eng,
        Serial.id
    ).filter(
        or_(
            Serial.name_rus.like(f'{name_part}'),
            Serial.name_eng.like(f'{name_part}')
        )
    )
    return query.limit(limit).offset(offset).all(), query.count()


def get_serial_by_search_key(db: Session, search_key: str, search_value: str):
    filter_condition = getattr(Serial, search_key) == search_value
    return db.query(
        Serial.id,
        Serial.name_rus,
        Serial.name_eng,
        Serial.creators,
        Serial.studio,
        Serial.format,
        Serial.actors,
        Serial.descr,
        Serial.imdb,
        Serial.kp_id,
    ).filter(filter_condition).one()


def get_seasons_by_serial_id(db: Session, serial_id: int):
    return db.query(
        Episode.season,
        func.count(Episode.id).label('episode_count')
    ).filter(Episode.serial_id == serial_id) \
     .group_by(Episode.season) \
     .order_by(Episode.season) \
     .all()


def get_kp_episodes_by_serial_id(db: Session, serial_id: int, ):
    return db.query(
        KPEpisode.id,
        KPEpisode.season,
        KPEpisode.episode,
        KPEpisode.name_rus,
        KPEpisode.name_eng
    ).join(
        Serial, Serial.kp_id == KPEpisode.kp_serial_id
    ).outerjoin(
        Episode,
        (Episode.serial_id == Serial.id) &
        (Episode.season == KPEpisode.season) &
        (Episode.episode == KPEpisode.episode)
    ).where(
        Serial.id == serial_id,
        Episode.id.is_(None),
        KPEpisode.ignore == 0,
    ).order_by(
        KPEpisode.season,
        KPEpisode.episode
    ).all()


def get_episodes_by_serial_and_season(
          db: Session,
          serial_id: int,
          season: int,
          user_id: int,
          limit: int = 10,
          offset: int = 0, ):
    subquery = db.query(
        EpisodeViewRecord.episode_id,
        func.count(EpisodeViewRecord.created_at).label('views')
    ).filter(EpisodeViewRecord.user_id == user_id) \
     .group_by(EpisodeViewRecord.episode_id) \
     .subquery()

    query = db.query(
        Episode.season,
        Episode.episode,
        Episode.name,
        Episode.id,
        Episode.file_id,
        subquery.c.views
    ).join(subquery, subquery.c.episode_id == Episode.id, isouter=True, ) \
     .filter(Episode.serial_id == serial_id, Episode.season == season,
             Episode.file_id.is_not(None)) \
     .group_by(Episode.id, Episode.episode, ) \
     .order_by(Episode.episode)

    all_episodes = query.all()
    total_count = len(all_episodes)

    if offset >= 0 or total_count == 0:
        return all_episodes[offset:offset+limit], total_count, \
            offset // limit + 1
    for idx, episode in enumerate(all_episodes):
        if episode.views is None:  # views берется из подзапроса
            offset = (idx // limit) * limit
            break
    else:
        offset = ((total_count - 1) // limit) * limit
    return all_episodes[offset:offset+limit], total_count, offset // limit + 1


def get_episode_by_id(db: Session, episode_id: int, ):
    return db.query(
        Episode.id,
        Episode.serial_id,
        Serial.name_rus,
        Serial.name_eng,
        Episode.season,
        Episode.episode,
        Episode.name,
        File.id.label('file_id'),
        File.file_id.label('tg_file_id'),
        File.width,
        File.height,
        Audio.name.label('audio'),
        Poster.file_id.label('poster_file_id'),
    ).join(
        Episode, Episode.serial_id == Serial.id, isouter=True,
    ).join(
        File, File.episode_id == Episode.id, isouter=True,
    ).join(
        Audio, Audio.id == File.audio_id, isouter=True,
    ).filter(Episode.id == episode_id, Serial.poster_id == Poster.id).all()


def get_next_episode(db: Session, current_episode):
    next_episode = db.query(
        Episode.id,
        Episode.file_id
    ).filter(
        Episode.serial_id == current_episode.serial_id,
        or_(
            and_(
                Episode.season == current_episode.season,
                Episode.episode > current_episode.episode
            ),
            and_(
                Episode.season > current_episode.season,
                Episode.episode == db.query(func.min(Episode.episode)).filter(
                    Episode.serial_id == current_episode.serial_id,
                    Episode.season > current_episode.season
                ).scalar_subquery()
            )
        )
    ).order_by(Episode.season, Episode.episode) \
     .first()
    return next_episode


def get_serials_rating(db: Session, limit=10, page=1):
    offset = limit * (page - 1)
    query = db.query(
        Serial.name_rus,
        Serial.name_eng,
        func.count(distinct(EpisodeViewRecord.user_id)).label('users'),
        Episode.serial_id
    ).select_from(EpisodeViewRecord)\
     .outerjoin(Episode, EpisodeViewRecord.episode_id == Episode.id)\
     .outerjoin(Serial, Episode.serial_id == Serial.id)\
     .group_by(Episode.serial_id, Serial.name_rus, Serial.name_eng)\
     .order_by(func.count(distinct(EpisodeViewRecord.user_id)).desc())

    return query.limit(limit).offset(offset).all(), query.count()


def ignore_kp_episode(db: Session, kp_episode_id: int):
    db.query(KPEpisode).filter(KPEpisode.id == kp_episode_id).update(
        {KPEpisode.ignore: True}
    )
    db.commit()
    return db.query(Serial.id).filter(
        KPEpisode.id == kp_episode_id,
        KPEpisode.kp_serial_id == Serial.kp_id
    ).one_or_none()


def add_all_episodes_from_kp_serial(db, serial_id: int) -> list[Episode]:
    kp_episodes = db.query(KPEpisode).join(
        KPSerial, KPSerial.kp_id == KPEpisode.kp_serial_id
    ).join(
        Serial, Serial.kp_id == KPSerial.kp_id
    ).outerjoin(
        Episode,
        (Episode.serial_id == Serial.id) &
        (Episode.season == KPEpisode.season) &
        (Episode.episode == KPEpisode.episode)
    ).filter(
        Serial.id == serial_id,
        ~KPEpisode.ignore,
        Episode.id.is_(None),  # Нет существующего эпизода
    ).all()

    created_episodes = []
    for kp_episode in kp_episodes:
        episode = add_episode_from_kp_episode(db, kp_episode.id)
        created_episodes.append(episode)

    return created_episodes


def add_episode_from_kp_episode(db: Session, kp_episode_id: int) -> Episode:
    """
    Добавляет эпизод в таблицу Episode на основе данных из KPEpisode

    Args:
        session: сессия SQLAlchemy
        kp_episode_id: ID эпизода из таблицы kp_episodes

    Returns:
        Episode: созданный объект Episode

    Raises:
        ValueError: если KPEpisode с указанным ID не найден
        ValueError: если Serial с таким kp_id не найден
        ValueError: если уже есть эпизод с таким serial_id, season и episode
    """
    # Получаем KPEpisode из базы
    kp_episode = db.query(KPEpisode).filter(KPEpisode.id == kp_episode_id) \
        .first()

    if not kp_episode:
        raise ValueError(f'KPEpisode с id={kp_episode_id} не найден')

    kp_id = kp_episode.kp_serial.kp_id

    serial = db.query(Serial).filter(Serial.kp_id == str(kp_id)).first()
    if not serial:
        raise ValueError(
            f"Serial с kp_id={kp_id} не найден в таблице serials. "
            f"Сначала необходимо добавить сериал."
        )

    existing_episode = db.query(Episode).filter(
        Episode.serial_id == serial.id,
        Episode.season == kp_episode.season,
        Episode.episode == kp_episode.episode
    ).first()
    if existing_episode:
        raise ValueError(
            f'Эпизод с serial_id={serial.id}, season={kp_episode.season}, '
            f'episode={kp_episode.episode} уже существует'
        )

    # Формируем название эпизода (приоритет у русского названия)
    episode_name = f'{kp_episode.name_rus} ({kp_episode.name_eng})' \
        if kp_episode.name_rus else kp_episode.name_eng

    # Создаем новый эпизод
    new_episode = Episode(
        serial_id=serial.id,
        season=kp_episode.season,
        episode=kp_episode.episode,
        name=episode_name,
    )

    db.add(new_episode)
    db.flush()  # Чтобы получить id нового эпизода

    return new_episode


def insert_kp_serial(db: Session, serial, episodes):
    serial_id = serial['kinopoiskId']
    kp_serial = db.get(KPSerial, serial_id)
    if kp_serial:
        db.delete(kp_serial)
    new_kp_serial = KPSerial(
            kp_id=serial_id,
            name_rus=serial['nameRu'],
            name_eng=serial['nameOriginal'] or serial['nameEn'] or '',
            descr=serial['description'],
            poster=serial['posterUrlPreview'],
            imdb=serial['imdbId'],
        )
    for season in episodes.get('items', []):
        for episode in season['episodes']:
            # logging.error(episode)
            new_kp_serial.episodes.append(
                KPEpisode(
                    season=episode['seasonNumber'],
                    episode=episode['episodeNumber'],
                    name_rus=episode['nameRu'] or '',
                    name_eng=episode['nameEn'] or '',
                )
            )

    db.add(new_kp_serial)


def insert_episode_view_record(db: Session, user_id: int, episode_id: int):
    db.add(
        EpisodeViewRecord(
            user_id=user_id,
            episode_id=episode_id,
            created_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        )
    )


def insert_new_episode(db: Session, serial_id: int, season: int,
                       episode: int, name: str):
    db.add(
        Episode(
            serial_id=serial_id,
            season=season,
            episode=episode,
            name=name,
        )
    )


def insert_new_user(db: Session, user):
    db.merge(
        User(
            id=user.id,
            username=user.username or '',
            first_name=user.first_name or '',
            last_name=user.last_name or '',
            language_code=user.language_code or '',
            is_bot=user.is_bot,
        )
    )


def create_new_movie_request(db: Session, user_id: int, url: str,
                             kp_id: str = '', imdb: str = ''):
    try:
        movie_request = RequestedNewMovie(
            user_id=user_id,
            url=url,
            kp_id=kp_id,
            imdb=imdb,
            created_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        )

        db.add(movie_request)
        db.commit()
        db.refresh(movie_request)

        return movie_request

    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f'Ошибка при сохранении запроса: {e}')
        return None
