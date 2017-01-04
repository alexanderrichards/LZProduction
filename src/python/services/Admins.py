"""Admin service."""
from collections import namedtuple
from sqlalchemy_utils import create_db, db_session
from apache_utils import name_from_dn
from tables import Users

User = namedtuple('User', ('id', 'admin', 'name'))


class Admins(object):
    """
    """
    exposed = True

    def __init__(self, dburl, template_env):
        self._users_dburl = dburl
        create_db(dburl)
        self._template_env = template_env

    def GET(self):
        """"""
        with db_session(self._users_dburl) as session:
            return self._template_env.get_template('admins.html').render({'users': [
                User(user.id, user.admin, name_from_dn(user.dn)) for user in session.query(Users).all()
            ]})

    def PUT(self):
        """"""
