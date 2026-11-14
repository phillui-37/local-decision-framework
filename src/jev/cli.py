"""Deprecated alias of :mod:`ldf.cli`; ``python -m jev.cli`` keeps working."""
from ldf.cli import *  # noqa: F401,F403
from ldf.cli import main
if __name__=='__main__': main()
