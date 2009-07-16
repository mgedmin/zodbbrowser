import unittest
import sys

import transaction
from BTrees.OOBTree import OOBTree
from persistent import Persistent
from zope.app.testing import setup
from zope.app.container.sample import SampleContainer
from zope.interface.verify import verifyObject
from zope.interface import implements
from zope.component import provideAdapter
from zope.traversing.interfaces import IContainmentRoot

from zodbbrowser.interfaces import IStateInterpreter
from zodbbrowser.history import getHistory, loadState
from zodbbrowser.state import (GenericState,
                               EmptyOOBTreeState,
                               OOBTreeState,
                               PersistentDictState,
                               PersistentMappingState,
                               FallbackState)
from zodbbrowser.tests.realdb import RealDatabaseTest


class Frob(object):
    pass


class Root(Persistent, SampleContainer):
    implements(IContainmentRoot)


class Folder(Persistent, SampleContainer):
    pass


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
        self.foo = self.root['foo'] = Folder()
        self.bar = self.root['foo']['bar'] = Folder()
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
        self.tids = [d['tid'] for d in getHistory(self.tree)]

    def getState(self, tid):
        state = loadState(self.tree, tid)
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

