"""Requests service."""
import os
import json
from datetime import datetime
from collections import namedtuple
import cherrypy
import html
from apache_utils import name_from_dn
from sqlalchemy_utils import create_db, db_session
from tables import Requests, Users, ParametricJobs

COLUMNS = ['id', 'request_date', 'sim_lead', 'status', 'description']
SelectedMacro = namedtuple('SelectedMacro', ('path', 'name', 'njobs', 'nevents', 'seed', 'status', 'output'))

class RequestsDB(object):
    """
    RequestsDB Service.

    Service for checking the requests in the LZProd DB and for returning
    a given row.
    """

    exposed = True

    def __init__(self, dburl):
        """Initialisation."""
        self.dburl = dburl
        create_db(dburl)

    def GET(self, reqid=None):  # pylint: disable=C0103
        """REST Get method."""
        print "IN GET: reqid=(%s)" % reqid
        requester = cherrypy.request.verified_user

        with db_session(self.dburl) as session:
            if reqid is None:
                if not requester.admin:
                    query = session.query(Requests.id,
                                          Requests.request_date,
                                          Requests.sim_lead,
                                          Requests.status,
                                          Requests.description)\
                                   .filter(Requests.requester_id == requester.id)
                    return json.dumps({'data': [dict(zip(COLUMNS, request))
                                                for request in query.all()]})
                query = session.query(Requests.id,
                                      Requests.request_date,
                                      Requests.sim_lead,
                                      Requests.status,
                                      Requests.description,
                                      Users.dn)\
                               .join(Users, Requests.requester_id == Users.id)
                data = []
                for request in query.all():
                    tmp = dict(zip(COLUMNS, request))
                    tmp['requester'] = name_from_dn(request.dn)
                    data.append(tmp)

                return json.dumps({'data': data})

            table = html.HTML().table(border='1')
            request = session.query(Requests).filter(Requests.id == reqid).first()
            if request is not None:
                for colname, value in request.iteritems():
                    row = table.tr()
                    row.td(colname)
                    row.td(str(value))
        return str(table)

    def POST(self, **kwargs):  # pylint: disable=C0103
        """REST Post method."""
        print "IN POST", kwargs
        kwargs['request_date'] = datetime.now().strftime('%d/%m/%Y')
        kwargs['status'] = 'Requested'
        selected_macros = kwargs.pop('selected_macros', [])
        if not isinstance(selected_macros, list):
            selected_macros = [selected_macros]



        with db_session(self.dburl) as session:
            request = Requests(requester_id=cherrypy.request.verified_user.id, request_date=kwargs['request_date'], source=kwargs['source'], detector=kwargs['detector'], sim_lead=kwargs['sim_lead'], status=kwargs['status'], description=kwargs['description'])
            session.add(request)
            session.flush()
            session.refresh(request)

            macros = []
            for macro in selected_macros:
                path, njobs, nevents, seed = macro.split()
                macros.append(ParametricJobs(request_id=request.id, status="Requested", macro=path, tag=kwargs['tag'], app=kwargs.get('app'), fastnest_version=kwargs.get('fastnest_version'), reduction_version=kwargs.get('reduction_version'), der_version=kwargs.get('der_version'), lzap_version=kwargs.get('lzap_version'),
                                             outputdir_lfns=[], njobs=njobs, nevents=nevents, seed=seed, app_version=kwargs.get('app_version'),
                                           dirac_jobs={}))

            session.add_all(macros)
        return self.GET()

    def PUT(self, reqid, **kwargs):  # pylint: disable=C0103
        """REST Put method."""
        print "IN PUT: reqid=(%s)" % reqid, kwargs
        requester = cherrypy.request.verified_user

        with db_session(self.dburl) as session:
            query = session.query(Requests).filter(Requests.id == reqid)
            if not requester.admin:
                query = query.filter(Requests.requester_id == requester.id)
            query.update(kwargs)

    def DELETE(self, reqid):  # pylint: disable=C0103
        """REST Delete method."""
        print "IN DELETE: reqid=(%s)" % reqid

        if cherrypy.request.verified_user.admin:
            with db_session(self.dburl) as session:
                session.query(Requests)\
                       .filter(Requests.id == reqid)\
                       .delete(synchronize_session=False)
        return self.GET()
