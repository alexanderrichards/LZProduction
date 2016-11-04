"""Certificate authenticated web server."""
import os
import cherrypy
import jinja2


class CertWebServer(object):
    """The Web server."""

    def __init__(self, html_root):
        """Initialisation."""
        self.html_root = html_root
        self.template_env = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath=html_root))

    @cherrypy.expose
    def index(self):
        """Return the index page."""
        return self.template_env.get_template('index.html').render({'user': cherrypy.request.verified_user})


    @cherrypy.expose
    def newrequest(self):
        """Return the new requests page."""
        with open(os.path.join(self.html_root, 'newrequest.html')) as new_request:
            return new_request.read()
