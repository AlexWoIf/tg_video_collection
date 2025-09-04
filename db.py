from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base


class Database:
    def __init__(self, db_url, echo=False):
        """
        Initialize the database connection.

        Args:
            db_url (str): URL for connecting to the database
            echo (bool): Log SQL queries (for debugging)
        """
        self.engine = create_engine(
            db_url,
            echo=echo,
            pool_size=10,
            max_overflow=20,
            pool_recycle=3600,
            pool_pre_ping=True
        )
        
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        self.Base = Base

    def init_db(self):
        """
        Initialize the database.
        Creates tables based on models if necessary.
        """
        self.Base.metadata.create_all(bind=self.engine)

    @contextmanager
    def session(self):
        """
        Context manager for working with the database session.
        Automatically handles commit, rollback, and session closure.

        Usage:
            with database.session() as session:
                # work with the session
                session.add(some_object)
                # commit happens automatically upon successful exit of the block
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_session(self):
        """
        Get a database session (without context manager).
        Requires manual session closing.

        Returns:
            Session: Database session
        """
        return self.SessionLocal()
