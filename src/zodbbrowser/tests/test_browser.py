import unittest
import transaction
import tempfile
import shutil
import sys
import os

from BTrees.OOBTree import OOBTree
from ZODB.FileStorage import FileStorage
from ZODB.utils import u64, p64
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
from zodbbrowser.state import OOBTreeState, GenericState, ZodbObjectState
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

    def _zodbInfoView(self, obj, request):
        view = ZodbInfoView(obj, request)
        view.template = lambda: ''
        view()
        return view

    def setUp(self):
        RealDatabaseTest.setUp(self)
        self.root = self.conn.root()
        self.root['stub'] = PersistentStub()
        self.root['stub']['member'] = {'notpersistent':'string'}
        self.root['root'] = RootFolderStub()
        self.root['root']['item'] = PersistentStub()
        transaction.commit()
        provideAdapter(GenericState)

    def testCall(self):
        request = TestRequest()
        view = self._zodbInfoView(self.root, request)
        self.assertEquals(view(), '')
        self.assertEquals(view.latest, True)

        request = TestRequest(form={'tid':u64(ZodbObjectState(self.root).tid)})
        view = self._zodbInfoView(self.root, request)
        self.assertEquals(view.latest, False)

        request = TestRequest(form={'oid':u64(self.root._p_oid)})
        request.annotations['ZODB.interfaces.IConnection'] = self.root._p_jar
        view = self._zodbInfoView(None, request)
        print view.obj._p_oid

    def testFindClosestPersistent(self):
        view = ZodbInfoView(self.root['stub']['member'], TestRequest())
        self.assertEquals(view.findClosestPersistent(), self.root['stub']['member'])

    def testGetRequestedTid(self):
        view = ZodbInfoView(self.root, TestRequest())
        self.assertEquals(view.getRequestedTid(), None)
        self.assertEquals(view.getRequestedTidNice(), None)
        view = ZodbInfoView(self.root,
                            TestRequest(form={'tid':'12345678912345678'}))
        self.assertEquals(view.getRequestedTid(), '12345678912345678')
        self.assertEquals(view.getRequestedTidNice(),
                          '1905-05-13 03:32:22.050327')

    def testPrimitiveMethods(self):
        view = self._zodbInfoView(self.root, TestRequest())
        self.assertEquals(view.getObjectId(), u64(self.root._p_oid))
        self.assertTrue('PersistentMapping' in view.getObjectType())
        self.assertEquals(view.getStateTid(),
                          u64(ZodbObjectState(self.root).tid))
        self.assertEquals(view.getStateTidNice(),
                          view._tidToTimestamp(ZodbObjectState(self.root).tid))

    def testLocate(self):
        view = self._zodbInfoView(self.root, TestRequest())
        jsonResult = view.locate_json('/')
        self.assertTrue('"url": "@@zodbbrowser?oid=0"' in jsonResult)
        self.assertTrue('"oid": 0' in jsonResult)
        jsonResult = view.locate_json('/stub/member/notpersistent')
        self.assertTrue('"partial_url"' in jsonResult)
        self.assertTrue('"partial_oid"' in jsonResult)
        self.assertTrue('"error": "Not persistent: /stub/member/notpersistent"')
        jsonResult = view.locate_json('/stub/nonexistent')
        self.assertTrue('"partial_url": "@@zodbbrowser?oid=1"' in jsonResult)
        self.assertTrue('"partial_path": "/stub", ' in jsonResult)
        self.assertTrue('"error": "Not found: /stub/nonexistent"}' in jsonResult)
        self.assertTrue('"partial_oid": 1' in jsonResult)

    def testGetPath(self):
        view = self._zodbInfoView(self.root, TestRequest())
        self.assertEquals(view.getPath(), '???')
        view = self._zodbInfoView(self.root['root']['item'], TestRequest())
        self.assertEquals(view.getPath(), '/item')

    def testGetUrl(self):
        view = self._zodbInfoView(self.root, TestRequest())
        self.assertEquals(view.getUrl(), '@@zodbbrowser?oid=' +
                          str(u64(self.root._p_oid)))
        view = self._zodbInfoView(self.root, TestRequest())
        self.assertEquals(view.getUrl(1, 2), '@@zodbbrowser?oid=1&tid=2')
        view = ZodbInfoView(self.root, TestRequest(form={'tid':'2'}))
        self.assertEquals(view.getUrl(1), '@@zodbbrowser?oid=1&tid=2')

    def testGetBreadcrumbs(self):
        view = self._zodbInfoView(self.root, TestRequest())
        self.assertEquals(view.getBreadcrumbs(),
                          '<a href="@@zodbbrowser?oid=0">/</a>'\
                          '<a href="@@zodbbrowser?oid=0">???</a>')


def test_suite():
    this = sys.modules[__name__]
    return unittest.TestSuite([
        unittest.defaultTestLoader.loadTestsFromModule(this)])
