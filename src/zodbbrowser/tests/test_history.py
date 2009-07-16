import unittest
import sys

import transaction
from persistent import Persistent
from zodbbrowser.tests.realdb import RealDatabaseTest
from zodbbrowser.history import getHistory, loadState


class PersistentObject(Persistent):
    pass # we need a subclass so we get a __dict__


class TestFileStorage(RealDatabaseTest):

    def test_no_history(self):
        obj = self.conn.root()
        history = getHistory(obj)
        self.assertEquals(len(history), 1)
        self.assertTrue('tid' in history[0])
        self.assertTrue('time' in history[0])
        self.assertTrue('user_name' in history[0])
        self.assertTrue('description' in history[0])

    def test_some_history(self):
        obj = self.conn.root()
        for n in range(10):
            obj[n] = n
            transaction.commit()
        history = getHistory(obj)
        self.assertEquals(len(history), 11)


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
        state = loadState(self.adam)
        self.assertEquals(state, dict(laptop='ThinkPad T61'))

    def test_exact_state(self):
        tid = getHistory(self.adam)[1]['tid']
        state = loadState(self.adam, tid)
        self.assertEquals(state, dict(laptop='ThinkPad T42'))

    def test_earlier_state(self):
        tid = getHistory(self.eve)[0]['tid']
        state = loadState(self.adam, tid)
        self.assertEquals(state, dict(laptop='ThinkPad T23'))

    def test_error_handling(self):
        tid = getHistory(self.adam)[-1]['tid']
        try:
            loadState(self.eve, tid)
        except Exception, e:
            self.assertTrue("did not exist in or before" in str(e))
        else:
            self.fail("did not raise")


def test_suite():
    this = sys.modules[__name__]
    return unittest.defaultTestLoader.loadTestsFromModule(this)

