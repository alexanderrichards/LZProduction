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

    install_requires=['CherryPy==18.1.2',
                      'daemonize==2.5.0',
                      'enum34==1.1.6',
                      'GitPython==3.0.2',
                      'html==1.16',
                      'jinja2==2.10.1',
                      'natsort==6.0.0',
                      'pylru==1.2.0',
                      'PyMySQL==0.9.3',
                      'requests==2.22.0',
                      'SQLAlchemy==1.3.7',
                      'suds==0.4',
                      'rpyc==4.1.1'],
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
