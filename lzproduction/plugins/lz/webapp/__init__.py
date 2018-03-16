import pkg_resources

def index_includes():
    with open(pkg_resources.resource_filename('lzproduction', 'plugins/lz/resources/static/javascript/index.js'), 'rb') as file_:
        return file_.read()