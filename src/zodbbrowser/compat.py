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
