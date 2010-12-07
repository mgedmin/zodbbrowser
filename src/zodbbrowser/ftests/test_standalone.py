import os
import re
import sys
import tempfile
import shutil
import doctest
import unittest
import threading
from cgi import escape

import transaction
from lxml.html import fromstring, tostring
from ZODB.POSException import ReadOnlyError
from ZODB.FileStorage.FileStorage import FileStorage
from ZODB.DB import DB
from zope.testing.renormalizing import RENormalizing
from zope.testbrowser.browser import Browser
from zope.testbrowser.interfaces import IBrowser
from zope.app.testing import setup
from zope.app.publication.zopepublication import ZopePublication
from zope.app.folder.folder import Folder
from zope.app.appsetup.interfaces import DatabaseOpened
from zope.app.appsetup.bootstrap import bootStrapSubscriber

from zodbbrowser.standalone import main, serve_forever, stop_serving


class ServerController(object):

    def __init__(self):
        self.server_thread = None
        self.url = None
        self.port_number = None

    def findUnusedPort(self):
        """Find an unused TCP port number."""
        return 1234 # TODO: be smarter

    def run(self, *args):
        """Run the standalone ZODB Browser web app in the background."""
        if self.server_thread is not None:
            raise AssertionError('Already running a server')

        if not self.port_number:
            self.port_number = self.findUnusedPort()

        self.url = 'http://localhost:%d/' % self.port_number

        args += ('--listen', str(self.port_number))
        args += ('--quiet', )
        main(list(args), start_serving=False)

        self.server_thread = threading.Thread(name='server',
                                              target=serve_forever,
                                              kwargs=dict(interval=0.5))
        # Daemon threads are evil and cause weird errors on shutdown,
        # but we want ^C to not hang
        self.server_thread.setDaemon(True)
        self.server_thread.start()

    def stop(self):
        """Stop the background ZODB Browser web, if running."""
        if self.server_thread is not None:
            stop_serving()
            self.server_thread.join(1.0)
            self.server_thread = None
            self.url = None
            self.port_number = None
            # XXX: leaves zserver threads behind
            # XXX: leaves global Zope state, you'll need to run
            #      setup.placelessTearDown()


class TestsWithoutServer(object):
    """Functional tests for no special setup.

    Used simply for grouping purposes.
    """


class TestsWithServer(object):
    """Functional tests with a web app running in the background."""

    @classmethod
    def setUp(cls):
        cls.server = ServerController()
        cls.tempdir = tempfile.mkdtemp('zodbbrowser')
        cls.data_fs = os.path.join(cls.tempdir, 'data.fs')
        cls.createTestData()
        cls.server.run(cls.data_fs, '--rw')
        cls.url = cls.server.url

    @classmethod
    def tearDown(cls):
        cls.server.stop()
        shutil.rmtree(cls.tempdir)
        setup.placelessTearDown()

    @classmethod
    def createTestData(cls):
        storage = FileStorage(cls.data_fs)
        db = DB(storage)
        # Create root folder and all that jazz
        bootStrapSubscriber(DatabaseOpened(db))
        connection = db.open()
        root = connection.root()
        root_folder = root[ZopePublication.root_name]
        # This is not a great way to set up test fixtures, but it'll do
        # for now
        cls.createTestDataForBrowsing(root_folder)
        cls.createTestDataForRollbacking(root_folder)
        cls.createTestDataForRollbackCanBeCancelled(root_folder)
        connection.close()
        db.close()

    @classmethod
    def createTestDataForBrowsing(cls, root_folder):
        # set up data that browsing.txt expects
        root_folder['browsing'] = Folder()
        transaction.commit()

    @classmethod
    def createTestDataForRollbacking(cls, root_folder):
        # set up data that rollbacking.txt expects
        root_folder['rollbacking'] = Folder()
        transaction.commit()
        root_folder['rollbacking'].random_attribute = 'hey'
        transaction.commit()

    @classmethod
    def createTestDataForRollbackCanBeCancelled(cls, root_folder):
        # set up data that rollback-can-be-cancelled.txt expects
        root_folder['rbcbc'] = Folder()
        transaction.commit()
        root_folder['rbcbc'].random_attribute = 'hey'
        transaction.commit()


class TestCanCreateEmptyDataFs(unittest.TestCase):

    layer = TestsWithoutServer

    def setUp(self):
        self.tempdir = tempfile.mkdtemp('zodbbrowser')
        self.empty_fs = os.path.join(self.tempdir, 'empty.fs')
        self.server = ServerController()

    def tearDown(self):
        self.server.stop()
        shutil.rmtree(self.tempdir)
        setup.placelessTearDown()

    def test_can_create_empty_data_fs(self):
        self.server.run(self.empty_fs, '--rw')
        browser = Browser(self.server.url)
        self.assertTrue('zodbbrowser' in browser.contents)
        self.assertTrue('persistent.mapping.PersistentMapping' in browser.contents)

    def test_cannot_start_in_read_only_mode(self):
        self.assertRaises(ReadOnlyError, self.server.run, self.empty_fs)
        # Due to a bug in ZODB, the new database *is* created, it just
        # has no objects in it
        # self.assertTrue(not os.path.exists(self.empty_fs))


def printXPath(html, xpath, pretty_print=True):
    """Print a selected HTML excerpt using XPath syntax.

    Example usage:

        printXPath(browser.contents, '//div[@class="something"]')

    For more convenient integration with zope.testbrowser, you can pass
    in a browser object directly:

        printXPath(browser, '//div[@class="something"]')

    """
    printResults(html, 'xpath', xpath, pretty_print=pretty_print)


def printCSSPath(html, csspath, pretty_print=True):
    """Print a selected HTML excerpt using CSS selector syntax.

    Example usage:

        printCSS(browser.contents, 'div.something')

    For more convenient integration with zope.testbrowser, you can pass
    in a browser object directly:

        printCSS(browser, 'div.something')

    """
    printResults(html, 'cssselect', csspath, pretty_print=pretty_print)


def printResults(html, method, arg, pretty_print=True):
    if IBrowser.providedBy(html):
        # it would be nice to extract the charset from the content-type
        # header, but let's assume UTF-8, which is the only charset that
        # we use in our system
        html = html.contents.decode('UTF-8')
    # XXX: not the most appropriate place for this.  I cannot do it with
    # a renormalizer since at that point the server URL is not yet known
    html = html.replace(TestsWithServer.url, 'http://localhost/')
    results = getattr(fromstring(html), method)(arg)
    for element in results:
        if isinstance(element, basestring):
            value = element.strip()
            # XXX it would be better to specialcase lxml elements.  How?
        else:
            if pretty_print:
                fixupWhitespace(element)
            value = tostring(element, pretty_print=pretty_print).rstrip()
        if value:
            print value
    if not results:
        print "Not found: %s" % arg


def stripify(s):
    """Strip indentation and trailing whitespace from a string.

    This is a rather quirky internal function.
    """
    if s is None:
        s = ''
    had_space = s[:1].isspace()
    s = s.strip()
    if '\n' in s:
        s = ' '.join(l.strip() for l in s.splitlines())
    if had_space and s:
        s = ' ' + s
    return s


def fixupWhitespace(element, indent=0, step=2, split_if_longer=38):
    """Normalize whitespace on lxml elements."""
    # Input:
    #   <tag ...>[text]<children ...></tag>[tail]
    # Output:
    #   {indent}<tag ...>\n
    #   [indent+2][text]\n
    #             <children>
    #   [indent]</tag>\n
    #   [indent][text]

    children = element.getchildren()

    element.text = stripify(element.text)
    # heuristic for splitting long elements
    should_split = (len(str(element.attrib)) > split_if_longer or
                    len(escape(element.text)) > split_if_longer)
    if should_split and element.text:
        element.text = ('\n' + ' ' * (indent + step) + element.text.lstrip())
    if children:
        element.text += '\n' + ' ' * (indent + step)
    else:
        if '\n' in element.text:
            element.text += '\n' + ' ' * indent

    for idx, child in enumerate(children):
        fixupWhitespace(child, indent + step, step)
        if idx == len(children) - 1:
            child.tail += '\n' + ' ' * indent
        else:
            child.tail += '\n' + ' ' * (indent + step)

    if indent == 0:
        element.tail = None
    element.tail = stripify(element.tail)
    if element.tail and element.tail.startswith(' '):
        element.tail = '\n' +  ' ' * indent + element.tail.lstrip()


def setUp(test):
    test.globs['Browser'] = Browser
    test.globs['printXPath'] = printXPath
    test.globs['printCSSPath'] = printCSSPath
    test.globs['url'] = TestsWithServer.url


def test_suite():
    this = sys.modules[__name__]
    suite = unittest.defaultTestLoader.loadTestsFromModule(this)
    checker = RENormalizing([
        (re.compile(r'object at 0x[0-9a-fA-F]+'), 'object at 0xXXXXXXX'),
        (re.compile(r'\btid[0-9xA-Fa-f]+'), 'tidXXXXXXXXXXXXXXXXXX'),
        (re.compile(r'\btid=[0-9xA-Fa-f]+'), 'tid=XXXXXXXXXXXXXXXXXX'),
        (re.compile(r'\boid=[0-9xA-Fa-f]+'), 'oid=XX'),
        (re.compile(r'\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d[.]\d\d\d\d\d\d'),
            'YYYY-MM-DD HH:MM:SS.SSSSSS'),
        (re.compile(r'\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d'),
            'YYYY-MM-DD HH:MM:SS'),
        (re.compile(r'zope\.app\.folder\.folder\.Folder'),
            'zope.site.folder.Folder'),
    ])
    here = os.path.dirname(__file__)
    for filename in os.listdir(here):
        if not filename.endswith('.txt') or filename.startswith('.'):
            continue
        test = doctest.DocFileSuite(filename,
                                    setUp=setUp,
                                    checker=checker,
                                    optionflags=doctest.REPORT_NDIFF)
        test.layer = TestsWithServer
        suite.addTest(test)
    return suite

