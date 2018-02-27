"""
Initialise module.

Load all tables at module scope.
"""
import pkg_resources
from sqlalchemy import create_engine
from .SQLTableBase import SQLTableBase
from .Users import Users
from .Services import Services
from .ParametricJobsBase import ParametricJobsBase
from .RequestsBase import RequestsBase
from .DiracJobs import DiracJobs
from ..utils import rebind_session


def create_all_tables(url):
    """Create all tables of type Base."""
    engine = create_engine(url)
    SQLTableBase.metadata.create_all(bind=engine)
    rebind_session(engine)

ParametricJobs = pkg_resources.load_entry_point('lzproduction', 'tables.parametricjobs', 'lz')
Requests = pkg_resources.load_entry_point('lzproduction', 'tables.requests', 'lz')