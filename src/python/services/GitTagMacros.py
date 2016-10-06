import os
import threading
import html
import pylru
from git import Git, Repo
from natsort import natsorted

class GitTagMacros(object):
    exposed = True

    def __init__(self, repo, git_dir):
        if not os.path.isdir(git_dir):
            Git().clone(repo, git_dir)
        self.git_dir = git_dir
        self.fs_lock = threading.Lock()
        self.tag_cache = pylru.lrucache(50)

#    @pylru.lrudecorator(50)  # don't want to cache list of tags where id = None
    def GET(self, id=None):
        print "IN GET: id=(%s)" % id
        if id in self.tag_cache:
            return self.tag_cache[id]

        h=html.HTML()
        if id is None:
            tags = natsorted(tag.name for tag in Repo(self.git_dir).tags)
            for tag in tags:
                h.option(tag)
            #print "returning:", str(h)
            return str(h)

        with self.fs_lock:
            Git(self.git_dir).checkout(id)
            for root, dirs, files in os.walk(os.path.join(self.git_dir,'BackgroundMacros')):
                for f in files:
                    if f.endswith('.mac'):
                        h.option(f, path=os.path.relpath(root, self.git_dir))
            #print "returning:", str(h)
            self.tag_cache[id] = str(h)
            return str(h)
