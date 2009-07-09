import unittest
import doctest


from zodbbrowser.diff import compareDicts


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


def test_suite():
    return doctest.DocTestSuite()
