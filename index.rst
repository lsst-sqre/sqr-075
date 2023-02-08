####################################################################
A vertical monorepo architecture for FastAPI client-server codebases
####################################################################

.. abstract::

   The SQuaRE team has successfully adopted Python and FastAPI for building applications for the Rubin Science Platform.
   The Pydantic model classes that define REST API requests and responses in a FastAPI server are also useful for clients (which can be other Rubin Science Platform applications).
   This technical note proposes a new vertical monorepo architecture where the server application (deployed as a Docker image) is developed alongside a client library (deployed as a PyPI package) that hosts the Pydantic models for the application's REST API.
   The vertical monorepo is the most efficient development architecture because both the client and server are developed and released simultaneously from the same Git repository.

Problem statement
=================

Every web service has clients.
Sometimes we consume the services we build (especially in microservice architectures), but sometimes the primary consumers are third parties.
Traditionally, we have focused our efforts on optimizing the development processes for the server application, since that's often where most of the complexity resides.

.. This technote came about from a recognition that there are valuable efficiency gains for ourselves and others if we take client development with the same care.

One of our most significant improvements in developing server applications in recent years has been in adopting FastAPI_ and Pydantic_ modelling for describing our API's data models.
Pydantic integrates with Python annotations so that we can be confident that we are using API interface models correctly in a code base (e.g., validate that fields exist, or that the field can be set to null/None) using a static type checker like Mypy.
Additionally, Pydantic performs validation of datasets to ensure that it conforms to the schema described by the type annotations and any additional validation functions.
Finally, FastAPI automatically uses these Pydantic models to generate detailed REST API documentation with the OpenAPI standard.

Clients can also benefit from Pydantic models both to ensure that request bodies are correctly structured and to parse server responses into typed classes.
In fact, the Pydantic models used by the client *should* match those used by the server.
Create a system where these Pydantic models are shared is the purpose of this technote.
How to efficiently share Pydantic models between the server application and any REST API client is the subject of this technical note.

.. Make in-text citations with: :cite:`bibkey`.

.. References
.. ==========

.. .. bibliography:: local.bib lsstbib/books.bib lsstbib/lsst.bib lsstbib/lsst-dm.bib lsstbib/refs.bib lsstbib/refs_ads.bib
..    :style: lsst_aa

.. _fastapi: https://fastapi.tiangolo.com
.. _pydantic: https://docs.pydantic.dev
