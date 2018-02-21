"""CVMFS Servcice."""
import os
import re
import logging
import cherrypy
import html
from natsort import natsorted

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name
VERSION_RE = re.compile(r"^release-(\d{1,3}\.\d{1,3}\.\d{1,3})$")


@cherrypy.popargs('appid')
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
    def index(self, appid=None):
        """Return the index page."""
        print "IN CVMFSAppVersion: appid=(%s)" % appid
        if appid not in self.valid_apps:
            print "Invalid app type %s" % appid
            return ''
        html_ = html.HTML()
        dirs = []
        try:
            _, dirs, _ = os.walk(os.path.join(self.cvmfs_root, appid)).next()
        except StopIteration:
            logger.error("Couldn't access CVMFS dir: %s",
                         os.path.join(self.cvmfs_root, appid))

        for dir_ in natsorted(dirs, reverse=True):
            for version in VERSION_RE.findall(dir_):
                html_.option(version)
        return str(html_)
