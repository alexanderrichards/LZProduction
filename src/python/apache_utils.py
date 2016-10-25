from collections import namedtuple
import cherrypy
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy_utils import SQLTableBase, create_db, db_session

class Users(SQLTableBase):
    """Users SQL Table."""

    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    dn = Column(String(250), nullable=False)
    ca = Column(String(250), nullable=False)
    suspended = Column(Boolean(), nullable=False)
    admin = Column(Boolean(), nullable=False)

VerifiedUser = namedtuple('VerifiedUser', ('id', 'dn', 'ca', 'admin'))

def apache_client_convert(dn, ca=None):
    """
    Convert Apache style client certs.

    Convert from the Apache comma delimeted style to the
    more usual slash delimeted style.

    Args:
        dn (str): The client DN
        ca (str): [Optional] The client CA

    Returns:
        tuple: The converted client (DN, CA)
    """
    dn = '/' + '/'.join(reversed(dn.split(',')))
    if ca is not None:
        ca = '/' + '/'.join(reversed(ca.split(',')))
    return dn, ca


def check_credentials(users_dburl):
    clientDN, clientCA = apache_client_convert(cherrypy.request.headers['Ssl-Client-S-Dn'],
                                               cherrypy.request.headers['Ssl-Client-I-Dn'])
    clientVerified = cherrypy.request.headers['Ssl-Client-Verify']
    if clientVerified != 'SUCCESS':
        raise AuthenticationError('401 Unauthorized: Cert not verified for user DN: %s, CA: %s.' % (clientDN, clientCA))

    create_db(users_dburl)
    with db_session(users_dburl) as session:
        users = session.query(Users).filter(Users.dn == clientDN).filter(Users.ca == clientCA).all()
        if not users:
            raise AuthenticationError('403 Forbidden: Unknown user: (%s, %s), users: %s' % (clientDN, clientCA, users))
        if len(users) > 1:
            raise AuthenticationError('500 Internal Server Error: Duplicate user detected. users: %s' % users)
        if users[0].suspended:
            raise AuthenticationError('403 Forbidden: User is suspended by VO')
        return VerifiedUser(users[0].id, users[0].dn, users[0].ca, users[0].admin)

class AuthenticationError(Exception):
    pass
