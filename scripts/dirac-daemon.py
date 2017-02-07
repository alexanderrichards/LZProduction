#!/usr/bin/env python
"""Dirac daemon run script."""
import os
import argparse
from SimpleXMLRPCServer import SimpleXMLRPCServer
from daemonize import Daemonize
from DIRAC.Core.Base import Script
Script.parseCommandLine(ignoreErrors=True)
from DIRAC.Interfaces.API.Dirac import Dirac


class DiracDaemon(Daemonize):
    """Dirac Daemon."""

    def __init__(self, address, **kwargs):
        """Initialise."""
        super(DiracDaemon, self).__init__(action=self.main, **kwargs)
        self._address = address

    def main(self):
        """Daemon main."""
        dirac_server = SimpleXMLRPCServer(self._address)
        dirac_server.register_introspection_functions()
        dirac_server.register_instance(Dirac())
        dirac_server.serve_forever()


if __name__ == '__main__':
    app_name = os.path.splitext(os.path.basename(__file__))[0]
    lzprod_root = os.path.dirname(
        os.path.dirname(
            os.path.expanduser(
                os.path.expandvars(
                    os.path.realpath(
                        os.path.abspath(__file__))))))
    parser = argparse.ArgumentParser(description='Run the DIRAC environment daemon.')
    parser.add_argument('-s', '--host', default='localhost',
                        help="The dirac environment API host [default: %(default)s]")
    parser.add_argument('-p', '--port', default=8000, type=int,
                        help="The dirac environment API port [default: %(default)s]")
    parser.add_argument('-f', '--pid-file', default=os.path.join(lzprod_root, app_name + '.pid'),
                        help="The pid file used by the daemon [default: %(default)s]")
    parser.add_argument('--debug-mode', action='store_true', default=False,
                        help="Run the daemon in a debug interactive monitoring mode. "
                             "(debugging only)")
    args = parser.parse_args()

    # Daemon setup
    ###########################################################################
    DiracDaemon(address=(args.host, args.port),
                app=app_name,
                pid=args.pid_file,
                foreground=args.debug_mode).start()
