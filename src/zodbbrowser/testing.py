from zope.component import adapts
from zope.interface import implements

from zodbbrowser.interfaces import IValueRenderer


class SimpleValueRenderer(object):
    adapts(None)
    implements(IValueRenderer)

    def __init__(self, context):
        self.context = context

    def render(self, tid=None):
        s = repr(self.context)
        if tid:
            s += ' [tid=%s]' % tid
        return s

