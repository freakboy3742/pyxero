#/usr/bin/env python
import io
import re
from setuptools import setup


with io.open('./xero/__init__.py', encoding='utf8') as version_file:
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", version_file.read(), re.M)
    if version_match:
        version = version_match.group(1)
    else:
        raise RuntimeError("Unable to find version string.")


with io.open('README.md', encoding='utf8') as readme:
    long_description = readme.read()


setup(
    name='pyxero',
    version=version,
    description='Python API for accessing the REST API of the Xero accounting tool.',
    long_description=long_description,
    author='Russell Keith-Magee',
    author_email='russell@keith-magee.com',
    url='http://github.com/freakboy3742/pyxero',
    packages=['xero', ],
    install_requires=[
        'six>=1.8.0',
        'requests>=1.1.0',
        'requests-oauthlib>=0.3.0',
        'python-dateutil>=2.1',
        'PyJWT>=1.6.4', # This is required as part of oauthlib but doesn't seem to get included sometimes.
        'cryptography>=1.3.1', # As above, but fixes issue with missing module imports not picked up for some reason.
    ],
    tests_require=[
        'mock',
    ],
    license='New BSD',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Financial and Insurance Industry',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Office/Business :: Financial :: Accounting',
    ],
    test_suite="tests",
)
