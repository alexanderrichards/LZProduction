"""
Apache Utils.

Tools for dealing with credential checking from X509 SSL certificates.
These are useful when using Apache as a reverse proxy to check user
credentials against a local DB.
"""
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

    Convert from the Apache comma delimited style to the
    more usual slash delimited style.

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
    """
    Check credentials of incoming request.

    Takes the credentials from the incoming requests header which is where Apache
    places them and checks them against a local DB. It returns information about the
    user in a VerifiedUser tuple if the user is valid. If not then an
    AuthenticationError is raised.

    Args:
        users_dburl (str): The URL for the DB containing the valid users information

    Returns
        VerifiedUser: A named tuple containing the users (id, dn, ca, admin status)
                      from the DB.
    """
    client_dn, client_ca = apache_client_convert(cherrypy.request.headers['Ssl-Client-S-Dn'],
                                                 cherrypy.request.headers['Ssl-Client-I-Dn'])
    client_verified = cherrypy.request.headers['Ssl-Client-Verify']
    if client_verified != 'SUCCESS':
        raise AuthenticationError('401 Unauthorized: Cert not verified for user DN: %s, CA: %s.'
                                  % (client_dn, client_ca))

    create_db(users_dburl)
    with db_session(users_dburl) as session:
        users = session.query(Users).filter(Users.dn == client_dn).filter(Users.ca == client_ca).all()
        if not users:
            raise AuthenticationError('403 Forbidden: Unknown user: (%s, %s), users: %s'
                                      % (client_dn, client_ca, users))
        if len(users) > 1:
            raise AuthenticationError('500 Internal Server Error: Duplicate user detected. users: %s' % users)
        if users[0].suspended:
            raise AuthenticationError('403 Forbidden: User is suspended by VO')
        return VerifiedUser(users[0].id, users[0].dn, users[0].ca, users[0].admin)


class AuthenticationError(Exception):
    """Error authentication user."""

    pass
