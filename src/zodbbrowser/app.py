"""
zodbbrowser application
"""

import inspect
import time
from cgi import escape

from BTrees._OOBTree import OOBTree

from ZODB.utils import u64
from persistent import Persistent
from persistent.dict import PersistentDict
from zope.traversing.interfaces import IContainmentRoot
from zope.proxy import removeAllProxies
from zope.component import adapts, getMultiAdapter
from zope.interface import implements
from zope.interface import Interface

# be compatible with Zope 3.4:
try:
    from zope.container.folder import Folder
except ImportError:
    from zope.app.folder import Folder # BBB
try:
    from zope.container.sample import SampleContainer
except ImportError:
    from zope.app.container.sample import SampleContainer # BBB
try:
    from zope.container.btree import BTreeContainer
except ImportError:
    from zope.app.container.btree import BTreeContainer # BBB
try:
    from zope.container.ordered import OrderedContainer
except ImportError:
    from zope.app.container.ordered import OrderedContainer # BBB


class IValueRenderer(Interface):

    def render(self):
        """Render object value to HTML."""


class ZodbObjectAttribute(object):

    def __init__(self, name, value, tid=None):
        self.name = name
        self.value = value
        self.tid = tid

    def rendered_name(self):
        return IValueRenderer(self.name).render(self.tid)

    def rendered_value(self):
        return IValueRenderer(self.value).render(self.tid)


class GenericValue(object):
    adapts(Interface)
    implements(IValueRenderer)

    def __init__(self, context):
        self.context = context

    def render(self, tid=None, limit=200):
        text = repr(self.context)
        if len(text) > limit:
            text = escape(text[:limit]) + '<span class="truncated">...</span>'
        else:
            text = escape(text)
        return text


class TupleValue(object):
    adapts(tuple)
    implements(IValueRenderer)

    def __init__(self, context):
        self.context = context

    def render(self, tid=None):
        html = []
        for item in self.context:
            html.append(IValueRenderer(item).render())
        if len(html) == 1:
            html.append('') # (item) -> (item, )
        return '(%s)' % ', '.join(html)


class ListValue(object):
    adapts(list)
    implements(IValueRenderer)

    def __init__(self, context):
        self.context = context

    def render(self, tid=None):
        html = []
        for item in self.context:
            html.append(IValueRenderer(item).render())
        return '[%s]' % ', '.join(html)


class DictValue(object):
    adapts(dict)
    implements(IValueRenderer)

    def __init__(self, context):
        self.context = context

    def render(self, tid=None):
        html = []
        for key, value in sorted(self.context.items()):
            html.append(IValueRenderer(key).render() + ': ' +
                        IValueRenderer(value).render())
        return '{%s}' % ', '.join(html)


class PersistentValue(object):
    adapts(Persistent)
    implements(IValueRenderer)

    def __init__(self, context):
        self.context = removeAllProxies(context)

    def render(self, tid=None):
        url = '/zodbinfo.html?oid=%d' % u64(self.context._p_oid)
        if tid is not None:
            url += "&amp;tid=" + str(u64(tid))
        value = GenericValue(self.context).render()
        return '<a href="%s">%s</a>' % (url, value)


class IState(Interface):

    def listAttributes(self):
        """Return the attributes of this object as tuples (name, value)."""

    def listItems(self):
        """Return the items of this object as tuples (name, value)."""

    def getParent(self):
        """Return the parent of this object."""

    def getName(self):
        """Return the name of this object."""

    def asDict(self):
        """Return the state expressed as an attribute dictionary."""


def _diff_dicts(this, other):
    diffs = {}
    for key, value in sorted(this.items()):
        if key not in other:
            diffs[key] = ['added', value]
        elif other[key] != value:
            diffs[key] = ['changed to', value]
    for key, value in sorted(other.items()):
        if key not in this:
            diffs[key] = ['removed', value]
    return diffs


class FallbackState(object):
    adapts(Interface, Interface, None)
    implements(IState)

    def __init__(self, type, state, tid):
        pass

    def getName(self):
        return '???'

    def getParent(self):
        return None

    def listAttributes(self):
        return None

    def listItems(self):
        return None

    def asDict(self):
        return {}


class IntState(object):
    adapts(Interface, int, None)
    implements(IState)

    def __init__(self, type, state, tid):
        self.state = state

    def getName(self):
        return '???'

    def getParent(self):
        return None

    def listAttributes(self):
        return [('int value', self.state)]

    def listItems(self):
        return None

    def asDict(self):
        return {'int value': self.state}


class OOBTreeState(object):
    adapts(OOBTree, tuple, None)
    implements(IState)

    def __init__(self, type, state, tid):
        self.btree = OOBTree()
        self.btree.__setstate__(state)

    def getName(self):
        return '???'

    def getParent(self):
        return None

    def listAttributes(self):
        return None

    def listItems(self):
        return self.btree.items()

    def asDict(self):
        return self.btree


class GenericState(object):
    adapts(Interface, dict, None)
    implements(IState)

    def __init__(self, type, state, tid):
        self.state = state
        self.tid = tid

    def getName(self):
        return self.state.get('__name__', '???')

    def getParent(self):
        return self.state.get('__parent__')

    def listAttributes(self):
        return self.state.items()

    def listItems(self):
        return None

    def asDict(self):
        return self.state


class PersistentDictState(GenericState):
    adapts(PersistentDict, dict, None)

    def listItems(self):
        return sorted(self.state.get('data', {}).items())


class FolderState(GenericState):
    adapts(Folder, dict, None)

    def listItems(self):
        data = self.state.get('data')
        if not data:
            return []
        # data will be an OOBTree
        loadedstate = _loadState(data, tid=self.tid)
        return getMultiAdapter((data, loadedstate, self.tid), IState).listItems()


class SampleContainerState(GenericState):
    adapts(SampleContainer, dict, None)

    def listItems(self):
        data = self.state.get('_SampleContainer__data')
        if not data:
            return []
        # data will be a PersistentDict
        loadedstate = _loadState(data, tid=self.tid)
        return getMultiAdapter((data, loadedstate, self.tid), IState).listItems()


class BTreeContainerState(GenericState):
    adapts(BTreeContainer, dict, None)

    def listItems(self):
        # This is not a typo; BTreeContainer really uses
        # _SampleContainer__data, for BBB
        data = self.state.get('_SampleContainer__data')
        if not data:
            return []
        # data will be an OOBTree
        loadedstate = _loadState(data, tid=self.tid)
        return getMultiAdapter((data, loadedstate, self.tid), IState).listItems()


class OrderedContainerState(GenericState):
    adapts(OrderedContainer, dict, None)

    def listItems(self):
        container = OrderedContainer()
        container.__setstate__(self.context)
        container._data.__setstate__(_loadState(container._data, tid=self.tid))
        container._order.__setstate__(_loadState(container._order, tid=self.tid))
        return container.items()


def _loadState(obj, tid=None):
    history = _gimmeHistory(obj)
    if tid is None:
        tid = history[0]['tid']
    else:
        for i, d in enumerate(history):
            if u64(d['tid']) <= u64(tid):
                tid = d['tid']
                break
    return obj._p_jar.oldstate(obj, tid)


def _gimmeHistory(obj):
    storage = obj._p_jar._storage
    oid = obj._p_oid
    history = None
    # XXX OMG ouch
    if 'length' in inspect.getargspec(storage.history)[0]: # ZEO
        history = storage.history(oid, version='', length=999999999999)
    else: # FileStorage
        history = storage.history(oid, size=999999999999)

    return history


class ZodbObject(object):

    state = None
    current = True
    tid = None
    requestedTid = None
    history = None

    def __init__(self, obj):
        self.obj = removeAllProxies(obj)

    def load(self, tid=None):
        """Load current state if no tid is specified"""
        self.requestedTid = tid
        self.history = _gimmeHistory(self.obj)
        if tid is not None:
            # load object state with tid less or equal to given tid
            self.current = False
            for i, d in enumerate(self.history):
                if u64(d['tid']) <= u64(tid):
                    self.tid = d['tid']
                    break
            self.current = False
        else:
            self.tid = self.history[0]['tid']
        self.state = self._loadState(self.tid)

    def listAttributes(self):
        attrs = self.state.listAttributes()
        if attrs is None:
            return None
        return [ZodbObjectAttribute(name, value, self.requestedTid)
                for name, value in sorted(attrs)]

    def listItems(self):
        items = self.state.listItems()
        if items is None:
            return None
        return [ZodbObjectAttribute(name, value, self.requestedTid)
                for name, value in items]

    def _loadState(self, tid):
        loadedState = self.obj._p_jar.oldstate(self.obj, tid)
        return getMultiAdapter((self.obj, loadedState, self.requestedTid),
                               IState)

    def getName(self):
        if self.isRoot():
            return "ROOT"
        else:
            return self.state.getName()

    def getObjectId(self):
        return u64(self.obj._p_oid)

    def getParent(self):
        return self.state.getParent()

    def isRoot(self):
        if IContainmentRoot.providedBy(self.obj):
            return True
        else:
            return False

    def listHistory(self):
        """List transactions that modified a persistent object."""
        results = []
        if not isinstance(self.obj, Persistent):
            return results

        for n, d in enumerate(self.history):
            short = (str(time.strftime('%Y-%m-%d %H:%M:%S',
                                       time.localtime(d['time']))) + " "
                     + d['user_name'] + " "
                     + d['description'])
            url = '/zodbinfo.html?oid=%d&tid=%d' % (u64(self.obj._p_oid),
                                                    u64(d['tid']))
            current = d['tid'] == self.tid and self.requestedTid is not None
            curState = self._loadState(d['tid']).asDict()
            if n < len(self.history) - 1:
                oldState = self._loadState(self.history[n + 1]['tid']).asDict()
            else:
                oldState = {}
            diff = _diff_dicts(curState, oldState)
            for key, (action, value) in diff.items():
                diff[key][1] = IValueRenderer(value).render(d['tid'])

            results.append(dict(short=short, utid=u64(d['tid']),
                                href=url, current=current, diff=diff, **d))

        for i in range(len(results)):
            results[i]['index'] = len(results) - i

        return results

