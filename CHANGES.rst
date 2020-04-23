CHANGELOG
=========

1.3.2 (unreleased)
------------------

- Add support for Python-3.8

- Drop support for Python-2.7

- Modernize development environment with pipenv


1.3.1 (2019-03-01)
------------------

- Updated the script template to make it lint friendly.


1.3.0 (2018-07-11)
------------------

- Suppport for Python 3.6 and 3.7. Dropped Python 3.5.

- Fixed compatibility to not use `future`, since it imported `ConfigParser` as
  `configparser` in Python 2.7. Instead the official `configparser` backport
  is used.


1.2.1 (2018-02-06)
------------------

- Bugfix: proper error when `cmd` argument missing in Python 3


1.2.0 (2018-02-06)
------------------

- Python 3 compatibility.


1.1.1 (2017-05-23)
------------------

- Update README.rst badges.


1.1.0 (2017-05-23)
------------------

- First public release using all public tools.


1.0.0 (2017-05-16)
------------------

- First packaged version.
