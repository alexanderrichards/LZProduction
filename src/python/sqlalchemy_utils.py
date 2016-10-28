"""
SQLAlchemy utility module.

Contains helper classes and functions for working
with SQLAlchemy.
"""
from inspect import getmembers
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.ext.declarative import declarative_base


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

SQLTableBase = declarative_base(cls=_IterableBase)


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
        session.rollback()
        raise
    finally:
        session.close()

__all__ = ('SQLTableBase', 'create_db', 'db_session')
