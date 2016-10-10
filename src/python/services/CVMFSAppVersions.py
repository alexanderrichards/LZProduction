"""CVMFS Servcice."""
import os
import re
import html
from natsort import natsorted

version_re = re.compile(r"^release-(\d{1,3}\.\d{1,3}\.\d{1,3})$")


class CVMFSAppVersions(object):
    """
    CVMFS App Version checking service.

    CVMFS Service to get the list of versions available
    on CVMFS for a given app.
    """

    exposed = True

    def __init__(self, cvmfs_root, valid_apps):
        """Initialise."""
        self.cvmfs_root = cvmfs_root
        self.valid_apps = valid_apps

    def GET(self, id=None):
        """REST GET method."""
        print "IN AppVersion GET: id=(%s)" % id
        if id not in self.valid_apps:
            print "Invalid app type %s" % id
            return ''
        h = html.HTML()
        _, dirs, _ = os.walk(os.path.join(self.cvmfs_root, id)).next()
        for d in natsorted(dirs):
            for version in version_re.findall(d):
                h.option(version)
        return str(h)
