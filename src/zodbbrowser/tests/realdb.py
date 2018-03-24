import unittest
import tempfile
import shutil
import os
import transaction

from ZODB.FileStorage.FileStorage import FileStorage
from ZODB.DB import DB


class RealDatabaseTest(unittest.TestCase):

    open_db = True

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='test-zodbbrowser-')
        self.addCleanup(shutil.rmtree, self.tmpdir)
        self.db_filename = os.path.join(self.tmpdir, 'Data.fs')
        if self.open_db:
            self.storage = FileStorage(self.db_filename)
            self.addCleanup(self.storage.close)
            self.db = DB(self.storage)
            self.addCleanup(self.db.close)
            self.conn = self.db.open()
            self.addCleanup(self.conn.close)

    def tearDown(self):
        transaction.abort()

    def packDatabase(self):
        self.db.pack()
