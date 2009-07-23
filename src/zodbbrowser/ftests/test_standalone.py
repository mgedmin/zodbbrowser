import os
import sys
import tempfile
import shutil
import unittest
import threading
from cgi import escape

from lxml.html import fromstring, tostring
from ZODB.POSException import ReadOnlyError
from zope.testing import doctest
from zope.testbrowser.browser import Browser
from zope.testbrowser.interfaces import IBrowser
from zope.app.testing import setup

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


class FunctionalTestLayer(object):
    """Functional tests for no special setup.

    Used simply for grouping purposes.
    """


class StandaloneZodbBrowserTestLayer(object):
    """Functional tests with a web app running in the background."""

    @classmethod
    def setUp(cls):
        cls.server = ServerController()
        cls.tempdir = tempfile.mkdtemp('zodbbrowser')
        cls.data_fs = os.path.join(cls.tempdir, 'data.fs')
        # TODO: copy some predefined test data
        cls.server.run(cls.data_fs, '--rw')
        cls.url = cls.server.url

    @classmethod
    def tearDown(cls):
        cls.server.stop()
        shutil.rmtree(cls.tempdir)
        setup.placelessTearDown()


class TestCanCreateEmptyDataFs(unittest.TestCase):

    layer = FunctionalTestLayer

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
        self.assertTrue('zope.app.folder.folder.Folder' in browser.contents)

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
    html = html.replace(StandaloneZodbBrowserTestLayer.url,
                        'http://localhost/')
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
    if s is None:
        s = ''
    had_space = s[:1].isspace()
    s = s.strip()
    if had_space and s:
        s = ' ' + s
    return s


def fixupWhitespace(element, indent=0, step=2):
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
    if children:
        element.text += '\n' + ' ' * (indent + step)
    else:
        if len(escape(element.text)) > 40:
            element.text = ('\n' + ' ' * (indent + step) + element.text + '\n'
                            + ' ' * indent)

    for idx, child in enumerate(children):
        fixupWhitespace(child, indent + step, step)
        if idx == len(children) - 1:
            child.tail += ' ' * indent
        else:
            child.tail += ' ' * (indent + step)

    element.tail = stripify(element.tail) + '\n'


def setUp(test):
    test.globs['Browser'] = Browser
    test.globs['printXPath'] = printXPath
    test.globs['printCSSPath'] = printCSSPath
    test.globs['url'] = StandaloneZodbBrowserTestLayer.url


def test_suite():
    this = sys.modules[__name__]
    suite = unittest.defaultTestLoader.loadTestsFromModule(this)
    for files in ['browsing.txt']:
        test = doctest.DocFileSuite('browsing.txt',
                                    setUp=setUp,
                                    optionflags=doctest.REPORT_NDIFF)
        test.layer = StandaloneZodbBrowserTestLayer
        suite.addTest(test)
    return suite

