import logging

from persistent.dict import PersistentDict
from persistent.list import PersistentList
from persistent.mapping import PersistentMapping
from zope.component import adapts, getMultiAdapter
from zope.interface import implements, Interface
from zope.interface.interfaces import IInterface
from zope.interface.interface import InterfaceClass
from zope.proxy import removeAllProxies
from zope.traversing.interfaces import IContainmentRoot
from ZODB.utils import u64

import zope.interface.declarations

# be compatible with Zope 3.4, but prefer the modern package structure
try:
    from zope.container.sample import SampleContainer
except ImportError:
    from zope.app.container.sample import SampleContainer # BBB
try:
    from zope.container.ordered import OrderedContainer
except ImportError:
    from zope.app.container.ordered import OrderedContainer # BBB
try:
    from zope.container.contained import ContainedProxy
except ImportError:
    from zope.app.container.contained import ContainedProxy # BBB

from zodbbrowser.interfaces import IStateInterpreter, IObjectHistory


log = logging.getLogger(__name__)


real_Provides = zope.interface.declarations.Provides


def install_provides_hack():
    """Monkey-patch zope.interface.Provides with a more lenient version.

    A common result of missing modules in sys.path is that you cannot
    unpickle objects that have been marked with directlyProvides() to
    implement interfaces that aren't currently available.  Those interfaces
    are replaced by persistent broken placeholders, which aren classes,
    not interfaces, and aren't iterable, causing TypeErrors during unpickling.
    """
    zope.interface.declarations.Provides = Provides


def flatten_interfaces(args):
    result = []
    for a in args:
        if isinstance(a, (list, tuple)):
            result.extend(flatten_interfaces(a))
        elif IInterface.providedBy(a):
            result.append(a)
        else:
            log.warning('  replacing %s with a placeholder', repr(a))
            result.append(InterfaceClass(a.__name__,
                            __module__='broken ' + a.__module__))
    return result


def Provides(cls, *interfaces):
    try:
        return real_Provides(cls, *interfaces)
    except TypeError, e:
        log.warning('Suppressing TypeError while unpickling Provides: %s', e)
        args = flatten_interfaces(interfaces)
        return real_Provides(cls, *args)


class ZodbObjectState(object):
    implements(IStateInterpreter)

    def __init__(self, obj, tid=None, _history=None):
        self.obj = removeAllProxies(obj)
        if _history is None:
            _history = IObjectHistory(self.obj)
        else:
            assert _history._obj is self.obj
        self.history = _history
        self.tid = None
        self.requestedTid = tid
        self.loadError = None
        self.pickledState = ''
        self._load()

    def _load(self):
        self.tid = self.history.lastChange(self.requestedTid)
        try:
            self.pickledState = self.history.loadStatePickle(self.tid)
            loadedState = self.history.loadState(self.tid)
        except Exception, e:
            self.loadError = "%s: %s" % (e.__class__.__name__, e)
            self.state = LoadErrorState(self.loadError, self.requestedTid)
        else:
            self.state = getMultiAdapter((self.obj, loadedState,
                                         self.requestedTid),
                                         IStateInterpreter)

    def getError(self):
        return self.loadError

    def listAttributes(self):
        return self.state.listAttributes()

    def listItems(self):
        return self.state.listItems()

    def getParent(self):
        return self.state.getParent()

    def getName(self):
        name = self.state.getName()
        if name is None:
            # __name__ is not in the pickled state, but it may be defined
            # via other means (e.g. class attributes, custom __getattr__ etc.)
            try:
                name = getattr(self.obj, '__name__', None)
            except Exception:
                # Ouch.  Oh well, we can't determine the name.
                pass
        return name

    def asDict(self):
        return self.state.asDict()

    # These are not part of IStateInterpreter

    def getObjectId(self):
        return u64(self.obj._p_oid)

    def isRoot(self):
        return IContainmentRoot.providedBy(self.obj)

    def getParentState(self):
        parent = self.getParent()
        if parent is None:
            return None
        else:
            return ZodbObjectState(parent, self.requestedTid)


class LoadErrorState(object):
    """Placeholder for when an object's state could not be loaded"""
    implements(IStateInterpreter)

    def __init__(self, error, tid):
        self.error = error
        self.tid = tid

    def getError(self):
        return self.error

    def getName(self):
        return None

    def getParent(self):
        return None

    def listAttributes(self):
        return []

    def listItems(self):
        return None

    def asDict(self):
        return {}


class GenericState(object):
    """Most persistent objects represent their state as a dict."""
    adapts(Interface, dict, None)
    implements(IStateInterpreter)

    def __init__(self, type, state, tid):
        self.state = state
        self.tid = tid

    def getError(self):
        return None

    def getName(self):
        return self.state.get('__name__')

    def getParent(self):
        return self.state.get('__parent__')

    def listAttributes(self):
        return self.state.items()

    def listItems(self):
        return None

    def asDict(self):
        return self.state


class PersistentMappingState(GenericState):
    """Convenient access to a persistent mapping's items."""
    adapts(PersistentMapping, dict, None)

    def listItems(self):
        return sorted(self.state.get('data', {}).items())


if PersistentMapping is PersistentDict:
    # ZODB 3.9 deprecated PersistentDict and made it an alias for
    # PersistentMapping.  I don't know a clean way to conditionally disable the
    # <adapter> directive in ZCML to avoid conflicting configuration actions,
    # therefore I'll register a decoy adapter registered for a decoy class.
    # This adapter will never get used.

    class DecoyPersistentDict(PersistentMapping):
        """Decoy to avoid ZCML errors while supporting both ZODB 3.8 and 3.9."""

    class PersistentDictState(PersistentMappingState):
        """Decoy to avoid ZCML errors while supporting both ZODB 3.8 and 3.9."""
        adapts(DecoyPersistentDict, dict, None)

else:
    class PersistentDictState(PersistentMappingState):
        """Convenient access to a persistent dict's items."""
        adapts(PersistentDict, dict, None)


class SampleContainerState(GenericState):
    """Convenient access to a SampleContainer's items"""
    adapts(SampleContainer, dict, None)

    def listItems(self):
        data = self.state.get('_SampleContainer__data')
        if not data:
            return []
        # data will be something persistent, maybe a PersistentDict, maybe a
        # OOBTree -- SampleContainer itself uses a plain Python dict, but
        # subclasses are supposed to overwrite the _newContainerData() method
        # and use something persistent.
        loadedstate = IObjectHistory(data).loadState(self.tid)
        return getMultiAdapter((data, loadedstate, self.tid),
                               IStateInterpreter).listItems()


class OrderedContainerState(GenericState):
    """Convenient access to an OrderedContainer's items"""
    adapts(OrderedContainer, dict, None)

    def listItems(self):
        # Now this is tricky: we want to construct a small object graph using
        # old state pickles without ever calling __setstate__ on a real
        # Persistent object, as _that_ would poison ZODB in-memory caches
        # in a nasty way (LP #487243).
        container = OrderedContainer()
        container.__setstate__(self.state)
        old_data_state = IObjectHistory(container._data).loadState(self.tid)
        old_order_state = IObjectHistory(container._order).loadState(self.tid)
        container._data = PersistentDict()
        container._data.__setstate__(old_data_state)
        container._order = PersistentList()
        container._order.__setstate__(old_order_state)
        return container.items()


class ContainedProxyState(GenericState):
    adapts(ContainedProxy, tuple, None)

    def __init__(self, proxy, state, tid):
        GenericState.__init__(self, proxy, state, tid)
        self.proxy = proxy

    def getName(self):
        return self.state[1]

    def getParent(self):
        return self.state[0]

    def listAttributes(self):
        return [('__name__', self.getName()),
                ('__parent__', self.getParent()),
                ('proxied_object', self.proxy.__getnewargs__()[0])]

    def listItems(self):
        return []

    def asDict(self):
        return dict(self.listAttributes())


class FallbackState(object):
    """Fallback when we've got no idea how to interpret the state"""
    adapts(Interface, Interface, None)
    implements(IStateInterpreter)

    def __init__(self, type, state, tid):
        self.state = state

    def getError(self):
        return None

    def getName(self):
        return None

    def getParent(self):
        return None

    def listAttributes(self):
        return [('pickled state', self.state)]

    def listItems(self):
        return None

    def asDict(self):
        return dict(self.listAttributes())

