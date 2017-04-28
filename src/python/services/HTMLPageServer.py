"""Certificate authenticated web server."""
from datetime import datetime
import cherrypy
from cherrypy.lib.static import serve_fileobj
from sqlalchemy_utils import create_db, db_session
from apache_utils import name_from_dn
from tables import Services, ParametricJobs, Users, Requests
import csv, cStringIO

MINS = 60
SERVICE_COLOUR_MAP = {'up': 'brightgreen',
                      'down': 'red',
                      'unknown': 'lightgrey',
                      'stuck%3F': 'yellow'}  # %3F = ?


class HTMLPageServer(object):
    """The Web server."""

    def __init__(self, dburl, template_env):
        """Initialisation."""
        self.dburl = dburl
        create_db(dburl)
        self.template_env = template_env

    @cherrypy.expose
    def index(self):
        """Return the index page."""
        data = {'user': cherrypy.request.verified_user}
        data['index_script'] = self.template_env.get_template('javascript/index.js')\
                                                .render(data)
        with db_session(self.dburl) as session:
            gangad = session.query(Services).filter(Services.name == 'gangad').one_or_none()
            if gangad is None:
                data.update({'gangad_status': 'Not in DB!', 'gangad_status_colour': 'red'})
                return self.template_env.get_template('html/index.html').render(data)

            nongangad_services = session.query(Services).filter(Services.name != 'gangad').all()
            out_of_date = (datetime.now() - gangad.timestamp).total_seconds() > 30. * MINS
            if gangad.status == 'down' or out_of_date:
                nongangad_services = (Services(name=service.name, status='unknown')
                                      for service in nongangad_services)
                if gangad.status != 'down':
                    gangad = Services(name=gangad.name, status='stuck%3F')  # %3F = ?

            data.update({'gangad_status': gangad.status,
                         'gangad_status_colour': SERVICE_COLOUR_MAP[gangad.status]})
            for service in nongangad_services:
                data.update({service.name + '_status': service.status,
                             service.name + '_status_colour': SERVICE_COLOUR_MAP[service.status]})
        return self.template_env.get_template('html/index.html').render(data)

    @cherrypy.expose
    def details(self, id):
        with db_session(self.dburl) as session:
            macros = session.query(ParametricJobs)\
                            .filter(ParametricJobs.request_id == id)\
                            .all()
            if not macros:
                return "Error: No macro information!"
            return self.template_env.get_template('html/subtables.html').render({'macros': macros})
    
    @cherrypy.expose
    def csv_export(self, filter=None):
        with db_session(self.dburl) as session:
            query = session.query(Requests.id,
                                  Users.dn,
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
                                  ParametricJobs.reduced_lfns)\
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
                tmp['requester'] = name_from_dn(tmp['requester'])
		rows.append(tmp)
            writer.writeheader()
    	    for row in rows:
                 writer.writerow(
                     dict(
                        (k, v.encode('utf-8') if type(v) is unicode else v) for k, v in row.iteritems()
                     )
                 )
            csvfile.seek(0)
            return serve_fileobj(csvfile, disposition='attachment', content_type='text/csv', name='requests.csv')
 

