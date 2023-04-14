The unified ``sphinx`` command
==============================

Goals
-----

1. Speed
2. Ease of use
3. Unified interface
4. Abstract the Python interface

Potential sub-commands
----------------------

* ``sphinx build``

  - Main command -- build documentation from sources
  - Aliases?
  - 'make mode' to be default

* ``sphinx init``

  - Create a new Sphinx project
  - Aliases: ``create``, ``quickstart``, ``new``?

* Current ``sphinx-autogen`` and ``sphinx-apidoc``

* ``sphinx config``

  - Explain config settings, and modify ``.Sphinx.toml``

* ``sphinx config migrate``

  - move from ``conf.py`` to ``Sphinx.toml``
  - move between versions of ``Sphinx.toml``?
  - config needs some forward compatability mechanism if we add new fields (e.g.
    Ruff's ``external``)

* ``sphinx inventory *``

  - integrate ``sphobjinv``

* ``sphinx serve`` (``preview``?)

  - integrate ``sphinx-autobuild``

* ``sphinx lint`` (``validate``?)


Inspiration
-----------

https://www.mkdocs.org/user-guide/cli/
https://docusaurus.io/docs/cli

Quarto_
~~~~~~~

.. _Quarto: https://quarto.org

render
    Render files or projects to various document types

preview
    Render and preview a document or website project

serve
    Serve a Shiny interactive document

create
    Create a Quarto project or extension

create-project
    Create a project for rendering multiple documents

convert
    Convert documents to alternate representations

pandoc
    Run the version of Pandoc embedded within Quarto

run
    Run a TypeScript, R, Python, or Lua script

add
    Add an extension to this folder or project

install
    Installs an extension or global dependency

publish
    Publish a document or project Available providers include:

check
    Verify correct functioning of Quarto installation

help
    Show this help or the help of a sub-command

tools
    Installation and update of ancillary tools

capabilities
    Query for current capabilities (formats, engines, kernels etc.)

inspect
    Inspect a Quarto project or input path

build-js
    Builds all the javascript assets necessary for IDE support

update
    Updates an extension or global dependency

remove
    Removes an extension

list
    Lists an extension or global dependency

use
    Automate document or project setup tasks

uninstall
    Removes an extension

editor-support
    Miscellaneous tools to support Quarto editor modes


