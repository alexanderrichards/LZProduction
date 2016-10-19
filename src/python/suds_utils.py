"""
Suds utility module.

A couple of utility classes for working with certificate
authentication in suds.
"""
import requests

from suds.client import Client
from suds.transport import Reply
from suds.transport.https import HttpAuthenticated


class HttpCertAuthenticated(HttpAuthenticated):
    """Certificate authenticated http transport."""

    def __init__(self, cert, verify=True, **kwargs):
        """
        Initialisation.

        Args:
            cert (tuple): Tuple containing the path to the cert file followed
                          by the path to the key file as strings.
            verify (bool/str): Whether to verify the handled request url. If a
                               string is given then this is used as the path to
                               a CA_BUNDLE file or directory with certificates of
                               trusted CAs. Note: If verify is set to a path to a
                               directory, the directory must have been processed
                               using the c_rehash utility supplied with OpenSSL.
                               This list of trusted CAs can also be specified through
                               the REQUESTS_CA_BUNDLE environment variable (this may
                               cause pip to fail to validate against PyPI).
        """
        HttpAuthenticated.__init__(self, **kwargs)
        self.cert = cert
        self.verify = verify

    def open(self, request):
        """
        Open the url.

        Open the url in the specified request.
        """
        # raw method of the response object returns a file-like object.
        return requests.get(request.url,
                            cert=self.cert,
                            verify=self.verify,
                            stream=True).raw

    def send(self, request):
        """Send the request."""
        response = requests.post(request.url,
                                 data=request.message,
                                 headers=request.headers,
                                 cert=self.cert,
                                 verify=self.verify,
                                 stream=True)
        return Reply(response.status_code, response.headers, response.content)


class CertClient(Client):
    """Certificate authenticated suds client."""

    def __init__(self, url, cert, verify=True, **kwargs):
        """
        Initialisation.

        Sets up the underlying client with a certificate authenticated
        http transport. This can be overridden if the user provides an
        alternative transport in keyword args.

        Args:
            url (str): The url to connect to.
            cert (tuple): Tuple containing the path to the cert file followed
                          by the path to the key file as strings.
            verify (bool/str): Whether to verify the url. If a string is given
                               then this is used as the path to a CA_BUNDLE file
                               or directory with certificates of trusted CAs.
                               Note: If verify is set to a path to a directory,
                               the directory must have been processed using the
                               c_rehash utility supplied with OpenSSL. This list
                               of trusted CAs can also be specified through the
                               REQUESTS_CA_BUNDLE environment variable (this may
                               cause pip to fail to validate against PyPI).
        """
        kwargs.setdefault('transport', HttpCertAuthenticated(cert, verify))
        Client.__init__(self, url, **kwargs)


__all__ = ('HttpCertAuthenticated', 'CertClient')
