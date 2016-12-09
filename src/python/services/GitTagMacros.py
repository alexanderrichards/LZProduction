"""Git tag service."""
import os
import threading
import cherrypy
import html
import pylru
from git import Git, Repo
from natsort import natsorted


@cherrypy.popargs('tagid')
class GitTagMacros(object):
    """
    Git tag checking service.

    Service for reporting the macros associated to a given git tag
    or returning list of available tags.
    """

    def __init__(self, repo, git_dir):
        """Initialisation."""
        if not os.path.isdir(git_dir):
            Git().clone(repo, git_dir)
        self.git_dir = git_dir
        self.fs_lock = threading.Lock()
        self.tag_cache = pylru.lrucache(50)

    @cherrypy.expose
    def index(self, tagid=None):
        """Return the index page."""
        print "IN GitTagMacro: tagid=(%s)" % tagid
        if tagid in self.tag_cache:
            return self.tag_cache[tagid]

        html_ = html.HTML()
        if tagid is None:
            tags = natsorted(tag.name for tag in Repo(self.git_dir).tags)
            for tag in tags:
                html_.option(tag)
            # print "returning:", str(html_)
            return str(html_)

        with self.fs_lock:
            Git(self.git_dir).checkout(tagid)
            for root, _, files in os.walk(os.path.join(self.git_dir, 'BackgroundMacros')):
                for file_ in files:
                    if file_.endswith('.mac'):
                        html_.option(file_, path=os.path.relpath(root, self.git_dir))
            # print "returning:", str(ret_html)
            self.tag_cache[tagid] = str(html_)
            return str(html_)
