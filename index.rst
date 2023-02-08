:tocdepth: 1

.. sectnum::

.. Metadata such as the title, authors, and description are set in metadata.yaml

.. TODO: Delete the note below before merging new content to the main branch.

.. note::

   **This technote is a work-in-progress.**

Abstract
========

The SQuaRE team has successfully adopted Python and FastAPI for building applications for the Rubin Science Platform. The Pydantic model classes that define REST API requests and responses in a FastAPI server are also useful for clients (which can be other Rubin Science Platform applications). This technical note proposes a new vertical monorepo architecture where the server application (deployed as a Docker image) is developed alongside a client library (deployed as a PyPI package) that hosts the Pydantic models for the application's REST API. The vertical monorepo is the most efficient development architecture because both the client and server are developed and released simultaneously from the same Git repository.

Add content here
================

Add content here.
See the `reStructuredText Style Guide <https://developer.lsst.io/restructuredtext/style.html>`__ to learn how to create sections, links, images, tables, equations, and more.

.. Make in-text citations with: :cite:`bibkey`.
.. Uncomment to use citations
.. .. rubric:: References
.. 
.. .. bibliography:: local.bib lsstbib/books.bib lsstbib/lsst.bib lsstbib/lsst-dm.bib lsstbib/refs.bib lsstbib/refs_ads.bib
..    :style: lsst_aa
