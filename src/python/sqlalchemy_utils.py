"""
SQLAlchemy utility module.

Contains helper classes and functions for working
with SQLAlchemy.
"""
import logging
from inspect import getmembers
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.ext.declarative import declarative_base

logger = logging.getLogger(__name__)


class _IterableBase(object):
    """
    Iterable base class.

    A base class that provides the functionality of
    being able to iterate over the instrumented attributes
    of an SQLAlchemy declarative base.
    """

    def __iter__(self):
        """Get an iterator over instrumented attributes."""
        for name, _ in getmembers(self.__class__,
                                  lambda value: isinstance(value, InstrumentedAttribute)):
            yield name, getattr(self, name)

    def __getitem__(self, item):
        """Access instrumented attributes as a dict."""
        instrumented_attrs = dict(iter(self))
        return instrumented_attrs[item]

SQLTableBase = declarative_base(cls=_IterableBase)  # pylint: disable=C0103


def create_db(url):
    """
    Create a DB.

    Creates a DB from a given url.
    """
    SQLTableBase.metadata.create_all(create_engine(url))


@contextmanager
def db_session(url):
    """
    DB Session context.

    Returns a DB session context which automatically rolls back on
    any exception as well as automatically committing if no exception is
    thrown.

    Args:
        url (str): The DB access URL.
    """
    engine = create_engine(url)
    # Bind the engine to the metadata of the Base class so that the
    # declaratives can be accessed through a DBSession instance
    SQLTableBase.metadata.bind = engine

    session = sessionmaker(bind=engine)()
    try:
        yield session
        session.commit()
    except:
        logger.error("Problem with DB session, rolling back.")
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def db_subsession(session):
    """
    DB sub-session context.

    Returns a DB sub-session context which automatically rolls back on
    any exception as well as automatically committing if no exception
    is thrown. Note that this context swallows any exception allowing
    any other DB sub-sessions to carry on even if this one fails.

    Args:
        session (SQLAlchemy DB session): The open DB session
    """
    try:
        with session.begin_nested():
            yield
    except:
        logger.exception("Problem with DB sub-session, rolling back.")


__all__ = ('SQLTableBase', 'create_db', 'db_session', 'db_subsession')
