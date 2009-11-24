import unittest

import transaction
from BTrees.OOBTree import OOBTree
from zope.interface.verify import verifyObject
from zope.component import provideAdapter
from zope.app.folder import Folder
from zope.app.container.btree import BTreeContainer
from zope.app.testing import setup

from zodbbrowser.interfaces import IStateInterpreter, IObjectHistory
from zodbbrowser.history import ZodbObjectHistory
from zodbbrowser.btreesupport import (
        OOBTreeHistory,
        OOBTreeState,
        EmptyOOBTreeState, 
        FolderState,
        BTreeContainerState,
)
from zodbbrowser.tests.realdb import RealDatabaseTest


class TestOOBTreeState(unittest.TestCase):

    def setUp(self):
        setup.placelessSetUp()
        provideAdapter(ZodbObjectHistory)
        tree = OOBTree()
        tree[1] = 42
        tree[2] = 23
        tree[3] = 17
        state = tree.__getstate__()
        self.state = EmptyOOBTreeState(None, state, None)

    def tearDown(self):
        setup.placelessTearDown()

    def test_interface_compliance(self):
        verifyObject(IStateInterpreter, self.state)

    def test_getName(self):
        self.assertEquals(self.state.getName(), None)

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
        setup.placelessSetUp()
        provideAdapter(ZodbObjectHistory)
        RealDatabaseTest.setUp(self)
        self.tree = self.conn.root()['tree'] = OOBTree()
        for i in range(0, 1000):
            self.tree[i] = -1
        transaction.commit()
        for i in range(0, 1000, 2):
            self.tree[i] = 1
        transaction.commit()
        self.tids = [d['tid'] for d in IObjectHistory(self.tree)]

    def tearDown(self):
        RealDatabaseTest.tearDown(self)
        setup.placelessTearDown()

    def getState(self, tid):
        state = IObjectHistory(self.tree).loadState(tid)
        return OOBTreeState(self.tree, state, tid)

    def test_current_state(self):
        state = self.getState(None)
        self.assertEquals(sum(state.asDict().values()), 0)

    def test_historical_state(self):
        state = self.getState(self.tids[-1])
        self.assertEquals(sum(state.asDict().values()), -1000)

    def test_historical_state_does_not_leave_modified_caches(self):
        state = self.getState(self.tids[-1])
        self.assertEquals(sum(state.asDict().values()), -1000)
        self.assertEquals(sum(self.tree.values()), 0)


class TestLargeOOBTreeHistory(RealDatabaseTest):

    def setUp(self):
        setup.placelessSetUp()
        provideAdapter(ZodbObjectHistory)
        provideAdapter(OOBTreeHistory)
        RealDatabaseTest.setUp(self)
        self.tree = self.conn.root()['tree'] = OOBTree()
        for i in range(0, 100):
            self.tree[i] = i
            transaction.commit()

    def tearDown(self):
        RealDatabaseTest.tearDown(self)
        setup.placelessTearDown()

    def getState(self, tid):
        state = IObjectHistory(self.tree).loadState(tid)
        return OOBTreeState(self.tree, state, tid)

    def test_full_history(self):
        tids = [d['tid'] for d in IObjectHistory(self.tree)][::-1]
        for i in range(0, 100):
            state = self.getState(tids[i])
            self.assertEquals(len(state.asDict()), i + 1)

    def test_rollback_to_last_state_does_nothing(self):
        history = IObjectHistory(self.tree)
        history.rollback(history.lastChange())
        self.assertEquals(len(self.tree), 100)
        # BTrees play funky games with cached lenghts, make sure the content
        # matches that
        self.assertEquals(len(list(self.tree)), 100)
        self.assertFalse(self.tree._p_changed)

    def test_rollback_changes_buckets(self):
        history = OOBTreeHistory(self.tree)
        history.rollback(history._lastRealChange())
        # therefore the state of the tree itself stays constant, but
        # one or more of its buckets change
        self.assertNotEquals(len(self.tree), 100)
        self.assertNotEquals(len(list(self.tree)), 100)
        self.assertFalse(self.tree._p_changed)

    def test_rollback(self):
        history = OOBTreeHistory(self.tree)
        tid = history[len(history) / 2]['tid']
        history.rollback(tid)
        self.assertEquals(len(self.tree), 50)
        # BTrees play funky games with cached lenghts, make sure the content
        # matches that
        self.assertEquals(len(list(self.tree)), 50)
        self.assertTrue(self.tree._p_changed)


class TestEmptyOOBTreeState(unittest.TestCase):

    def setUp(self):
        self.state = EmptyOOBTreeState(None, None, None)

    def test_interface_compliance(self):
        verifyObject(IStateInterpreter, self.state)

    def test_getName(self):
        self.assertEquals(self.state.getName(), None)

    def test_getParent(self):
        self.assertEquals(self.state.getParent(), None)

    def test_listAttributes(self):
        self.assertEquals(self.state.listAttributes(), None)

    def test_listItems(self):
        self.assertEquals(list(self.state.listItems()), [])

    def test_asDict(self):
        self.assertEquals(dict(self.state.asDict()), {})


class TestFolderState(RealDatabaseTest):

    def setUp(self):
        setup.placelessSetUp()
        provideAdapter(OOBTreeState)
        provideAdapter(ZodbObjectHistory)
        RealDatabaseTest.setUp(self)
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


class TestBTreeContainerState(RealDatabaseTest):

    def setUp(self):
        setup.placelessSetUp()
        provideAdapter(OOBTreeState)
        provideAdapter(ZodbObjectHistory)
        RealDatabaseTest.setUp(self)
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

