from datetime import datetime

from sqlalchemy import and_, case, distinct, func, or_
from sqlalchemy.orm import Session

from models import *


def get_aggregated_view_history(db: Session, user_id: int, limit: int = 10, offset: int = 0):
    """
    Получает агрегированную историю просмотров по сериалам с группировкой по 
    последовательным просмотрам с поддержкой пагинации.
    Если limit=0, то возвращает общее количество групп просмотров.
    """
    # Сначала создаем подзапрос, который вычисляет флаг изменения сериала
    subquery = db.query(
        EpisodeViewRecord.user_id,
        EpisodeViewRecord.episode_id,
        EpisodeViewRecord.updated_at,
        Serial.id.label('serial_id'),
        Serial.name_rus,
        Serial.name_eng,
        # Вычисляем предыдущий serial_id с помощью LAG
        func.lag(Serial.id).over(
            partition_by=EpisodeViewRecord.user_id,
            order_by=EpisodeViewRecord.updated_at
        ).label('prev_serial_id')
    ).join(Episode, EpisodeViewRecord.episode_id == Episode.id) \
     .join(Serial, Episode.serial_id == Serial.id) \
     .filter(EpisodeViewRecord.user_id == user_id) \
     .subquery()

    # Теперь в основном запросе вычисляем группу на основе сравнения с предыдущим serial_id
    # и применяем агрегатную функцию SUM уже к простому полю CASE
    cte_query = db.query(
        subquery.c.user_id,
        subquery.c.episode_id,
        subquery.c.updated_at,
        subquery.c.serial_id,
        subquery.c.name_rus,
        subquery.c.name_eng,
        subquery.c.prev_serial_id,
        # Вычисляем группу с помощью SUM и CASE, но уже без оконных функций внутри
        func.sum(
            case(
                (subquery.c.serial_id != subquery.c.prev_serial_id, 1),
                else_=0
            )
        ).over(
            partition_by=subquery.c.user_id,
            order_by=subquery.c.updated_at
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
    ).order_by(func.max(cte_query.c.updated_at).desc())

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
        Serial.kp_id
    ).filter(Serial.id == serial_id).one()


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


def get_seasons_by_serial_id(db: Session, serial_id: int):
        return db.query(
        Episode.season,
        func.count(Episode.id).label('episode_count')
    ).filter(Episode.serial_id == serial_id) \
     .group_by(Episode.season) \
     .order_by(Episode.season) \
     .all()


def get_episodes_by_serial_id(
          db: Session,
          serial_id: int,
          season: int,
          user_id: int,
          limit: int = 10,
          offset: int = 0, ):
    subquery = db.query(
        EpisodeViewRecord.episode_id,
        func.count(EpisodeViewRecord.updated_at).label('views')
    ).filter(EpisodeViewRecord.user_id==user_id) \
     .group_by(EpisodeViewRecord.episode_id) \
     .subquery()

    query = db.query(
        Episode.season,
        Episode.episode,
        Episode.name,
        Episode.id,
        Episode.file_id,
        subquery.c.views
    ).join(subquery, subquery.c.episode_id==Episode.id, isouter=True, ) \
     .filter(Episode.serial_id==serial_id, Episode.season==season, ) \
     .group_by(Episode.id, Episode.episode, ) \
     .order_by(Episode.episode)

    return query.limit(limit).offset(offset).all(), query.count()


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
    File.width,
    File.height,
    Audio.name.label('audio'),
).join(
    Episode, Episode.serial_id==Serial.id, isouter=True,
).join(
    File, File.episode_id==Episode.id, isouter=True,
).join(
    Audio, Audio.id==File.audio_id, isouter=True,
).filter(Episode.id==episode_id).all()


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


def insert_episode_view_record(db: Session, user_id: int, episode_id: int):
    db.add(
        EpisodeViewRecord(
            user_id=user_id,
            episode_id=episode_id,
            updated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
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
