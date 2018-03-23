"""CVMFS Servcice."""
import os
import re
import logging
import cherrypy
import html
from natsort import natsorted

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name
VERSION_RE = re.compile(r"^[vV].*$")


@cherrypy.popargs('appid', 'version', 'blah', 'la')
class CVMFSAppVersions(object):
    """
    CVMFS App Version checking service.

    CVMFS Service to get the list of versions available
    on CVMFS for a given app.
    """

    def __init__(self, cvmfs_root, valid_apps):
        """Initialise."""
        self.cvmfs_root = cvmfs_root
        self.valid_apps = valid_apps


    @cherrypy.expose
    def index(self, appid=None, version=None, blah=None, la=None):
        """Return the index page."""
        print "IN CVMFSAppVersion: appid=(%s)" % appid
        logger.error("HERE: %s '%s'", appid, ' '.join([str(version), str(blah), str(la)]))
        #if appid not in self.valid_apps:
        #    print "Invalid app type %s" % appid
        #    return ''
        html_ = html.HTML()
        dirs = []
        try:
            path = '/'.join(i for i in (appid, version, blah, la) if i is not None)
            _, dirs, files = os.walk(os.path.join(self.cvmfs_root, path)).next()
        except StopIteration:
            logger.error("Couldn't access CVMFS dir: %s",
                         os.path.join(self.cvmfs_root, appid))

        if version is not None:
            for file_ in natsorted(files):
                html_.option(file_)
        else:
            for dir_ in natsorted(dirs, reverse=True):
                html_.option(dir_)
        return str(html_)
