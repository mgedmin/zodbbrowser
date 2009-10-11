"""
ZODB Browser has the following submodules:

  diff        -- compute differences between two dictionaries
  testing     -- doodads to make writing tests easier

  history     -- extracts historical state information from the ZODB
  state       -- IStateInterpreter adapters for making sense of unpickled data
  value       -- IValueRenderer adapters for pretty-printing objects to HTML

  interfaces  -- interface definitions
  browser     -- browser views

  standalone  -- standalone application that starts a web server

"""


__version__ = '0.4'
__homepage__ = 'http://launchpad.net/zodbbrowser'
