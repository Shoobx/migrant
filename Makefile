PYTHON = python2.7


all: bin/py.test

bootstrap.py:
	wget http://downloads.buildout.org/2/bootstrap.py

.venv:
	virtualenv -p $(PYTHON) .venv

bin/buildout: .venv bootstrap.py
	.venv/bin/python bootstrap.py

bin/py.test: bin/buildout buildout.cfg setup.py versions.cfg
	bin/buildout
	touch bin/py.test

.PHONY: test
test: bin/py.test
	bin/py.test --cov=src --cov-report=term-missing --cov-report=html -s --tb=native

jenkins-build: bin/py.test
	bin/py.test -vv --cov=src --cov-report=xml --junit-xml=testresults.xml

clean:
	rm -rvf bin src/*.egg-info .installed.cfg parts .venv

