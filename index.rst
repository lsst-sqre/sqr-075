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
FastAPI uses Pydantic models to describe the data schemas for both requests and responses in a REST API.
Pydantic integrates with Python annotations so that we can be confident that we are using API interface models correctly in a code base (e.g., validate that fields exist, or that the field can be set to null/None) using a static type checker like Mypy_.
Additionally, Pydantic performs validation of datasets to ensure that it conforms to the schema described by the type annotations and any additional validation functions.
Finally, FastAPI automatically uses these Pydantic models to generate detailed REST API documentation with the OpenAPI standard.

Clients are, of course, using the same schemas for the complementary actions of sending requests and parsing responses.
And although it's not strictly necessary, client development benefits greatly from also using Pydantic classes to describe the request and response schemas for the same reasons of static type analysis and automatic data parsing and validation.

In principle, the client and server *can* use the very same Pydantic classes to describe the request and response bodies in a REST API.
To date, though, we have failed to establish an effective pattern for sharing these model classes.
As a concrete example, both Mobu_ and Noteburst_ are clients for the `JupyterLab Controller`_.
In both Mobu and Noteburst we are independently reproducing the Pydantic models of the JupyterLab Controller, either by copying-and-pasting from the JupyterLab Controller application codebase, or by developing new Pydantic models classes based on the JupyterLab Controller schema in principle.

Although this works, it is not efficient, due to the duplication of code (and more fundamentally, *information*) across multiple repositories.
This technote proposes a solution.

Possible ways to share models between server and clients
========================================================

While working on this problem of model and code duplication between servers and clients, we examined multiple approaches.
This section outlines those, and these were discarded, before proposing the *vertical monorepo* architecture.

.. _separate-client-repo:

Client model repositories
-------------------------

Fundamentally, Python code is shared through *library* packages that are installable from repositories like PyPI and importable into other libraries or Python applications.
Note that applications (such as SQuaRE's FastAPI web applications) are *not* libraries.
Even if they were published to a repository like PyPI, applications have pinned dependencies for reasons of build reproducibilty that prevent them from realistically being installed in other contexts.
This is also why SQuaRE has two fundamentally different templates for python projects: the FastAPI application template and the Python library template.

Keeping with the common SQuaRE practice of using separate Git repositories for Python library packages from applications, we found three concievable patterns:

1. A client package repository for every application repository
2. Using Safir_ as a shared library for application models
3. A dedicated monorepo for application models

The first option keeps libraries focused on a single domain, but has the downside of doubling the number of GitHub repositories that need to be maintained.
Options 2 and 3 collect models together, which reduces the number of repositories, but introduces new issues of version management if different versions of an application's models need to be used simultaneously by a client.

In all of these cases, using a separate library for application models makes application development much more inconvenient.
This is because server application dependencies are resolved and hashed with pip-tools_.
This practice results in highly reproducible Docker image builds, and of course implies that a server application's depenencies are stable.
There isn't a good workflow for developing a library simultaneously with an application.

A vertical monorepo architecture
--------------------------------

The potential solutions listed previously introduce the issue of coordianted pull requests and releases being required to make any change to any REST API change.
This indicates that separate client library repositories are not the right approach.

The orthogonal approach, then, is to consider a vertical mono repo architecture within the domain of each web API.
Put concretely: in the same GitHub repository where a FastAPI application is developed, a Python library containing the Pydantic models is also developed.
Now, any change to a web API only requires a single pull request to one repository.
When a release is made, the FastAPI application is published as a Docker image, while the library with Pydantic models is published to PyPI.
The FastAPI application itself imports the library locally, while external clients can depend on the library from PyPI.

This solution seems to solve the problem of both making Pydantic interface models efficiently reusable, while eliminating repository sprawl and making it possible to encapsulate feature update to a single pull request.
On the other hand, this solution us to change how we structure GitHub repositories, effectively combining the existing FastAPI application template and the PyPI package template into one.
The next section explores the mechanics of a vertical monorepo.

The mechanics of a vertical monorepo
====================================

SQuaRE conventionally structures both its application and library repositories such that a single Python package (as defined by a ``pyproject.toml`` file) is developed from the root of an individual Git repository.
Although it's appealing to think that both the FastAPI application and the client library could be developed and released from the same Python package, Python applications and libraries are distinct in a number of ways, starting with how their dependencies are managed (see the discussion in :ref:`separate-client-repo` about pip-tools_).
This necessites that a vertical monorepo must have two directories at its root to host separate Python projects for the client and server:

.. code-block:: text
   :caption: Vertical client-server monorepo layout (abridged)

   example
   ├── .github
   │   ├── dependabot.yml
   │   └── workflows
   ├── .pre-commit-config.yaml
   ├── client
   │   ├── pyproject.toml
   │   └── src
   │       ├── exampleclient
   │       │   ├── __init__.py
   │       │   └── models.py
   │       └── tests
   └── server
       ├── Dockerfile
       ├── pyproject.toml
       ├── requirements
       └── src
           ├── example
           │   ├── __init__.py
           │   ├── config.py
           │   ├── dependencies
           │   ├── domain
           │   ├── main.py
           │   ├── handlers
           │   └── services
           └── tests

This monorepo contains two Python packages: ``example`` (the application) and ``exampleclient`` (the library).
The ``exampleclient.models`` module contains the Pydantic classes that define the REST API for the ``example`` application.

How the application depends on the client library
-------------------------------------------------

For an effective development workflow, the application needs to be able to import models from the client library locally, rather than through a PyPI release.
Applications use the ``requirements.txt`` file format to declare their dependencies.
Local dependencies can be declared with a relative path:

.. code-block::
   :caption: example/requirements/main.in
   
   example-client @ file://../../exampleclient

References:

- `requirements.txt format <https://pip.pypa.io/en/stable/reference/requirements-file-format/?highlight=requirements.txt#requirements-file-format>`__
- `VCS support with a file protocol <https://pip.pypa.io/en/stable/topics/vcs-support/#vcs-support>`__

.. note::
   
   To date, SQuaRE uses setuptools as the build backend for its projects.
   Applications additionally use pip and pip-tools to compile pinned dependencies in a ``requirements.txt`` format from abstract dependencies.
   Is there an obviously better build backend that we should use in our client-server monorepos?
   
   TK:
   
   - Poetry does many of the same things that we we're already doing with compiled dependencies and tox for environment. Poetry doesn't seem to be specifically made for Poetry though.
   - Pants is a build infrastructure for Python monorepos (with growing capabilities for other language). Its not clear that the vertical monorepos proposed here are *enough* of a mono repo to warrant Pants (or warrant our investment in changing to it now).
     Pants raison d'etre is to support caching in tests and builds in _real_ monorepos.
     By comparison, the vertical monorepos described here are a minor step-up from the standard multi-repo setup that standard Python tooling caters to.
     For more information, see this Pants talk: https://youtu.be/1qurVKSYVqY


.. Make in-text citations with: :cite:`bibkey`.

.. References
.. ==========

.. .. bibliography:: local.bib lsstbib/books.bib lsstbib/lsst.bib lsstbib/lsst-dm.bib lsstbib/refs.bib lsstbib/refs_ads.bib
..    :style: lsst_aa

.. _fastapi: https://fastapi.tiangolo.com
.. _`JupyterLab Controller`: https://github.com/lsst-sqre/jupyterlab-controller
.. _mobu: https://github.com/lsst-sqre/mobu
.. _mypy: https://mypy.readthedocs.io/en/stable/
.. _noteburst: https://github.com/lsst-sqre/noteburst
.. _pip-tools: https://pip-tools.rtfd.io/
.. _pydantic: https://docs.pydantic.dev
.. _safir: https://safir.lsst.io
