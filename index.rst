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

One of our most significant advances in developing server applications in recent years has been in adopting FastAPI_, the application framework, and Pydantic_, the data modelling and validation library.
FastAPI uses Pydantic models to describe the schemas for both requests and responses in a REST API.
Pydantic integrates with Python annotations so that we can be confident that we are using API interface models correctly in a code base (e.g., validate that fields exist, or that the field can be set to null/None) using a static type checker like Mypy.
Additionally, Pydantic performs validation of datasets to ensure that it conforms to the schema described by the type annotations and any additional validation functions.
Finally, FastAPI automatically uses these Pydantic models to generate detailed REST API documentation with the OpenAPI standard.

When we develop clients, we are of course using the same schemas for the complementary actions of sending requests and parsing responses.
And although it's not strictly necessary, client development benefits greatly from also using Pydantic classes to describe the request and response schemas for the same reasons of static type analysis and automatic data parsing and validation.

In principle, the client and server *can* use the very same Pydantic classes to describe the request and response bodies in a REST API.
To date, though, we have failed to establish an effective pattern for sharing these model classes.
As a concrete example, both Mobu and Noteburst are clients for the JupyterLab Controller.
In both Mobu and Noteburst we are independently reproducing the Pydantic models of the JupyterLab Controller, either by copying-and-pasting from the JupyterLab Controller application codebase, or by developing new Pydantic models classes based on the JupyterLab Controller schema in principle.

Although this works, it is not efficient, due to the duplication of code (and more fundamentally, *information*) across multiple repositories.
This technote proposes a solution.

Possible ways to share models between server and clients
========================================================

While working on this problem of model and code duplication between servers and clients, we examined multiple approaches.
This section outlines those, and these were discarded, before proposing the *vertical monorepo* architecture that we propose.

A client package repository for every application repository
------------------------------------------------------------

Fundamentally, Python code is shared through *library* packages that are installable from repositories like PyPI and importable into other libraries or Python applications.
Note that applications (such as SQuaRE's FastAPI web applications) are *not* libraries.
Even if they were published to a repository like PyPI, applications have pinned dependencies for reasons of build reproducibilty that prevent them from realistically being installed in other contexts.
This is also why SQuaRE has two fundamentally different templates for python projects: the FastAPI application template and the Python library template.

A potential approach, though, is to create a client library repository for every server application repository.
For example, if a server application is developed in a GitHub repository ``lsst-sqre/noteburst``, we would create a complementary GitHub repository ``lsst-sqre/noteburst-client``.
That client repository would contain the Pydantic model classes that describe the application's REST API, for both requests and responses.
It would be structured as a Python library package, and be available from PyPI.
Then the server application and any clients alike could depend on that client package.

The downside of this approach is a doubling of the number of GitHub repositories that need to be maintained.
Although we have started to automated many aspects of Python project maintenance, there is still effort in migrating projects to newer build and testing infrastructures, creating documentation sites, and making releases.

The issue then, if finding an architecture that enables us to refactor the Pydantic models for our REST APIs into reusable library packages without unnecessarily expanding the number of Git repositories that need to be managed.

Safir as a source for server application models
-----------------------------------------------

Safir_ is SQuaRE's library of shared code for building FastAPI applications.
Since every application already depends on Safir, we could refactor all the Pydantic models of applications down into Safir.
The clients that are also SQuaRE applications would immediately be able to import the Pydantic model classes of other applications.
A downside of this approach is that clients that are not FastAPI applications (like a JupyterLab widget or a CLI) would get many of the server-oriented dependencies of Safir, such as FastAPI itself.
This could be solved by refactoring Safir and its Python dependencies slightly so it would be possible to install Safir without also installing FastAPI.

A dedicated horizontal monorepo for SQuaRE API models
-----------------------------------------------------

If Safir is not the right Python package for sharing Pydantic models, an alternative solution is to create a dedicated monorepo for these classes that both FastAPI applications *and* Python clients can easily depend on.
For example, a Python package named ``square-apis``.
The problem with this horizontally-scaling monorepo — as with using Safir as the monorepo — is that updates to an application's REST API require at least two coordinated codebase changes, and likely three or more.
First, the models must be updated in the shared models monorepo; second, the application itself must be updated to use these models, and finally any clients need to be updated to use the revised models.

A vertical monorepo architecture
--------------------------------

The previous two monorepo approaches scaled *horizontally* by collecting the Pydantic models for every SQuaRE FastAPI application into a single library.
While those solutions solve the issue of doubling the number of GitHub repositories, they introduce a new issue of coordinated pull requests and releases being required to make any change to any REST API change.
This indicates that a horizontal monorepo is not the right approach.

The orthogonal approach, then, is to consider a vertical mono repo architecture within the domain of each web API.
Put concretely: in the same GitHub repository where a FastAPI application is developed, a Python library containing the Pydantic models is also developed.
Now, any change to a web API only requires a single pull request to one repository.
When a release is made, the FastAPI application is published as a Docker image, while the library with Pydantic models is published to PyPI.
The FastAPI application itself imports the library locally, while external clients can depend on the library from PyPI.

This solution seems to solve the problem of both making Pydantic interface models efficiently reusable, while eliminating repository sprawl and making it possible to encapsulate feature update to a single pull request.
On the other hand, this solution us to change how we structure GitHub repositories, effectively combining the existing FastAPI application template and the PyPI package template into one.
The next section explores the mechanics of a vertical monorepo.

.. Make in-text citations with: :cite:`bibkey`.

.. References
.. ==========

.. .. bibliography:: local.bib lsstbib/books.bib lsstbib/lsst.bib lsstbib/lsst-dm.bib lsstbib/refs.bib lsstbib/refs_ads.bib
..    :style: lsst_aa

.. _fastapi: https://fastapi.tiangolo.com
.. _pydantic: https://docs.pydantic.dev
.. _safir: https://safir.lsst.io
