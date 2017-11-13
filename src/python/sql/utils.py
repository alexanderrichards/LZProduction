"""
SQLAlchemy utility module.

Contains helper classes and functions for working
with SQLAlchemy.
"""
import logging
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session


logger = logging.getLogger(__name__)  # pylint: disable=invalid-name

SESSION = scoped_session(sessionmaker())


def rebind_session(engine):
    """Rebind the scoped session's engine."""
    SESSION.remove()
    SESSION.configure(bind=engine)

@contextmanager
def db_session(url=None, reraise=True):
    """Provide a transactional scope around a series of operations."""
    if url is not None:
        rebind_session(create_engine(url))

    try:
        yield SESSION()
        SESSION.commit()
    except:  # pylint: disable=bare-except
        logger.exception("Problem with DB session, rolling back.")
        SESSION.rollback()
        if reraise:
            raise
    finally:
        SESSION.remove()
