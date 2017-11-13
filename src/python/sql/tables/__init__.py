"""
Initialise module.

Load all tables at module scope.
"""
from sqlalchemy import create_engine
from .SQLTableBase import SQLTableBase
from .Users import Users
from .Services import Services
from .ParametricJobs import ParametricJobs
from .Requests import Requests
from .DiracJobs import DiracJobs
from ..utils import rebind_session

def create_all_tables(url):
    """Create all tables of type Base."""
    engine = create_engine(url)
    SQLTableBase.metadata.create_all(bind=engine)
    rebind_session(engine)

