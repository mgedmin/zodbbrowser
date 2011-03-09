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
        try:
            return repr(self.context)
        except Exception:
            try:
                return '<unrepresentable %s>' % self.context.__class__.__name__
            except Exception:
                return '<unrepresentable>'

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


class TupleValue(object):
    """Tuple renderer."""
    adapts(tuple)
    implements(IValueRenderer)

    def __init__(self, context):
        self.context = context

    def render(self, tid=None, threshold=100):
        html = []
        for item in self.context:
            html.append(IValueRenderer(item).render(tid))
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

    def render(self, tid=None, threshold=100):
        html = []
        for item in self.context:
            html.append(IValueRenderer(item).render(tid))
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

    def render(self, tid=None, threshold=100):
        html = []
        for key, value in sorted(self.context.items()):
            html.append(IValueRenderer(key).render(tid) + ': ' +
                        IValueRenderer(value).render(tid))
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

