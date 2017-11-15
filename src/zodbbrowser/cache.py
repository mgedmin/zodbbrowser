"""
Ad-hoc caching, because uncached zodbbrowser is slow and sad.
"""

import time
import weakref
from contextlib import closing


MINUTES = 60
HOURS = 60 * MINUTES

STORAGE_TIDS = weakref.WeakKeyDictionary()


def expired(cache_dict, cache_for):
    if 'last_update' not in cache_dict:
        return True
    return time.time() > cache_dict['last_update'] + cache_for


def getStorageTids(storage, cache_for=5 * MINUTES):
    cache_dict = STORAGE_TIDS.setdefault(storage, {})
    if expired(cache_dict, cache_for):
        if cache_dict.get('tids'):
            first = cache_dict['tids'][0]
            last = cache_dict['tids'][-1]
            try:
                with closing(storage.iterator()) as it:
                    first_record = next(it)
            except StopIteration:  # pragma: nocover
                # I don't think this is possible -- a database always
                # has at least one transaction.  But, hey, maybe somebody
                # truncated the file or something?
                first_record = None
            if first_record and first_record.tid == first:
                # okay, look for new transactions appended at the end
                with closing(storage.iterator(start=last)) as it:
                    new = [t.tid for t in it]
                if new and new[0] == last:
                    del new[0]
                cache_dict['tids'].extend(new)
            else:
                # first record changed, we must've packed the DB
                with closing(storage.iterator()) as it:
                    cache_dict['tids'] = [t.tid for t in it]
        else:
            with closing(storage.iterator()) as it:
                cache_dict['tids'] = [t.tid for t in it]
        cache_dict['last_update'] = time.time()
    return cache_dict['tids']

