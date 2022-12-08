from setuptools import setup
import sys
import re

_version_re = re.compile(r"(?<=^__version__ = (\"|'))(.+)(?=\"|')")

def get_version(rel_path: str) -> str:
    """
    Searches for the ``__version__ = `` line in a source code file.
    https://packaging.python.org/en/latest/guides/single-sourcing-package-version/
    """
    with open(rel_path, 'r') as f:
        matches = map(_version_re.search, f)
        filtered = filter(lambda m: m is not None, matches)
        version = next(filtered, None)
        if version is None:
            raise RuntimeError(f'Could not find __version__ in {rel_path}')
        return version.group(0)

# Make sure we are running python3.5+
if 10 * sys.version_info[0]  + sys.version_info[1] < 35:
    sys.exit("Sorry, only Python 3.5+ is supported.")


def readme():
    with open('README.rst') as f:
        return f.read()

setup(
      name             =   'pfdo_run',
      version          =   get_version('pfdo_run/__init__.py'),
      description      =   'Run arbitrary CLI on each nested dir of an inputdir',
      long_description =   readme(),
      author           =   'FNNDSC',
      author_email     =   'dev@babymri.org',
      url              =   'https://github.com/FNNDSC/pfdo_med2image',
      packages         =   ['pfdo_run'],
      install_requires =   ['pfmisc', 'pftree', 'pfdo', 'Faker'],
      #test_suite       =   'nose.collector',
      #tests_require    =   ['nose'],
      #scripts          =   ['bin/pfdo_run'],
      entry_points={
          'console_scripts': [
              'pfdo_run = pfdo_run.__main__:main'
          ]
      },
      license          =   'MIT',
      zip_safe         =   False)
