from zope.component import adapter
from zope.interface import implementer

from zodbbrowser.interfaces import IValueRenderer


@adapter(None)
@implementer(IValueRenderer)
class SimpleValueRenderer(object):

    def __init__(self, context):
        self.context = context

    def render(self, tid=None):
        s = repr(self.context)
        if tid:
            s += ' [tid=%s]' % tid
        return s

