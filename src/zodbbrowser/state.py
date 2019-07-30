import logging

from persistent.dict import PersistentDict
from persistent.list import PersistentList
from persistent.mapping import PersistentMapping
from zope.component import adapter, getMultiAdapter
from zope.interface import implementer, Interface
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
from zodbbrowser.history import ZodbObjectHistory


log = logging.getLogger(__name__)


real_Provides = zope.interface.declarations.Provides


def install_provides_hack():
    """Monkey-patch zope.interface.Provides with a more lenient version.

    A common result of missing modules in sys.path is that you cannot
    unpickle objects that have been marked with directlyProvides() to
    implement interfaces that aren't currently available.  Those interfaces
    are replaced by persistent broken placeholders, which are classes,
    not interfaces, and aren't iterable, causing TypeErrors during unpickling.
    """
    zope.interface.declarations.Provides = Provides


def uninstall_provides_hack():
    """Undo the monkey-patch installed by install_provides_hack()."""
    zope.interface.declarations.Provides = real_Provides


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
    except TypeError as e:
        log.warning('Suppressing TypeError while unpickling Provides: %s', e)
        args = flatten_interfaces(interfaces)
        return real_Provides(cls, *args)


@implementer(IStateInterpreter)
class ZodbObjectState(object):

    def __init__(self, obj, tid=None, _history=None):
        self.obj = removeAllProxies(obj)
        if _history is None:
            # Not using IObjectHistory(self.obj) because LP#1185175
            _history = ZodbObjectHistory(self.obj)
        else:
            assert _history._obj is self.obj
        self.history = _history
        self.tid = None
        self.requestedTid = tid
        self.loadError = None
        self.pickledState = ''
        self._load()

    def _load(self):
        try:
            self.tid = self.history.lastChange(self.requestedTid)
            self.pickledState = self.history.loadStatePickle(self.tid)
            loadedState = self.history.loadState(self.tid)
            self.state = getMultiAdapter((self.obj, loadedState,
                                         self.requestedTid),
                                         IStateInterpreter)
        except Exception as e:
            self.loadError = "%s: %s" % (e.__class__.__name__, e)
            self.state = LoadErrorState(self.loadError, self.requestedTid)

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


@implementer(IStateInterpreter)
class LoadErrorState(object):
    """Placeholder for when an object's state could not be loaded"""

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


@adapter(Interface, dict, None)
@implementer(IStateInterpreter)
class GenericState(object):
    """Most persistent objects represent their state as a dict."""

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


@adapter(PersistentMapping, dict, None)
class PersistentMappingState(GenericState):
    """Convenient access to a persistent mapping's items."""

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

    @adapter(DecoyPersistentDict, dict, None)
    class PersistentDictState(PersistentMappingState):
        """Decoy to avoid ZCML errors while supporting both ZODB 3.8 and 3.9."""

else:  # pragma: nocover
    @adapter(PersistentDict, dict, None)
    class PersistentDictState(PersistentMappingState):
        """Convenient access to a persistent dict's items."""


@adapter(SampleContainer, dict, None)
class SampleContainerState(GenericState):
    """Convenient access to a SampleContainer's items"""

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


@adapter(OrderedContainer, dict, None)
class OrderedContainerState(GenericState):
    """Convenient access to an OrderedContainer's items"""

    def listItems(self):
        # Now this is tricky: we want to construct a small object graph using
        # old state pickles without ever calling __setstate__ on a real
        # Persistent object, as _that_ would poison ZODB in-memory caches
        # in a nasty way (LP #487243).
        container = OrderedContainer()
        container.__setstate__(self.state)
        if isinstance(container._data, PersistentDict):
            old_data_state = IObjectHistory(container._data).loadState(self.tid)
            container._data = PersistentDict()
            container._data.__setstate__(old_data_state)
        if isinstance(container._order, PersistentList):
            old_order_state = IObjectHistory(container._order).loadState(self.tid)
            container._order = PersistentList()
            container._order.__setstate__(old_order_state)
        return container.items()


@adapter(ContainedProxy, tuple, None)
class ContainedProxyState(GenericState):

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


@adapter(Interface, Interface, None)
@implementer(IStateInterpreter)
class FallbackState(object):
    """Fallback when we've got no idea how to interpret the state"""

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

