#!/usr/bin/env python
import cPickle
import io
import itertools
import gc
import logging
import optparse
import sys
import ZODB.broken

from ZODB.utils import p64, u64
from zodbbrowser.standalone import open_database

def referredoids(data):
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

def check(db):
    forward_references = {}
    back_references = {}

    for transaction in db._storage.iterator():
        for record in transaction:
            refs = map(u64, referredoids(record.data))
            forward_references[u64(record.oid)] = refs
            for oid in refs:
                back_references[oid] = u64(record.oid)

    forward = set(forward_references.iterkeys())
    back = set(back_references.iterkeys())
    broken = back - forward
    if broken:
        # We have broken objects
        print broken
        sys.exit(1)
    print 'no broken objects'
    sys.exit(0)

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
    parser.add_option('--rw', action='store_false', dest='readonly',
                      default=True,
                      help='open the database read-write (default: read-only)')
    opts, args = parser.parse_args(args)
    db = open_database(opts)
    check(db)

if __name__ == '__main__':
    main()
