"""DIRAC utility module."""
import logging
import xmlrpclib
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@contextmanager
def dirac_server(url):
    """RPC context for communication with dirac environment API."""
    try:
        yield xmlrpclib.ServerProxy(url)
    except xmlrpclib.ProtocolError:
        logger.exception("Protocol error reaching server.")
    except xmlrpclib.Fault:
        logger.exception("Exception raised in server.")
