import os
import sys
import importlib
import ganga

if __name__ == '__main__':
    lzprod_root = os.path.dirname(os.path.dirname(os.path.expanduser(os.path.expandvars(os.path.realpath(os.path.abspath(__file__))))))

    # Add the python src path to the sys.path for future imports
    sys.path = [os.path.join(lzprod_root, 'src', 'python')] + sys.path

    Requests = importlib.import_module('services.RequestsDB').Requests
    sqlalchemy_utils = importlib.import_module('sqlalchemy_utils')


    existing_requests = set(t.requestid for t in ganga.tasks if hasattr(t, 'requestid'))
    print existing_requests
    sqlalchemy_utils.create_db("mysql://lzprod:JuvMoafcug2@localhost/lzprod")
    with sqlalchemy_utils.db_session("mysql://lzprod:JuvMoafcug2@localhost/lzprod") as session:
        query = session.query(Requests)
        if existing_requests:
            query = session.query(Requests).filter(Requests.id.notin_(existing_requests))
        new_requests = set(session.query(Requests).all())
        print new_requests

        for request in new_requests:
            t = ganga.CoreTask()
            tr = ganga.CoreTransform()
            tr.backend = ganga.Dirac()
            tr.application = ganga.LZApp()
            tr.application.luxsim_version=request.app_version
            tr.application.reduction_version = request.reduction_version
            tr.application.requestid = request.id
            tr.application.tag = request.tag
            macros, njobs, nevents, seed = zip(*(i.split() for i in request.selected_macros.splitlines()))
            tr.unit_splitter = GenericSplitter()
            tr.unit_splitter.multi_attrs={'application.macro': macros,
                                          'application.njobs': [int(i) for i in njobs],
                                          'application.nevents': [int(i) for i in nevents],
                                          'application.seed': [int(i) for i in seed]}
            t.appendTransform(tr)
            t.float = 100

    # combine with above tasks loop
    for t in ganga.tasks():
        if t.status != 'New' and t.request_status == "Approved":
            t.run()
