####################################################################
A vertical monorepo architecture for FastAPI client-server codebases
####################################################################

.. abstract::

   The SQuaRE team has successfully adopted Python and FastAPI for building applications for the Rubin Science Platform.
   The Pydantic model classes that define REST API requests and responses in a FastAPI server are also useful for clients (which can be other Rubin Science Platform applications).
   This technical note proposes a new vertical monorepo architecture where the server application (deployed as a Docker image) is developed alongside a client library (deployed as a PyPI package) that hosts the Pydantic models for the application's REST API.
   The vertical monorepo is the most efficient development architecture because both the client and server are developed and released simultaneously from the same Git repository.

Problem statement
================

TK

.. Make in-text citations with: :cite:`bibkey`.
.. Uncomment to use citations
.. .. rubric:: References
.. 
.. .. bibliography:: local.bib lsstbib/books.bib lsstbib/lsst.bib lsstbib/lsst-dm.bib lsstbib/refs.bib lsstbib/refs_ads.bib
..    :style: lsst_aa
