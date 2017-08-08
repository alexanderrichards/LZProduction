"""Requests service."""
import os
import json
import logging
from datetime import datetime
from collections import namedtuple
import cherrypy
import html
from utils.apache_utils import name_from_dn
from utils.sqlalchemy_utils import create_db, db_session
from tables import Requests, Users, ParametricJobs

logger = logging.getLogger(__name__)
COLUMNS = ['id', 'request_date', 'sim_lead', 'status', 'description']
SelectedMacro = namedtuple('SelectedMacro', ('path', 'name', 'njobs', 'nevents', 'seed', 'status', 'output'))

def masked_dict(d, mask):
    mask = tuple(mask)  # incase it's a generator/iterator
    return {k: v for k, v in d.iteritems() if k in mask}

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
        selected_macros = kwargs.pop('selected_macros', [])
        if not isinstance(selected_macros, list):
            selected_macros = [selected_macros]

        with db_session(self.dburl) as session:
            request = Requests(requester_id=cherrypy.request.verified_user.id,
                               request_date=datetime.now().strftime('%d/%m/%Y'),
                               status='Requested',
                               **masked_dict(kwargs, Requests.attributes()))
            session.add(request)
            session.flush()
            session.refresh(request)

            macros = []
            for macro in selected_macros:
                path, njobs, nevents, seed = macro.split()
                macros.append(ParametricJobs(request_id=request.id,
                                             status="Requested",
                                             macro=path,
                                             njobs=njobs,
                                             nevents=nevents,
                                             seed=seed,
                                             dirac_jobs=[],
                                             reschedule=False,
                                             **masked_dict(kwargs, ParametricJobs.attributes())))

            if set(['reduction_lfn_inputdir', 'der_lfn_inputdir', 'lzap_lfn_inputdir']).intersection(kwargs.iterkeys()):
                macros.append(ParametricJobs(request_id=request.id,
                                             status="Requested",
                                             dirac_jobs=[],
                                             reschedule=False,
                                             **masked_dict(kwargs, ParametricJobs.attributes())))

            session.add_all(macros)
            if not macros:
                logger.warning("No ParametricJobs added to the DB.")
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
                session.query(ParametricJobs)\
                       .filter(ParametricJobs.request_id == reqid)\
                       .delete(synchronize_session=False)
        return self.GET()
