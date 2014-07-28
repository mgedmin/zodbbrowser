import cPickle
import io
import logging
import optparse
import sys
import types

import ZODB.broken
from zodbbrowser.standalone import open_database


def is_broken(symb):
    """Return true if the given symbol is broken.
    """
    return (isinstance(symb, types.TypeType) and
            ZODB.broken.Broken in symb.__mro__)


class Search(object):

    def __init__(self, classes=[]):
        self.classes = classes

    def validate(self, cls_info, cls):
        fullname = '.'.join(cls_info)
        if is_broken(cls):
            print 'Broken class {}'.format(fullname)
        if self.classes and fullname in self.classes:
            print 'Instance of {} found'.format(fullname)

    def read_class_meta(self, class_meta):
        if isinstance(class_meta, tuple):
            symb, _ = class_meta
            if isinstance(symb, tuple):
                self.validate(symb, ZODB.broken.find_global(*symb))
            else:
                symb_info = (getattr(symb, '__module__', None),
                             getattr(symb, '__name__', None))
                self.validate(symb_info, symb)

    def find_global(self, *cls_info):
        cls = ZODB.broken.find_global(*cls_info)
        self.validate(cls_info, cls)
        return cls

    def persistent_load(self, reference):
        cls_info = None
        if isinstance(reference, tuple):
            oid, cls_info = reference
        if isinstance(reference, list):
            mode, information = reference
            if mode == 'm':
                db, oid, cls_info = information
        if isinstance(cls_info, tuple):
            self.find_global(cls_info)


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
    parser.add_option('--data', action="store_true",
                      dest="data", default=False,
                      help='check inside persisted data too')
    opts, args = parser.parse_args(args)
    try:
        db = open_database(opts)
    except ValueError as error:
        parser.error(error.args[0])

    search = Search(args)
    for transaction in db._storage.iterator():
        for record in transaction:
            unpickler = cPickle.Unpickler(io.BytesIO(record.data))
            unpickler.persistent_load = search.persistent_load
            unpickler.find_global = search.find_global
            search.read_class_meta(unpickler.load())
            if opts.data:
                unpickler.load()
