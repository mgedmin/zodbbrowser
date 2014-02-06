
import sqlite3
import logging

from zope.interface import implements
from zodbbrowser.interfaces import IReferencesDatabase
from ZODB.utils import u64

log = logging.getLogger("zodbbrowser")


class ReferencesDatabase(object):
    implements(IReferencesDatabase)

    def __init__(self, db_name):
        self.db_name = db_name

    def check_database(self):
        """Connect to the database and test it presence.
        """
        try:
            connection = sqlite3.connect(self.db_name)
        except:
            raise ValueError('impossible to open references database')
        cursor = connection.cursor()
        try:
            result = cursor.execute("SELECT count(*) FROM forward_references")
            result.fetchall()
        except sqlite3.OperationalError:
            log.error("Could not find forward_references in "
                      "the reference database.")
            connection.close()
            return False
        try:
            result = cursor.execute("SELECT count(*) FROM backward_references")
            result.fetchall()
        except sqlite3.OperationalError:
            log.error("Could not find backward_references in "
                      "the reference database.")
            connection.close()
            return False
        connection.close()
        return True

    def get_forward_references(self, oid):
        oids = set([])
        connection = sqlite3.connect(self.db_name)
        cursor = connection.cursor()
        result = cursor.execute("""
SELECT target_oid FROM forward_references WHERE source_oid = {0}
        """.format(u64(oid)))
        for oid in result.fetchall():
            oids.add(oid[0])
        return oids

    def get_backward_references(self, oid):
        oids = set([])
        connection = sqlite3.connect(self.db_name)
        cursor = connection.cursor()
        result = cursor.execute("""
SELECT target_oid FROM backward_references WHERE source_oid = {0}
        """.format(u64(oid)))
        for oid in result.fetchall():
            oids.add(oid[0])
        return oids



