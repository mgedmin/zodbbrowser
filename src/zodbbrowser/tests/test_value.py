import unittest

from zope.app.testing import setup
from zope.interface.verify import verifyObject

from zodbbrowser.interfaces import IValueRenderer
from zodbbrowser.value import GenericValue


class TestGenericValue(unittest.TestCase):

    def test_interface_compliance(self):
        verifyObject(IValueRenderer, GenericValue(None))

    def test_simple_repr(self):
        for s in [None, '', 'xyzzy', '\x17', u'\u1234']:
            self.assertEquals(GenericValue(s).render(), repr(s))

    def test_html_quoting(self):
        self.assertEquals(GenericValue('<html>').render(),
                          "'&lt;html&gt;'")

    def test_truncation(self):
        self.assertEquals(GenericValue('a very long string').render(limit=10),
                          """'a very lo<span class="truncated">...</span>""")


def setUp(test):
    setup.placelessSetUp()


def tearDown(test):
    setup.placelessTearDown()


def test_suite():
    return unittest.makeSuite(TestGenericValue)

