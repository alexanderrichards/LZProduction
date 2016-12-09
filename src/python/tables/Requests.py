"""Requests Table."""
from sqlalchemy import Column, Integer, String, Text, ForeignKeyConstraint
from sqlalchemy_utils import SQLTableBase


class Requests(SQLTableBase):
    """Requests SQL Table."""

    __tablename__ = 'requests'
    id = Column(Integer, primary_key=True)  # pylint: disable=C0103
    requester_id = Column(Integer, nullable=False)
    request_date = Column(String(250), nullable=False)
    source = Column(String(250), nullable=False)
    detector = Column(String(250), nullable=False)
    tag = Column(String(250), nullable=False)
    app = Column(String(250), nullable=False)
    app_version = Column(String(250))
    request = Column(String(250))
    reduction_version = Column(String(250), nullable=False)
    sim_lead = Column(String(250), nullable=False)
    status = Column(String(250), nullable=False)
    timestamp = Column(String(250), nullable=False)
    description = Column(String(250), nullable=False)
    selected_macros = Column(Text())
    output_lfns = Column(Text())
    ForeignKeyConstraint(['requester_id'], ['users.id'])
