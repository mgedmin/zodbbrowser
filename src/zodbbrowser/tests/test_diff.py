import doctest

from zope.app.testing import setup
from zope.component import provideAdapter

from zodbbrowser.diff import compareDicts, compareDictsHTML
from zodbbrowser.diff import compareTuples, compareTuplesHTML
from zodbbrowser.testing import SimpleValueRenderer


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


def doctest_compareTuples():
    """Tests for compareTuples

        >>> old = (1, 2, 3)
        >>> new = ()
        >>> compareTuples(new, old)
        ((), (1, 2, 3), (), ())

        >>> old = (1, 2, 3)
        >>> new = (1, 2, 3, 4)
        >>> compareTuples(new, old)
        ((1, 2, 3), (), (4,), ())

        >>> old = (1, 2, 3, 5)
        >>> new = (2, 3, 4, 5)
        >>> compareTuples(new, old)
        ((), (1, 2, 3), (2, 3, 4), (5,))

        >>> old = (1, 2, 3, 5)
        >>> new = (1, 3, 4, 5)
        >>> compareTuples(new, old)
        ((1,), (2, 3), (3, 4), (5,))

        >>> old = (1, 2, 3, 5)
        >>> new = (1, 3, 4, 6)
        >>> compareTuples(new, old)
        ((1,), (2, 3, 5), (3, 4, 6), ())

        >>> old = (1, 2, 3, 5)
        >>> new = (2, 3, 4, 6)
        >>> compareTuples(new, old)
        ((), (1, 2, 3, 5), (2, 3, 4, 6), ())

    """


def doctest_compareTuplesHTML():
    """Tests for compareTuplesHTML

        >>> old = (1, 2, 3, 5)
        >>> new = (2, 3, 4, 5)
        >>> print compareTuplesHTML(new, old)
        <div class="diff">
          <div class="diffitem removed">
            removed 1
          </div>
          <div class="diffitem removed">
            removed 2
          </div>
          <div class="diffitem removed">
            removed 3
          </div>
          <div class="diffitem added">
            added 2
          </div>
          <div class="diffitem added">
            added 3
          </div>
          <div class="diffitem added">
            added 4
          </div>
          <div class="diffitem same">
            last item kept the same
          </div>
        </div>

        >>> old = (1, 2, 3, 5)
        >>> new = (1, 3, 4, 5)
        >>> print compareTuplesHTML(new, old)
        <div class="diff">
          <div class="diffitem same">
            first item kept the same
          </div>
          <div class="diffitem removed">
            removed 2
          </div>
          <div class="diffitem removed">
            removed 3
          </div>
          <div class="diffitem added">
            added 3
          </div>
          <div class="diffitem added">
            added 4
          </div>
          <div class="diffitem same">
            last item kept the same
          </div>
        </div>

        >>> old = (1, 2, 3, 5)
        >>> new = (1, 3, 4, 6)
        >>> print compareTuplesHTML(new, old)
        <div class="diff">
          <div class="diffitem same">
            first item kept the same
          </div>
          <div class="diffitem removed">
            removed 2
          </div>
          <div class="diffitem removed">
            removed 3
          </div>
          <div class="diffitem removed">
            removed 5
          </div>
          <div class="diffitem added">
            added 3
          </div>
          <div class="diffitem added">
            added 4
          </div>
          <div class="diffitem added">
            added 6
          </div>
        </div>

        >>> old = (1, 2, 3, 5)
        >>> new = (2, 3, 4, 6)
        >>> print compareTuplesHTML(new, old)
        <div class="diff">
          <div class="diffitem removed">
            removed 1
          </div>
          <div class="diffitem removed">
            removed 2
          </div>
          <div class="diffitem removed">
            removed 3
          </div>
          <div class="diffitem removed">
            removed 5
          </div>
          <div class="diffitem added">
            added 2
          </div>
          <div class="diffitem added">
            added 3
          </div>
          <div class="diffitem added">
            added 4
          </div>
          <div class="diffitem added">
            added 6
          </div>
        </div>

    """


def doctest_compareDictsHTML():
    """Tests for compareDicts

        >>> old = dict(a=1, b=2, c=3)
        >>> new = dict(a=1, b=3, e=4)
        >>> print compareDictsHTML(new, old)
        <div class="diff">
          <div class="diffitem changed">
            <strong>b</strong>: changed to 3
          </div>
          <div class="diffitem removed">
            <strong>c</strong>: removed 3
          </div>
          <div class="diffitem added">
            <strong>e</strong>: added 4
          </div>
        </div>

    """


def doctest_compareDictsHTML_recursive():
    """Tests for compareDicts

        >>> old = dict(a=1, b=dict(x=2, y=5), c=3, d=42, e=dict(x=42))
        >>> new = dict(a=1, b=dict(x=3, y=5), d=dict(x=42), e=42, f=dict(x=4))
        >>> print compareDictsHTML(new, old)
        <div class="diff">
          <div class="diffitem changed">
            <strong>b</strong>: dictionary changed:
            <div class="diff">
              <div class="diffitem changed">
                <strong>x</strong>: changed to 3
              </div>
            </div>
          </div>
          <div class="diffitem removed">
            <strong>c</strong>: removed 3
          </div>
          <div class="diffitem changed">
            <strong>d</strong>: changed to {'x': 42}
          </div>
          <div class="diffitem changed">
            <strong>e</strong>: changed to 42
          </div>
          <div class="diffitem added">
            <strong>f</strong>: added {'x': 4}
          </div>
        </div>

    """


def doctest_compareDictsHTML_tid_is_used():
    """Tests for compareDicts

        >>> old = dict(a=1, b=dict(x=2, y=5))
        >>> new = dict(a=2, b=dict(x=3, y=5))
        >>> print compareDictsHTML(new, old, tid=42)
        <div class="diff">
          <div class="diffitem changed">
            <strong>a</strong>: changed to 2 [tid=42]
          </div>
          <div class="diffitem changed">
            <strong>b</strong>: dictionary changed:
            <div class="diff">
              <div class="diffitem changed">
                <strong>x</strong>: changed to 3 [tid=42]
              </div>
            </div>
          </div>
        </div>

    """


def doctest_compareDictsHTML_html_quoting():
    """Tests for compareDicts

        >>> old = {}
        >>> new = {'<': 'less than'}
        >>> print compareDictsHTML(new, old)
        <div class="diff">
          <div class="diffitem added">
            <strong>&lt;</strong>: added 'less than'
          </div>
        </div>

    """


def doctest_compareDictsHTML_nonstring_keys():
    """Tests for compareDicts

        >>> old = {1: 2}
        >>> new = {1: 3}
        >>> print compareDictsHTML(new, old)
        <div class="diff">
          <div class="diffitem changed">
            <strong>1</strong>: changed to 3
          </div>
        </div>

    """


def doctest_compareDictsHTML_has_no_unicode_problems():
    r"""Tests for compareDicts

        >>> old = {u'\N{SNOWMAN}': 1, '\xFE': 2}
        >>> new = {u'\N{SNOWMAN}': 2, '\xFE': 3}
        >>> print compareDictsHTML(new, old)
        <div class="diff">
          <div class="diffitem changed">
            <strong>'\xfe'</strong>: changed to 3
          </div>
          <div class="diffitem changed">
            <strong>u'\u2603'</strong>: changed to 2
          </div>
        </div>

    """


def setUp(test):
    setup.placelessSetUp()
    provideAdapter(SimpleValueRenderer)


def tearDown(test):
    setup.placelessTearDown()


def test_suite():
    optionflags = doctest.REPORT_NDIFF|doctest.NORMALIZE_WHITESPACE
    return doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                optionflags=optionflags)

