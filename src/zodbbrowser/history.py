import inspect

from zope.proxy import removeAllProxies


class ZodbObjectHistory(object):

    def __init__(self, obj):
        self.obj = removeAllProxies(obj)
        self.storage = self.obj._p_jar._storage
        self.oid = self.obj._p_oid
        self.history = None
        self._load()

    def __len__(self):
        return len(self.history)

    def _load(self):
        """Load history of changes made to a Persistent object.

        Returns a list of dictionaries, from latest revision to the oldest.
        The dicts have various interesting pieces of data, such as:

            tid -- transaction ID (a byte string, usually 8 bytes)
            time -- transaction timestamp (number of seconds since the Unix epoch)
            user_name -- name of the user responsible for the change
            description -- short description (often a URL)

        Probably only works with FileStorage and ZEO ClientStorage.
        """
        all_of_it = 999999999999 # ought to be sufficient
        # XXX OMG ouch the APIs are different
        if 'length' in inspect.getargspec(self.storage.history)[0]: # ZEO
            self.history = self.storage.history(self.oid,
                                                version='', length=all_of_it)
        else: # FileStorage
            self.history = self.storage.history(self.oid, size=all_of_it)

    def __getitem__(self, item):
        return self.history[item]

