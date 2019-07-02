#!/usr/bin/env python
import io
import os
import re
from setuptools import setup, find_packages


def get_version_and_homepage():
    d = {}
    r = re.compile('''^(__[a-z]+__) = ["'](.+)["']$''')
    for line in read_file('src', 'zodbbrowser', '__init__.py').splitlines():
        m = r.match(line)
        if m:
            d[m.group(1)] = m.group(2)
    return d['__version__'], d['__homepage__']


def read_file(*relative_filename):
    here = os.path.dirname(__file__)
    with io.open(os.path.join(here, *relative_filename), encoding='UTF-8') as f:
        return f.read()


def linkify_bugs(text):
    text = re.sub(r'\bLP#(\d+)\b',
                  r'`\g<0> <https://pad.lv/\1>`__', text)
    text = re.sub(r'\bGH #(\d+)\b',
                  r'`\g<0> <https://github.com/mgedmin/zodbbrowser/issues/\1>`__', text)
    return text


def get_long_description():
    return linkify_bugs(
        read_file('README.rst') +
        '\n\n' +
        read_file('CHANGES.rst')
    )


version, homepage = get_version_and_homepage()
long_description = get_long_description()

setup(
    name="zodbbrowser",
    license='ZPL 2.1',
    author="Marius Gedminas",
    author_email="marius@pov.lt",
    maintainer="Programmers of Vilnius",
    maintainer_email="marius@pov.lt",
    description="ZODB browser",
    long_description=long_description,
    version=version,
    url=homepage,
    keywords='ZODB database interactive history browser',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Zope Public License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],
    packages=find_packages('src'),
    include_package_data=True,
    zip_safe=False,
    package_dir={'': 'src'},
    install_requires=[
        "BTrees",
        "ZODB",
        "ZEO",
        "persistent",
        "transaction",
        "zope.app.pagetemplate",
        "zope.app.publication",
        "zope.component",
        "zope.interface",
        "zope.location",
        "zope.publisher",
        "zope.security",
        "zope.traversing",
        "zope.cachedescriptors",
        # dependencies just for the standalone app
        "zope.app.authentication",
        "zope.app.component",
        "zope.securitypolicy",
        "zope.app.server",
        "zope.app.session", # purely BBB for old Data.fs'es
        "zope.app.zcmlfiles",
        "zope.server",
        "zope.error",
        "zope.exceptions",
        "zope.session",
        # dependencies that easy_install pulls in via setuptools extras
        # but that are dropped when you do pip install, *sigh*
        "zope.hookable",
        "RestrictedPython",
        ],
    extras_require=dict(
        test=[
            'mock',
            "zope.app.folder",
            "zope.app.container",
            "zope.app.testing",
            "zope.testbrowser >= 5.1",
            "lxml",
            "cssselect",
        ],
        # extras for backwards compatibility only, not to break
        # people's setups if they depend on zodbbrowser[app]
        app=[],
    ),
    entry_points={
        'console_scripts': [
            'zodbbrowser = zodbbrowser.standalone:main',
        ],
        'z3c.autoinclude.plugin': [
            'target = plone',
        ],
    },
)
