import logging
import optparse
import sys

from zodbbrowser.references import ReferencesDatabase


def main(args=None):
    logging.basicConfig(format="%(message)s")

    if args is None:
        args = sys.argv[1:]
    else:
        args = args + sys.argv[1:]

    parser = optparse.OptionParser(
        'usage: %prog [options]',
        prog='sqlpack',
        description='Generate an SQL file with delete statements.')
    parser.add_option('--references', metavar='FILE.DB', dest='refsdb',
                      help='reference information computed by zodbcheck')
    opts, args = parser.parse_args(args)
    try:
        refs = ReferencesDatabase(opts.refsdb)
    except ValueError as error:
        parser.error(error.args[0])
    print 'BEGIN;'
    for oid in refs.getUnUsedOIDs():
        print 'DELETE FROM object_state WHERE zoid = {};'.format(oid)
    print 'COMMIT;'
