PYTHON = python2.7


all: bin/test

bootstrap.py:
	wget http://downloads.buildout.org/2/bootstrap.py

.venv:
	virtualenv -p $(PYTHON) .venv

bin/buildout: .venv bootstrap.py
	# ve/bin/pip install --upgrade setuptools
	.venv/bin/python bootstrap.py

bin/test: bin/buildout buildout.cfg setup.py versions.cfg
	bin/buildout
	touch bin/test

test: bin/test
	bin/test -v

clean:
	rm -rvf bin src/*.egg-info .installed.cfg parts .venv
