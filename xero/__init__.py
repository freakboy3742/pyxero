try:
    # This try-catch is necessary to make sure we can get
    # VERSION from the base xero module before all the
    # dependencies have been imported.
    from .api import Xero
except ImportError:
    pass

NUM_VERSION = (0, 5, 3)
VERSION = ".".join(str(nv) for nv in NUM_VERSION)
