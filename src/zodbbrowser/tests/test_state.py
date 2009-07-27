import unittest
import sys

import transaction
from BTrees.OOBTree import OOBTree
from persistent import Persistent
from zope.app.folder import Folder
from zope.app.container.sample import SampleContainer
from zope.app.container.btree import BTreeContainer
from zope.app.container.ordered import OrderedContainer
from zope.app.testing import setup
from zope.interface.verify import verifyObject
from zope.interface import implements
from zope.traversing.interfaces import IContainmentRoot
from zope.component import provideAdapter

from zodbbrowser.interfaces import IStateInterpreter
from zodbbrowser.history import ZodbObjectHistory
from zodbbrowser.state import (GenericState,
                               EmptyOOBTreeState,
                               FolderState,
                               OOBTreeState,
                               OrderedContainerState,
                               BTreeContainerState,
                               PersistentDictState,
                               PersistentMappingState,
                               SampleContainerState,
                               FallbackState,
                               ZodbObjectState, _loadState)
from zodbbrowser.tests.realdb import RealDatabaseTest


class Frob(object):
    pass


class Root(Persistent, SampleContainer):
    implements(IContainmentRoot)


class SampleFolder(Persistent, SampleContainer):
    pass


class PersistentObject(Persistent):
    pass # we need a subclass so we get a __dict__


class TestZodbObjectState(RealDatabaseTest):

    def setUp(self):
        RealDatabaseTest.setUp(self)
        provideAdapter(GenericState)
        self.obj = self.conn.root()['obj'] = SampleFolder()
        transaction.commit()

    def testZodbObjectState(self):
        state = ZodbObjectState(self.obj)
        self.assertEquals(state.listItems(), None)
        self.assertTrue(state.listAttributes()[0][0], '_SampleContainer__data')
        self.assertEquals(state.getParent(), None)
        self.assertEquals(state.getName(), '???')
        self.assertTrue('_SampleContainer__data' in state.asDict().keys())


class TestLoadState(RealDatabaseTest):

    def setUp(self):
        RealDatabaseTest.setUp(self)
        root = self.conn.root()
        self.adam = root['adam'] = PersistentObject()
        transaction.commit()
        self.eve = root['eve'] = PersistentObject()
        transaction.commit()
        self.adam.laptop = 'ThinkPad T23'
        transaction.commit()
        self.eve.laptop = 'MacBook'
        transaction.commit()
        self.adam.laptop = 'ThinkPad T42'
        transaction.commit()
        self.adam.laptop = 'ThinkPad T61'
        transaction.commit()

    def test_latest_state(self):
        state = _loadState(self.adam).state
        self.assertEquals(state, dict(laptop='ThinkPad T61'))

    def test_exact_state(self):
        tid = ZodbObjectHistory(self.adam)[1]['tid']
        state = _loadState(self.adam, tid).state
        self.assertEquals(state, dict(laptop='ThinkPad T42'))

    def test_earlier_state(self):
        tid = ZodbObjectHistory(self.eve)[0]['tid']
        state = _loadState(self.adam, tid).state
        self.assertEquals(state, dict(laptop='ThinkPad T23'))

    def test_error_handling(self):
        tid = ZodbObjectHistory(self.adam)[-1]['tid']
        try:
            _loadState(self.eve, tid).state
        except Exception, e:
            self.assertTrue("did not exist in or before" in str(e))
        else:
            self.fail("did not raise")


class TestGenericState(unittest.TestCase):

    def test_interface_compliance(self):
        verifyObject(IStateInterpreter, GenericState(Frob(), {}, None))

    def test_getName_no_name(self):
        self.assertEquals(GenericState(Frob(), {}, None).getName(), '???')

    def test_getName_with_name(self):
        state = GenericState(Frob(), {'__name__': 'xyzzy'}, None)
        self.assertEquals(state.getName(), 'xyzzy')

    def test_getParent_no_parent(self):
        self.assertEquals(GenericState(Frob(), {}, None).getParent(), None)

    def test_getParent_with_parent(self):
        parent = Frob()
        state = GenericState(Frob(), {'__parent__': parent}, None)
        self.assertEquals(state.getParent(), parent)

    def test_listAttributes(self):
        state = GenericState(Frob(), {'foo': 1, 'bar': 2, 'baz': 3}, None)
        self.assertEquals(sorted(state.listAttributes()),
                          [('bar', 2), ('baz', 3), ('foo', 1)])

    def test_listItems(self):
        state = GenericState(Frob(), {'foo': 1, 'bar': 2, 'baz': 3}, None)
        self.assertEquals(state.listItems(), None)

    def test_asDict(self):
        state = GenericState(Frob(), {'foo': 1, 'bar': 2, 'baz': 3}, None)
        self.assertEquals(state.asDict(), {'foo': 1, 'bar': 2, 'baz': 3})


class TestGenericStateWithHistory(RealDatabaseTest):

    def setUp(self):
        RealDatabaseTest.setUp(self)
        self.root = self.conn.root()['root'] = Root()
        self.foo = self.root['foo'] = SampleFolder()
        self.bar = self.root['foo']['bar'] = SampleFolder()
        transaction.commit()
        self.foo.__name__ = 'new'
        transaction.commit()

    def test_getParent_no_tid(self):
        state = GenericState(self.bar, {'__parent__': self.foo}, None)
        self.assertEquals(state.getParent().__name__, 'new')

    def test_getParent_old_tid(self):
        self.bar._p_activate()
        tid = self.bar._p_serial
        state = GenericState(self.bar, {'__parent__': self.foo}, tid)
        self.assertEquals(state.getParent().__name__, 'foo')


class TestOrderedContainerState(RealDatabaseTest):

    def setUp(self):
        RealDatabaseTest.setUp(self)
        self.container = self.conn.root()['container'] = OrderedContainer()
        self.container['foo'] = 1
        self.container['bar'] = 2
        transaction.commit()
        self.state = OrderedContainerState(None, self.container.__getstate__(),
                                           None)

    def test_listItems(self):
        self.assertEquals(list(self.state.listItems()),
                          [('foo', 1), ('bar', 2)])


class TestFolderState(RealDatabaseTest):

    def setUp(self):
        setup.placelessSetUp()
        RealDatabaseTest.setUp(self)
        provideAdapter(OOBTreeState)
        self.folder = self.conn.root()['folder'] = Folder()
        self.folder['foo'] = 1
        self.folder['bar'] = 2
        transaction.commit()
        self.state = FolderState(None, self.folder.__getstate__(),
                                 None)

    def tearDown(self):
        RealDatabaseTest.tearDown(self)
        setup.placelessTearDown()

    def test_listItems(self):
        self.assertEquals(list(self.state.listItems()),
                          [('bar', 2), ('foo', 1)])

    def test_listItems_no_data(self):
        state = FolderState(None, Folder().__getstate__(), None)
        self.assertEquals(list(state.listItems()), []);


class TestSampleContainerState(RealDatabaseTest):

    def setUp(self):
        setup.placelessSetUp()
        RealDatabaseTest.setUp(self)
        provideAdapter(OOBTreeState)
        self.container = self.conn.root()['container'] = BTreeContainer()
        self.container['foo'] = 1
        self.container['bar'] = 2
        transaction.commit()
        self.state = SampleContainerState(None, self.container.__getstate__(),
                                          None)

    def tearDown(self):
        RealDatabaseTest.tearDown(self)
        setup.placelessTearDown()

    def test_listItems(self):
        self.assertEquals(list(self.state.listItems()),
                          [('bar', 2), ('foo', 1)])

    def test_listItems_no_data(self):
        state = SampleContainerState(None, BTreeContainer().__getstate__(),
                                     None)
        self.assertEquals(list(state.listItems()), []);


class TestBTreeContainerState(RealDatabaseTest):

    def setUp(self):
        setup.placelessSetUp()
        RealDatabaseTest.setUp(self)
        provideAdapter(OOBTreeState)
        self.container = self.conn.root()['container'] = BTreeContainer()
        self.container['foo'] = 1
        self.container['bar'] = 2
        transaction.commit()
        self.state = BTreeContainerState(None, self.container.__getstate__(),
                                         None)

    def tearDown(self):
        RealDatabaseTest.tearDown(self)
        setup.placelessTearDown()

    def test_listItems(self):
        self.assertEquals(list(self.state.listItems()),
                          [('bar', 2), ('foo', 1)])

    def test_listItems_no_data(self):
        state = BTreeContainerState(None, BTreeContainer().__getstate__(),
                                    None)
        self.assertEquals(list(state.listItems()), []);


class TestOOBTreeState(unittest.TestCase):

    def setUp(self):
        tree = OOBTree()
        tree[1] = 42
        tree[2] = 23
        tree[3] = 17
        state = tree.__getstate__()
        self.state = EmptyOOBTreeState(None, state, None)

    def test_interface_compliance(self):
        verifyObject(IStateInterpreter, self.state)

    def test_getName(self):
        self.assertEquals(self.state.getName(), '???')

    def test_getParent(self):
        self.assertEquals(self.state.getParent(), None)

    def test_listAttributes(self):
        self.assertEquals(self.state.listAttributes(), None)

    def test_listItems(self):
        self.assertEquals(list(self.state.listItems()),
                          [(1, 42), (2, 23), (3, 17)])

    def test_asDict(self):
        self.assertEquals(dict(self.state.asDict()), {1: 42, 2: 23, 3: 17})


class TestLargeOOBTreeState(RealDatabaseTest):

    def setUp(self):
        RealDatabaseTest.setUp(self)
        self.tree = self.conn.root()['tree'] = OOBTree()
        for i in range(0, 1000):
            self.tree[i] = -1
        transaction.commit()
        for i in range(0, 1000, 2):
            self.tree[i] = 1
        transaction.commit()
        self.tids = [d['tid'] for d in ZodbObjectHistory(self.tree)]

    def getState(self, tid):
        state = _loadState(self.tree, tid).state
        return OOBTreeState(self.tree, state, tid)

    def test_current_state(self):
        state = self.getState(None)
        self.assertEquals(sum(state.asDict().values()), 0)

    def test_historical_state(self):
        state = self.getState(self.tids[-1])
        self.assertEquals(sum(state.asDict().values()), -1000)


class TestEmptyOOBTreeState(unittest.TestCase):

    def setUp(self):
        self.state = EmptyOOBTreeState(None, None, None)

    def test_interface_compliance(self):
        verifyObject(IStateInterpreter, self.state)

    def test_getName(self):
        self.assertEquals(self.state.getName(), '???')

    def test_getParent(self):
        self.assertEquals(self.state.getParent(), None)

    def test_listAttributes(self):
        self.assertEquals(self.state.listAttributes(), None)

    def test_listItems(self):
        self.assertEquals(list(self.state.listItems()), [])

    def test_asDict(self):
        self.assertEquals(dict(self.state.asDict()), {})


class TestPersistentDictSate(unittest.TestCase):

    def test_listItems(self):
        state = PersistentDictState(Frob(),
                                    {'data': dict(a=42, b=23, c=17)},
                                    None)
        self.assertEquals(state.listItems(),
                          [('a', 42), ('b', 23), ('c', 17)])

    def test_listItems_no_data(self):
        # shouldn't happen, but let's display what exists in the DB instead
        # of crashing
        state = PersistentDictState(Frob(), {}, None)
        self.assertEquals(state.listItems(), [])


class TestPersistentMappingSate(unittest.TestCase):

    def test_listItems(self):
        state = PersistentMappingState(Frob(),
                                    {'data': dict(a=42, b=23, c=17)},
                                    None)
        self.assertEquals(state.listItems(),
                          [('a', 42), ('b', 23), ('c', 17)])

    def test_listItems_no_data(self):
        # shouldn't happen, but let's display what exists in the DB instead
        # of crashing
        state = PersistentMappingState(Frob(), {}, None)
        self.assertEquals(state.listItems(), [])


class TestFallbackState(unittest.TestCase):

    def setUp(self):
        self.state = FallbackState(Frob(), object(), None)

    def test_interface_compliance(self):
        verifyObject(IStateInterpreter, self.state)

    def test_getName(self):
        self.assertEquals(self.state.getName(), '???')

    def test_getParent(self):
        self.assertEquals(self.state.getParent(), None)

    def test_listAttributes(self):
        self.assertEquals(self.state.listAttributes(),
                          [('pickled state', self.state.state)])

    def test_listItems(self):
        self.assertEquals(self.state.listItems(), None)

    def test_asDict(self):
        self.assertEquals(self.state.asDict(),
                          {'pickled state': self.state.state})


def test_suite():
    this = sys.modules[__name__]
    return unittest.defaultTestLoader.loadTestsFromModule(this)

