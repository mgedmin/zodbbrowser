import os
import sys
import tempfile
import shutil
import unittest
import threading
import asyncore

from zope.testbrowser.browser import Browser
from zodbbrowser.standalone import main, serve_forever, stop_serving


class StandaloneZodbBrowserTestLayer(object):
    pass


class StandaloneZodbBrowserTestCase(unittest.TestCase):

    def setUp(self):
        self.port_number = self.findUnusedPort()
        self.url = 'http://localhost:%d' % self.port_number

    def findUnusedPort(self):
        return 1234 # TODO: be smarter

    def runServer(self, *args):
        if '--listen' not in args:
            args += ('--listen', str(self.port_number))
        args += ('--quiet', )
        main(list(args), start_serving=False)
        self.serverThread = threading.Thread(name='server',
                                             target=serve_forever,
                                             kwargs=dict(interval=0.5))
        # Daemon threads are evil and cause weird errors on shutdown,
        # but we want ^C to not hang
        self.serverThread.setDaemon(True)
        self.serverThread.start()

    def tearDown(self):
        # signal the server thread to stop serving
        stop_serving()
        self.serverThread.join(1.0)


class TestCanCreateEmptyDataFs(StandaloneZodbBrowserTestCase):

    layer = StandaloneZodbBrowserTestLayer

    def setUp(self):
        StandaloneZodbBrowserTestCase.setUp(self)
        self.tempdir = tempfile.mkdtemp('zodbbrowser')

    def tearDown(self):
        StandaloneZodbBrowserTestCase.tearDown(self)
        shutil.rmtree(self.tempdir)

    def test(self):
        self.runServer(os.path.join(self.tempdir, 'empty.fs'), '--rw')
        browser = Browser(self.url)
        self.assertTrue('zodbbrowser' in browser.contents)
        self.assertTrue('zope.app.folder.folder.Folder' in browser.contents)


def test_suite():
    this = sys.modules[__name__]
    return unittest.defaultTestLoader.loadTestsFromModule(this)
