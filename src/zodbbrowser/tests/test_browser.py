import unittest
import transaction
import gc
import json

from ZODB.interfaces import IDatabase
from ZODB.utils import u64, p64, tid_repr, oid_repr
from persistent import Persistent
from zope.app.container.btree import BTreeContainer
from zope.app.container.interfaces import IContained
from zope.app.testing import setup
from zope.component import provideAdapter, getGlobalSiteManager
from zope.exceptions.interfaces import UserError
from zope.interface import implementer
from zope.publisher.browser import TestRequest
from zope.traversing.interfaces import IContainmentRoot
from zope.security.proxy import Proxy
from zope.security.checker import ProxyFactory

from zodbbrowser.browser import (
    ZodbObjectAttribute, VeryCarefulView, ZodbInfoView, ZodbHistoryView,
    getObjectType, getObjectTypeShort, getObjectPath)
from zodbbrowser.btreesupport import EmptyOOBTreeState
from zodbbrowser.history import ZodbObjectHistory, ZodbHistory, getIterableStorage
from zodbbrowser.state import GenericState, ZodbObjectState
from zodbbrowser.testing import SimpleValueRenderer

from .realdb import RealDatabaseTest


@implementer(IDatabase)
class DatabaseStub(object):

    opened = 0

    def open(self):
        self.opened += 1
        return ConnectionStub(self)


class ConnectionStub(object):
    def __init__(self, db):
        self.db = db

    def close(self):
        self.db.opened -= 1


@implementer(IContainmentRoot)
class RootFolderStub(BTreeContainer):
    pass


class PersistentStub(BTreeContainer):
    pass


@implementer(IContained)
class NonpersistentStub(dict):

    __name__ = __parent__ = None


class TestZodbObjectAttribute(unittest.TestCase):

    def setUp(self):
        setup.placelessSetUp()
        provideAdapter(SimpleValueRenderer)
        self.attribute = ZodbObjectAttribute('foo', 42, 't565')

    def tearDown(self):
        setup.placelessTearDown()

    def test_rendered_name(self):
        self.assertEqual(self.attribute.rendered_name(),
                         "'foo' [tid=t565]")

    def test_rendered_value(self):
        self.assertEqual(self.attribute.rendered_value(),
                         "42 [tid=t565]")

    def test_repr(self):
        self.assertEqual(repr(self.attribute),
                         "ZodbObjectAttribute('foo', 42, 't565')")

    def test_equality(self):
        self.assertEqual(self.attribute,
                         ZodbObjectAttribute('foo', 42, 't565'))

    def test_inequality(self):
        self.assertNotEqual(self.attribute,
                            ZodbObjectAttribute('foo', 42, 't575'))
        self.assertNotEqual(self.attribute,
                            ZodbObjectAttribute('foo', 43, 't565'))
        self.assertNotEqual(self.attribute,
                            ZodbObjectAttribute('fox', 42, 't565'))
        self.assertNotEqual(self.attribute,
                            object())

    def test_not_equals(self):
        self.assertFalse(self.attribute !=
                         ZodbObjectAttribute('foo', 42, 't565'))
        self.assertTrue(self.attribute != object())


class RandomThing(Persistent):
    pass


class SampleCarefulView(VeryCarefulView):
    def render(self):
        self.context.attr = 42
        transaction.get().join(CustomResource())
        return 'hi'


class CustomResource(object):
    def __repr__(self):
        return '<CustomResource>'

    def abort(self, txn):
        pass


class TestVeryCarefulView(RealDatabaseTest):

    def test_call_undoes_changes(self):
        self.root = self.conn.root()
        self.root['obj'] = obj = RandomThing()
        transaction.commit()
        view = SampleCarefulView(obj, None)
        view()
        self.assertFalse(hasattr(obj, 'attr'))


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
        self.conn.add(self.root['stub']) # force oid allocation
        self.root['root'] = RootFolderStub()
        self.root['root']['item'] = PersistentStub()
        transaction.commit()
        provideAdapter(GenericState)
        provideAdapter(ZodbObjectHistory)

    def testCall(self):
        request = TestRequest()
        view = self._zodbInfoView(self.root, request)
        self.assertEqual(view(), '')
        self.assertEqual(view.latest, True)

        tid = ZodbObjectState(self.root).tid
        request = TestRequest(form={'tid': tid_repr(tid)})
        view = self._zodbInfoView(self.root, request)
        self.assertEqual(view.latest, False)

        oid = self.root._p_oid
        request = TestRequest(form={'oid': oid_repr(oid)})
        request.annotations['ZODB.interfaces.IConnection'] = self.root._p_jar
        view = self._zodbInfoView(None, request)

    def testGetJar(self):
        view = ZodbInfoView(self.root, TestRequest())
        self.assertEqual(view.jar, self.root._p_jar)
        view = ZodbInfoView(self.root['stub']['member'], TestRequest())
        self.assertEqual(view.jar, self.root._p_jar)

    def testSelectObjectToView_use_context(self):
        view = ZodbInfoView(self.root, TestRequest())
        self.assertEqual(view.selectObjectToView(), self.root)
        view = ZodbInfoView(self.root['root']['item'], TestRequest())
        self.assertEqual(view.selectObjectToView(), self.root['root']['item'])

    def testSelectObjectToView_find_parent(self):
        view = ZodbInfoView(self.root['stub']['member'], TestRequest())
        self.assertEqual(view.selectObjectToView(), self.root['stub'])

    def testSelectObjectToView_find_parent_fail(self):
        view = ZodbInfoView(self.root['stub']['member']['notpersistent'], TestRequest())
        self.assertRaises(Exception, view.selectObjectToView)

    def testSelectObjectToView_find_parent_fail_fall_back_to_root(self):
        view = ZodbInfoView(self.root['stub']['member']['notpersistent'], TestRequest())
        view.jar = self.root._p_jar
        self.assertEqual(view.selectObjectToView(), self.root)

    def testSelectObjectToView_by_oid(self):
        oid = u64(self.root['stub']._p_oid)
        view = ZodbInfoView(self.root, TestRequest(form={'oid': str(oid)}))
        self.assertEqual(view.selectObjectToView(), self.root['stub'])

    def testSelectObjectToView_by_oid_in_hex(self):
        oid = u64(self.root['stub']._p_oid)
        hex_oid = hex(oid).rstrip('L')
        view = ZodbInfoView(self.root, TestRequest(form={'oid': hex_oid}))
        self.assertEqual(view.selectObjectToView(), self.root['stub'])

    def testSelectObjectToView_by_oid_bad_format(self):
        view = ZodbInfoView(self.root, TestRequest(form={'oid': 'dunno'}))
        self.assertRaises(UserError, view.selectObjectToView)

    def testSelectObjectToView_by_oid_bad_value(self):
        view = ZodbInfoView(self.root, TestRequest(form={'oid': '0xdeafbeef'}))
        self.assertRaises(UserError, view.selectObjectToView)

    def testFindClosestPersistent(self):
        view = ZodbInfoView(self.root['stub']['member'], TestRequest())
        self.assertEqual(view.findClosestPersistent(), self.root['stub'])
        view = ZodbInfoView(self.root['stub']['member']['notpersistent'],
                            TestRequest())
        self.assertEqual(view.findClosestPersistent(),
                         None)

    def testGetRequestedTid(self):
        view = ZodbInfoView(self.root, TestRequest())
        self.assertEqual(view.getRequestedTid(), None)
        self.assertEqual(view.getRequestedTidNice(), None)
        view = ZodbInfoView(self.root,
                            TestRequest(form={'tid': '12345678912345678'}))
        self.assertEqual(view.getRequestedTid(), '12345678912345678')
        self.assertEqual(view.getRequestedTidNice(),
                         '1905-05-13 03:32:22.050327')

    def testPrimitiveMethods(self):
        view = self._zodbInfoView(self.root, TestRequest())
        self.assertEqual(view.getObjectId(), u64(self.root._p_oid))
        self.assertTrue('PersistentMapping' in view.getObjectType())
        self.assertEqual(view.getStateTid(),
                         u64(ZodbObjectState(self.root).tid))
        self.assertEqual(view.getStateTidNice(),
                         view._tidToTimestamp(ZodbObjectState(self.root).tid))

    def testLocate(self):
        view = self._zodbInfoView(self.root, TestRequest())
        jsonResult = json.loads(view.locate_json('/'))
        self.assertEqual(jsonResult,
                         {"url": "@@zodbbrowser?oid=0x0",
                          "oid": 0})
        jsonResult = json.loads(view.locate_json('/stub/member/notpersistent'))
        self.assertTrue("partial_url" in jsonResult)
        self.assertTrue("partial_oid" in jsonResult)
        self.assertEqual(jsonResult["error"],
                         "Not persistent: /stub/member/notpersistent")
        jsonResult = json.loads(view.locate_json('/stub/nonexistent'))
        self.assertEqual(jsonResult,
                         {"partial_url": "@@zodbbrowser?oid=0x1",
                          "partial_path": "/stub",
                          "error": "Not found: /stub/nonexistent",
                          "partial_oid": 1})

    def testLocateNoLeadingSlash(self):
        view = self._zodbInfoView(self.root, TestRequest())
        jsonResult = json.loads(view.locate_json('stub'))
        self.assertEqual(jsonResult,
                         {"url": "@@zodbbrowser?oid=0x1",
                          "oid": 1})

    def testLocateStartWithOID(self):
        view = self._zodbInfoView(self.root, TestRequest())
        jsonResult = json.loads(view.locate_json('0'))
        self.assertEqual(jsonResult,
                         {"url": "@@zodbbrowser?oid=0x0",
                          "oid": 0})
        jsonResult = json.loads(view.locate_json('0x0'))
        self.assertEqual(jsonResult,
                         {"url": "@@zodbbrowser?oid=0x0",
                          "oid": 0})
        jsonResult = json.loads(view.locate_json('0x1/nonexistent'))
        self.assertEqual(jsonResult,
                         {"partial_url": "@@zodbbrowser?oid=0x1",
                          "partial_path": "0x1",
                          "error": "Not found: 0x1/nonexistent",
                          "partial_oid": 1})

    def testLocateStartWithOID_that_does_not_exist(self):
        view = self._zodbInfoView(self.root, TestRequest())
        jsonResult = json.loads(view.locate_json('0x1234'))
        self.assertEqual(jsonResult,
                         {"partial_url": "@@zodbbrowser?oid=0x0",
                          "partial_path": "/",
                          "error": "Not found: 0x1234",
                          "partial_oid": 0})

    def testGetUrl(self):
        view = self._zodbInfoView(self.root, TestRequest())
        self.assertEqual(view.getUrl(), '@@zodbbrowser?oid=0x%x' %
                         u64(self.root._p_oid))
        view = self._zodbInfoView(self.root, TestRequest())
        self.assertEqual(view.getUrl(1, 2), '@@zodbbrowser?oid=0x1&tid=0x2')
        view = ZodbInfoView(self.root, TestRequest(form={'tid': '2'}))
        self.assertEqual(view.getUrl(1), '@@zodbbrowser?oid=0x1&tid=2')


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
        self.assertEqual(view.getBreadcrumbs(),
                         [('/', '@@zodbbrowser?oid=0x1'), ])

    def test_non_root(self):
        view = self.createView(self.foo)
        self.assertEqual(view.getBreadcrumbs(),
                         [('/', '@@zodbbrowser?oid=0x1'),
                          ('foo', '@@zodbbrowser?oid=0x1b'), ])

    def test_more_levels(self):
        view = self.createView(self.foobar)
        self.assertEqual(view.getBreadcrumbs(),
                         [('/', '@@zodbbrowser?oid=0x1'),
                          ('foo', '@@zodbbrowser?oid=0x1b'),
                          ('/', None),
                          ('bar', '@@zodbbrowser?oid=0x20'), ])

    def test_unknown(self):
        view = self.createView(self.unknown)
        self.assertEqual(view.getBreadcrumbs(),
                         [('0xf', '@@zodbbrowser?oid=0xf'), ])

    def test_unknown_child(self):
        view = self.createView(self.unknown_child)
        self.assertEqual(view.getBreadcrumbs(),
                         [('0xf', '@@zodbbrowser?oid=0xf'),
                          ('/', None),
                          ('child', '@@zodbbrowser?oid=0x11'), ])

    def test_unparented(self):
        view = self.createView(self.unparented)
        self.assertEqual(view.getBreadcrumbs(),
                         [('/', '@@zodbbrowser?oid=0x1'),
                          ('...', None),
                          ('/', None),
                          ('wat', '@@zodbbrowser?oid=0x13'), ])

    def test_unnamed_direct_child_of_root(self):
        view = self.createView(self.unnamed)
        self.assertEqual(view.getBreadcrumbs(),
                         [('/', '@@zodbbrowser?oid=0x1'),
                          ('???', '@@zodbbrowser?oid=0x37'), ])


class TestZodbInfoView(unittest.TestCase):

    def assertEqual(self, first, second):
        # Align the two values below each other so they're easier to compare.
        if first != second:
            self.fail('\n%r !=\n%r' % (first, second))

    def test_jar_uses_explicit_target_db(self):
        stub_db = DatabaseStub()
        registry = getGlobalSiteManager()
        registry.registerUtility(stub_db, IDatabase, name='<target>')
        self.addCleanup(registry.unregisterUtility,
                        stub_db, IDatabase, name='<target>')
        view = ZodbInfoView(object(), TestRequest())
        self.assertEqual(view.jar.db, stub_db)
        del view
        gc.collect()
        self.assertEqual(stub_db.opened, 0)

    def test_getPath(self):
        view = ZodbInfoView(None, None)
        view.getBreadcrumbs = lambda: [('/', None), ('foo', None),
                                       ('/', None), ('bar baz', None)]
        self.assertEqual(view.getPath(), '/foo/bar baz')

    def test_getBreadcrumbsHTML(self):
        view = ZodbInfoView(None, None)
        view.getBreadcrumbs = lambda: [('/', 'here'),
                                       ('foo>', 'so"there'),
                                       ('/', None),
                                       ('bar<baz', None)]
        self.assertEqual(view.getBreadcrumbsHTML(),
                         '<a href="here">/</a>'
                         '<a href="so&quot;there">foo&gt;</a>'
                         '/bar&lt;baz')

    def test_getDisassembledPickleData(self):
        view = ZodbInfoView(None, None)
        view.state = ZodbObjectStateStub(PersistentStub())
        view.state.pickledState = b''
        self.assertEqual(
            view.getDisassembledPickleData(),
            'ValueError: pickle exhausted before seeing STOP\n\n'
            'ValueError: pickle exhausted before seeing STOP\n'
        )

    def test_listAttributes(self):
        view = ZodbInfoView(None, None)
        view.state = ZodbObjectStateStub(PersistentStub())
        view.state.requestedTid = 42
        view.state.listAttributes = lambda: [('zoinks', 17),
                                             ('scoobysnack', None)]
        self.assertEqual(view.listAttributes(),
                         [ZodbObjectAttribute('scoobysnack', None, 42),
                          ZodbObjectAttribute('zoinks', 17, 42)])

    def test_listAttributes_empty(self):
        view = ZodbInfoView(None, None)
        view.state = ZodbObjectStateStub(PersistentStub())
        view.state.requestedTid = 42
        view.state.listAttributes = lambda: []
        self.assertEqual(view.listAttributes(), [])

    def test_listAttributes_none_exist(self):
        view = ZodbInfoView(None, None)
        view.state = ZodbObjectStateStub(PersistentStub())
        view.state.requestedTid = 42
        view.state.listAttributes = lambda: None
        self.assertEqual(view.listAttributes(), None)

    def test_listItems(self):
        view = ZodbInfoView(None, None)
        view.state = ZodbObjectStateStub(PersistentStub())
        view.state.requestedTid = 42
        view.state.listItems = lambda: [('zoinks', 17),
                                        ('scoobysnack', None)]
        self.assertEqual(view.listItems(),
                         [ZodbObjectAttribute('zoinks', 17, 42),
                          ZodbObjectAttribute('scoobysnack', None, 42)])

    def test_listItems_empty(self):
        view = ZodbInfoView(None, None)
        view.state = ZodbObjectStateStub(PersistentStub())
        view.state.listItems = lambda: []
        self.assertEqual(view.listItems(), [])

    def test_listItems_none_exist(self):
        view = ZodbInfoView(None, None)
        view.state = ZodbObjectStateStub(PersistentStub())
        view.state.listItems = lambda: None
        self.assertEqual(view.listItems(), None)

    def test_loadHistoricalState(self):
        view = ZodbInfoView(None, None)
        view.obj = None
        view.history = [{}]  # injected fault: KeyError('tid')
        self.assertEqual(view._loadHistoricalState(),
                         [{'state': {}, 'error': "KeyError: 'tid'"},
                          {'state': {}, 'error': None}])

    def test_tidToTimestamp(self):
        view = ZodbInfoView(None, None)
        self.assertEqual(view._tidToTimestamp(p64(12345678912345678)),
                         '1905-05-13 03:32:22.050327')
        self.assertEqual(view._tidToTimestamp('something else'),
                         "'something else'")


class HistoryStub(object):
    def __init__(self, tids=()):
        self.tids = list(tids)

    def __len__(self):
        return len(self.tids)

    def __getitem__(self, idx):
        if isinstance(idx, slice):
            return [TransactionRecordStub()
                    for n in range(*idx.indices(len(self)))]
        else:
            return TransactionRecordStub()


class TransactionRecordStub(object):
    tid = p64(0x3c41adbde3708aa)
    status = ' '
    user = b'system /'
    description = b'stuff changed'
    extension = {}

    def __iter__(self):
        return iter(())


class TestZodbHistoryView(RealDatabaseTest):

    def setUp(self):
        RealDatabaseTest.setUp(self)
        self.root = self.conn.root()
        self.root['root'] = RootFolderStub()
        transaction.get().note(u'test setup')
        transaction.get().setUser(u'system')
        transaction.commit()
        provideAdapter(ZodbHistory)
        provideAdapter(getIterableStorage)
        provideAdapter(GenericState)
        provideAdapter(EmptyOOBTreeState)
        provideAdapter(SimpleValueRenderer)

    def _makeView(self, **kw):
        request = TestRequest(**kw)
        view = ZodbHistoryView(self.root, request)
        view.template = lambda: ''
        return view

    def test_render(self):
        view = self._makeView()
        view.render()
        self.assertEqual(view.page_size, 5)
        self.assertEqual(view.page, 0)
        self.assertEqual(view.last_page, 0)
        self.assertEqual(view.last_idx, 2)
        self.assertEqual(view.first_idx, 0)

    def test_render_custom_page(self):
        view = self._makeView(form={'page_size': 2, 'page': 3})
        view.render()
        self.assertEqual(view.page_size, 2)
        self.assertEqual(view.page, 0)
        self.assertEqual(view.last_page, 0)
        self.assertEqual(view.last_idx, 2)
        self.assertEqual(view.first_idx, 0)

    def test_render_bad_tid(self):
        view = self._makeView(form={'tid': '123454321'})
        view.render()
        self.assertEqual(view.page, 0)
        self.assertEqual(view.last_page, 0)
        self.assertEqual(view.last_idx, 2)
        self.assertEqual(view.first_idx, 0)

    def test_getUrl(self):
        view = self._makeView()
        self.assertEqual(view.getUrl(), '@@zodbbrowser_history')
        self.assertEqual(view.getUrl(tid=0x456),
                         '@@zodbbrowser_history?tid=0x456')

    def test_getUrl_preserves_tid(self):
        view = self._makeView(form={'tid': '123'})
        self.assertEqual(view.getUrl(), '@@zodbbrowser_history?tid=123')
        self.assertEqual(view.getUrl(tid=0x456),
                         '@@zodbbrowser_history?tid=0x456')

    def test_findPage(self):
        view = self._makeView()
        view.history = HistoryStub(tids=range(1000, 2000, 10))
        # page 0: [1990, 1980, 1970, 1960, 1950]
        # page 1: [1940, 1930, 1920, 1910, 1900]
        # ...
        # page 18: [1090, 1080, 1070, 1060, 1050]
        # page 19: [1040, 1030, 1020, 1010, 1000]
        self.assertEqual(view.findPage(1990), 0)
        self.assertEqual(view.findPage(1950), 0)
        self.assertEqual(view.findPage(1940), 1)
        self.assertEqual(view.findPage(1050), 18)
        self.assertEqual(view.findPage(1040), 19)
        self.assertEqual(view.findPage(1000), 19)
        self.assertEqual(view.findPage(1337), 0)

    def test_listHistory(self):
        view = self._makeView(form={'tid': '123'})
        view.update()
        prepared_history = view.listHistory()
        self.assertEqual(prepared_history[0]['description'], 'test setup')
        self.assertEqual(prepared_history[0]['user_id'], 'system')
        self.assertEqual(prepared_history[0]['user_location'], '/')

    def test_listHistory_no_transaction_size(self):
        view = self._makeView()
        view.history = HistoryStub(tids=[0x1234])
        view.first_idx = 0
        view.last_idx = 1
        view.page = 0
        prepared_history = view.listHistory()
        self.assertEqual(prepared_history[0]['size'], None)


class TestHelperFunctions(unittest.TestCase):

    def test_getObjectType(self):
        self.assertEqual(getObjectType(NonpersistentStub()),
                         "<class 'zodbbrowser.tests.test_browser.NonpersistentStub'>")
        self.assertEqual(getObjectType(ProxyFactory(NonpersistentStub())),
                         str(Proxy) + " - " +
                         "<class 'zodbbrowser.tests.test_browser.NonpersistentStub'>")

    def test_getObjectTypeShort(self):
        self.assertEqual(getObjectTypeShort(NonpersistentStub()),
                         'NonpersistentStub')
        self.assertEqual(getObjectTypeShort(ProxyFactory(NonpersistentStub())),
                         Proxy.__name__ + ' - NonpersistentStub')


class TestHelperFunctionsWithRealDb(RealDatabaseTest):

    def setUp(self):
        RealDatabaseTest.setUp(self)
        self.root = self.conn.root()
        self.root['root'] = RootFolderStub()
        self.root['root']['item'] = PersistentStub()
        self.root['root']['item']['subitem'] = PersistentStub()
        self.root['detached_item'] = PersistentStub()
        self.root['named_detached_item'] = PersistentStub()
        self.root['named_detached_item'].__name__ = 'named_detached_item'
        transaction.commit()
        provideAdapter(GenericState)

    def test_getObjectPath(self):
        self.assertEqual(
            getObjectPath(self.root['root']['item']['subitem'], None),
            '/item/subitem')

    def test_getObjectPath_no_path_no_name(self):
        oid = u64(self.root['detached_item']._p_oid)
        self.assertEqual(getObjectPath(self.root['detached_item'], None),
                         '0x%x' % oid)

    def test_getObjectPath_no_path_to_root(self):
        self.assertEqual(getObjectPath(self.root['named_detached_item'], None),
                         '/.../named_detached_item')
