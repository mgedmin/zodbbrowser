#!/usr/bin/env python
"""
ZODB Browser as a standalone app

This is a pile of hacks since bootstrapping a Zope 3 based app is incredibly
painful.
"""
import errno
import logging
import optparse
import os
import socket
import stat
import sys
import traceback
import warnings

import waitress
import zope.app.component.hooks
from ZEO.ClientStorage import ClientStorage
from ZODB.DB import DB
from ZODB.FileStorage.FileStorage import FileStorage
from ZODB.interfaces import IDatabase
from ZODB.MappingStorage import MappingStorage
from zope.app.appsetup.appsetup import SystemConfigurationParticipation
from zope.app.wsgi import WSGIPublisherApplication
from zope.component import provideUtility, queryUtility
from zope.event import notify
from zope.exceptions import exceptionformatter

from zodbbrowser.state import install_provides_hack


try:
    import faulthandler
except ImportError:
    faulthandler = None  # pragma: PY2


class Options(object):
    db_filename = None
    zeo_address = None
    zeo_storage = '1'
    zeo_timeout = 30  # seconds
    readonly = True
    listen_on = ('localhost', 8070)
    verbose = True
    debug = False
    threads = 4
    features = ('standalone-zodbbrowser', ) # maybe 'devmode' too?
    site_definition = """
        <configure xmlns="http://namespaces.zope.org/zope"
                   i18n_domain="zodbbrowser">
          <include package="zope.securitypolicy" file="meta.zcml" />
          <include package="zope.app.zcmlfiles" file="meta.zcml" />

          <include package="zope.app.zcmlfiles" />
          <include package="zope.app.component" />
          <include package="zope.error"/>
          <include package="zope.publisher" />
          <include package="zope.traversing" />
          <include package="zope.traversing.browser" />

          <include package="zodbbrowser" />

          <browser:defaultView
              for="persistent.Persistent"
              name="zodbbrowser"
              xmlns:browser="http://namespaces.zope.org/browser" />

          <unauthenticatedPrincipal id="zope.anybody" title="Unauthenticated User" />
          <unauthenticatedGroup id="zope.Anybody" title="Unauthenticated Users" />
          <authenticatedGroup id="zope.Authenticated" title="Authenticated Users" />
          <everybodyGroup id="zope.Everybody" title="All Users" />
          <securityPolicy
              component="zope.securitypolicy.zopepolicy.ZopeSecurityPolicy" />
          <role id="zope.Anonymous" title="Everybody"
                description="All users have this role implicitly" />
          <role id="zope.Manager" title="Site Manager" />
          <role id="zope.Member" title="Site Member" />
          <grant permission="zope.View"
                 role="zope.Anonymous" />
          <grantAll role="zope.Manager" />
          <!-- INSECURE -->
          <grant permission="zope.ManageContent"
                 role="zope.Anonymous" />
        </configure>
        """


def configure(options):
    from zope.error.error import globalErrorReportingUtility
    globalErrorReportingUtility.copy_to_zlog = True

    from zope.security.management import endInteraction, newInteraction
    endInteraction()
    newInteraction(SystemConfigurationParticipation())
    zope.app.component.hooks.setHooks()

    from zope.configuration import config, xmlconfig
    context = config.ConfigurationMachine()
    xmlconfig.registerCommonDirectives(context)
    for feature in options.features:
        context.provideFeature(feature)
    with warnings.catch_warnings():
        # zope.app.security globalmodules.zcml declares security directives for
        # some modules deprecated in newer versions of Python.
        warnings.filterwarnings('ignore',
                                message='^the formatter module is deprecated')
        context = xmlconfig.string(options.site_definition, context=context)

    endInteraction()


def create_wsgi_app(options, db):
    return WSGIPublisherApplication(db)


def start_server(options, db):
    app = create_wsgi_app(options, db)
    host, port = options.listen_on
    try:
        server = waitress.server.create_server(
            app, host=host, port=port, threads=options.threads
        )
    except socket.error as e:
        if e.errno == errno.EADDRINUSE:
            sys.exit("Cannot listen on %s:%s: %s" % (host or '0.0.0.0',
                                                     port, e))
        else:
            raise
    if options.verbose:
        server.print_listen("Listening on http://{}:{}/")
    return server


def serve_forever(server):
    try:
        server.run()
    except KeyboardInterrupt:
        pass
    finally:
        server.close()
        close_database()


def close_database():
    db = queryUtility(IDatabase, '<target>')
    if db:
        db.close()


def print_exception(
    exc, value=None, tb=None, limit=None, file=None, chain=True, **kw
):
    if value is None and tb is None:
        exc, value, tb = type(exc), exc, exc.__traceback__
    exceptionformatter.print_exception(exc, value, tb, limit=limit, file=file)


def format_exception(
    exc, value=None, tb=None, limit=None, chain=True, **kw
):
    if value is None and tb is None:
        exc, value, tb = type(exc), exc, exc.__traceback__
    return exceptionformatter.format_exception(exc, value, tb, limit=limit)


def monkeypatch_error_formatting():
    """Use Zope's custom traceback formatter for clearer error messages."""
    traceback.format_exception = format_exception
    traceback.print_exception = print_exception


def parse_args(args=None):
    if args is None:
        args = sys.argv[1:]

    parser = optparse.OptionParser(
        'usage: %prog [options] [FILENAME | --zeo ADDRESS]',
        prog='zodbbrowser',
        description='Open a ZODB database and start a web-based browser app.')
    parser.add_option('--zeo', metavar='ADDRESS',
                      help='connect to ZEO server instead'
                      ' (host:port or socket name)')
    parser.add_option('--storage', metavar='NAME',
                      help='connect to given ZEO storage')
    parser.add_option('--listen', metavar='ADDRESS',
                      help='specify port (or host:port) to listen on',
                      default='localhost:8070')
    parser.add_option('-q', '--quiet', action='store_const', const=0,
                      dest='verbose', default=1,
                      help='be quiet')
    parser.add_option('-v', '--verbose', action='count', dest='verbose',
                      help='be more verbose')
    parser.add_option('--debug', action='store_true', dest='debug',
                      default=False,
                      help='enable debug logging')
    parser.add_option('--rw', action='store_false', dest='readonly',
                      default=True,
                      help='open the database read-write (default: read-only)')
    opts, args = parser.parse_args(args)

    options = Options()
    options.verbose = opts.verbose
    options.debug = opts.debug

    if opts.listen:
        if ':' in opts.listen:
            host, port = opts.listen.rsplit(':', 1)
        else:
            host = 'localhost'
            port = opts.listen
        try:
            port = int(port)
        except ValueError:
            parser.error('invalid TCP port: %s' % port)
        options.listen_on = host, port

    if len(args) > 1:
        parser.error('too many arguments')

    if len(args) == 1:
        opts.db = args[0]
    else:
        opts.db = None

    if opts.db and opts.zeo:
        parser.error('you specified both ZEO and FileStorage; pick one')

    if opts.storage and not opts.zeo:
        parser.error('a ZEO storage was specified without ZEO connection')

    if opts.db:
        options.db_filename = opts.db
    elif opts.zeo:
        if ':' in opts.zeo:
            # remote hostname:port ZEO connection
            zeo_address = opts.zeo.rsplit(':', 1)
            try:
                zeo_address[1] = int(zeo_address[1])
            except ValueError:
                parser.error('specified ZEO port must be an integer')
            zeo_address = tuple(zeo_address)
        else:
            # socket filename
            zeo_address = opts.zeo
            if os.path.exists(zeo_address):  # pragma: Linux
                # try ZEO connection through UNIX socket
                mode = os.stat(zeo_address)
                if not stat.S_ISSOCK(mode.st_mode):
                    parser.error('specified file is not a valid UNIX socket')
            else:
                # remote ZEO connection
                zeo_address = (zeo_address, 8100)
        if opts.storage:
            zeo_storage = opts.storage
        else:
            zeo_storage = '1'
        options.zeo_address = zeo_address
        options.zeo_storage = zeo_storage
    else:
        parser.error('please specify a database')

    options.readonly = opts.readonly

    return options


def open_db(options):
    if options.db_filename:
        storage = FileStorage(options.db_filename, read_only=options.readonly)
    else:  # pragma: Linux
        storage = ClientStorage(options.zeo_address,
                                wait_timeout=options.zeo_timeout,
                                storage=options.zeo_storage,
                                read_only=options.readonly)
    return DB(storage)


def set_up_logging(options):
    if options.verbose >= 2:
        format = "%(name)s: %(message)s"
    else:
        format = "%(message)s"
    logging.basicConfig(format=format, level=logging.INFO)
    if options.debug:
        logging.getLogger('zodbbrowser').setLevel(logging.DEBUG)
    else:
        logging.getLogger('zope.generations').setLevel(logging.WARNING)


def main(args=None, start_serving=True):
    if faulthandler is not None:
        faulthandler.enable()   # pragma: PY3

    monkeypatch_error_formatting()

    options = parse_args(args)

    set_up_logging(options)

    db = open_db(options)

    internal_db = DB(MappingStorage())

    configure(options)

    provideUtility(db, IDatabase, name='<target>')

    notify(zope.app.appsetup.interfaces.DatabaseOpened(internal_db))

    server = start_server(options, internal_db)

    notify(zope.app.appsetup.interfaces.ProcessStarting())

    install_provides_hack()

    if start_serving:
        serve_forever(server)
    else:
        # This is used in the test suite
        return server


if __name__ == '__main__':
    main()
