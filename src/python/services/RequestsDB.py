import json
import html
from datetime import datetime
from sqlalchemy import Column, ForeignKey, Integer, String, Boolean
from sqlalchemy_utils import SQLTableBase, create_db, db_session

class Requests(SQLTableBase):
    __tablename__ = 'requests'
    id = Column(Integer, primary_key=True)
    requester = Column(String(250), nullable=False)
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

class RequestsDB(object):
    exposed = True
    def __init__(self, dburl):
        self.dburl = dburl
        create_db(dburl)

    def GET(self, id=None):
        print "IN GET: id=(%s)" % id
        with db_session(self.dburl) as session:
            if id is None:
                return json.dumps({'data': [dict(request) for request in session.query(Requests).all()]})

            table = html.HTML().table(border='1')
            request = session.query(Requests).filter(Requests.id==id).first()
            if request is not None:
                for colname, value in request:
                    tr = table.tr()
                    tr.td(colname)
                    tr.td(str(value))
        return str(table)
                    
    def POST(self, **kwargs):
        print "IN POST", kwargs
        kwargs['request_date'] = datetime.now().strftime('%d/%m/%Y')
        kwargs['timestamp'] = str(datetime.now())
        kwargs['status'] = 'Requested'
        kwargs['selected_macros'] = '\n'.join(kwargs['selected_macros'])
        with db_session(self.dburl) as session:
            session.add(Requests(**kwargs))
        return self.GET()

    def PUT(self, id, **kwargs):
        print "IN PUT: id=(%s)" % id, kwargs
        with db_session(self.dburl) as session:
            session.query(Requests).filter(Requests.id==id).update(kwargs)

    def DELETE(self, id):
        print "IN DELETE: id=(%s)" % id
        with db_session(self.dburl) as session:
            session.query(Requests).filter(Requests.id==id).delete(synchronize_session=False)
        return self.GET()
