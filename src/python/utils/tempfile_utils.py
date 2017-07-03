import os
from textwrap import dedent
from string import Template
from tempfile import NamedTemporaryFile
from contextlib import contextmanager
import jinja2
from git import Git

@contextmanager
def temporary_runscript(**kwargs):
    templates_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'bash')
    template_env = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath=templates_dir))
    with open('/tmp/runscript.sh', 'wb') as runscript:
        runscript.write("#!/bin/bash\n")
        if kwargs.get('app_version'):
            runscript.write(template_env.get_template('Simulation.bash').render(**kwargs))
            runscript.write('\n')
        if kwargs.get('reduction_version'):
            runscript.write(template_env.get_template('Reduction.bash').render(**kwargs))
            runscript.write('\n')
        if kwargs.get('der_version'):
            runscript.write(template_env.get_template('DER.bash').render(**kwargs))
            runscript.write('\n')
        if kwargs.get('lzap_version'):
            runscript.write(template_env.get_template('LZap.bash').render(**kwargs))
            runscript.write('\n')
    try:
        yield runscript.name
    finally:
        os.remove(runscript.name)

@contextmanager
def temporary_macro(tag, macro, app, nevents):
    app_map = {'BACCARAT': 'Bacc'}
    macro_extras = Template(dedent("""
        /control/getEnv SEED
        /$app/randomSeed {SEED}
        /$app/beamOn $nevents
        exit
        """))
    lzprod_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
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

