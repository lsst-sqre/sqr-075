"""Sphinx configuration.

To learn more about the Sphinx configuration for technotes, and how to
customize it, see:

https://documenteer.lsst.io/technotes/configuration.html
"""

from documenteer.conf.technote import *  # noqa: F401, F403

# https://github.com/mgaitan/sphinxcontrib-mermaid/issues/110
mermaid_version = "9.4.0"

exclude.append(".tox")
