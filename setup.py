"""
Flask-WebCache
-------------

A Flask extension that adds HTTP based caching to Flask apps.
"""
from setuptools import setup

setup(
    name='Flask-WebCache',
    version='0.9',
    url='http://github.com/fusic-com/flask-webcache/',
    license='BSD',
    author='Yaniv Aknin',
    author_email='yaniv@aknin.name',
    description='A Flask extension that adds HTTP based caching to Flask apps',
    long_description=__doc__,
    packages=['flask_webcache'],
    zip_safe=False,
    include_package_data=True,
    platforms='any',
    install_requires=[
        'Flask'
    ],
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Development Status :: 4 - Beta'
    ]
)
