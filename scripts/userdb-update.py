#!/usr/bin/env python
# pylint: disable=invalid-name
"""Script to read users info from VOMS and update locat SQL table."""
import os
import sys
import logging
import argparse
import importlib


if __name__ == '__main__':
    lzprod_root = os.path.dirname(
        os.path.dirname(
            os.path.expanduser(
                os.path.expandvars(
                    os.path.realpath(
                        os.path.abspath(__file__))))))

    parser = argparse.ArgumentParser(description='Read list of users from VOMS and update '
                                                 'local table.')
    parser.add_argument('-m', '--voms', default='https://voms.hep.wisc.edu:8443/voms/lz/services',
                        help='Root path of VOMS server services. [default: %(default)s]')
    parser.add_argument('-c', '--cert', default=os.path.expanduser('~/.globus/usercert.pem'),
                        help='Path to cert .pem file [default: %(default)s]')
    parser.add_argument('-k', '--key', default=os.path.expanduser('~/.globus/userkey.pem'),
                        help='Path to key .pem file. Note must be an unencrypted key. '
                             '[default: %(default)s]')
    parser.add_argument('-v', '--verbose', default=logging.INFO, action="store_const",
                        const=logging.DEBUG, dest='logginglevel',
                        help="Increase the verbosity of output")
    parser.add_argument('-l', '--log-dir', default=os.path.join(lzprod_root, 'log'),
                        help="Path to the log directory. Will be created if doesn't exist "
                             "[default: %(default)s]")
    parser.add_argument('-d', '--dburl',
                        default="sqlite:///" + os.path.join(lzprod_root, 'requests.db'),
                        help="URL for the requests DB. Note can use the prefix 'mysql+pymysql://' "
                             "if you have a problem with MySQLdb.py [default: %(default)s]")
    parser.add_argument('-y', '--verify', default=False, action="store_true",
                        help="Verify the VOMS server.")
    parser.add_argument('-t', '--trusted-cas', default='',
                        help="Path to the trusted CA_BUNDLE file or directory containing the "
                             "certificates of trusted CAs. Note if set to a directory, the "
                             "directory must have been processed using the c_rehash utility "
                             "supplied with OpenSSL. If using a CA_BUNDLE file can also consider "
                             "using the REQUESTS_CA_BUNDLE environment variable instead (this may "
                             "cause pip to fail to validate against PyPI). This option implies and "
                             "superseeds -y")
    args = parser.parse_args()
    if args.trusted_cas:
        args.verify = args.trusted_cas

    logging.basicConfig(level=args.logginglevel, format="%(name)15s : %(levelname)8s : %(message)s")
    logger = logging.getLogger("userdb-update")
    logger.debug("Script called with args: %s", args)

    # Add the python src path to the sys.path for future imports
    sys.path = [os.path.join(lzprod_root, 'src', 'python')] + sys.path

    Users = importlib.import_module('sql.tables').Users
    CertClient = importlib.import_module('utils.suds_utils').CertClient
    sql_utils = importlib.import_module('sql.utils')

    # Note if clients share the same transport we get a
    # 'Duplicate domain "suds.options" found' exception.
    headers = {"Content-Type": "text/xml;charset=UTF-8",
               "SOAPAction": "",
               'X-VOMS-CSRF-GUARD': '1'}
    vomsAdmin = CertClient(os.path.join(args.voms, 'VOMSAdmin?wsdl'),
                           cert=(args.cert, args.key),
                           headers=headers, verify=args.verify)
    vomsCompat = CertClient(os.path.join(args.voms, 'VOMSCompatibility?wsdl'),
                            cert=(args.cert, args.key),
                            headers=headers, verify=args.verify)

    voms_users_info = vomsAdmin.service.listMembers(vomsAdmin.service.getVOName())
    voms_valid_users = set(vomsCompat.service.getGridmapUsers())

    voms_users = {Users(dn=user_info['DN'],
                        ca=user_info['CA'],
                        email=user_info['mail'],
                        suspended=user_info['DN'] not in voms_valid_users,
                        admin=False) for user_info in voms_users_info}

    session_factory = sql_utils.create_all_tables(args.dburl)
    with sql_utils.scoped_session(session_factory) as session:
        db_users = set(session.query(Users).all())

        new_users = voms_users.difference(db_users)
        removed_users = db_users.difference(voms_users)
        common_users = db_users.intersection(voms_users)  # takes from arg first

        # Add new users in VOMS
        for new_user in new_users:
            logger.info("Adding user: DN='%s', CA='%s'", new_user.dn, new_user.ca)
            session.add(new_user)

        # Remove users removed from VOMS
        for removed_user in removed_users:
            logger.info("Removing user: DN='%s', CA='%s'", removed_user.dn, removed_user.ca)
            session.query(Users)\
                   .filter_by(dn=removed_user.dn, ca=removed_user.ca)\
                   .delete(synchronize_session=False)

        # Users with modified suspended status, update from VOMS
        for common_user in common_users:
            voms_dn, voms_ca = common_user.dn, common_user.ca
            voms_email, voms_suspended = common_user.email, common_user.suspended
            db_email, db_suspended = session.query(Users.email, Users.suspended)\
                                            .filter_by(dn=voms_dn, ca=voms_ca)\
                                            .one()

            if voms_email != db_email:
                logger.info("Updating user: DN='%s', CA='%s', Email=%s->%s",
                             voms_dn, voms_ca, db_email, voms_email)
                session.query(Users)\
                       .filter_by(dn=voms_dn, ca=voms_ca)\
                       .update({'email': voms_email})

            if voms_suspended != db_suspended:
                logger.info("Updating user: DN='%s', CA='%s', Suspended=%s->%s",
                             voms_dn, voms_ca, db_suspended, voms_suspended)
                session.query(Users)\
                       .filter_by(dn=voms_dn, ca=voms_ca)\
                       .update({'suspended': voms_suspended})

    logging.shutdown()
