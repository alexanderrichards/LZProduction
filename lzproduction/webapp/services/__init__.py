"""
Initialise module.

Load all services at module scope.
"""
import pkg_resources

from .Admins import Admins
HTMLPageServer = pkg_resources.load_entry_point('lzproduction', 'services.htmlpageserver', 'lz')