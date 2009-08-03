import unittest
import transaction
import sys

from ZODB.utils import u64, p64
from zope.app.container.btree import BTreeContainer
from zope.app.testing import setup
from zope.component import provideAdapter
from zope.interface import implements
from zope.publisher.browser import TestRequest
from zope.traversing.interfaces import IContainmentRoot

from zodbbrowser.state import GenericState, ZodbObjectState
from zodbbrowser.browser import ZodbObjectAttribute, ZodbInfoView
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
        view = ZodbInfoView(self.root['stub']['member']['notpersistent'],
                            TestRequest())
        self.assertEquals(view.findClosestPersistent(),
                          None)

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

    def testGetUrl(self):
        view = self._zodbInfoView(self.root, TestRequest())
        self.assertEquals(view.getUrl(), '@@zodbbrowser?oid=' +
                          str(u64(self.root._p_oid)))
        view = self._zodbInfoView(self.root, TestRequest())
        self.assertEquals(view.getUrl(1, 2), '@@zodbbrowser?oid=1&tid=2')
        view = ZodbInfoView(self.root, TestRequest(form={'tid':'2'}))
        self.assertEquals(view.getUrl(1), '@@zodbbrowser?oid=1&tid=2')



class ZodbObjectStateStub(object):

    def __init__(self, context):
        self.context = context

    def getName(self):
        return self.context.__name__

    def getParent(self):
        return self.context.__parent__

    def getParentState(self):
        return ZodbObjectStateStub(self.getParent())


class TestZodbInfoViewBreadcrumbs(unittest.TestCase):

    def setUp(self):
        self.root = RootFolderStub()
        self.root._p_oid = p64(1)
        self.foo = PersistentStub()
        self.foo._p_oid = p64(27)
        self.root['foo'] = self.foo
        self.foobar = PersistentStub()
        self.foobar._p_oid = p64(32)
        self.foo['bar'] = self.foobar
        self.unknown = PersistentStub()
        self.unknown._p_oid = p64(15)
        self.unknown_child = PersistentStub()
        self.unknown_child._p_oid = p64(17)
        self.unknown['child'] = self.unknown_child
        self.unparented = PersistentStub()
        self.unparented._p_oid = p64(19)
        self.unparented.__name__ = 'wat'

    def createView(self, obj):
        view = ZodbInfoView(obj, TestRequest())
        view.obj = obj
        view.state = ZodbObjectStateStub(view.obj)
        view.requestedTid = None
        view.getRootOid = lambda: 1
        return view

    def test_root(self):
        view = self.createView(self.root)
        self.assertEquals(view.getBreadcrumbs(),
                          '<a href="@@zodbbrowser?oid=1">/</a>')
        self.assertEquals(view.getPath(), '/')

    def test_non_root(self):
        view = self.createView(self.foo)
        self.assertEquals(view.getBreadcrumbs(),
                          '<a href="@@zodbbrowser?oid=1">/</a>'
                          '<a href="@@zodbbrowser?oid=27">foo</a>')
        self.assertEquals(view.getPath(), '/foo')

    def test_more_levels(self):
        view = self.createView(self.foobar)
        self.assertEquals(view.getBreadcrumbs(),
                          '<a href="@@zodbbrowser?oid=1">/</a>'
                          '<a href="@@zodbbrowser?oid=27">foo</a>/'
                          '<a href="@@zodbbrowser?oid=32">bar</a>')
        self.assertEquals(view.getPath(), '/foo/bar')

    def test_unknown(self):
        view = self.createView(self.unknown)
        self.assertEquals(view.getBreadcrumbs(),
                          '<a href="@@zodbbrowser?oid=1">/</a>'
                          '<a href="@@zodbbrowser?oid=15">???</a>')
        self.assertEquals(view.getPath(), '/???')

    def test_unknown_child(self):
        view = self.createView(self.unknown_child)
        self.assertEquals(view.getBreadcrumbs(),
                          '<a href="@@zodbbrowser?oid=1">/</a>'
                          '<a href="@@zodbbrowser?oid=15">???</a>/'
                          '<a href="@@zodbbrowser?oid=17">child</a>')
        self.assertEquals(view.getPath(), '/???/child')

    def test_unparented(self):
        view = self.createView(self.unparented)
        self.assertEquals(view.getBreadcrumbs(),
                          '<a href="@@zodbbrowser?oid=1">/</a>'
                          '???/'
                          '<a href="@@zodbbrowser?oid=19">wat</a>')
        self.assertEquals(view.getPath(), '/???/wat')


def test_suite():
    this = sys.modules[__name__]
    return unittest.TestSuite([
        unittest.defaultTestLoader.loadTestsFromModule(this)])
