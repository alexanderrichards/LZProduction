"""Requests service."""
import json
from datetime import datetime
import html
from sqlalchemy import Column, Integer, String, ForeignKeyConstraint
from sqlalchemy_utils import SQLTableBase, create_db, db_session
from apache_utils import check_credentials, AuthenticationError


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
    selected_macros = Column(String(250), nullable=False)
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

    def GET(self, reqid=None):
        """REST Get method."""
        print "IN GET: reqid=(%s)" % reqid
        with db_session(self.dburl) as session:
            if reqid is None:
                return json.dumps({'data': [dict(request) for request in session.query(Requests).all()]})

            table = html.HTML().table(border='1')
            request = session.query(Requests).filter(Requests.id == reqid).first()
            if request is not None:
                for colname, value in request:
                    tr = table.tr()
                    tr.td(colname)
                    tr.td(str(value))
        return str(table)

    def POST(self, **kwargs):
        """REST Post method."""
        print "IN POST", kwargs
        try:
            # if coming through the web app then this should be
            # checked already but could use curl
            requester_id, _, _ = check_credentials(self.dburl)
        except AuthenticationError as e:
            return e.message
        kwargs['request_date'] = datetime.now().strftime('%d/%m/%Y')
        kwargs['timestamp'] = str(datetime.now())
        kwargs['status'] = 'Requested'
        kwargs['selected_macros'] = '\n'.join(kwargs['selected_macros'])
        with db_session(self.dburl) as session:
            session.add(Requests(requester_id=requester_id, **kwargs))
        return self.GET()

    def PUT(self, reqid, **kwargs):
        """REST Put method."""
        print "IN PUT: reqid=(%s)" % reqid, kwargs
        with db_session(self.dburl) as session:
            session.query(Requests).filter(Requests.id == reqid).update(kwargs)

    def DELETE(self, reqid):
        """REST Delete method."""
        print "IN DELETE: reqid=(%s)" % reqid
        with db_session(self.dburl) as session:
            session.query(Requests).filter(Requests.id == reqid).delete(synchronize_session=False)
        return self.GET()
