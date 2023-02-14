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
Even if they were published to a repository like PyPI, applications have pinned dependencies for reasons of build reproducibility that prevent them from realistically being installed in other contexts.
This is also why SQuaRE has two fundamentally different templates for python projects: the FastAPI application template and the Python library template.

Keeping with the common SQuaRE practice of using separate Git repositories for Python library packages from applications, we found three conceivable patterns:

1. A client package repository for every application repository
2. Using Safir_ as a shared library for application models
3. A dedicated monorepo for application models

The first option keeps libraries focused on a single domain, but has the downside of doubling the number of GitHub repositories that need to be maintained.
Options 2 and 3 collect models together, which reduces the number of repositories, but introduces new issues of version management if different versions of an application's models need to be used simultaneously by a client.

In all of these cases, using a separate library for application models makes application development much more inconvenient.
This is because server application dependencies are resolved and hashed with pip-tools_.
This practice results in highly reproducible Docker image builds, and of course implies that a server application's dependencies are stable.
There isn't a good workflow for developing a library simultaneously with an application.

A vertical monorepo architecture
--------------------------------

The potential solutions listed previously introduce the issue of coordinated pull requests and releases being required to make any change to any REST API change.
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

How the application depends on the client library
-------------------------------------------------

For an effective development workflow, the application needs to be able to import models from the client library locally, rather than through a PyPI release.
In current practice, applications use the ``requirements.txt`` file format to declare their dependencies.
We were not able to declare a local dependency in the requirements file.

We found the only viable mechanism is to manually pip install the client library in development and deployment contexts (the specific patterns are explored below).
The downside of this approach is that the client isn't considered by the pinned dependencies compiled by pip-tools_.
Normally runtime dependencies for the server application are abstractly listed in a ``requirements/main.in`` file for each application; pip-tools_ compiles these dependencies and their sub-dependencies into a ``requirements/main.txt`` file which is committed to the Git repository and actually used for installing dependencies.
This practice ensures that Docker builds and development environments alike are reproducible.
In practice, the client library's absence from ``requirements/main.txt`` itself isn't harmful because the client is inherently pinned by virtue of being co-developed in the same Git repository.

What's potentially concerning, though, is the absence of the client's own dependencies from the application's ``requirements/main.txt`` dependencies.
We could mitigate this risk by limiting client library dependencies to packages that are already in the main application's ``requirements/main.txt``.

Installing the client in the Docker image
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In the Docker image, both the client and server directories are copied into the intermediate ``install-image`` stage of the Docker build and installed into the virtual environment:

.. code-block:: Dockerfile

   RUN pip install --no-cache-dir ./client
   RUN pip install --no-cache-dir ./server

Installing the client in the server's Tox environments
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Tox_ runs tests and other development tasks in virtual environments that Tox itself manages.
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

We found this only works if the ``requirements/main.txt`` and ``dev.txt`` requirements are *unhashed*.
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
Add extra tests for the client library is superfluous.

Linting the client and server code bases
----------------------------------------

For Python projects, we use linters to ensure consistency and correctness:

- isort, to sort imports consistently
- block, to format Python code consistently
- mypy, to check type annotations
- flake8, to statically validate Python code

These linters are generally triggered by automatically with the pre-commit Git hook manager, or manually through a tox environment.

In the monorepo, pre-commit itself needs to be configured at the root since it doesn't have specific support for monorepos (see `pre-commit/pre-commit#466 <https://github.com/pre-commit/pre-commit/issues/466>`__).
Thus the monorepo has a ``.pre-commit-config.yaml`` file at its root.
If the pre-commit hooks need to be configured different for each repo, though
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
Since both the client and server APIs are available in the documentation build time, code from both the server and client can be documented in the same Sphinx project by referencing the correct modules with the ``automodapi`` directive.
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
This will reduce the risk of collisions with other packages on open source package registries.

Python namespace
----------------

We may want place client libraries in a common namespace using a Python packaging feature called `namespace packages`_.
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
   │               └── example
   │                   ├── __init__.py
   │                   └── models.py
   ├── Dockerfile
   ├── Makefile
   └── server
       ├── pyproject.toml
       └── src
           └── example

With a setuptools build backend, the namespace package for the client can be discovered with this configuration in ``pyproject.toml``:

.. code-block:: toml

   [tool.setuptools.packages.find]
   where = ["src"] # for namespace package discovery

.. note::

   Client libraries for Roundtable applications may or may not use a similar namespace prefix, depending on our marketing strategy.
   For example, LSST the Docs (or its successor) might not use "roundtable" in its branding if we want advertise it as being deployable separately from Phalanx/Roundtable.

Architectural patterns for Pydantic models
==========================================

In many of our applications, our existing practice has been to reuse the same Pydantic models for both the REST API and the application's internal domain layer.
This is a convenient, but has the downside of exposing the application's internal domain through the REST API.
If the models are now shared with clients, the interface models truly must be separate because clients are unlikely to have access to the dependencies of the server's domain models.

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

To demonstrate how this architecture works, we'll consider Noteburst.
Noteburst has a simple REST API.
Clients can send a ``POST /notebooks/`` request with a Jupyter notebook they would like to run on the Rubin Science Platform.
The result of that initial request is a dataset containing information about the job, including a URL where the client can poll for the result with ``GET`` requests.

Interface model example
-----------------------

The client library for Noteburst would include these two Pydantic models.
The ``PostNotebookRequest`` model describes the JSON-formatted data that clients send in their ``POST /notebooks/`` requests.
The ``NotebookResponse`` model describes the format of the server's initial response, both to the original ``POST /notebooks/`` request and any subsequent ``GET`` requests to the job result URL.
Notice how the models describe the schemas of fields and don't rely on domain information.

.. literalinclude:: example-code/interface.py

.. note::

   The ``arq.Jobs.JobStatus`` dependency, which is an enum, is actually domain specific.
   Best practice would be to create a generic enum in the client library that defines job states and then transform ``arq``\ 's ``JobStatus`` into that enum type.
   Then if Noteburst no longer uses ``arq``, the status variables would not change.
   Additionally, the client library would no longer depend on ``arq``.

Server-side interface model example
-----------------------------------

In the server application, alongside the module containing the endpoint handlers, Noteburst imports and subclasses the base interface models from the client library.
Notice how the purpose of these subclasses is to add additional constructors and helper methods.
The ``NotebookResponse.from_job_metadata`` classmethod specifically creates a notebook response from internal domain models (namely JobMetadata).

.. literalinclude:: example-code/serverinterface.py

.. Make in-text citations with: :cite:`bibkey`.

.. References
.. ==========

.. .. bibliography:: local.bib lsstbib/books.bib lsstbib/lsst.bib lsstbib/lsst-dm.bib lsstbib/refs.bib lsstbib/refs_ads.bib
..    :style: lsst_aa

.. _fastapi: https://fastapi.tiangolo.com
.. _`JupyterLab Controller`: https://github.com/lsst-sqre/jupyterlab-controller
.. _mobu: https://github.com/lsst-sqre/mobu
.. _mypy: https://mypy.readthedocs.io/en/stable/
.. _namespace packages: https://setuptools.pypa.io/en/latest/userguide/package_discovery.html
.. _noteburst: https://github.com/lsst-sqre/noteburst
.. _pip-tools: https://pip-tools.rtfd.io/
.. _pydantic: https://docs.pydantic.dev
.. _safir: https://safir.lsst.io
.. _tox: https://tox.wiki/en/latest/
