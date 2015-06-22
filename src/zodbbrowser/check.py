#!/usr/bin/env python
import logging
import optparse
import os
import sys
import tempfile

from zodbbrowser.standalone import open_database
from zodbbrowser.references import ReferencesDatabase


def iter_database(db):
    """Iter over records located inside the database.
    """
    for transaction in db.storage.iterator():
        for record in transaction:
            yield record


def main(args=None):
    logging.basicConfig(format="%(message)s")

    if args is None:
        args = sys.argv[1:]
    else:
        args = args + sys.argv[1:]

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
                      help='save computed references in a database for reuse')
    parser.add_option('--override-references', action="store_true",
                      dest="override", default=False,
                      help='override a reference database')
    parser.add_option('--rw', action='store_false', dest='readonly',
                      default=True,
                      help='open the database read-write (default: read-only)')
    opts, args = parser.parse_args(args)
    try:
        db = open_database(opts)
    except ValueError as error:
        parser.error(error.args[0])

    try:
        support = db.storage.supportsVersions()
    except AttributeError:
        support = True
    if support:
        parser.error('only supports non-versionned databases')

    database_file = opts.save
    if not database_file:
        # If we don't save, create a temporary file for the database.
        database_descriptor, database_file = tempfile.mkstemp('zodbchecker')
    references = ReferencesDatabase(database_file)
    if opts.save:
        if opts.override and os.path.isfile(opts.save):
            os.unlink(opts.save)
        elif references.checkDatabase():
            parser.error('database already initialized')
    references.createDatabase()
    references.analyzeRecords(iter_database(db))

    broken_oids = references.getBrokenOIDs()
    if not opts.save:
        # Cleanup temporary file
        os.unlink(database_file)

    if broken_oids:
        # We have broken objects
        print '{0} broken objects'.format(len(broken_oids))
        sys.exit(1)
    print 'no broken objects'
    sys.exit(0)


if __name__ == '__main__':
    main()
