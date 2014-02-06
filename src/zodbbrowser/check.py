#!/usr/bin/env python
import logging
import optparse
import sys

from zodbbrowser.standalone import open_database
from zodbbrowser.references import ReferencesDatabase

def iter_database(db):
    """Iter over records located inside the database.
    """
    for transaction in db._storage.iterator():
        for record in transaction:
            yield record

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
    parser.add_option('--save-references', metavar='FILE.DB', dest='save',
                      help='save computed information for reuse')
    parser.add_option('--rw', action='store_false', dest='readonly',
                      default=True,
                      help='open the database read-write (default: read-only)')
    opts, args = parser.parse_args(args)
    try:
        db = open_database(opts)
    except ValueError as e:
        parser.error(e.msg)

    references = ReferencesDatabase(opts.save or ':memory:')
    if references.checkDatabase():
        parser.error('database already initialized')
    references.createDatabase()
    # XXX We should implement other iteration methods over the
    # database depending on the database capabilities.
    references.analyzeRecords(iter_database(db))

    broken_oids = references.getBrokenOIDs()
    if broken_oids:
        # We have broken objects
        print '{0} broken objects'.format(len(broken_oids))
        sys.exit(1)
    print 'no broken objects'
    sys.exit(0)


if __name__ == '__main__':
    main()
