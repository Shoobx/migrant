=======
Migrant
=======

.. image:: https://travis-ci.org/Shoobx/migrant.png?branch=master
   :target: https://travis-ci.org/Shoobx/migrant

.. image:: https://coveralls.io/repos/github/Shoobx/migrant/badge.svg?branch=master
   :target: https://coveralls.io/github/Shoobx/migrant?branch=master

.. image:: https://img.shields.io/pypi/v/migrant.svg
    :target: https://pypi.python.org/pypi/migrant

.. image:: https://img.shields.io/pypi/pyversions/migrant.svg
    :target: https://pypi.python.org/pypi/migrant/

.. image:: https://api.codeclimate.com/v1/badges/08342b65bdf96b761dcd/maintainability
   :target: https://codeclimate.com/github/Shoobx/migrant/maintainability
   :alt: Maintainability

Migrant is a database schema version management framework

Features include:

  * backend agnostic core
  * explicit migration script ordering
  * support for downgrading
  * support for out-of-order migrations
  * support for migrating multiple homogenuous databases


Development
-----------

To set up development environment, use `pipenv`::

    pipenv install --dev

To run tests, use `pytest`::

    pytest

To run tests under all supported environments, use `tox`::

    tox --skip-missing-interpreters

To check for typing errors, use `mypy`::

    mypy src
