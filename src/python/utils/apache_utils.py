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

def name_from_dn(client_dn):
    """
    Get human-readable name from DN.

    Attempt to determine a meaningful name from a
    clients DN. Requires the DN to have already been
    converted to the more usual slash delimeted style.

    Args:
        client_dn (str): The client DN

    Returns:
        str: The human-readable name
    """
    cns = (token.strip('CN= ') for token in client_dn.split('/')
           if token.startswith('CN='))
    return sorted(cns, key=len)[-1]

def apache_client_convert(client_dn, client_ca=None):
    """
    Convert Apache style client certs.

    Convert from the Apache comma delimited style to the
    more usual slash delimited style.

    Args:
        client_dn (str): The client DN
        client_ca (str): [Optional] The client CA

    Returns:
        tuple: The converted client (DN, CA)
    """
    if not client_dn.startswith('/'):
        client_dn = '/' + '/'.join(reversed(client_dn.split(',')))
        if client_ca is not None:
            client_ca = '/' + '/'.join(reversed(client_ca.split(',')))
    return client_dn, client_ca


class CredentialDispatcher(object):
    """
    Dispatcher that checks SSL credentials.

    This dispatcher is a wrapper that simply checks SSL credentials and
    then hands off to the wrapped dispatcher.
    """

    def __init__(self, users_dburl, dispatcher, admin_only=False):
        """Initialise."""
        self._users_dburl = users_dburl
        self._dispatcher = dispatcher
        self._admin_only = admin_only

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
            users = session.query(Users)\
                           .filter(Users.dn == client_dn)\
                           .filter(Users.ca == client_ca)\
                           .all()
            if not users:
                raise cherrypy.HTTPError(403, 'Forbidden: Unknown user. user: (%s, %s)'
                                         % (client_dn, client_ca))
            if len(users) > 1:
                raise cherrypy.HTTPError(500, 'Internal Server Error: Duplicate user detected. user: (%s, %s)'
                                         % (client_dn, client_ca))
            if users[0].suspended:
                raise cherrypy.HTTPError(403, 'Forbidden: User is suspended by VO. user: (%s, %s)'
                                         % (client_dn, client_ca))

            if self._admin_only and not users[0].admin:
                raise cherrypy.HTTPError(403, 'Forbidden: Admin users only')

            cherrypy.request.verified_user = VerifiedUser(users[0].id,
                                                          users[0].dn,
                                                          users[0].ca,
                                                          users[0].admin)
        return self._dispatcher(path)


__all__ = ('VerifiedUser', 'name_from_dn', 'apache_client_convert', 'CredentialDispatcher')
