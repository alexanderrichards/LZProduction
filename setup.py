"""Setuptools Module."""
from setuptools import setup, find_packages

setup(
    name="lzproduction",
    version="0.1",
#    package_dir={'': 'src/python'},
#    packages=find_packages('src/python'),
    packages=find_packages(),
    package_data={'lzproduction': ['resources/html/*',
                                   'resources/javascript/*',
                                   'resources/bash/*']},
    scripts=['scripts/userdb-update.py',
             'scripts/webapp-daemon.py',
             'scripts/dirac-daemon.py',
             'scripts/monitoring-daemon.py'],

    install_requires=['CherryPy==15.0.0',
                      'daemonize==2.4.7',
                      'enum34==1.1.6',
                      'GitPython==2.1.10',
                      'html==1.16',
                      'jinja2==2.10',
                      'natsort==5.3.2',
                      'pylru==1.1.0',
                      'PyMySQL==0.8.1',
                      'requests==2.18.4',
                      'SQLAlchemy==1.2.8',
                      'suds==0.4',
                      'rpyc==4.0.1'],
    extras_require={
        'development':  ["pytest", "mock"]
        #'webapp': [frontend stuff],
        #'monitoring': [backend stuff]
    },

    # metadata for upload to PyPI
    author="Alexander Richards",
    author_email="a.richards@imperial.ac.uk",
    description="LZ Production Interface",
    license="MIT",
    keywords="LZ production",
    url="https://github.com/alexanderrichards/LZProduction"
)
