import os
import re
import html
from natsort import natsorted

version_re = re.compile(r"^release-(\d{1,3}\.\d{1,3}\.\d{1,3})$")
class CVMFSAppVersions(object):
    exposed = True

    def __init__(self, cvmfs_root, valid_apps):
        self.cvmfs_root = cvmfs_root
        self.valid_apps = valid_apps

    def GET(self, id=None):
        print "IN AppVersion GET: id=(%s)" % id
        if id not in self.valid_apps:
            print "Invalid app type %s" % id
            return ''
        h=html.HTML()
        _, dirs, _ = os.walk(os.path.join(self.cvmfs_root, id)).next()
        for d in natsorted(dirs):
            for version in version_re.findall(d):
                h.option(version)
        return str(h)
