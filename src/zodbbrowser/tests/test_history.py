import unittest
import sys

import transaction
from zodbbrowser.tests.realdb import RealDatabaseTest
from zodbbrowser.history import getHistory


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


def test_suite():
    this = sys.modules[__name__]
    return unittest.defaultTestLoader.loadTestsFromModule(this)

