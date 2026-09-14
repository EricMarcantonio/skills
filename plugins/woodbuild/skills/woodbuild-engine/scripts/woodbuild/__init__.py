"""woodbuild - reference structure -> wood cutlist, optimised buy plan, priced cart."""
__version__ = "0.1.0"


def __getattr__(name):
    """Expose `cli_main` lazily: importing the package must not pull in the CLI.

    `cli` imports `report`, which is a separate concern from `pricing`; test
    modules that only need one of them should not import the other as a side
    effect.
    """
    if name == "cli_main":
        from .cli import cli_main
        return cli_main
    raise AttributeError("module %r has no attribute %r" % (__name__, name))
