import inspect

from ZODB.utils import tid_repr
from persistent import Persistent


def getHistory(obj):
    """Load history of changes made to a Persistent object.

    Returns a list of dictionaries, from latest revision to the oldest.
    The dicts have various interesting pieces of data, such as:

        tid -- transaction ID (a byte string, usually 8 bytes)
        time -- transaction timestamp (number of seconds since the Unix epoch)
        user_name -- name of the user responsible for the change
        description -- short description (often a URL)

    Probably only works with FileStorage and ZEO ClientStorage.
    """
    assert isinstance(obj, Persistent)
    storage = obj._p_jar._storage
    oid = obj._p_oid
    history = None
    all_of_it = 999999999999 # ought to be sufficient
    # XXX OMG ouch the APIs are different
    if 'length' in inspect.getargspec(storage.history)[0]: # ZEO
        history = storage.history(oid, version='', length=all_of_it)
    else: # FileStorage
        history = storage.history(oid, size=all_of_it)
    return history


def loadState(obj, tid=None):
    """Load (old) state of a Persistent object."""
    assert isinstance(obj, Persistent)
    conn = obj._p_jar
    # sadly ZODB has no API for get revision at or before tid
    for record in getHistory(obj):
        if tid is None or record['tid'] <= tid:
            return conn.oldstate(obj, record['tid'])
    raise Exception('%r did not exist in or before transaction %r' % (
                        obj, tid_repr(tid)))

