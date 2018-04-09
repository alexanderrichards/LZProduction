"""
Apache Utils.

Tools for dealing with credential checking from X509 SSL certificates.
These are useful when using Apache as a reverse proxy to check user
credentials against a local DB.
"""
from functools import wraps
import cherrypy
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from lzproduction.sql.utils import db_session
from lzproduction.sql.tables import Users


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

def admin_only(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not cherrypy.request.verified_user.admin:
            raise cherrypy.HTTPError(403, 'Forbidden: Admin users only')
        return func(*args, **kwargs)
    return wrapper

def check_credentials(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        required_headers = {'Ssl-Client-S-Dn', 'Ssl-Client-I-Dn', 'Ssl-Client-Verify'}
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

        with db_session() as session:
            try:
                user = session.query(Users) \
                    .filter_by(dn=client_dn, ca=client_ca) \
                    .one()
            except MultipleResultsFound:
                raise cherrypy.HTTPError(500, 'Internal Server Error: Duplicate user detected. '
                                              'user: (%s, %s)'
                                         % (client_dn, client_ca))
            except NoResultFound:
                raise cherrypy.HTTPError(403, 'Forbidden: Unknown user. user: (%s, %s)'
                                         % (client_dn, client_ca))
            if user.suspended:
                raise cherrypy.HTTPError(403, 'Forbidden: User is suspended by VO. user: (%s, %s)'
                                         % (client_dn, client_ca))
            session.expunge(user)
            cherrypy.request.verified_user = user
            return func(*args, **kwargs)
    return wrapper

class CredentialDispatcher(object):
    """
    Dispatcher that checks SSL credentials.

    This dispatcher is a wrapper that simply checks SSL credentials and
    then hands off to the wrapped dispatcher.
    """

    def __init__(self, dispatcher, admin_only=False):
        """Initialise."""
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

        with db_session() as session:
            try:
                user = session.query(Users)\
                              .filter_by(dn=client_dn, ca=client_ca)\
                              .one()
            except MultipleResultsFound:
                raise cherrypy.HTTPError(500, 'Internal Server Error: Duplicate user detected. '
                                              'user: (%s, %s)'
                                         % (client_dn, client_ca))
            except NoResultFound:
                raise cherrypy.HTTPError(403, 'Forbidden: Unknown user. user: (%s, %s)'
                                         % (client_dn, client_ca))
            if user.suspended:
                raise cherrypy.HTTPError(403, 'Forbidden: User is suspended by VO. user: (%s, %s)'
                                         % (client_dn, client_ca))

            if self._admin_only and not user.admin:
                raise cherrypy.HTTPError(403, 'Forbidden: Admin users only')

            session.expunge(user)
            cherrypy.request.verified_user = user

        return self._dispatcher(path)


__all__ = ('apache_client_convert', 'CredentialDispatcher')
