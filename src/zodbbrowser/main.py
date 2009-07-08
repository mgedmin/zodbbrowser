"""
ZODB Browser as a standalone app

This is a pile of hacks since bootstrapping a Zope 3 based app is incredibly
painful.
"""
import asyncore
import socket
import optparse
import logging

from ZEO.ClientStorage import ClientStorage
from ZODB.DB import DB
from ZODB.FileStorage.FileStorage import FileStorage
from zope.app.server.servertype import IServerType
from zope.app.appsetup.appsetup import SystemConfigurationParticipation
from zope.component import getUtility
from zope.server.taskthreads import ThreadedTaskDispatcher
import zope.app.component.hooks


class Options(object):
    listen_on = ('localhost', 8070)
    server_type = 'WSGI-HTTP'
    verbose = True
    threads = 4
    features = ('zserver',) # maybe 'devmode' too?
    site_definition = """
        <configure xmlns="http://namespaces.zope.org/zope"
            i18n:domain="zodbbrowser">
          <include package="zope.app.securitypolicy" file="meta.zcml" />
          <include package="zope.app.zcmlfiles" file="meta.zcml" />

          <include package="zope.publisher" />
          <include package="zope.traversing" />
          <include package="zope.traversing.browser" />
          <include package="zope.app.zcmlfiles" />
          <include package="zope.app.server" />
          <include package="zope.app.component" />
          <include package="zope.error"/>
          <include package="zope.publisher" />
          <include package="zope.traversing" />
          <include package="zope.traversing.browser" />

<!--
          <include package="zope.app.authentication" />
          <include package="zope.app.securitypolicy" />
          <include package="zope.session" />
  -->

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
          <grant permission="zope.app.dublincore.view"
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

    from zope.security.management import newInteraction
    newInteraction(SystemConfigurationParticipation())
    zope.app.component.hooks.setHooks()

    from zope.configuration import xmlconfig, config
    context = config.ConfigurationMachine()
    xmlconfig.registerCommonDirectives(context)
    for feature in options.features:
        context.provideFeature(feature)
    context = xmlconfig.string(options.site_definition, context=context)

    from zope.security.management import endInteraction
    endInteraction()


def start_server(options, db):
    task_dispatcher = ThreadedTaskDispatcher()
    task_dispatcher.setThreadCount(options.threads)

    server = getUtility(IServerType, options.server_type)
    host, port = options.listen_on
    server.create(options.server_type, task_dispatcher, db,
                  ip=host, port=port, verbose=options.verbose)

    print "Listening on http://%s:%d/" % (host or socket.gethostname(),
                                          port)

def serve_forever():
    try:
        while asyncore.socket_map:
            asyncore.poll(30.0)
    except KeyboardInterrupt:
        pass


def main():
    logging.basicConfig(format="%(message)s")

    parser = optparse.OptionParser('usage: %prog [/path/to/Data.fs]')
    parser.add_option('--zeo')
    opts, args = parser.parse_args()

    if len(args) > 1:
        parser.error('too many arguments')

    if len(args) == 1:
        opts.db = args[0]
    else:
        opts.db = None

    if opts.db and opts.zeo:
        parser.error('you specified both ZEO and FileStorage; pick one')

    if opts.db:
        filename = opts.db
        db = DB(FileStorage(filename, read_only=True))
    elif opts.zeo:
        if ':' in opts.zeo:
            zeo_address = opts.zeo.split(':', 1)
        else:
            zeo_address = opts.zeo
        db = DB(ClientStorage(zeo_address, read_only=True))
    else:
        parser.error('please specify a database')

    options = Options()
    configure(options)

    ## notify(zope.app.appsetup.interfaces.DatabaseOpened(db))

    start_server(options, db)

    ## notify(zope.app.appsetup.interfaces.ProcessStarting())

    serve_forever()

