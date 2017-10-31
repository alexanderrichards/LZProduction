"""Certificate authenticated web server."""
import logging
from datetime import datetime
import cStringIO
import cherrypy
from cherrypy.lib.static import serve_fileobj
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sql.utils import db_session
from sql.statuses import SERVICESTATUS
from sql.tables import Services, ParametricJobs, Users, Requests
import csv

logger = logging.getLogger(__name__)
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
        data['index_script'] = self.template_env.get_template('javascript/index.js')\
                                                .render(data)
        with db_session() as session:
            nonmonitoringd_services = session.query(Services)\
                                             .filter(Services.name != 'monitoringd')\
                                             .all()
            try:
                monitoringd = session.query(Services).filter_by(name='monitoringd').one()
            except NoResultFound:
                logger.warning("Monitoring daemon 'monitoringd' service status not in DB.")
                monitoringd = Services(name='monitoringd', status=SERVICESTATUS.Unknown)
            except MultipleResultsFound:
                logger.error("Multiple monitoring daemon 'monitoringd' services found in DB.")
                monitoringd = Services(name='monitoringd', status=SERVICESTATUS.Unknown)

        data['services'].update({monitoringd.name: monitoringd.status})
        out_of_date = (datetime.now() - monitoringd.timestamp).total_seconds() > 30. * MINS
        if monitoringd.status is not SERVICESTATUS.Up or out_of_date:
            nonmonitoringd_services = (Services(name=service.name, status=SERVICESTATUS.Unknown)
                                       for service in nonmonitoringd_services)
        data['services'].update({service.name: service.status for service in nonmonitoringd_services})
        return self.template_env.get_template('html/index.html').render(data)

    @cherrypy.expose
    def details(self, request_id):
        """Return details of a request."""
        with db_session() as session:
            macros = session.query(ParametricJobs)\
                            .filter(ParametricJobs.request_id == request_id)\
                            .all()
            if not macros:
                return "Error: No macro information!"
            return self.template_env.get_template('html/subtables.html').render({'macros': macros})

    @cherrypy.expose
    def reschedule(self, job_id):
        """Reschedule a given job."""
        with db_session() as session:
            macro = session.query(ParametricJobs)\
                           .filter(ParametricJobs.id == int(job_id))\
                           .one_or_none()
            if macro is not None:
                macro.reschedule = True
                macro.status = "Submitted"
                request = session.query(Requests)\
                                 .filter(Requests.id == macro.request_id)\
                                 .one_or_none()
                if request is not None:
                    request.status = "Submitted"

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
