"""
ZODB Browser has the following submodules:

  diff         -- compute differences between two dictionaries
  testing      -- doodads to make writing tests easier

  history      -- extracts historical state information from the ZODB
  state        -- IStateInterpreter adapters for making sense of unpickled data
  value        -- IValueRenderer adapters for pretty-printing objects to HTML

  btreesupport -- special handling of OOBTree objects

  interfaces   -- interface definitions
  browser      -- browser views

  standalone   -- standalone application that starts a web server

"""


__version__ = '0.10.0'
__homepage__ = 'http://launchpad.net/zodbbrowser'


if __name__ == '__main__':
    # support python -m zodbbrowser on Python 2.5
    from zodbbrowser.standalone import main
    main()
