"""
Apache Utils.

Tools for dealing with credential checking from X509 SSL certificates.
These are useful when using Apache as a reverse proxy to check user
credentials against a local DB.
"""
from collections import namedtuple
import cherrypy
from sqlalchemy_utils import create_db, db_session
from tables import Users

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


class CredentialDispatcher(object):
    """
    Dispatcher that checks SSL credentials.

    This dispatcher is a wrapper that simply checks SSL credentials and
    then hands off to the wrapped dispatcher.
    """

    def __init__(self, users_dburl, dispatcher):
        """Initialise."""
        self._users_dburl = users_dburl
        self._dispatcher = dispatcher

    def __call__(self, path):
        """Dispatch."""
        required_headers = set(['Ssl-Client-S-Dn', 'Ssl-Client-I-Dn', 'Ssl-Client-Verify'])
        missing_headers = required_headers.difference(cherrypy.request.headers.iterkeys())
        if missing_headers:
            raise cherrypy.HTTPError(401, 'Unauthorized: Incomplete certificate information '
                                     'available, required: %s' % list(missing_headers))

        client_dn, client_ca = apache_client_convert(cherrypy.request.headers['Ssl-Client-S-Dn'],
                                                     cherrypy.request.headers['Ssl-Client-I-Dn'])
        client_verified = cherrypy.request.headers['Ssl-Client-Verify']
        if client_verified != 'SUCCESS':
            raise cherrypy.HTTPError(401, 'Unauthorized: Cert not verified for user DN: %s, CA: %s.'
                                     % (client_dn, client_ca))

        create_db(self._users_dburl)
        with db_session(self._users_dburl) as session:
            users = session.query(Users).filter(Users.dn == client_dn).filter(Users.ca == client_ca).all()
            if not users:
                raise cherrypy.HTTPError(403, 'Forbidden: Unknown user. user: (%s, %s)'
                                         % (client_dn, client_ca))
            if len(users) > 1:
                raise cherrypy.HTTPError(500, 'Internal Server Error: Duplicate user detected. user: (%s, %s)'
                                         % (client_dn, client_ca))
            if users[0].suspended:
                raise cherrypy.HTTPError(403, 'Forbidden: User is suspended by VO. user: (%s, %s)'
                                         % (client_dn, client_ca))
            cherrypy.request.verified_user = VerifiedUser(users[0].id, users[0].dn, users[0].ca, users[0].admin)
        return self._dispatcher(path)


class AuthenticationError(Exception):
    """Error authentication user."""

    pass
