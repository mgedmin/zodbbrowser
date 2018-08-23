import logging
import itertools
import collections
import re
from functools import partial

from ZODB.utils import u64, oid_repr
from persistent import Persistent
from persistent.dict import PersistentDict
from persistent.list import PersistentList
from persistent.mapping import PersistentMapping
from zope.component import adapter
from zope.interface.declarations import ProvidesClass
from zope.interface import implementer, Interface
from zope.security.proxy import removeSecurityProxy


from zodbbrowser.compat import basestring, escape
from zodbbrowser.interfaces import IValueRenderer, IObjectHistory


# Persistent has a __repr__ now that shows the OID, but it's shown poorly
# (as a Python string full of backslash escapes) and includes lots of
# irrelevant details (in-memory object address, repr of the Connection object).
CLASSES_WITH_BAD_REPR = (object, Persistent)
try:
    from BTrees._base import Bucket, Set, Tree, TreeSet
except ImportError:
    pass
else:
    CLASSES_WITH_BAD_REPR += (Bucket, Set, Tree, TreeSet)


log = logging.getLogger(__name__)


MAX_CACHE_SIZE = 1000
TRUNCATIONS = {}
TRUNCATIONS_IN_ORDER = collections.deque()
next_id = partial(next, itertools.count(1))


def resetTruncations(): # for tests only!
    global next_id
    next_id = partial(next, itertools.count(1))
    TRUNCATIONS.clear()
    TRUNCATIONS_IN_ORDER.clear()


def pruneTruncations():
    while len(TRUNCATIONS_IN_ORDER) > MAX_CACHE_SIZE:
        del TRUNCATIONS[TRUNCATIONS_IN_ORDER.popleft()]


def truncate(text):
    id = 'tr%d' % next_id()
    TRUNCATIONS[id] = text
    TRUNCATIONS_IN_ORDER.append(id)
    return id


@adapter(Interface)
@implementer(IValueRenderer)
class GenericValue(object):
    """Default value renderer.

    Uses the object's __repr__, truncating if too long.
    """

    def __init__(self, context):
        self.context = context

    if hasattr(object.__repr__, '__func__'):  # pragma: nocover
        # PyPy
        def _same_method(self, a, b):
            return getattr(a, '__func__', None) is b.__func__
    else:
        # CPython
        def _same_method(self, a, b):
            return a is b

    def _has_no_repr(self, obj):
        obj_repr = getattr(obj.__class__, '__repr__', None)
        return any(self._same_method(obj_repr, cls.__repr__)
                   for cls in CLASSES_WITH_BAD_REPR)

    def _repr(self):
        # hook for subclasses
        if self._has_no_repr(self.context):
            # Special-case objects with the default __repr__ (LP#1087138)
            if isinstance(self.context, Persistent):
                return '<%s.%s with oid %s>' % (
                    self.context.__class__.__module__,
                    self.context.__class__.__name__,
                    oid_repr(self.context._p_oid))
        try:
            return repr(self.context)
        except Exception:
            try:
                return '<unrepresentable %s>' % self.context.__class__.__name__
            except Exception:
                return '<unrepresentable>'

    def render(self, tid=None, can_link=True, limit=200):
        text = self._repr()
        if len(text) > limit:
            id = truncate(text[limit:])
            text = '%s<span id="%s" class="truncated">...</span>' % (
                escape(text[:limit], False), id)
        else:
            text = escape(text, False)
        if not isinstance(self.context, (basestring, bytes)):
            try:
                n = len(self.context)
            except Exception:
                pass
            else:
                if n == 1: # this is a crime against i18n, but oh well
                    text += ' (%d item)' % n
                else:
                    text += ' (%d items)' % n
        return text


def join_with_commas(html, open, close):
    """Helper to join multiple html snippets into a struct."""
    prefix = open + '<span class="struct">'
    suffix = '</span>'
    for n, item in enumerate(html):
        if n == len(html) - 1:
            trailer = close
        else:
            trailer = ','
        if item.endswith(suffix):
            item = item[:-len(suffix)] + trailer + suffix
        else:
            item += trailer
        html[n] = item
    return prefix + '<br />'.join(html) + suffix


@adapter(basestring)
@implementer(IValueRenderer)
class StringValue(GenericValue):
    """String renderer."""

    def __init__(self, context):
        self.context = context

    def render(self, tid=None, can_link=True, limit=200, threshold=4):
        newline = b'\n' if isinstance(self.context, bytes) else u'\n'
        if self.context.count(newline) <= threshold:
            return GenericValue.render(self, tid, can_link=can_link,
                                       limit=limit)
        else:
            if isinstance(self.context, bytes):
                context = self.context.decode('latin-1').encode('ascii',
                                                            'backslashreplace')
            else:
                context = self.context
            if isinstance(self.context, str):
                prefix = ''
            else:
                prefix = 'u'
            lines = [re.sub(r'^[ \t]+',
                            lambda m: '&nbsp;' * len(m.group(0).expandtabs()),
                            escape(line, False))
                     for line in context.splitlines()]
            nl = '<br />' # hm, maybe '\\n<br />'?
            if sum(map(len, lines)) > limit:
                head = nl.join(lines[:5])
                tail = nl.join(lines[5:])
                id = truncate(tail)
                return (prefix + "'<span class=\"struct\">" + head + nl
                        + '<span id="%s" class="truncated">...</span>' % id
                        + "'</span>")
            else:
                return (prefix + "'<span class=\"struct\">" + nl.join(lines)
                        + "'</span>")


@adapter(tuple)
@implementer(IValueRenderer)
class TupleValue(object):
    """Tuple renderer."""

    def __init__(self, context):
        self.context = context

    def render(self, tid=None, can_link=True, threshold=100):
        html = []
        for item in self.context:
            html.append(IValueRenderer(item).render(tid, can_link))
        if len(html) == 1:
            html.append('') # (item) -> (item, )
        result = '(%s)' % ', '.join(html)
        if len(result) > threshold or '<span class="struct">' in result:
            if len(html) == 2 and html[1] == '':
                return join_with_commas(html[:1], '(', ', )')
            else:
                return join_with_commas(html, '(', ')')
        return result


@adapter(list)
@implementer(IValueRenderer)
class ListValue(object):
    """List renderer."""

    def __init__(self, context):
        self.context = context

    def render(self, tid=None, can_link=True, threshold=100):
        html = []
        for item in self.context:
            html.append(IValueRenderer(item).render(tid, can_link))
        result = '[%s]' % ', '.join(html)
        if len(result) > threshold or '<span class="struct">' in result:
            return join_with_commas(html, '[', ']')
        return result


@adapter(dict)
@implementer(IValueRenderer)
class DictValue(object):
    """Dict renderer."""

    def __init__(self, context):
        self.context = context

    def render(self, tid=None, can_link=True, threshold=100):
        html = []
        for key, value in sorted(self.context.items()):
            html.append(IValueRenderer(key).render(tid, can_link) + ': ' +
                        IValueRenderer(value).render(tid, can_link))
        if (sum(map(len, html)) < threshold and
                '<span class="struct">' not in ''.join(html)):
            return '{%s}' % ', '.join(html)
        else:
            return join_with_commas(html, '{', '}')


@adapter(Persistent)
@implementer(IValueRenderer)
class PersistentValue(object):
    """Persistent object renderer.

    Uses __repr__ and makes it a hyperlink to the actual object.
    """

    view_name = '@@zodbbrowser'
    delegate_to = GenericValue

    def __init__(self, context):
        self.context = removeSecurityProxy(context)

    def render(self, tid=None, can_link=True):
        obj = self.context
        url = '%s?oid=0x%x' % (self.view_name, u64(self.context._p_oid))
        if tid is not None:
            url += "&tid=0x%x" % u64(tid)
            try:
                oldstate = IObjectHistory(self.context).loadState(tid)
                clone = self.context.__class__.__new__(self.context.__class__)
                clone.__setstate__(oldstate)
                clone._p_oid = self.context._p_oid
                obj = clone
            except Exception:
                log.debug('Could not load old state for %s 0x%x',
                          self.context.__class__, u64(self.context._p_oid))
        value = self.delegate_to(obj).render(tid, can_link=False)
        if can_link:
            return '<a class="objlink" href="%s">%s</a>' % (escape(url, True),
                                                            value)
        else:
            return value


@adapter(PersistentMapping)
class PersistentMappingValue(PersistentValue):
    delegate_to = DictValue


@adapter(PersistentList)
class PersistentListValue(PersistentValue):
    delegate_to = ListValue


if PersistentMapping is PersistentDict:
    # ZODB 3.9 deprecated PersistentDict and made it an alias for
    # PersistentMapping.  I don't know a clean way to conditionally disable the
    # <adapter> directive in ZCML to avoid conflicting configuration actions,
    # therefore I'll register a decoy adapter registered for a decoy class.
    # This adapter will never get used.

    class DecoyPersistentDict(PersistentMapping):
        """Decoy to avoid ZCML errors while supporting both ZODB 3.8 and 3.9."""

    @adapter(DecoyPersistentDict)
    class PersistentDictValue(PersistentValue):
        """Decoy to avoid ZCML errors while supporting both ZODB 3.8 and 3.9."""
        delegate_to = DictValue

else:  # pragma: nocover
    @adapter(PersistentDict)
    class PersistentDictValue(PersistentValue):
        delegate_to = DictValue


@adapter(ProvidesClass)
@implementer(IValueRenderer)
class ProvidesValue(GenericValue):
    """zope.interface.Provides object renderer.

    The __repr__ of zope.interface.Provides is decidedly unhelpful.
    """

    def _repr(self):
        return '<Provides: %s>' % ', '.join(i.__identifier__
                                            for i in self.context._Provides__args[1:])

