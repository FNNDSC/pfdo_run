from importlib.metadata import Distribution

__pkg = Distribution.from_name(__package__)
__version__ = '3.0.0'

try:
    from .pfdo_run    import pfdo_run
except:
    from pfdo_run     import pfdo_run
