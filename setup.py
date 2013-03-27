#/usr/bin/env python
from setuptools import setup
from xero import VERSION

try:
    readme = open("README.rst")
    long_description = str(readme.read())
finally:
    readme.close()

setup(
    name='pyxero',
    version=VERSION,
    description='Python API for accessing the REST API of the Xero accounting tool.',
    long_description=long_description,
    author='Russell Keith-Magee',
    author_email='russell@keith-magee.com',
    url='http://github.com/freakboy3742/pyxero',
    packages=['xero', ],
    install_requires=[
        'requests>=1.1.0',
        'requests-oauthlib>=0.3.0',
        'python-dateutil>=2.1',
    ],
    license='New BSD',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Financial and Insurance Industry',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Office/Business :: Financial :: Accounting',
    ],
    test_suite="tests",
)
