#!/usr/bin/env python
import cPickle
import io
import logging
import optparse
import sqlite3
import sys

from ZODB.utils import u64
from zodbbrowser.standalone import open_database

def referredoids(data):
    """Analyze a record data an return a set of unique OID referred inside
    this record.
    """
    oids = set()
    refs = []
    unpickler = cPickle.Unpickler(io.BytesIO(data))
    unpickler.persistent_load = refs
    unpickler.noload()
    unpickler.noload()
    for ref in refs:
        if isinstance(ref, tuple):
            oids.add(ref[0])
        elif isinstance(ref, str):
            oids.add(ref)
        else:
            assert isinstance(ref, list)
            oids.add(ref[1][1])
    return oids

def analyze_database(db):
    """Analyze a Zope database and return two dictionnary: one called
    forward_references containing which OID refers which other and a
    second one called backward_references containing a list of which
    OID are referred by which other.

    """
    forward_references = {}
    backward_references = {}

    for transaction in db._storage.iterator():
        for record in transaction:
            current_oid = u64(record.oid)
            referred_oids = map(u64, referredoids(record.data))
            forward_references[current_oid] = referred_oids
            for oid in referred_oids:
                backward_references.setdefault(oid, set([])).add(current_oid)

    return forward_references, backward_references

def save_references(db_name, forward_references, backward_references):
    """Save forward and backward references into an SQLite database.
    """
    connection = sqlite3.connect(db_name)
    cursor = connection.cursor()
    cursor.execute("""
CREATE TABLE IF NOT EXISTS forward_references
(source_oid BIGINT, target_oid BIGINT)
    """)
    cursor.execute("""
CREATE TABLE IF NOT EXISTS backward_references
(source_oid BIGINT, target_oid BIGINT)
    """)
    for source_oid, target_oids in forward_references.iteritems():
        for target_oid in target_oids:
            cursor.execute("""
INSERT INTO forward_references (source_oid, target_oid) VALUES
({0}, {1})
            """.format(source_oid, target_oid))
    for source_oid, target_oids in backward_references.iteritems():
        for target_oid in target_oids:
            cursor.execute("""
INSERT INTO backward_references (source_oid, target_oid) VALUES
({0}, {1})
            """.format(source_oid, target_oid))
    connection.commit()
    connection.close()

def main(args=None):
    logging.basicConfig(format="%(message)s")

    if args is None:
        args = sys.argv[1:]

    parser = optparse.OptionParser(
        'usage: %prog [options] [--db DATA.FS | --zeo ADDRESS | --zconfig FILE]',
        prog='zodbbrowser',
        description='Open a ZODB database and start a web-based browser app.')
    parser.add_option('--zconfig', metavar='FILE',
                      help='use a ZConfig file to specify database')
    parser.add_option('--zeo', metavar='ADDRESS',
                      help='connect to ZEO server instead'
                      ' (host:port or socket name)')
    parser.add_option('--storage', metavar='NAME',
                      help='connect to given ZEO storage')
    parser.add_option('--db', metavar='DATA.FS',
                      help='use given Data.fs file')
    parser.add_option('--save', metavar='FILE.DB',
                      help='save computed information for reuse')
    parser.add_option('--rw', action='store_false', dest='readonly',
                      default=True,
                      help='open the database read-write (default: read-only)')
    opts, args = parser.parse_args(args)
    try:
        db = open_database(opts)
    except ValueError as e:
        parser.error(e.msg)

    forward_references, backward_references = analyze_database(db)

    if opts.save:
        save_references(opts.save, forward_references, backward_references)

    found_oids = set(forward_references.iterkeys())
    referred_oids = set(backward_references.iterkeys())
    broken_oids = referred_oids - found_oids
    if broken_oids:
        # We have broken objects
        print '{0} broken objects'.format(len(broken_oids))
        sys.exit(1)
    print 'no broken objects'
    sys.exit(0)


if __name__ == '__main__':
    main()
