from cgi import escape

from ZODB.utils import u64
from persistent import Persistent
from zope.component import adapts
from zope.interface import implements, Interface
from zope.security.proxy import removeSecurityProxy

from zodbbrowser.interfaces import IValueRenderer


class GenericValue(object):
    """Default value renderer.

    Uses the object's __repr__, truncating if too long.
    """
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
    """Tuple renderer."""
    adapts(tuple)
    implements(IValueRenderer)

    def __init__(self, context):
        self.context = context

    def render(self, tid=None):
        html = []
        for item in self.context:
            html.append(IValueRenderer(item).render(tid))
        if len(html) == 1:
            html.append('') # (item) -> (item, )
        return '(%s)' % ', '.join(html)


class ListValue(object):
    """List renderer."""
    adapts(list)
    implements(IValueRenderer)

    def __init__(self, context):
        self.context = context

    def render(self, tid=None):
        html = []
        for item in self.context:
            html.append(IValueRenderer(item).render(tid))
        return '[%s]' % ', '.join(html)


class DictValue(object):
    """Dict renderer."""
    adapts(dict)
    implements(IValueRenderer)

    def __init__(self, context):
        self.context = context

    def render(self, tid=None):
        html = []
        for key, value in sorted(self.context.items()):
            html.append(IValueRenderer(key).render(tid) + ': ' +
                        IValueRenderer(value).render(tid))
        return '{%s}' % ', '.join(html)


class PersistentValue(object):
    """Persistent object renderer.

    Uses __repr__ and makes it a hyperlink to the actual object.
    """
    adapts(Persistent)
    implements(IValueRenderer)

    view_name = '@@zodbbrowser'

    def __init__(self, context):
        self.context = removeSecurityProxy(context)

    def render(self, tid=None):
        url = '%s?oid=%d' % (self.view_name, u64(self.context._p_oid))
        if tid is not None:
            url += "&tid=%d" % u64(tid)
        value = GenericValue(self.context).render(tid)
        return '<a href="%s">%s</a>' % (escape(url), value)

