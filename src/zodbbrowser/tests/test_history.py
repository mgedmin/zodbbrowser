import transaction
from persistent import Persistent
from persistent.dict import PersistentDict
from zope.interface.verify import verifyObject
from zope.component import provideAdapter

from zodbbrowser.tests.realdb import RealDatabaseTest
from zodbbrowser.history import ZodbObjectHistory, ZodbHistory
from zodbbrowser.history import getIterableStorage
from zodbbrowser.interfaces import IObjectHistory, IDatabaseHistory


class PersistentObject(Persistent):
    pass # we need a subclass so we get a __dict__


class TestFileStorage(RealDatabaseTest):

    def setUp(self):
        RealDatabaseTest.setUp(self)
        self.obj = self.conn.root()['obj'] = PersistentDict()
        transaction.commit()

    def test_no_history(self):
        obj = self.obj
        history = ZodbObjectHistory(obj)
        verifyObject(IObjectHistory, history)
        self.assertEqual(len(history), 1)
        self.assertTrue('tid' in history[0])
        self.assertTrue('time' in history[0])
        self.assertTrue('user_name' in history[0])
        self.assertTrue('description' in history[0])
        self.assertNotIsInstance(history[0]['user_name'], bytes)
        self.assertNotIsInstance(history[0]['description'], bytes)

    def test_some_history(self):
        obj = self.obj
        for n in range(10):
            obj[n] = n
            transaction.commit()
        history = ZodbObjectHistory(obj)
        self.assertEqual(len(history), 11)


class WorkloadMixin(object):

    def commitSomeStuff(self):
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


class TestLoadState(WorkloadMixin, RealDatabaseTest):

    def setUp(self):
        RealDatabaseTest.setUp(self)
        self.commitSomeStuff()

    def test_latest_state(self):
        state = ZodbObjectHistory(self.adam).loadState()
        self.assertEqual(state, dict(laptop='ThinkPad T61'))

    def test_exact_state(self):
        tid = ZodbObjectHistory(self.adam)[1]['tid']
        state = ZodbObjectHistory(self.adam).loadState(tid)
        self.assertEqual(state, dict(laptop='ThinkPad T42'))

    def test_earlier_state(self):
        tid = ZodbObjectHistory(self.eve)[0]['tid']
        state = ZodbObjectHistory(self.adam).loadState(tid)
        self.assertEqual(state, dict(laptop='ThinkPad T23'))

    def test_error_handling(self):
        tid = ZodbObjectHistory(self.adam)[-1]['tid']
        history = ZodbObjectHistory(self.eve)
        try:
            history.loadState(tid)
        except KeyError as e:
            self.assertTrue("did not exist in or before" in str(e))
        else:
            self.fail("did not raise")

    def test_rollback_does_nothing(self):
        history = ZodbObjectHistory(self.adam)
        history.rollback(history.lastChange())
        self.assertEqual(self.adam.laptop, 'ThinkPad T61')
        self.assertFalse(self.adam._p_changed)

    def test_rollback(self):
        history = ZodbObjectHistory(self.adam)
        history.rollback(history[-2]['tid'])
        self.assertEqual(self.adam.laptop, 'ThinkPad T23')
        self.assertTrue(self.adam._p_changed)


class TestZodbHistory(WorkloadMixin, RealDatabaseTest):

    def setUp(self):
        super(TestZodbHistory, self).setUp()
        provideAdapter(getIterableStorage)

    def test_no_history(self):
        history = ZodbHistory(self.conn)
        self.addCleanup(history.cleanup)
        verifyObject(IDatabaseHistory, history)
        self.assertEqual(len(history), 1)
        self.assertEqual(len(history.tids), 1)
        self.assertEqual(len(list(history)), 1)
        self.assertEqual([tr.tid for tr in history],
                         [tr.tid for tr in history[-5:]])
        self.assertEqual(history[10:], [])
        self.assertEqual(history[0].tid, history.tids[0])

    def test_some_history(self):
        self.commitSomeStuff()
        history = ZodbHistory(self.conn)
        self.addCleanup(history.cleanup)
        verifyObject(IDatabaseHistory, history)
        self.assertEqual(len(history), 7)
        self.assertEqual(len(list(history)), 7)
        self.assertEqual([tr.tid for tr in history][-5:],
                         [tr.tid for tr in history[-5:]])

