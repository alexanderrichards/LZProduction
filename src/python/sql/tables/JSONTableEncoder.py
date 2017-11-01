"""JSON Utilities Module."""
import json
from .SQLTableBase import SQLTableBase


class JSONTableEncoder(json.JSONEncoder):
    """JSON encoder for SQLAlchemy tables."""

    def default(self, obj):
        """Override base default method."""
        if isinstance(obj, SQLTableBase):
            return dict(obj, status=obj.status.name)
        if isinstance(obj, datetime):
            return obj.isoformat(' ')
        return super(SQLAlchemyTableEncoder, self).default(obj)
