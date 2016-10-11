"""Git tag service."""
import os
import threading
import html
import pylru
from git import Git, Repo
from natsort import natsorted


class GitTagMacros(object):
    """
    Git tag checking service.

    Service for reporting the macros associated to a given git tag
    or returning list of available tags.
    """

    exposed = True

    def __init__(self, repo, git_dir):
        """Initialisation."""
        if not os.path.isdir(git_dir):
            Git().clone(repo, git_dir)
        self.git_dir = git_dir
        self.fs_lock = threading.Lock()
        self.tag_cache = pylru.lrucache(50)

#    @pylru.lrudecorator(50)  # don't want to cache list of tags where tagid = None
    def GET(self, tagid=None):
        """REST Get method."""
        print "IN GET: tagid=(%s)" % tagid
        if tagid in self.tag_cache:
            return self.tag_cache[tagid]

        h = html.HTML()
        if tagid is None:
            tags = natsorted(tag.name for tag in Repo(self.git_dir).tags)
            for tag in tags:
                h.option(tag)
            # print "returning:", str(h)
            return str(h)

        with self.fs_lock:
            Git(self.git_dir).checkout(tagid)
            for root, _, files in os.walk(os.path.join(self.git_dir, 'BackgroundMacros')):
                for f in files:
                    if f.endswith('.mac'):
                        h.option(f, path=os.path.relpath(root, self.git_dir))
            # print "returning:", str(h)
            self.tag_cache[tagid] = str(h)
            return str(h)
