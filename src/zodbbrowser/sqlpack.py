import logging
import optparse
import os
import sys

import ZODB.blob
import ZODB.utils
from zodbbrowser.references import ReferencesDatabase


def list_all_blobs_in(base_dir):
    blobs = set()
    if not base_dir:
        return blobs
    trim_size = len(base_dir.rstrip(os.path.sep)) + 1
    for (directory, _, filenames) in os.walk(base_dir):
        if not filenames or '.layout' in filenames:
            continue
        blobs.add(directory[trim_size:])
    return blobs


def main(args=None):
    logging.basicConfig(format="%(message)s")

    if args is None:
        args = sys.argv[1:]

    parser = optparse.OptionParser(
        'usage: %prog [options]',
        prog='sqlpack',
        description='Generate an SQL file with delete statements to remove '
            'unused objects.')
    parser.add_option('--references', metavar='FILE.DB', dest='refsdb',
                      help='reference information computed by zodbcheck')
    parser.add_option('--blobs', metavar='BLOBS', dest='blobs',
                      help='directory where blobs are stored')
    parser.add_option('--output-sql', metavar='FILE.SQL', dest='outputsql',
                      help='SQL output file', default='pack.sql')
    parser.add_option('--output-sh', metavar='FILE.SH', dest='outputsh',
                      help='shell output file', default='pack.sh')
    opts, args = parser.parse_args(args)
    try:
        refs = ReferencesDatabase(opts.refsdb)
    except ValueError as error:
        parser.error(error.args[0])
    blobs = list_all_blobs_in(opts.blobs)
    compute_blob = None
    if blobs:
        compute_blob = ZODB.blob.FilesystemHelper(
            opts.blobs).layout.oid_to_path
    count_oid = 0
    count_blobs = 0
    with open(opts.outputsh, 'w') as shell:
        shell.write('#!/usr/bin/env bash\n')
        with open(opts.outputsql, 'w') as sql:
            sql.write('BEGIN;\n')
            for oid in refs.getUnUsedOIDs():
                count_oid += 1
                sql.write('DELETE FROM object_state WHERE zoid = {};\n'.format(
                    oid))
                if compute_blob:
                    blob = compute_blob(ZODB.utils.p64(oid))
                    if blob in blobs:
                        count_blobs += 1
                        blobs.remove(blob)
                        shell.write('rm -rf {}\n'.format(blob))
            sql.write('COMMIT;\n')
    print 'Found {} objects and {} blobs to remove.'.format(
        count_oid, count_blobs)
