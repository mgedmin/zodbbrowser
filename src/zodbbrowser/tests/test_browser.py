import unittest
import transaction
import sys
import gc

from ZODB.utils import u64, p64, tid_repr, oid_repr
from ZODB.interfaces import IDatabase
from zope.app.container.btree import BTreeContainer
from zope.app.container.interfaces import IContained
from zope.app.testing import setup
from zope.component import provideAdapter, getGlobalSiteManager
from zope.interface import implements
from zope.publisher.browser import TestRequest
from zope.traversing.interfaces import IContainmentRoot

from zodbbrowser.state import GenericState, ZodbObjectState
from zodbbrowser.browser import ZodbObjectAttribute, ZodbInfoView
from zodbbrowser.history import ZodbObjectHistory
from zodbbrowser.testing import SimpleValueRenderer

from realdb import RealDatabaseTest


class DatabaseStub(object):
    implements(IDatabase)

    opened = 0

    def open(self):
        self.opened += 1
        return ConnectionStub(self)


class ConnectionStub(object):
    def __init__(self, db):
        self.db = db

    def close(self):
        self.db.opened -= 1


class RootFolderStub(BTreeContainer):
    implements(IContainmentRoot)


class PersistentStub(BTreeContainer):
    pass


class NonpersistentStub(dict):
    implements(IContained)

    __name__ = __parent__ = None


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
        self.root['stub']['member'] = NonpersistentStub()
        self.root['stub']['member']['notpersistent'] = 'string'
        self.root['root'] = RootFolderStub()
        self.root['root']['item'] = PersistentStub()
        transaction.commit()
        provideAdapter(GenericState)
        provideAdapter(ZodbObjectHistory)

    def testCall(self):
        request = TestRequest()
        view = self._zodbInfoView(self.root, request)
        self.assertEquals(view(), '')
        self.assertEquals(view.latest, True)

        tid = ZodbObjectState(self.root).tid
        request = TestRequest(form={'tid': tid_repr(tid)})
        view = self._zodbInfoView(self.root, request)
        self.assertEquals(view.latest, False)

        oid = self.root._p_oid
        request = TestRequest(form={'oid': oid_repr(oid)})
        request.annotations['ZODB.interfaces.IConnection'] = self.root._p_jar
        view = self._zodbInfoView(None, request)

    def testGetJar(self):
        view = ZodbInfoView(self.root, TestRequest())
        self.assertEquals(view.jar, self.root._p_jar)
        view = ZodbInfoView(self.root['stub']['member'], TestRequest())
        self.assertEquals(view.jar, self.root._p_jar)

    def testSelectObjectToView_use_context(self):
        view = ZodbInfoView(self.root, TestRequest())
        self.assertEquals(view.selectObjectToView(), self.root)
        view = ZodbInfoView(self.root['root']['item'], TestRequest())
        self.assertEquals(view.selectObjectToView(), self.root['root']['item'])

    def testSelectObjectToView_find_parent(self):
        view = ZodbInfoView(self.root['stub']['member'], TestRequest())
        self.assertEquals(view.selectObjectToView(), self.root['stub'])

    def testSelectObjectToView_find_parent_fail(self):
        view = ZodbInfoView(self.root['stub']['member']['notpersistent'], TestRequest())
        self.assertRaises(Exception, view.selectObjectToView)

    def testSelectObjectToView_find_parent_fail_fall_back_to_root(self):
        view = ZodbInfoView(self.root['stub']['member']['notpersistent'], TestRequest())
        view.jar = self.root._p_jar
        self.assertEquals(view.selectObjectToView(), self.root)

    def testSelectObjectToView_by_oid(self):
        oid = u64(self.root['stub']._p_oid)
        view = ZodbInfoView(self.root, TestRequest(form={'oid': str(oid)}))
        self.assertEquals(view.selectObjectToView(), self.root['stub'])

    def testSelectObjectToView_by_oid_in_hex(self):
        oid = u64(self.root['stub']._p_oid)
        hex_oid = hex(oid).rstrip('L')
        view = ZodbInfoView(self.root, TestRequest(form={'oid': hex_oid}))
        self.assertEquals(view.selectObjectToView(), self.root['stub'])

    def testFindClosestPersistent(self):
        view = ZodbInfoView(self.root['stub']['member'], TestRequest())
        self.assertEquals(view.findClosestPersistent(), self.root['stub'])
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
        self.assertTrue('"url": "@@zodbbrowser?oid=0x0"' in jsonResult)
        self.assertTrue('"oid": 0' in jsonResult)
        jsonResult = view.locate_json('/stub/member/notpersistent')
        self.assertTrue('"partial_url"' in jsonResult)
        self.assertTrue('"partial_oid"' in jsonResult)
        self.assertTrue('"error": "Not persistent: /stub/member/notpersistent"')
        jsonResult = view.locate_json('/stub/nonexistent')
        self.assertTrue('"partial_url": "@@zodbbrowser?oid=0x1"' in jsonResult)
        self.assertTrue('"partial_path": "/stub", ' in jsonResult)
        self.assertTrue('"error": "Not found: /stub/nonexistent"}' in jsonResult)
        self.assertTrue('"partial_oid": 1' in jsonResult)

    def testLocateStartWithOID(self):
        view = self._zodbInfoView(self.root, TestRequest())
        jsonResult = view.locate_json('0')
        self.assertTrue('"url": "@@zodbbrowser?oid=0x0"' in jsonResult)
        self.assertTrue('"oid": 0' in jsonResult)
        jsonResult = view.locate_json('0x0')
        self.assertTrue('"url": "@@zodbbrowser?oid=0x0"' in jsonResult)
        self.assertTrue('"oid": 0' in jsonResult)
        jsonResult = view.locate_json('0x1/nonexistent')
        self.assertTrue('"partial_url": "@@zodbbrowser?oid=0x1"' in jsonResult)
        self.assertTrue('"partial_path": "0x1", ' in jsonResult)
        self.assertTrue('"error": "Not found: 0x1/nonexistent"}' in jsonResult)
        self.assertTrue('"partial_oid": 1' in jsonResult)

    def testLocateStartWithOID_that_does_not_exist(self):
        view = self._zodbInfoView(self.root, TestRequest())
        jsonResult = view.locate_json('0x1234')
        self.assertTrue('"partial_url": "@@zodbbrowser?oid=0x0"' in jsonResult)
        self.assertTrue('"partial_path": "/", ' in jsonResult)
        self.assertTrue('"error": "Not found: 0x1234"}' in jsonResult)
        self.assertTrue('"partial_oid": 0' in jsonResult)

    def testGetUrl(self):
        view = self._zodbInfoView(self.root, TestRequest())
        self.assertEquals(view.getUrl(), '@@zodbbrowser?oid=0x%x' %
                          u64(self.root._p_oid))
        view = self._zodbInfoView(self.root, TestRequest())
        self.assertEquals(view.getUrl(1, 2), '@@zodbbrowser?oid=0x1&tid=0x2')
        view = ZodbInfoView(self.root, TestRequest(form={'tid': '2'}))
        self.assertEquals(view.getUrl(1), '@@zodbbrowser?oid=0x1&tid=2')


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
                          [('/', '@@zodbbrowser?oid=0x1'),
                          ])

    def test_non_root(self):
        view = self.createView(self.foo)
        self.assertEquals(view.getBreadcrumbs(),
                          [('/', '@@zodbbrowser?oid=0x1'),
                           ('foo','@@zodbbrowser?oid=0x1b'),
                          ])

    def test_more_levels(self):
        view = self.createView(self.foobar)
        self.assertEquals(view.getBreadcrumbs(),
                          [('/', '@@zodbbrowser?oid=0x1'),
                           ('foo','@@zodbbrowser?oid=0x1b'),
                           ('/', None),
                           ('bar','@@zodbbrowser?oid=0x20'),
                          ])

    def test_unknown(self):
        view = self.createView(self.unknown)
        self.assertEquals(view.getBreadcrumbs(),
                          [('0xf','@@zodbbrowser?oid=0xf'),
                          ])

    def test_unknown_child(self):
        view = self.createView(self.unknown_child)
        self.assertEquals(view.getBreadcrumbs(),
                          [('0xf','@@zodbbrowser?oid=0xf'),
                           ('/', None),
                           ('child', '@@zodbbrowser?oid=0x11'),
                          ])

    def test_unparented(self):
        view = self.createView(self.unparented)
        self.assertEquals(view.getBreadcrumbs(),
                          [('/', '@@zodbbrowser?oid=0x1'),
                           ('...', None),
                           ('/', None),
                           ('wat', '@@zodbbrowser?oid=0x13'),
                          ])

    def test_unnamed_direct_child_of_root(self):
        view = self.createView(self.unnamed)
        self.assertEquals(view.getBreadcrumbs(),
                          [('/', '@@zodbbrowser?oid=0x1'),
                           ('???', '@@zodbbrowser?oid=0x37'),
                          ])


class TestZodbInfoView(unittest.TestCase):

    def assertEquals(self, first, second):
        if first != second:
            self.fail('\n%r !=\n%r' % (first, second))

    def addCleanUp(self, fn, *args, **kw):
        self.cleanups.append((fn, args, kw))

    def setUp(self):
        self.cleanups = []

    def tearDown(self):
        for fn, args, kw in reversed(self.cleanups):
            fn(*args, **kw)

    def testGetJar_uses_explicit_target_db(self):
        stub_db = DatabaseStub()
        registry = getGlobalSiteManager()
        registry.registerUtility(stub_db, IDatabase, name='<target>')
        self.addCleanUp(registry.unregisterUtility,
                        stub_db, IDatabase, name='<target>')
        view = ZodbInfoView(object(), TestRequest())
        self.assertEquals(view.jar.db, stub_db)
        del view
        gc.collect()
        self.assertEquals(stub_db.opened, 0)

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

    def test_tidToTimestamp(self):
        view = ZodbInfoView(None, None)
        self.assertEquals(view._tidToTimestamp(p64(12345678912345678)),
                          '1905-05-13 03:32:22.050327')
        self.assertEquals(view._tidToTimestamp('something else'),
                          "'something else'")


def test_suite():
    this = sys.modules[__name__]
    return unittest.TestSuite([
        unittest.defaultTestLoader.loadTestsFromModule(this)])
