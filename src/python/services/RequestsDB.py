"""Requests service."""
import json
from datetime import datetime
import cherrypy
import html
from sqlalchemy import Column, Integer, String, Text, ForeignKeyConstraint
from sqlalchemy_utils import SQLTableBase, create_db, db_session


class Requests(SQLTableBase):
    """Requests SQL Table."""

    __tablename__ = 'requests'
    id = Column(Integer, primary_key=True)
    requester_id = Column(Integer, nullable=False)
    request_date = Column(String(250), nullable=False)
    source = Column(String(250), nullable=False)
    detector = Column(String(250), nullable=False)
    tag = Column(String(250), nullable=False)
    app = Column(String(250), nullable=False)
    app_version = Column(String(250))
    request = Column(String(250))
    reduction_version = Column(String(250), nullable=False)
    sim_lead = Column(String(250), nullable=False)
    status = Column(String(250), nullable=False)
    timestamp = Column(String(250), nullable=False)
    description = Column(String(250), nullable=False)
    selected_macros = Column(Text())
    output_lfns = Column(Text())
    ForeignKeyConstraint(['requester_id'], ['users.id'])


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
                columns = ['id']
                query = session.query(Requests.id,
                                      Requests.request_date,
                                      Requests.sim_lead,
                                      Requests.status,
                                      Requests.description)\
                               .filter(Requests.requester_id == requester.id)
                if requester.admin:
                    columns += ['requester_id']
                    query = session.query(Requests.id,
                                          Requests.requester_id,
                                          Requests.request_date,
                                          Requests.sim_lead,
                                          Requests.status,
                                          Requests.description)
                columns += ['request_date', 'sim_lead', 'status', 'description']
                return json.dumps({'data': [dict(zip(columns, request)) for request in query.all()]})

            table = html.HTML().table(border='1')
            request = session.query(Requests).filter(Requests.id == reqid).first()
            if request is not None:
                for colname, value in request:
                    tr = table.tr()
                    tr.td(colname)
                    tr.td(str(value))
        return str(table)

    def POST(self, **kwargs):  # pylint: disable=C0103
        """REST Post method."""
        print "IN POST", kwargs
        kwargs['request_date'] = datetime.now().strftime('%d/%m/%Y')
        kwargs['timestamp'] = str(datetime.now())
        kwargs['status'] = 'Requested'
        kwargs['selected_macros'] = '\n'.join(kwargs['selected_macros'])
        kwargs['output_lfns'] = ''
        with db_session(self.dburl) as session:
            session.add(Requests(requester_id=cherrypy.request.verified_user.id, **kwargs))
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
                session.query(Requests).filter(Requests.id == reqid).delete(synchronize_session=False)
        return self.GET()
