import logging
import itertools
import collections
import re
from cgi import escape

from ZODB.utils import u64
from persistent import Persistent
from persistent.dict import PersistentDict
from persistent.list import PersistentList
from persistent.mapping import PersistentMapping
from zope.component import adapts
from zope.interface.declarations import ProvidesClass
from zope.interface import implements, Interface
from zope.security.proxy import removeSecurityProxy

from zodbbrowser.interfaces import IValueRenderer
from zodbbrowser.interfaces import IObjectHistory


log = logging.getLogger(__name__)


MAX_CACHE_SIZE = 1000
TRUNCATIONS = {}
TRUNCATIONS_IN_ORDER = collections.deque()
next_id = itertools.count(1).next


def resetTruncations(): # for tests only!
    global next_id
    next_id = itertools.count(1).next
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


class GenericValue(object):
    """Default value renderer.

    Uses the object's __repr__, truncating if too long.
    """
    adapts(Interface)
    implements(IValueRenderer)

    def __init__(self, context):
        self.context = context

    def _repr(self):
        # hook for subclasses
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
            text = escape(text[:limit]) + (
                        '<span id="%s" class="truncated">...</span>' % id)
        else:
            text = escape(text)
        if not isinstance(self.context, basestring):
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


class StringValue(GenericValue):
    """String renderer."""
    adapts(basestring)
    implements(IValueRenderer)

    def __init__(self, context):
        self.context = context

    def render(self, tid=None, can_link=True, limit=200, threshold=4):
        if self.context.count('\n') <= threshold:
            return GenericValue.render(self, tid, can_link=can_link,
                                       limit=limit)
        else:
            if isinstance(self.context, unicode):
                prefix = 'u'
                context = self.context
            else:
                prefix = ''
                context = self.context.decode('latin-1').encode('ascii',
                                                            'backslashreplace')
            lines = [re.sub(r'^[ \t]+',
                            lambda m: '&nbsp;' * len(m.group(0).expandtabs()),
                            escape(line))
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


class TupleValue(object):
    """Tuple renderer."""
    adapts(tuple)
    implements(IValueRenderer)

    def __init__(self, context):
        self.context = context

    def render(self, tid=None, can_link=True, threshold=100):
        html = []
        for item in self.context:
            html.append(IValueRenderer(item).render(tid, can_link))
        if len(html) == 1:
            html.append('') # (item) -> (item, )
        result = '(%s)' % ', '.join(html)
        if  len(result) > threshold or '<span class="struct">' in result:
            if len(html) == 2 and html[1] == '':
                return join_with_commas(html[:1], '(', ', )')
            else:
                return join_with_commas(html, '(', ')')
        return result


class ListValue(object):
    """List renderer."""
    adapts(list)
    implements(IValueRenderer)

    def __init__(self, context):
        self.context = context

    def render(self, tid=None, can_link=True, threshold=100):
        html = []
        for item in self.context:
            html.append(IValueRenderer(item).render(tid, can_link))
        result = '[%s]' % ', '.join(html)
        if  len(result) > threshold or '<span class="struct">' in result:
            return join_with_commas(html, '[', ']')
        return result


class DictValue(object):
    """Dict renderer."""
    adapts(dict)
    implements(IValueRenderer)

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


class PersistentValue(object):
    """Persistent object renderer.

    Uses __repr__ and makes it a hyperlink to the actual object.
    """
    adapts(Persistent)
    implements(IValueRenderer)

    view_name = '@@zodbbrowser'
    delegate_to = GenericValue

    def __init__(self, context):
        self.context = removeSecurityProxy(context)

    def render(self, tid=None, can_link=True):
        obj = self.context
        url = '%s?oid=%d' % (self.view_name, u64(self.context._p_oid))
        if tid is not None:
            url += "&tid=%d" % u64(tid)
            try:
                oldstate = IObjectHistory(self.context).loadState(tid)
                clone = self.context.__class__.__new__(self.context.__class__)
                clone.__setstate__(oldstate)
                obj = clone
            except Exception:
                log.debug('Could not load old state for %s 0x%x',
                          self.context.__class__, u64(self.context._p_oid))
        value = self.delegate_to(obj).render(tid, can_link=False)
        if can_link:
            return '<a class="objlink" href="%s">%s</a>' % (escape(url), value)
        else:
            return value



class PersistentMappingValue(PersistentValue):
    adapts(PersistentMapping)
    delegate_to = DictValue


class PersistentListValue(PersistentValue):
    adapts(PersistentList)
    delegate_to = ListValue


if PersistentMapping is PersistentDict:
    # ZODB 3.9 deprecated PersistentDict and made it an alias for
    # PersistentMapping.  I don't know a clean way to conditionally disable the
    # <adapter> directive in ZCML to avoid conflicting configuration actions,
    # therefore I'll register a decoy adapter registered for a decoy class.
    # This adapter will never get used.

    class DecoyPersistentDict(PersistentMapping):
        """Decoy to avoid ZCML errors while supporting both ZODB 3.8 and 3.9."""

    class PersistentDictValue(PersistentValue):
        """Decoy to avoid ZCML errors while supporting both ZODB 3.8 and 3.9."""
        adapts(DecoyPersistentDict)
        delegate_to = DictValue

else:
    class PersistentDictValue(PersistentValue):
        adapts(PersistentDict)
        delegate_to = DictValue


class ProvidesValue(GenericValue):
    """zope.interface.Provides object renderer.

    The __repr__ of zope.interface.Provides is decidedly unhelpful.
    """
    adapts(ProvidesClass)
    implements(IValueRenderer)

    def _repr(self):
        return '<Provides: %s>' % ', '.join(i.__identifier__
                                            for i in self.context._Provides__args[1:])

