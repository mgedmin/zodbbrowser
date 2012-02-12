"""
Ad-hoc caching, because uncached zodbbrowser is slow and sad.
"""

import time
import weakref

MINUTES = 60
HOURS = 60 * MINUTES

STORAGE_TIDS = weakref.WeakKeyDictionary()


def expired(cache_dict, cache_for):
    if 'last_update' not in cache_dict:
        return True
    return cache_dict['last_update'] > time.time() - cache_for


def getStorageTids(storage, cache_for=5*MINUTES):
    cache_dict = STORAGE_TIDS.setdefault(storage, {})
    if expired(cache_dict, cache_for):
        if cache_dict.get('tids'):
            first = cache_dict['tids'][-1]
            last = cache_dict['tids'][-1]
            try:
                first_record = storage.iterator().next()
            except StopIteration:
                first_record = None
            if first_record and first_record.tid == first:
                # okay, look for new transactions appended at the end
                new = [t.tid for t in storage.iterator(start=last)]
                if new and new[0] == last:
                    del new[0]
                cache_dict['tids'].extend(new)
            else:
                # first record changed, we must've packed the DB
                cache_dict['tids'] = [t.tid for t in storage.iterator()]
        else:
            cache_dict['tids'] = [t.tid for t in storage.iterator()]
        cache_dict['last_update'] = time.time()
    return cache_dict['tids']

