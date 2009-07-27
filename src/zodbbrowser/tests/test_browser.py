import unittest
import transaction
import tempfile
import shutil
import sys
import os

from BTrees.OOBTree import OOBTree
from ZODB.FileStorage import FileStorage
from ZODB.utils import u64
from ZODB import DB
from zope.app.container.btree import BTreeContainer
from zope.app.testing import setup, ztapi
from zope.app.pagetemplate.simpleviewclass import SimpleViewClass
from zope.component import provideAdapter
from zope.interface import implements
from zope.publisher.browser import TestRequest
from zope.traversing.interfaces import IContainmentRoot
from zope.testing import doctest

from zodbbrowser.value import (GenericValue, TupleValue, DictValue,
                               ListValue, PersistentValue)
from zodbbrowser.state import OOBTreeState, GenericState
from zodbbrowser.browser import ZodbObjectAttribute, ZodbHelpView, ZodbInfoView
from zodbbrowser.tests.test_diff import pprintDict
from zodbbrowser.testing import SimpleValueRenderer

from realdb import RealDatabaseTest


class RootFolderStub(BTreeContainer):
    implements(IContainmentRoot)


class PersistentStub(BTreeContainer):
    pass


class TestZodbObjectAttribute(unittest.TestCase):

    def setUp(self):
        setup.placelessSetUp()
        provideAdapter(SimpleValueRenderer)
        self.attribute = ZodbObjectAttribute('foo', 42L, 't565')

    def tearDown(self):
        setup.placelessTearDown()

    def test_rendered_name(self):
        self.assertEquals(self.attribute.rendered_name(),
                          "'foo' [tid=t565]")

    def test_rendered_value(self):
        self.assertEquals(self.attribute.rendered_value(),
                          "42L [tid=t565]")


class TestZodbInfoView(RealDatabaseTest):

    def setUp(self):
        RealDatabaseTest.setUp(self)
        request = TestRequest()
        root = self.conn.root()
        self.view = ZodbInfoView(root, request)
        self.view.template = lambda: ''
        provideAdapter(GenericState)

#    def testCall(self):
#        self.view()

def test_suite():
    this = sys.modules[__name__]
    return unittest.TestSuite([
        unittest.defaultTestLoader.loadTestsFromModule(this)])
