import unittest
import time

import transaction

from zodbbrowser.cache import expired, MINUTES, getStorageTids
from zodbbrowser.tests.realdb import RealDatabaseTest


class TestCache(unittest.TestCase):

    def test_expired(self):
        now = time.time()
        self.assertTrue(expired({}, 5 * MINUTES))
        self.assertFalse(expired({'last_update': now - 1}, 5 * MINUTES))
        self.assertTrue(expired({'last_update': now - 1 - 5 * MINUTES}, 5 * MINUTES))


class TestStorageTids(RealDatabaseTest):

    def setUp(self):
        super(TestStorageTids, self).setUp()
        self.root = self.conn.root()
        self.root['adam'] = None
        transaction.commit()
        self.root['eve'] = None
        transaction.commit()

    def test_getStorageTids_no_cache(self):
        tids = getStorageTids(self.storage)
        self.assertEqual(len(tids), 3)

    def test_getStorageTids_cached(self):
        tids = getStorageTids(self.storage)
        tids_again = getStorageTids(self.storage)
        self.assertEqual(tids, tids_again)

    def test_getStorageTids_notices_new_commits_when_cache_expires(self):
        tids = getStorageTids(self.storage)[:]
        self.root['bob'] = None
        transaction.commit()
        tids_again = getStorageTids(self.storage, cache_for=-1)
        self.assertEqual(len(tids_again), len(tids) + 1)

    def test_getStorageTids_notices_db_packing(self):
        tids = getStorageTids(self.storage)  # prime the cache
        time.sleep(0.001)  # hmm, will this help?
        self.packDatabase()
        tids_again = getStorageTids(self.storage, cache_for=-1)
        self.assertEqual(
            len(tids_again), 1,
            'the impossible happened: my code has a bug?  or your clock is ticking backwards?\n'
            'tids:       {tids!r}\n'
            'tids_again: {tids_again!r}\n'
            'should be:  {should_be!r}\n'.format(
                tids=tids,
                tids_again=tids_again,
                should_be=[t.tid for t in self.storage.iterator()],
            )
        )
