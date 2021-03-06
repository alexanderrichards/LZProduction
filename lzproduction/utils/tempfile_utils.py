"""Functions for creating temporary job file."""
import os
import pkg_resources
from textwrap import dedent
from string import Template
from contextlib import contextmanager
import jinja2
from git import Git


@contextmanager
def temporary_runscript(**kwargs):
    """Create temporary runscript."""
#    pkg_resources.resource_filename(__name__, 'runscript_templates')
    templates_dir = pkg_resources.resource_filename('lzproduction', 'resources/bash')
#    templates_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'bash')
    template_env = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath=templates_dir),
                                      trim_blocks=True,
                                      lstrip_blocks=True)
    template_env.filters['filename'] = lambda path: os.path.splitext(os.path.basename(path))[0]
    with open('/tmp/runscript.sh', 'wb') as runscript:
        runscript.write(template_env.get_template('runscript_template.bash').render(**kwargs))
    try:
        yield runscript.name
    finally:
        os.remove(runscript.name)


@contextmanager
def temporary_macro(tag, macro, app, app_version, nevents):
    """Create temporary macro."""
    app_map = {'BACCARAT': 'Bacc'}
    if app_version.startswith('3'):
## mdc2 no longer requires these
        macro_extras = Template("")  # dedent("""
#            /$app/beamOn $nevents
#            exit
#            """))
    else:
        macro_extras = Template(dedent("""
            /control/getEnv SEED
            /$app/randomSeed {SEED}
            /$app/beamOn $nevents
            exit
            """))
    lzprod_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    git_dir = os.path.join(lzprod_root, 'git', 'TDRAnalysis')
    macro = os.path.join(git_dir, macro)
    git = Git(git_dir)
    git.fetch('origin')
    git.checkout(tag)
    if not os.path.isfile(macro):
        raise Exception("Macro file '%s' doesn't exist in tag %s" % (macro, tag))

    with open(os.path.join('/tmp', os.path.basename(macro)), 'wb') as tmp_macro, \
         open(macro, 'rb') as macro_file:
        tmp_macro.write(macro_file.read())
        tmp_macro.write(macro_extras.safe_substitute(app=app_map.get(app, app), nevents=nevents))
    try:
        yield tmp_macro.name
    finally:
        os.remove(tmp_macro.name)
