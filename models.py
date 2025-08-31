from sqlalchemy import Column, BigInteger, Integer, String, Text, ForeignKey, \
    Boolean, UniqueConstraint, PrimaryKeyConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship


Base = declarative_base()


class User(Base):
    __tablename__ = 'user'

    id = Column(BigInteger, primary_key=True, nullable=False)
    username = Column(Text, nullable=False, default='')
    first_name = Column(Text, nullable=False, default='')
    last_name = Column(Text, nullable=False, default='')
    language_code = Column(Text, nullable=False, default='')
    is_bot = Column(Boolean, nullable=False, default=False)

    view_requests = relationship("ViewRequest", back_populates="user")

    def __repr__(self):
        return f'<User(id={self.id}, username="{self.username}")>'


class Serial(Base):
    __tablename__ = 'serials'

    id = Column(Integer, primary_key=True, nullable=False)
    name_rus = Column(Text, default='')
    name_eng = Column(Text, default='')
    creators = Column(Text, default='')
    studio = Column(Text, default='')
    format = Column(Text, default='')
    actors = Column(Text, default='')
    descr = Column(Text, default='')
    IMDB = Column(String(10), nullable=False, default='')
    kp_id = Column(String(10), nullable=False, default='')

    episodes = relationship("Episode", back_populates="serial")

    def __repr__(self):
        return f'<Serial(id={self.id}, name_rus="{self.name_rus}")>'


class Audio(Base):
    __tablename__ = 'sounds'

    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    name = Column(String(32), nullable=False, default='')

    episodes = relationship("Episode", back_populates="audio")
    files = relationship("File", back_populates="audio")

    def __repr__(self):
        return f'<Audio(id={self.id}, name="{self.name}")>'


class Episode(Base):
    __tablename__ = 'episodes'
    __table_args__ = (
        UniqueConstraint('serial_id', 'season', 'episode', 
                         name='uq_serial_season_episode'),
    )

    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    serial_id = Column(Integer, ForeignKey('serials.id'), default=0)
    season = Column(Integer, default=0)
    episode = Column(Integer, default=0)
    name = Column(Text, default='')
    file_id = Column(Text, default='')
    duration = Column(Integer, default=0)
    width = Column(Integer, default=0)
    height = Column(Integer, default=0)
    audio_id = Column(Integer, ForeignKey('sounds.id'), nullable=False, default=0)  # noqa: E501

    serial = relationship("Serial", back_populates="episodes")
    audio = relationship("Audio", back_populates="episodes")
    files = relationship("File", back_populates="episode")
    view_requests = relationship("ViewRequest", back_populates="episode")

    def __repr__(self):
        return f'<Episode(id={self.id}, serial_id={self.serial_id})>'


class File(Base):
    __tablename__ = 'files'

    episode_id = Column(Integer, ForeignKey('episodes.id'), primary_key=True, nullable=False)  # noqa: E501
    file_id = Column(String(128), primary_key=True, nullable=False)
    duration = Column(Integer, nullable=False, default=0)
    width = Column(Integer, nullable=False, default=0)
    height = Column(Integer, nullable=False, default=0)
    audio_id = Column(Integer, ForeignKey('sounds.id'), nullable=False, default=0)  # noqa: E501

    # Отношения к другим таблицам
    episode = relationship("Episode", back_populates="files")
    audio = relationship("Audio", back_populates="files")

    def __repr__(self):
        return f'<File(episode_id={self.episode_id}, file_id="{self.file_id}")>'  # noqa: E501


class ViewRequest(Base):
    __tablename__ = 'requests'
    __table_args__ = (
        PrimaryKeyConstraint('user_id', 'episode_id', 'updated_at'),
    )

    user_id = Column(BigInteger, ForeignKey('user.id'), nullable=True)
    episode_id = Column(Integer, ForeignKey('episodes.id'), nullable=True)
    updated_at = Column(Text)

    # Связи с другими таблицами
    user = relationship("User", back_populates="view_requests")
    episode = relationship("Episode", back_populates="view_requests")

    def __repr__(self):
        return f'<ViewRequest(user_id={self.user_id}, episode_id={self.episode_id})>'  # noqa: E501