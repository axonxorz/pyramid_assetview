import os
import sys

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open('README', 'rb').read()
CHANGES = open('CHANGES', 'rb').read()

requires = [
    'pyramid>=1.3',
    'repoze.lru>=0.4'
    ]

setup(name='pyramid_assetview',
      version='0.3',
      description='Rendered views for Pyramid with templating/caching',
      long_description=README + '\n\n' +  CHANGES,
      classifiers=[
        "Programming Language :: Python",
        "Framework :: Pylons",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        ],
      author='Brendan Zerr',
      author_email='bzerr@brainwire.ca',
      url='http://brainwire.ca',
      keywords='web wsgi bfg pylons pyramid',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires = requires,
      entry_points = """""",
      )

