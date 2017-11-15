import unittest
import tempfile
import shutil
import os
import transaction

from ZODB.FileStorage.FileStorage import FileStorage
from ZODB.DB import DB


class RealDatabaseTest(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='test-zodbbrowser-')
        self.addCleanup(shutil.rmtree, self.tmpdir)
        self.storage = FileStorage(os.path.join(self.tmpdir, 'Data.fs'))
        self.addCleanup(self.storage.close)
        self.db = DB(self.storage)
        self.addCleanup(self.db.close)
        self.conn = self.db.open()
        self.addCleanup(self.conn.close)

    def tearDown(self):
        transaction.abort()

    def packDatabase(self):
        self.db.pack()
