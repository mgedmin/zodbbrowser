from cgi import escape

from ZODB.utils import u64
from persistent import Persistent
from zope.component import adapts
from zope.interface.declarations import ProvidesClass
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

    def _repr(self):
        # hook for subclasses
        return repr(self.context)

    def render(self, tid=None, limit=200):
        text = self._repr()
        if len(text) > limit:
            text = escape(text[:limit]) + '<span class="truncated">...</span>'
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

    def render(self, tid=None, threshold=50):
        html = []
        for key, value in sorted(self.context.items()):
            html.append(IValueRenderer(key).render(tid) + ': ' +
                        IValueRenderer(value).render(tid))
        if sum(map(len, html)) < threshold:
            return '{%s}' % ', '.join(html)
        else:
            prefix = '{<span class="dict">'
            suffix = '</span>'
            for n, item in enumerate(html):
                if n == len(html) - 1:
                    trailer = '}'
                else:
                    trailer = ','
                if item.endswith(suffix):
                    item = item[:-len(suffix)] + trailer + suffix
                else:
                    item += trailer
                html[n] = item
            return prefix + '<br />'.join(html) + suffix


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
        return '<a class="objlink" href="%s">%s</a>' % (escape(url), value)


class ProvidesValue(GenericValue):
    """zope.interface.Provides object renderer.

    The __repr__ of zope.interface.Provides is decidedly unhelpful.
    """
    adapts(ProvidesClass)
    implements(IValueRenderer)

    def _repr(self):
        return '<Provides: %s>' % ', '.join(i.__identifier__
                                            for i in self.context._Provides__args[1:])

