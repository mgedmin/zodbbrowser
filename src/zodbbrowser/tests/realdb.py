import unittest
import tempfile
import shutil
import os
import transaction

from ZODB.FileStorage.FileStorage import FileStorage
from ZODB.DB import DB


class RealDatabaseTest(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp('testzodbbrowser')
        self.storage = FileStorage(os.path.join(self.tmpdir, 'Data.fs'))
        self.db = DB(self.storage)
        self.conn = self.db.open()

    def tearDown(self):
        transaction.abort()
        self.conn.close()
        self.db.close()
        self.storage.close()
        shutil.rmtree(self.tmpdir)

