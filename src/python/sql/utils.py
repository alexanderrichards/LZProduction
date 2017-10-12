"""
SQLAlchemy utility module.

Contains helper classes and functions for working
with SQLAlchemy.
"""
import logging
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .SQLTableBase import SQLTableBase


logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


def create_all_tables(url):
    """Create all tables of type Base."""
    engine = create_engine(url)
    SQLTableBase.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)


@contextmanager
def scoped_session(session_factory, reraise=True):
    """Provide a transactional scope around a series of operations."""
    session = session_factory()
    try:
        yield session
        session.commit()
    except:
        logger.exception("Problem with DB session, rolling back.")
        session.rollback()
        if reraise:
            raise
    finally:
        session.close()
