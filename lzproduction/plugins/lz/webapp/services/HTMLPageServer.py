"""Certificate authenticated web server."""
import logging
import pkg_resources
import cherrypy
import jinja2
from lzproduction.webapp.services import HTMLPageServerBase

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name
MINS = 60
class HTMLPageServer(HTMLPageServerBase):
    """The Web server."""


    @cherrypy.expose
    def index_script(self):
        template_resources = pkg_resources.resource_filename('lzproduction',
                                                             'plugins/lz/resources/templates')
        template_env = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath=template_resources))
        template_env.get_template('javascript/index.js').render({'user': cherrypy.request.verified_user})

    @cherrypy.expose
    def newrequest_script(self):
        script = pkg_resources.resource_filename('lzproduction',
                                                             'plugins/lz/resources/static/javascript/newrequests.js')
        with open(script, 'rb') as file_:
            return file_.read()

    @cherrypy.expose
    def newrequest_content(self):
        content = pkg_resources.resource_filename('lzproduction',
                                                             'plugins/lz/resources/static/html/newrequest.html')
        with open(content, 'rb') as file_:
            return file_.read()

