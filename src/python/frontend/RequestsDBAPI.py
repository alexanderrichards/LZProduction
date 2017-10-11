"""Requests Database RESTful API."""
import json
import logging
from datetime import datetime
from collections import Mapping
import cherrypy
from sql.utils import create_all_tables, session_scope
from sql.tables import Requests, Users, ParametricJobs

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name

def subdict(dct, seq, **kwargs):
    """Sub dict."""
    # tuple(seq) as seq might be iterator
    # return {k: v for k, v in dct.iteritems() if k in tulpe(seq)}

    # This might be faster if dct is large as doesn't have to iterate through it.
    # also works natively with seq being an iterator, no tuple initialisation
    return dict({key: dct[key] for key in seq if key in dct}, **kwargs)


class DatetimeMappingEncoder(json.JSONEncoder):
    """JSON encoder for types Datetime and Mapping."""

    def default(self, obj):
        """Override base default method."""
        if isinstance(obj, Mapping):
            return dict(obj)
        if isinstance(obj, datetime):
            return obj.isoformat(' ')
        return super(DatetimeMappingEncoder, self).default(obj)


class RequestsDBAPI(object):
    """
    RequestsDB Service.

    Service for checking the requests in the LZProd DB and for returning
    a given row.
    """

    exposed = True

    def __init__(self, dburl):
        """Initialisation."""
        self.dburl = create_all_tables(dburl)

    def GET(self, reqid=None):  # pylint: disable=invalid-name
        """REST Get method."""
        logger.debug("In GET: reqid = %s", reqid)
        requester = cherrypy.request.verified_user

        with session_scope(self.dburl) as session:
            user_requests = session.query(Requests).filter_by(requester_id=requester.id)
            # Get all requests.
            if reqid is None:
                if requester.admin:
                    all_requests = session.query(Requests, Users)\
                                          .join(Users, Requests.requester_id == Users.id)\
                                          .all()
                    # could make a specialised encoder for this.
                    return json.dumps({'data': [dict(request, requester=user.name)
                                                for request, user in all_requests]},
                                      cls=DatetimeMappingEncoder)
                return json.dumps({'data': user_requests.all()}, cls=DatetimeMappingEncoder)

            # Get specific request.
            if requester.admin:
                user_requests = session.query(Requests)
            request = user_requests.filter_by(id=reqid).first()
            return json.dumps({'data': request}, cls=DatetimeMappingEncoder)




    def POST(self, **kwargs):  # pylint: disable=invalid-name
        """REST Post method."""
        logger.debug("In POST: kwargs = %s", kwargs)
        selected_macros = kwargs.pop('selected_macros', [])
        if not isinstance(selected_macros, list):
            selected_macros = [selected_macros]

        with session_scope(self.dburl) as session:
            request = Requests(**subdict(kwargs, Requests.columns,
                                         requester_id=cherrypy.request.verified_user.id,
                                         request_date=datetime.now().strftime('%d/%m/%Y'),
                                         status='Requested'))
            session.add(request)
            session.flush()
            session.refresh(request)

            parametricjobs = []
            if 'app' in kwargs:
                for macro in selected_macros:
                    path, njobs, nevents, seed = macro.split()
                    parametricjobs.append(ParametricJobs(**subdict(kwargs, ParametricJobs.columns,
                                                                   request_id=request.id,
                                                                   status="Requested",
                                                                   macro=path,
                                                                   njobs=njobs,
                                                                   nevents=nevents,
                                                                   seed=seed,
                                                                   dirac_jobs=[],
                                                                   reschedule=False)))
            elif kwargs.viewkeys() & {'reduction_lfn_inputdir', 'der_lfn_inputdir', 'lzap_lfn_inputdir'}:
                parametricjobs.append(ParametricJobs(**subdict(kwargs, ParametricJobs.columns,
                                                               request_id=request.id,
                                                               status="Requested",
                                                               dirac_jobs=[],
                                                               reschedule=False)))

            session.add_all(parametricjobs)
            if not parametricjobs:
                logger.warning("No ParametricJobs added to the DB.")
        return self.GET()

    def PUT(self, reqid, **kwargs):  # pylint: disable=invalid-name
        """REST Put method."""
        logger.debug("In PUT: reqid = %s, kwargs = %s", reqid, kwargs)
        requester = cherrypy.request.verified_user

        with session_scope(self.dburl) as session:
            query = session.query(Requests).filter_by(id=reqid)
            if not requester.admin:
                query = query.filter_by(requester_id=requester.id)
            query.update(kwargs)
        return self.GET()

    def DELETE(self, reqid):  # pylint: disable=invalid-name
        """REST Delete method."""
        logger.debug("In DELETE: reqid = %s", reqid)

        if cherrypy.request.verified_user.admin:
            with session_scope(self.dburl) as session:
                session.query(Requests)\
                       .filter_by(id=reqid)\
                       .delete(synchronize_session=False)
                session.query(ParametricJobs)\
                       .filter_by(request_id=reqid)\
                       .delete(synchronize_session=False)
        return self.GET()
