"""Certificate authenticated web server."""
import logging
import pkg_resources
import cherrypy
from lzproduction.webapp.services import HTMLPageServerBase

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name
MINS = 60
class HTMLPageServer(HTMLPageServerBase):
    """The Web server."""


    @cherrypy.expose
    def index_includes(self):
        return pkg_resources.load_entry_point('lzproduction', 'javascript.index_includes',
                                                        'lz')()

    @cherrypy.expose
    def newrequest_script(self):
        self.template_env.get_template('html/newrequest.html').render()

    @cherrypy.expose
    def newrequest_content(self):
        pass
