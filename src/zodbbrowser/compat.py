try:
    basestring = basestring
except NameError:
    # Python 3
    basestring = str

try:
    long = long
except NameError:
    # Python 3
    long = int

try:
    from cStringIO import StringIO
except ImportError:
    # Python 3
    from io import StringIO  # noqa
