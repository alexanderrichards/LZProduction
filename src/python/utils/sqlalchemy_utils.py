"""
SQLAlchemy utility module.

Contains helper classes and functions for working
with SQLAlchemy.
"""
import logging
from abc import ABCMeta
from collections import Mapping
from inspect import getmembers
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.declarative.api import DeclarativeMeta

logger = logging.getLogger(__name__)


class DeclarativeABCMeta(DeclarativeMeta, ABCMeta):
    pass


class _IterableBase(Mapping):
    """
    Iterable base class.

    A base class that provides the functionality of
    being able to iterate over the instrumented attributes
    of an SQLAlchemy declarative base.
    """

    @classmethod
    def attributes(cls):
        """Get an iterator over instrumented attributes."""
        for name, _ in getmembers(cls,
                                  lambda value: isinstance(value, InstrumentedAttribute)):
            yield name

    def __iter__(self):
        """Get an iterator over instrumented attributes."""
        return self.__class__.attributes()

    def __getitem__(self, item):
        """Access instrumented attributes as a dict."""
        if not item in self:
            raise KeyError("Invalid attribute name: %s" % item)
        return getattr(item)

    def __len__(self):
        return len(list(self))

SQLTableBase = declarative_base(cls=_IterableBase,  # pylint: disable=C0103
                                metaclass=DeclarativeABCMeta)


def create_db(url):
    """
    Create a DB.

    Creates a DB from a given url.
    """
    engine = create_engine(url)
    SQLTableBase.metadata.create_all(engine)
    SQLTableBase.metadata.bind = engine


def setup_session(url):
    engine = create_engine(url)
    SQLTableBase.metadata.create_all(engine)
    SQLTableBase.metadata.bind = engine
    return scoped_session(sessionmaker(bind=engine))


@contextmanager
def nonexpiring(scoped_session):
    try:
        yield scoped_session(expire_on_commit=False)
        scoped_session.commit()
    except:
        logger.exception("Problem with DB session, rolling back.")
        scoped_session.rollback()
        raise
    finally:
        scoped_session.remove()


@contextmanager
def reraising(scoped_session):
    try:
        yield scoped_session()
        scoped_session.commit()
    except:
        logger.exception("Problem with DB session, rolling back.")
        scoped_session.rollback()
        raise
    finally:
        scoped_session.remove()


@contextmanager
def continuing(scoped_session):
    try:
        yield scoped_session()
        scoped_session.commit()
    except:
        logger.exception("Problem with DB session, rolling back.")
        scoped_session.rollback()
    finally:
        scoped_session.remove()


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
