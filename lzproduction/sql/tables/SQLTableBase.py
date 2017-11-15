"""SQLAlchemy Base Table Module."""
import logging
from abc import ABCMeta
from collections import Mapping
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.declarative.api import DeclarativeMeta

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class DeclarativeABCMeta(DeclarativeMeta, ABCMeta):
    """
    Declarative abstract base metaclass.

    Metaclass combining the SQLAlchemy DeclarativeMeta
    with the ABCMeta giving us the ability to use abstract
    decorators etc.
    """

    pass


class ColumnsDescriptor(object):
    """Yield the column names."""

    def __get__(self, obj, cls):
        """Descriptor get."""
        for column in cls.__table__.columns:
            yield column.name

    def __set__(self, obj, value):
        """Descriptor set."""
        raise AttributeError("Read only attribute!")


class IterableBase(Mapping):
    """
    Iterable base class.

    A base class that provides the functionality of
    being able to iterate over the instrumented attributes
    of an SQLAlchemy declarative base.
    """

    # This we can get from the class as well as instance
    # unlike property
    columns = ColumnsDescriptor()

    def __iter__(self):
        """Get an iterator over instrumented attributes."""
        return self.columns

    def __getitem__(self, item):
        """Access instrumented attributes as a dict."""
        if item not in self.columns:
            raise KeyError("Invalid attribute name: %s" % item)
        return getattr(self, item)

    def __len__(self):
        return len(list(self.columns))

SQLTableBase = declarative_base(cls=IterableBase,  # pylint: disable=invalid-name
                                metaclass=DeclarativeABCMeta)



__all__ = ('SQLTableBase', )
