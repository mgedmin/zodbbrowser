import unittest
import sys

import transaction
from persistent import Persistent
from zodbbrowser.tests.realdb import RealDatabaseTest
from zodbbrowser.history import ZodbObjectHistory


class PersistentObject(Persistent):
    pass # we need a subclass so we get a __dict__


class TestFileStorage(RealDatabaseTest):

    def test_no_history(self):
        obj = self.conn.root()
        history = ZodbObjectHistory(obj)
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
        history = ZodbObjectHistory(obj)
        self.assertEquals(len(history), 11)


def test_suite():
    this = sys.modules[__name__]
    return unittest.defaultTestLoader.loadTestsFromModule(this)

