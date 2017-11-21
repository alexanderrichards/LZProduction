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

    install_requires=['CherryPy==12.0.1',
                      'daemonize==2.4.7',
                      'enum34==1.1.6',
                      'GitPython==2.1.7',
                      'html==1.16',
                      'jinja2==2.10',
                      'natsort==5.1.1',
                      'pylru==1.0.9',
                      'PyMySQL==0.7.11',
                      'requests==2.18.4',
                      'SQLAlchemy==1.1.15',
                      'suds==0.4',
                      'rpyc==3.4.4'],
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
