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
Pydantic integrates with Python annotations so that we can be confident that we are using API interface models correctly in a code base (e.g., validate that fields exist, or that fields can be set to null/None) using a static type checker like Mypy_.
Additionally, Pydantic performs validation of datasets to ensure that they conform to the schema described by type annotations and any additional validation functions.
Finally, FastAPI automatically uses these Pydantic models to generate detailed REST API documentation with the OpenAPI standard.

Clients, of course, use the same schemas for the complementary actions of sending requests and parsing responses.
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

.. _separate-client-repo:

Client model repositories
-------------------------

Fundamentally, Python code is shared through *library* packages that are installable from repositories like PyPI and importable into other libraries or Python applications.
Note that applications (such as SQuaRE's FastAPI web applications) are *not* libraries.
Even if they were published to a repository like PyPI, applications have pinned dependencies for reasons of build reproducibility that prevent them from realistically being installed in other contexts.
This is also why SQuaRE has two fundamentally different templates for python projects: the FastAPI application template and the Python library template.

Keeping with the common SQuaRE practice of using separate Git repositories for Python library packages and applications, we found three conceivable patterns:

1. A client package repository for every application repository
2. Using Safir_ as a shared library for application models
3. A dedicated monorepo for application models

The first option keeps libraries focused on a single domain, but has the downside of doubling the number of GitHub repositories that need to be maintained.
Options 2 and 3 collect models together, which reduces the number of repositories, but introduces new issues of version management if different versions of application models need to be used simultaneously by a client.

In all of these cases, using a separate library for application models makes application development much more inconvenient.
This is because server application dependencies are resolved and hashed with pip-tools_.
This practice results in highly reproducible Docker image builds, and of course implies that a server application's dependencies are stable.
There isn't a good workflow for developing a library simultaneously with an application.

A vertical monorepo architecture
--------------------------------

The potential solutions listed previously introduce the issue of coordinated pull requests and releases being required to make any change to any REST API change.
This indicates that client library repositories are not the right approach.

The orthogonal approach, then, is to consider a vertical monorepo architecture within the domain of each web API.
Put concretely: in the same GitHub repository where a FastAPI application is developed, a Python library containing the Pydantic models is also developed.
Now, any change to a web API only requires a single pull request to one repository.
When a release is made, the FastAPI application is published as a Docker image, while the library with Pydantic models is published to PyPI.
The FastAPI application itself imports the library locally, while external clients can depend on the library from PyPI.

This solution seems to solve the problem of both making Pydantic interface models efficiently reusable, while eliminating repository sprawl and making it possible to encapsulate feature updates to a single pull request.
On the other hand, this solution forces us to change how we structure GitHub repositories, effectively combining the existing FastAPI application template and the PyPI package template into one.
The next section explores the mechanics of a vertical monorepo.

The mechanics of a vertical monorepo
====================================

SQuaRE conventionally structures both its application and library repositories such that a single Python package (as defined by a ``pyproject.toml`` file) is developed from the root of an individual Git repository.
Although it's appealing to think that both the FastAPI application and the client library could be developed and released from the same Python package, Python applications and libraries are distinct in a number of ways, starting with how their dependencies are managed (see the discussion in :ref:`separate-client-repo` about pip-tools_).
This necessitates that a vertical monorepo must have two directories at its root to host separate Python projects for the client and server:

.. code-block:: text
   :name: layout
   :caption: Vertical client-server monorepo layout (abridged)

   example
   ├── .github
   │   ├── dependabot.yml
   │   └── workflows
   ├── .pre-commit-config.yaml
   ├── client
   │   ├── pyproject.toml
   │   └── src
   │       └── exampleclient
   │           ├── __init__.py
   │           └── models.py
   ├── Dockerfile
   ├── Makefile
   └── server
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

.. _client-dependency:

How the application depends on the client library
-------------------------------------------------

For an effective development workflow, the application needs to be able to import models from the client library locally, rather than through a PyPI release.
In current practice, applications use the ``requirements.txt`` file format to declare their dependencies.
We were not able to declare a local dependency in the requirements file, though.

We found the only viable mechanism is to manually pip install the client library in development and deployment contexts (the specific patterns are explored below).
The downside of this approach is that the client isn't considered by the pinned dependencies compiled by pip-tools_.
Normally runtime dependencies for the server application are abstractly listed in a ``requirements/main.in`` file for each application; pip-tools_ compiles these dependencies and their sub-dependencies into a ``requirements/main.txt`` file which is committed to the Git repository and actually used for installing dependencies.
This practice ensures that Docker builds and development environments alike are reproducible.
In practice, the client library's absence from ``requirements/main.txt`` itself isn't harmful because the client is inherently pinned by virtue of being co-developed in the same Git repository.

What's potentially concerning, though, is the absence of the client's own dependencies from the application's ``requirements/main.txt`` dependencies.
Though the server will still install all the client's dependencies via the pip-installation of the client into the Docker image, the client's dependencies *won't* be pinned — hence the build will not be reproducible.
This risk can be mitigated by ensuring that the client library's dependencies are also in the main application's ``requirements/main.txt``, which would be a manual process.
The impact of this will be limited since the aspects of the client that the server application will likely import will depend largely on Pydantic itself and perhaps the SQuaRE library with Pydantic extensions.
However, dependencies like libraries that provide custom Pydantic field types or validations will need to be deliberately added and managed to the application's own requirements to ensure proper version pinning.
This is a non-obvious workaround, and a downside of the vertical monorepo architecture.

Installing the client in the Docker image
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In the Docker image, both the client and server directories are copied into the intermediate ``install-image`` stage of the Docker build and installed into the virtual environment:

.. code-block:: Dockerfile

   RUN pip install --no-cache-dir ./client
   RUN pip install --no-cache-dir ./server

Installing the client in the server's Tox environments
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Tox_ runs tests and other development tasks in Python virtual environments that Tox itself manages.
To date, the application dependencies are installed using ``pip install -r ...``-type commands through the Tox ``deps`` environment configuration:

.. code-block:: ini

   [testenv]
   deps =
       -r{toxinidir}/requirements/main.txt
       -r{toxinidir}/requirements/dev.txt

As with the Dockerfile, the local pip installation of the client is accomplished by pointing to the client directory:

.. code-block:: ini

   [testenv]
   deps =
       -r{toxinidir}/requirements/main.txt
       -r{toxinidir}/requirements/dev.txt
       ../client

We found this works only if the ``requirements/main.txt`` and ``dev.txt`` requirements are *unhashed*.
Conventionally, we generate hashed requirements files with pip-tools_ as a security measure to ensure that the packages being installed in the deployment Docker image are *exactly* the same as those tested against.
However, when Tox uses pip to install hashed requirements file, it triggers a mode where pip requires hashed dependencies for all entries in the Tox ``deps`` configuration.
As the local client dependency is unhashed, the requirements files *cannot* be hashed.

A work-around for this is to generate both hashed and unhashed requirements, and use the hashed requirements for Docker builds and the unhashed dependencies in Tox environments.
This is a project Makefile that prepares both types of requirements files with pip-tools:

.. code-block:: Makefile
   :caption: Makefile

   .PHONY: update-deps
   update-deps:
   	pip install --upgrade pip-tools pip setuptools
   	pip-compile --upgrade --build-isolation --generate-hashes --output-file server/requirements/main.hashed.txt server/requirements/main.in
   	pip-compile --upgrade --build-isolation --generate-hashes --output-file server/requirements/dev.hashed.txt server/requirements/dev.in
   	pip-compile --upgrade --build-isolation --allow-unsafe --output-file server/requirements/main.txt server/requirements/main.in
   	pip-compile --upgrade --build-isolation --allow-unsafe --output-file server/requirements/dev.txt server/requirements/dev.in

   .PHONY: init
   init:
   	pip install --editable "./client[dev]"
   	pip install --editable ./server
   	pip install --upgrade -r server/requirements/main.txt -r server/requirements/dev.txt
   	rm -rf ./server.tox
   	pip install --upgrade pre-commit tox
   	pre-commit install

   .PHONY: update
   update: update-deps init

   .PHONY: run
   run:
   	cd server && tox run -e=run

Again, the Docker build uses the ``main.hashed.txt`` requirements, while the Tox environment uses the unhashed ``main.txt`` and ``dev.txt`` files.

Testing in the vertical monorepo
--------------------------------

We recommend that tests are only created for the server application, and that those tests are hosted out of the ``server/tests`` directory.

On a practical basis, we found that we could not create a single ``tests/`` directory in the project root that could be run from a single Tox_ configuration file in the project root.
Instead, the ``tox.ini`` configuration files needed to be located in the same directories as the ``pyproject.toml`` project files.
This naturally implies ``test/`` directories that are also in the ``server/`` and ``client/`` directories.

Only Python unit tests are needed in the ``server/tests`` directory, though, because the client and its models can be used in the server endpoint tests.
Adding extra tests for the client library is superfluous.

Linting the client and server code bases
----------------------------------------

For Python projects, we use linters to ensure consistency and correctness:

- isort, to sort imports consistently
- black, to format Python code consistently
- mypy, to check type annotations
- flake8, to statically validate Python code

These linters are generally triggered automatically with the pre-commit Git hook manager, or manually through a tox environment.

In the monorepo, pre-commit itself needs to be configured at the root since it doesn't have specific support for monorepos (see `pre-commit/pre-commit#466 <https://github.com/pre-commit/pre-commit/issues/466>`__).
Thus the monorepo has a ``.pre-commit-config.yaml`` file at its root.
It's possible to configure the pre-commit hooks differently for the client and server using file path filters in the pre-commit configuration (as described in the mentioned GitHub issue), but in practice this shouldn't be necessary.

Since flake8 is configured with a ``.flake8`` file, that file can be located at the root of the repository.
SQuaRE's flake8 configuration is uniform across all projects.

Mypy, black, and isort are configured in pyproject.toml files.
In those cases, the configurations are done separately in ``server/pyproject.toml`` and ``client/pyproject.toml`` files.

Docker build
------------

In the monorepo it's best to place the server application's Dockerfile at the root of the Git repository, rather than in the ``server`` subdirectory.
When the Dockerfile it located at the root, both the server and client directories can be copied and pip-installed into an intermediate stage of the Docker build.

Documentation
-------------

In most cases, a single documentation project for both the client and server is appropriate.
Since both code bases are available during the documentation build, APIs from both the server and client can be documented in the same Sphinx project by referencing the correct modules with the ``automodapi`` directive.
Because of how the ``tox.ini`` files need to be co-located alongside ``pyproject.toml`` files, the best place is likely in ``server/docs`` and built through a tox environment in the server.

GitHub Actions
--------------

GitHub Actions workflows for the entire repository are collected in the ``.github/workflows`` directory.
SQuaRE uses workflows to run tests, linters, and ultimately build and publish Docker images, PyPI packages, and documentation sites.
It's conceivable to treat the client and server completely separately with individual ``.github/workflows/server-ci.yaml`` and ``.github/workflows/client-ci.yaml`` workflow files.
In practice, though, there can actually be a benefit from running the CI/CD workflows on both the client and server in the *same* workflow, but with separate GitHub Actions jobs.
If the test jobs for either the client or server fail, then both of the publishing steps for the client and server can be cancelled.

Naming the client
=================

The :ref:`repository layout example <layout>` suggests that the client package and Python namespace should be ``exampleclient`` if the server application is named ``example``.
We may instead want to adopt a brand-centric approach to the client since it forms a public interface.

Client package naming
---------------------

We may want to systematically prefix the package names for discovery and sorting on PyPI and Conda-Forge.
For example, rather than ``noteburst-client``, we may prefer to use ``rsp-notebust-client`` or even ``rubin-rsp-noteburst-client``.
This reduces the risk of collisions with other packages on open source package registries.

Python namespace
----------------

We may want to place client libraries into a common namespace using a Python packaging feature called `namespace packages`_.
For example, clients for RSP services may want to use the ``lsst.rsp`` namespace: ``lsst.rsp.noteburst``.

Namespace packages can be set up by adding intermediate directories inside the ``src`` directory:

.. code-block:: text
   :name: namespaced-layout
   :caption: Namespace client package example (``lsst.rsp.noteburst``)

   example
   ├── .github
   ├── client
   │   ├── pyproject.toml
   │   └── src
   │       └── lsst
   │           └── rsp
   │               └── noteburst
   │                   ├── __init__.py
   │                   └── models.py
   ├── Dockerfile
   ├── Makefile
   └── server
       ├── pyproject.toml
       └── src
           └── noteburst

A setuptools build backend can discover the client's namespace package with this configuration in ``pyproject.toml``:

.. code-block:: toml

   [tool.setuptools.packages.find]
   where = ["src"] # for namespace package discovery

.. note::

   Client libraries for Roundtable applications may or may not use a similar namespace prefix, depending on our marketing strategy.
   For example, LSST the Docs (or its successor) might not use "roundtable" in its branding if we want advertise it as being deployable separately from Phalanx/Roundtable.

.. _pydantic-models:

Architectural patterns for Pydantic models
==========================================

In many applications, our existing practice has been to reuse the same Pydantic models for both the REST API and the application's internal domain layer.
This is a convenient, but has the downside of exposing the application's internal domain through the REST API.
If the models are now shared with clients, the interface models must be truly separate because clients are unlikely to have access to the dependencies needed by the server's domain models.

The client-server monorepo architecture suggests a four-layer model architecture:

Interface models
    These are stored in the client library, and strictly describe the API request and response schemas.
Server-side interface models
    These are stored in the server application alongside the API route handlers, and are subclasses of the interface models that include additional constructor class methods.
Server-side domain models
    These models (which could even be simple dataclasses) store the application's internal domain information and logic. The service layer acts on domain models, and the server-side interface response models take domain models as input in their constructors.
Storage models
    These models describe the data as it is stored in database like Postgres, Redis, or an external API.
    Our SQL database models are typically SQLAlchemy classes, while the Redis and external API models are typically Pydantic models.
    Using distinct storage models from the API and domain is already common SQuaRE practice.

To demonstrate how this architecture works, we'll consider Noteburst, which has a very simple REST API.
Clients send a ``POST /notebooks/`` request with a Jupyter notebook they would like to run on the Rubin Science Platform.
The result of that initial request is a response containing information about the job, including a URL where the client can poll for the result with ``GET`` requests.

Interface model example
-----------------------

The client library for Noteburst would include two Pydantic models for the request and response schemas.
The ``PostNotebookRequest`` model describes the JSON-formatted data that clients send in their ``POST /notebooks/`` requests.
The ``NotebookResponse`` model describes the format of the server's response, both to the original ``POST /notebooks/`` request and any subsequent ``GET`` requests to the job result URL.
Notice how the models describe the schemas of fields and don't rely on internal domain details of the application.

.. literalinclude:: example-code/interface.py

.. note::

   The ``arq.Jobs.JobStatus`` dependency, which is an enum, is technically domain-specific.
   Best practice would be to create a generic enum in the client library that defines job states.
   Then the noteburst server interface would transform ``arq``\ 's ``JobStatus`` into the Noteburst API enum.
   That way, if Noteburst no longer uses ``arq``, the status variables would not change.
   Additionally, the client library would no longer depend on ``arq``.

Server-side interface model example
-----------------------------------

In the server application, alongside the Python module containing the endpoint handlers, Noteburst imports and subclasses the base interface models from the client library.
Notice how the purpose of these subclasses is to add additional constructors and helper methods.
The ``NotebookResponse.from_job_metadata`` classmethod specifically creates a notebook response from internal domain models (namely ``JobMetadata``).

.. literalinclude:: example-code/serverinterface.py

A new library for SQuaRE Pydantic model utilities
=================================================

Safir includes several utilities for building Pydantic models, including validation methods and datetime formatters.
Given that the interface models in the client libraries should not depend on Safir (and hence the full FastAPI and Starlette server framework), these helpers should be moved into a separate library package.

.. _sansio-client:

A sans-I/O architecture for client classes
==========================================

Besides the Pydantic models, the client libraries can also include classes that make it easy to send requests to the application.
Those client classes would help with building URLs, assembling authentication headers, constructing the request models, and more.
Although not strictly necessary, a useful pattern we should consider when building these client classes is the `Sans-I/O pattern <https://sans-io.readthedocs.io>`__.
This pattern is used by Gidgethub_, the GitHub API client, and also by Kafkit_, SQuaRE's client for the Confluent Schema Registry.
With the sans-I/O pattern, it's possible to create a client that can work with multiple HTTP libraries, such as HTTPX, aiohttp, and Requests.

To implement a sans-I/O client, create a *abstract* class that implements the HTTP methods (``GET``, ``POST``, ``PATCH``, ``PUT``, ``DELETE``) which format headers and request bodies, as well as providing any higher-level methods that work with specific endpoints.
All actual HTTP calls are made through an abstract ``_request`` method that takes the HTTP method, URL, headers, and body (as bytes), as its arguments.
Then for each HTTP client library, create a subclass of that sans-I/O abstract class that implements the ``_request`` method for that HTTP client.

This approach future-proofs the client library for new HTTP libraries, and makes the client more widely useful.
As well, a mock version of the client can be implemented that doesn't do any network requests, but does capture information for introspection.
Such a mock can be useful for testing.

Review and recommendations
==========================

The vertical monorepo architecture is a means for efficiently developing and publishing code that is used both in the server and client applications.
With the vertical monorepo, the client and server share exactly the same Pydantic model that defines the structure of REST endpoint request and response bodies (:ref:`pydantic-models`).
The server also benefits from the client class, which can help drive the server's tests.
Other clients can also benefit from a centrally-maintained mock client of a service (:ref:`sansio-client`).

This technote has demonstrated that a vertical monorepo is possible to implement, but there are drawbacks:

- Client dependencies are not version-pinned in the server application by default (a manual maintenance process is necessary, see :ref:`client-dependency`).
- The architecture is unfamiliar to the common Python developer, so extra documentation is needed for both our team and for open source collaborators.
- Most Python tooling is not designed around monorepos, so the usage here is against the grain.

Ultimately there is a both a cost and a benefit to adopting the vertical client-server monorepo architecture in our applications.
For any given application, the balance of this analysis may weigh towards or away from implementing this pattern.
If an application has no API clients (or we are not developing Python clients), the client-server monorepo provides no benefit.
On the opposite end of the spectrum, if the application has a complex API, an API that is rapidly developed in ways that clients must quickly upgrade to, and we as a team are interacting with that application from multiple clients, then the client-server monorepo is clearly beneficial.
For applications that are somewhere in between it becomes a judgement call for whether the API is complex *enough*, changes *enough*, or has *enough* clients to justify the downsides of the client-server monorepo architecture.

.. mermaid:: decision-chart.mmd

Overall, we believe that SQuaRE does have applications where the client-server vertical monorepo provides clear benefits.
For example, the JupyterLab Controller (:sqr:`066`) has a substantial API with multiple Python clients (Mobu and Noteburst, among potential others).
Outside the scope of REST API servers and clients, the vertical monorepo could also benefit SQuaRE's Kafka producers and clients.
If the Avro-encoded messages have schemas originally defined as Pydantic models, then the producer could publish a client library containing those models which Kafka consumers could use.

.. Make in-text citations with: :cite:`bibkey`.

.. References
.. ==========

.. .. bibliography:: local.bib lsstbib/books.bib lsstbib/lsst.bib lsstbib/lsst-dm.bib lsstbib/refs.bib lsstbib/refs_ads.bib
..    :style: lsst_aa

.. _fastapi: https://fastapi.tiangolo.com
.. _gidgethub: https://gidgethub.readthedocs.io/
.. _`JupyterLab Controller`: https://github.com/lsst-sqre/jupyterlab-controller
.. _kafkit: https://kafkit.lsst.io
.. _mobu: https://github.com/lsst-sqre/mobu
.. _mypy: https://mypy.readthedocs.io/en/stable/
.. _namespace packages: https://setuptools.pypa.io/en/latest/userguide/package_discovery.html
.. _noteburst: https://github.com/lsst-sqre/noteburst
.. _pip-tools: https://pip-tools.rtfd.io/
.. _pydantic: https://docs.pydantic.dev
.. _safir: https://safir.lsst.io
.. _tox: https://tox.wiki/en/latest/
