"""Certificate authenticated web server."""
from datetime import datetime
import cStringIO
import cherrypy
from cherrypy.lib.static import serve_fileobj
from sql.utils import db_session
from sql.tables import Services, ParametricJobs, Users, Requests
import csv

MINS = 60
SERVICE_COLOUR_MAP = {'up': 'brightgreen',
                      'down': 'red',
                      'unknown': 'lightgrey',
                      'stuck%3F': 'yellow'}  # %3F = ?


class HTMLPageServer(object):
    """The Web server."""

    def __init__(self, template_env):
        """Initialisation."""
        self.template_env = template_env

    @cherrypy.expose
    def index(self):
        """Return the index page."""
        data = {'user': cherrypy.request.verified_user}
        data['index_script'] = self.template_env.get_template('javascript/index.js')\
                                                .render(data)
        with db_session() as session:
            monitoringd = session.query(Services).filter(Services.name == 'monitoringd').one_or_none()
            if monitoringd is None:
                data.update({'monitoringd_status': 'Not in DB!', 'monitoringd_status_colour': 'red'})
                return self.template_env.get_template('html/index.html').render(data)

            nonmonitoringd_services = session.query(Services).filter(Services.name != 'monitoringd').all()
            out_of_date = (datetime.now() - monitoringd.timestamp).total_seconds() > 30. * MINS
            if monitoringd.status == 'down' or out_of_date:
                nonmonitoringd_services = (Services(name=service.name, status='unknown')
                                           for service in nonmonitoringd_services)
                if monitoringd.status != 'down':
                    monitoringd = Services(name=monitoringd.name, status='stuck%3F')  # %3F = ?

            data.update({'monitoringd_status': monitoringd.status,
                         'monitoringd_status_colour': SERVICE_COLOUR_MAP[monitoringd.status]})
            for service in nonmonitoringd_services:
                data.update({service.name + '_status': service.status,
                             service.name + '_status_colour': SERVICE_COLOUR_MAP[service.status]})
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
