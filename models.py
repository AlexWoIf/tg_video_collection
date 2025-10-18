from sqlalchemy import Column, BigInteger, Integer, String, Text, ForeignKey, \
    Boolean, UniqueConstraint, PrimaryKeyConstraint, Index, SmallInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship


Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(BigInteger, primary_key=True, nullable=False)
    username = Column(Text, nullable=False, default='')
    first_name = Column(Text, nullable=False, default='')
    last_name = Column(Text, nullable=False, default='')
    language_code = Column(Text, nullable=False, default='')
    is_bot = Column(Boolean, nullable=False, default=False)

    view_requests = relationship('EpisodeViewRecord', back_populates='user')
    new_movie_requests = relationship('RequestedNewMovie', back_populates='user')

    def __repr__(self):
        return f'<User(id={self.id}, username="{self.username}")>'


class Serial(Base):
    __tablename__ = 'serials'

    id = Column(BigInteger, primary_key=True, nullable=False)
    name_rus = Column(Text, nullable=False, default='')
    name_eng = Column(Text, nullable=False, default='')
    creators = Column(Text, nullable=False, default='')
    studio = Column(Text, nullable=False, default='')
    format = Column(Text, nullable=False, default='')
    actors = Column(Text, nullable=False, default='')
    descr = Column(Text, nullable=False, default='')
    imdb = Column(String(10), nullable=False, default='')
    kp_id = Column(String(10), nullable=False, default='')

    episodes = relationship('Episode', back_populates='serial')

    def __repr__(self):
        return f'<Serial(id={self.id}, name_rus="{self.name_rus}")>'


class Audio(Base):
    __tablename__ = 'sounds'

    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    name = Column(Text, nullable=False, default='')

    files = relationship('File', back_populates='audio')

    def __repr__(self):
        return f'<Audio(id={self.id}, name="{self.name}")>'


class Episode(Base):
    __tablename__ = 'episodes'
    __table_args__ = (
        Index('ix_episodes_serial_id', 'serial_id'),
    )

    id = Column(BigInteger, primary_key=True, nullable=False, 
                autoincrement=True)
    serial_id = Column(BigInteger, ForeignKey('serials.id'), default=0)
    season = Column(Integer, nullable=False, default=0)
    episode = Column(Integer, nullable=False, default=0)
    name = Column(Text, nullable=False, default='')
    file_id = Column(Integer, ForeignKey('episodes.id'), nullable=True)

    serial = relationship('Serial', back_populates='episodes')
    files = relationship('File', back_populates='episode')
    view_requests = relationship('EpisodeViewRecord', back_populates='episode')

    def __repr__(self):
        return f'<Episode(id={self.id}, serial_id={self.serial_id})>'


class File(Base):
    __tablename__ = 'files'
    __table_args__ = (
        UniqueConstraint('file_id', name='uq_file_id'),
        Index('ix_file_id', 'file_id'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    episode_id = Column(BigInteger, ForeignKey('episodes.id'), nullable=False)
    file_id = Column(String(128), nullable=False)
    duration = Column(Integer, nullable=False, default=0)
    width = Column(SmallInteger, nullable=False, default=0)
    height = Column(SmallInteger, nullable=False, default=0)
    audio_id = Column(Integer, ForeignKey('sounds.id'), nullable=False, 
                      default=0)

    episode = relationship('Episode', back_populates='files')
    audio = relationship('Audio', back_populates='files')

    def __repr__(self):
        return f'<File(episode_id={self.episode_id}, file_id="{self.file_id}")>'  # noqa: E501


class EpisodeViewRecord (Base):
    __tablename__ = 'episode_view_records'
    __table_args__ = (
        PrimaryKeyConstraint('user_id', 'episode_id', 'created_at'),
    )

    user_id = Column(BigInteger, ForeignKey('users.id'), nullable=True)
    episode_id = Column(BigInteger, ForeignKey('episodes.id'), nullable=True)
    created_at = Column(String(26), nullable=False)

    user = relationship('User', back_populates='view_requests')
    episode = relationship('Episode', back_populates='view_requests')

    def __repr__(self):
        return f'<EpisodeViewRecord(user_id={self.user_id}, episode_id={self.episode_id})>'  # noqa: E501


class RequestedNewMovie(Base):
    __tablename__ = 'requested_new_movie'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.id'), nullable=False)
    url = Column(String(255), nullable=False, default='')
    kp_id = Column(String(10), nullable=False, default='')
    imdb = Column(String(10), nullable=False, default='')
    created_at = Column(String(26), nullable=False)

    user = relationship('User', back_populates='new_movie_requests')

    def __repr__(self):
        return f"<RequestedNewMovie(id={self.id}, user_id={self.user_id}, url='{self.url}')>"  # noqa: E501
