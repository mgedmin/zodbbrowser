
import sqlite3

from ZODB.utils import u64
from ZODB.serialize import referencesf
from zope.interface import implements

from zodbbrowser.interfaces import IReferencesDatabase


def connect(callback):
    """Decorator for the reference database to access the sqlite DB.
    """

    def wrapper(self, *args, **kwargs):
        try:
            connection = sqlite3.connect(self.db_name)
        except:
            raise ValueError('impossible to open references database')
        try:
            result = callback(self, connection, *args, **kwargs)
        except:
            connection.close()
            raise
        return result

    return wrapper


class ReferencesDatabase(object):
    implements(IReferencesDatabase)

    def __init__(self, db_name=':memory:'):
        self.db_name = db_name

    @connect
    def analyzeRecords(self, connection, records):
        cursor = connection.cursor()
        for record in records:
            current_oid = u64(record.oid)
            referred_oids = set(map(u64, referencesf(record.data)))

            for referred_oid in referred_oids or [-1]:
                cursor.execute("""
INSERT INTO links (source_oid, target_oid) VALUES
({0}, {1})
            """.format(current_oid, referred_oid))
        connection.commit()

    @connect
    def createDatabase(self, connection):
        cursor = connection.cursor()
        cursor.execute("""
CREATE TABLE IF NOT EXISTS links
(source_oid BIGINT, target_oid BIGINT)
        """)
        cursor.execute("""
CREATE INDEX IF NOT EXISTS source_oid_index ON links (source_oid)
        """)
        cursor.execute("""
CREATE INDEX IF NOT EXISTS target_oid_index ON links (target_oid)
        """)
        connection.commit()

    @connect
    def checkDatabase(self, connection):
        """Connect to the database and test it presence.
        """
        if self.db_name == ':memory:':
            return False
        cursor = connection.cursor()
        try:
            result = cursor.execute("SELECT count(*) FROM links")
            result.fetchall()
        except sqlite3.OperationalError:
            return False
        return True

    @connect
    def getBrokenOIDs(self, connection):
        oids = set([])
        cursor = connection.cursor()
        result = cursor.execute("""
SELECT a.target_oid FROM links AS a LEFT OUTER JOIN links AS b
ON a.target_oid = b.source_oid
WHERE a.target_oid > -1 AND b.source_oid IS NULL
        """)
        for oid in result.fetchall():
            oids.add(oid[0])
        return oids

    @connect
    def getForwardReferences(self, connection, oid):
        oids = set([])
        cursor = connection.cursor()
        result = cursor.execute("""
SELECT target_oid FROM links
WHERE source_oid = {0} AND target_oid > -1
        """.format(u64(oid)))
        for oid in result.fetchall():
            oids.add(oid[0])
        return oids

    @connect
    def getBackwardReferences(self, connection, oid):
        oids = set([])
        cursor = connection.cursor()
        result = cursor.execute("""
SELECT source_oid FROM links
WHERE target_oid = {0}
        """.format(u64(oid)))
        for oid in result.fetchall():
            oids.add(oid[0])
        return oids



