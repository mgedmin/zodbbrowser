import unittest
import time

from zodbbrowser.cache import expired, MINUTES


class TestCache(unittest.TestCase):

    def test_expired(self):
        now = time.time()
        self.assertTrue(expired({}, 5 * MINUTES))
        self.assertFalse(expired({'last_update': now - 1}, 5 * MINUTES))
        self.assertTrue(expired({'last_update': now - 1 - 5 * MINUTES}, 5 * MINUTES))

