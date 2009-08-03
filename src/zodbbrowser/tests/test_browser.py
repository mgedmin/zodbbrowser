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

    def test_repr(self):
        self.assertEquals(repr(self.attribute),
                          "ZodbObjectAttribute('foo', 42L, 't565')")

    def test_equality(self):
        self.assertEquals(self.attribute,
                          ZodbObjectAttribute('foo', 42L, 't565'))

    def test_inequality(self):
        self.assertNotEquals(self.attribute,
                             ZodbObjectAttribute('foo', 42L, 't575'))
        self.assertNotEquals(self.attribute,
                             ZodbObjectAttribute('foo', 43L, 't565'))
        self.assertNotEquals(self.attribute,
                             ZodbObjectAttribute('fox', 42L, 't565'))
        self.assertNotEquals(self.attribute,
                             object())

    def test_not_equals(self):
        self.assertFalse(self.attribute !=
                          ZodbObjectAttribute('foo', 42L, 't565'))
        self.assertTrue(self.attribute != object())


class TestZodbInfoViewWithRealDb(RealDatabaseTest):

    def _zodbInfoView(self, obj, request):
        view = ZodbInfoView(obj, request)
        view.template = lambda: ''
        view()
        return view

    def setUp(self):
        RealDatabaseTest.setUp(self)
        self.root = self.conn.root()
        self.root['stub'] = PersistentStub()
        self.root['stub']['member'] = {'notpersistent': 'string'}
        self.root['root'] = RootFolderStub()
        self.root['root']['item'] = PersistentStub()
        transaction.commit()
        provideAdapter(GenericState)

    def testCall(self):
        request = TestRequest()
        view = self._zodbInfoView(self.root, request)
        self.assertEquals(view(), '')
        self.assertEquals(view.latest, True)

        request = TestRequest(form={'tid': u64(ZodbObjectState(self.root).tid)})
        view = self._zodbInfoView(self.root, request)
        self.assertEquals(view.latest, False)

        request = TestRequest(form={'oid': u64(self.root._p_oid)})
        request.annotations['ZODB.interfaces.IConnection'] = self.root._p_jar
        view = self._zodbInfoView(None, request)

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
                            TestRequest(form={'tid': '12345678912345678'}))
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
        view = ZodbInfoView(self.root, TestRequest(form={'tid': '2'}))
        self.assertEquals(view.getUrl(1), '@@zodbbrowser?oid=1&tid=2')



class ZodbObjectStateStub(object):

    def __init__(self, context):
        self.context = context

    def getName(self):
        return self.context.__name__

    def getParent(self):
        return self.context.__parent__

    def isRoot(self):
        return IContainmentRoot.providedBy(self.context)

    def getObjectId(self):
        return u64(self.context._p_oid)

    def getParentState(self):
        if self.getParent() is None:
            return None
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
        self.unnamed = PersistentStub()
        self.unnamed._p_oid = p64(55)
        self.unnamed.__parent__ = self.root

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
                          [('/', '@@zodbbrowser?oid=1'),
                          ])

    def test_non_root(self):
        view = self.createView(self.foo)
        self.assertEquals(view.getBreadcrumbs(),
                          [('/', '@@zodbbrowser?oid=1'),
                           ('foo','@@zodbbrowser?oid=27'),
                          ])

    def test_more_levels(self):
        view = self.createView(self.foobar)
        self.assertEquals(view.getBreadcrumbs(),
                          [('/', '@@zodbbrowser?oid=1'),
                           ('foo','@@zodbbrowser?oid=27'),
                           ('/', None),
                           ('bar','@@zodbbrowser?oid=32'),
                          ])

    def test_unknown(self):
        view = self.createView(self.unknown)
        self.assertEquals(view.getBreadcrumbs(),
                          [('/', '@@zodbbrowser?oid=1'),
                           ('...', None),
                           ('/', None),
                           ('???','@@zodbbrowser?oid=15'),
                          ])

    def test_unknown_child(self):
        view = self.createView(self.unknown_child)
        self.assertEquals(view.getBreadcrumbs(),
                          [('/', '@@zodbbrowser?oid=1'),
                           ('...', None),
                           ('/', None),
                           ('???','@@zodbbrowser?oid=15'),
                           ('/', None),
                           ('child', '@@zodbbrowser?oid=17'),
                          ])

    def test_unparented(self):
        view = self.createView(self.unparented)
        self.assertEquals(view.getBreadcrumbs(),
                          [('/', '@@zodbbrowser?oid=1'),
                           ('...', None),
                           ('/', None),
                           ('wat', '@@zodbbrowser?oid=19'),
                          ])

    def test_unnamed_direct_child_of_root(self):
        view = self.createView(self.unnamed)
        self.assertEquals(view.getBreadcrumbs(),
                          [('/', '@@zodbbrowser?oid=1'),
                           ('???', '@@zodbbrowser?oid=55'),
                          ])


class TestZodbInfoView(unittest.TestCase):

    def assertEquals(self, first, second):
        if first != second:
            self.fail('\n%r !=\n%r' % (first, second))

    def test_getPath(self):
        view = ZodbInfoView(None, None)
        view.getBreadcrumbs = lambda: [('/', None), ('foo', None),
                                       ('/', None), ('bar baz', None)]
        self.assertEquals(view.getPath(), '/foo/bar baz')

    def test_getBreadcrumbsHTML(self):
        view = ZodbInfoView(None, None)
        view.getBreadcrumbs = lambda: [('/', 'here'),
                                       ('foo>', 'so"there'),
                                       ('/', None),
                                       ('bar<baz', None)]
        self.assertEquals(view.getBreadcrumbsHTML(),
                          '<a href="here">/</a>'
                          '<a href="so&quot;there">foo&gt;</a>'
                          '/bar&lt;baz')

    def test_listAttributes(self):
        view = ZodbInfoView(None, None)
        view.state = ZodbObjectStateStub(PersistentStub())
        view.state.requestedTid = 42
        view.state.listAttributes = lambda: [('zoinks', 17),
                                             ('scoobysnack', None)]
        self.assertEquals(view.listAttributes(),
                          [ZodbObjectAttribute('scoobysnack', None, 42),
                           ZodbObjectAttribute('zoinks', 17, 42)])

    def test_listAttributes_empty(self):
        view = ZodbInfoView(None, None)
        view.state = ZodbObjectStateStub(PersistentStub())
        view.state.requestedTid = 42
        view.state.listAttributes = lambda: []
        self.assertEquals(view.listAttributes(), [])

    def test_listAttributes_none_exist(self):
        view = ZodbInfoView(None, None)
        view.state = ZodbObjectStateStub(PersistentStub())
        view.state.requestedTid = 42
        view.state.listAttributes = lambda: None
        self.assertEquals(view.listAttributes(), None)

    def test_listItems(self):
        view = ZodbInfoView(None, None)
        view.state = ZodbObjectStateStub(PersistentStub())
        view.state.requestedTid = 42
        view.state.listItems = lambda: [('zoinks', 17),
                                        ('scoobysnack', None)]
        self.assertEquals(view.listItems(),
                          [ZodbObjectAttribute('zoinks', 17, 42),
                           ZodbObjectAttribute('scoobysnack', None, 42)])

    def test_listItems_empty(self):
        view = ZodbInfoView(None, None)
        view.state = ZodbObjectStateStub(PersistentStub())
        view.state.listItems = lambda: []
        self.assertEquals(view.listItems(), [])

    def test_listItems_none_exist(self):
        view = ZodbInfoView(None, None)
        view.state = ZodbObjectStateStub(PersistentStub())
        view.state.listItems = lambda: None
        self.assertEquals(view.listItems(), None)


def test_suite():
    this = sys.modules[__name__]
    return unittest.TestSuite([
        unittest.defaultTestLoader.loadTestsFromModule(this)])
