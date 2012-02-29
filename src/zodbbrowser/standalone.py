#!/usr/bin/env python
"""
ZODB Browser as a standalone app

This is a pile of hacks since bootstrapping a Zope 3 based app is incredibly
painful.
"""
import os
import stat
import sys
import asyncore
import socket
import optparse
import logging
import errno

from ZEO.ClientStorage import ClientStorage
from ZODB.DB import DB
from ZODB.MappingStorage import MappingStorage
from ZODB.FileStorage.FileStorage import FileStorage
from ZODB.interfaces import IDatabase
from zope.app.server.servertype import IServerType
from zope.app.appsetup.appsetup import SystemConfigurationParticipation
from zope.component import getUtility, provideUtility
from zope.server.taskthreads import ThreadedTaskDispatcher
from zope.event import notify
import zope.app.component.hooks

from zodbbrowser.state import install_provides_hack


class Options(object):
    listen_on = ('localhost', 8070)
    server_type = 'WSGI-HTTP'
    verbose = True
    threads = 4
    features = ('zserver',) # maybe 'devmode' too?
    site_definition = """
        <configure xmlns="http://namespaces.zope.org/zope"
                   i18n_domain="zodbbrowser">
          <include package="zope.securitypolicy" file="meta.zcml" />
          <include package="zope.app.zcmlfiles" file="meta.zcml" />

          <include package="zope.app.zcmlfiles" />
          <include package="zope.app.server" />
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
          <securityPolicy component="zope.securitypolicy.zopepolicy.ZopeSecurityPolicy" />
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

    from zope.security.management import newInteraction, endInteraction
    endInteraction()
    newInteraction(SystemConfigurationParticipation())
    zope.app.component.hooks.setHooks()

    from zope.configuration import xmlconfig, config
    context = config.ConfigurationMachine()
    xmlconfig.registerCommonDirectives(context)
    for feature in options.features:
        context.provideFeature(feature)
    context = xmlconfig.string(options.site_definition, context=context)

    endInteraction()


def start_server(options, db):
    global task_dispatcher
    task_dispatcher = ThreadedTaskDispatcher()
    task_dispatcher.setThreadCount(options.threads)

    server = getUtility(IServerType, options.server_type)
    host, port = options.listen_on
    try:
        server.create(options.server_type, task_dispatcher, db,
                      ip=host, port=port, verbose=options.verbose)
    except socket.error, e:
        if e.errno == errno.EADDRINUSE:
            sys.exit("Cannot listen on %s:%s: %s" % (host or '0.0.0.0',
                                                     port, e))
        else:
            raise

    if options.verbose:
        print "Listening on http://%s:%d/" % (host or socket.gethostname(),
                                              port)

def serve_forever(interval=30.0):
    try:
        while asyncore.socket_map:
            asyncore.poll(interval)
    except KeyboardInterrupt:
        pass


def stop_serving():
    task_dispatcher.shutdown(False)
    asyncore.close_all()


def main(args=None, start_serving=True):
    logging.basicConfig(format="%(message)s")

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
    parser.add_option('-q', '--quiet', action='store_false', dest='verbose',
                      default=True,
                      help='be quiet')
    parser.add_option('--rw', action='store_false', dest='readonly',
                      default=True,
                      help='open the database read-write (default: read-only)')
    opts, args = parser.parse_args(args)

    options = Options()
    options.verbose = opts.verbose

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
        filename = opts.db
        db = DB(FileStorage(filename, read_only=opts.readonly))
    elif opts.zeo:
        if ':' in opts.zeo:
            # remote hostname:port ZEO connection
            zeo_address = opts.zeo.split(':', 1)
            try:
                zeo_address[1] = int(zeo_address[1])
            except ValueError:
                parser.error('specified ZEO port must be an integer')
            zeo_address = tuple(zeo_address)
        else:
            # socket filename
            zeo_address = opts.zeo
            if os.path.exists(zeo_address):
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
        db = DB(ClientStorage(zeo_address, storage=zeo_storage, read_only=opts.readonly))
    else:
        parser.error('please specify a database')

    internal_db = DB(MappingStorage())

    configure(options)

    provideUtility(db, IDatabase, name='<target>')

    notify(zope.app.appsetup.interfaces.DatabaseOpened(internal_db))

    start_server(options, internal_db)

    notify(zope.app.appsetup.interfaces.ProcessStarting())

    install_provides_hack()

    if start_serving:
        serve_forever()


if __name__ == '__main__':
    main()
