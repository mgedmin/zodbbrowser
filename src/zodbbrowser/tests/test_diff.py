import doctest

from zope.app.testing import setup
from zope.component import adapts, provideAdapter
from zope.interface import implements

from zodbbrowser.interfaces import IValueRenderer
from zodbbrowser.diff import compareDicts, compareDictsHTML


def pprintDict(d):
    """Pretty-print a dictionary.

    pprint.pprint() doesn't cut it: when the dict is too short, it uses
    repr() which has no defined ordering.
    """
    print '{%s}' % ',\n '.join('%r: %r' % (key, value)
                               for key, value in sorted(d.items()))


def doctest_compareDicts():
    """Tests for compareDicts

        >>> old = dict(a=1, b=2, c=3)
        >>> new = dict(a=1, b=3, e=4)
        >>> pprintDict(compareDicts(new, old))
        {'b': ('changed to', 3, 2),
         'c': ('removed', None, 3),
         'e': ('added', 4, None)}

    """


def doctest_compareDictsHTML():
    """Tests for compareDicts

        >>> old = dict(a=1, b=2, c=3)
        >>> new = dict(a=1, b=3, e=4)
        >>> print compareDictsHTML(new, old)
        <div class="diff">
          <span class="diff changed">
            <strong>b</strong>: changed to 3<br />
          </span>
          <span class="diff removed">
            <strong>c</strong>: removed 3<br />
          </span>
          <span class="diff added">
            <strong>e</strong>: added 4<br />
          </span>
        </div>

    """


def doctest_compareDictsHTML_recursive():
    """Tests for compareDicts

        >>> old = dict(a=1, b=dict(x=2, y=5), c=3, d=42, e=dict(x=42))
        >>> new = dict(a=1, b=dict(x=3, y=5), d=dict(x=42), e=42, f=dict(x=4))
        >>> print compareDictsHTML(new, old)
        <div class="diff">
          <span class="diff changed">
            <strong>b</strong>: dictionary changed:
          </span>
        <div class="diff">
          <span class="diff changed">
            <strong>x</strong>: changed to 3<br />
          </span>
        </div>
          <span class="diff removed">
            <strong>c</strong>: removed 3<br />
          </span>
          <span class="diff changed">
            <strong>d</strong>: changed to {'x': 42}<br />
          </span>
          <span class="diff changed">
            <strong>e</strong>: changed to 42<br />
          </span>
          <span class="diff added">
            <strong>f</strong>: added {'x': 4}<br />
          </span>
        </div>

    """


def doctest_compareDictsHTML_tid_is_used():
    """Tests for compareDicts

        >>> old = dict(a=1, b=dict(x=2, y=5))
        >>> new = dict(a=2, b=dict(x=3, y=5))
        >>> print compareDictsHTML(new, old, tid=42)
        <div class="diff">
          <span class="diff changed">
            <strong>a</strong>: changed to 2 [tid=42]<br />
          </span>
          <span class="diff changed">
            <strong>b</strong>: dictionary changed:
          </span>
        <div class="diff">
          <span class="diff changed">
            <strong>x</strong>: changed to 3 [tid=42]<br />
          </span>
        </div>
        </div>

    """


def doctest_compareDictsHTML_html_quoting():
    """Tests for compareDicts

        >>> old = {}
        >>> new = {'<': 'less than'}
        >>> print compareDictsHTML(new, old)
        <div class="diff">
          <span class="diff added">
            <strong>&lt;</strong>: added 'less than'<br />
          </span>
        </div>

    """


def doctest_compareDictsHTML_nonstring_keys():
    """Tests for compareDicts

        >>> old = {1: 2}
        >>> new = {1: 3}
        >>> print compareDictsHTML(new, old)
        <div class="diff">
          <span class="diff changed">
            <strong>1</strong>: changed to 3<br />
          </span>
        </div>

    """


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


def setUp(test):
    setup.placelessSetUp()
    provideAdapter(SimpleValueRenderer)


def tearDown(test):
    setup.placelessTearDown()


def test_suite():
    optionflags = doctest.REPORT_NDIFF|doctest.NORMALIZE_WHITESPACE
    return doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                optionflags=optionflags)

