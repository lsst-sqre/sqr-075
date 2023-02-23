"""Sphinx configuration.

To learn more about the Sphinx configuration for technotes, and how to
customize it, see:

https://documenteer.lsst.io/technotes/configuration.html
"""

from documenteer.conf.technotebeta import *  # noqa: F401, F403

exclude_patterns += [".venv", ".tox"]

extensions.append("sphinxcontrib.mermaid")
extensions.append("documenteer.sphinxext")

# https://github.com/mgaitan/sphinxcontrib-mermaid/issues/110
mermaid_version = "9.4.0"
