"""Certificate authenticated web server."""
import csv
import logging
import pkg_resources
from datetime import datetime
import cStringIO
import cherrypy
from cherrypy.lib.static import serve_fileobj
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from lzproduction.sql.utils import db_session
from lzproduction.sql.statuses import SERVICESTATUS
from lzproduction.sql.tables import Services, ParametricJobs, Users, Requests

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name
MINS = 60
#SERVICE_COLOUR_MAP = {SERVICESTATUS.Up: 'brightgreen',
#                      SERVICESTATUS.Down: 'red',
#                      SERVICESTATUS.Unknown: 'lightgrey',
#                      'stuck%3F': 'yellow'}  # %3F = ?


class HTMLPageServer(object):
    """The Web server."""

    def __init__(self, template_env):
        """Initialisation."""
        self.template_env = template_env

    @cherrypy.expose
    def index(self):
        """Return the index page."""
        data = {'user': cherrypy.request.verified_user, 'services': {}}
        with db_session() as session:
            nonmonitoringd_services = session.query(Services)\
                                             .filter(Services.name != 'monitoringd')\
                                             .all()
            try:
                monitoringd = session.query(Services).filter_by(name='monitoringd').one()
            except NoResultFound:
                logger.warning("Monitoring daemon 'monitoringd' service status not in DB.")
                monitoringd = Services(name='monitoringd', status=SERVICESTATUS.Unknown, timestamp=datetime.utcnow())
            except MultipleResultsFound:
                logger.error("Multiple monitoring daemon 'monitoringd' services found in DB.")
                monitoringd = Services(name='monitoringd', status=SERVICESTATUS.Unknown, timestamp=datetime.utcnow())
            session.expunge_all()

        data['services'].update({monitoringd.name: monitoringd.status})
        out_of_date = (datetime.now() - monitoringd.timestamp).total_seconds() > 30. * MINS
        if monitoringd.status is not SERVICESTATUS.Up or out_of_date:
            nonmonitoringd_services = (Services(name=service.name, status=SERVICESTATUS.Unknown, timestamp=datetime.utcnow())
                                       for service in nonmonitoringd_services)
        data['services'].update({service.name: service.status for service in nonmonitoringd_services})
        return self.template_env.get_template('index.html').render(data)

    @cherrypy.expose
    def newrequest(self):
        """New request dialog."""
        newrequest_filename = pkg_resources.resource_filename('lzproduction', 'plugins/lz/resources/html/newrequests.html')
        with open(newrequest_filename, 'rb') as newrequest_file:
            return self.template_env.get_template('newrequest.html')\
                                    .render({'new_request_content': newrequest_file.read()})

    @cherrypy.expose
    def webapp_script(self):
        """Return dynamic javascript for webapp."""
        return self.template_env.get_template('index.js')\
                                .render({'user': cherrypy.request.verified_user})


    @cherrypy.expose
    def csv_export(self):
        """Return .csv of Requests and ParametricJobs tables"""
        with db_session() as session:
            query = session.query(Requests.id,
                                  Users,
                                  Requests.request_date,
                                  Requests.sim_lead,
                                  Requests.description,
                                  Requests.detector,
                                  Requests.source,
                                  ParametricJobs.id,
                                  ParametricJobs.macro,
                                  ParametricJobs.app,
                                  ParametricJobs.app_version,
                                  ParametricJobs.njobs,
                                  ParametricJobs.nevents,
                                  ParametricJobs.seed,
                                  ParametricJobs.status,
                                  ParametricJobs.outputdir_lfns)\
                                  .join(ParametricJobs, Requests.id == ParametricJobs.request_id)\
                                  .join(Users, Users.id == Requests.requester_id)\

            if not query:
                return "Error: No data"
            rows = []
            header = ['request_id', 'requester', 'request_date', 'sim_lead', 'description', 'detector', 'source', 'job_id', 'macro', 'app', 'app_version', 'njobs', 'nevents', 'seed', 'job_status', 'lfn']
            csvfile = cStringIO.StringIO()
            writer = csv.DictWriter(csvfile, header)
        for request in query.all():
            tmp = dict(zip(header, request))
            tmp['requester'] = tmp['requester'].name
            rows.append(tmp)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                dict((k, v.encode('utf-8') if isinstance(v, unicode) else v) for k, v in row.iteritems())
            )
        csvfile.seek(0)
        return serve_fileobj(csvfile, disposition='attachment', content_type='text/csv', name='requests.csv')
