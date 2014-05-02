PYTHON = python2.7


all: bin/test

bootstrap.py:
	wget http://downloads.buildout.org/2/bootstrap.py

.venv:
	virtualenv -p $(PYTHON) .venv

bin/buildout: .venv bootstrap.py
	.venv/bin/python bootstrap.py

bin/test: bin/buildout buildout.cfg setup.py versions.cfg
	bin/buildout
	touch bin/test

.PHONY: test
test: bin/test
	bin/test -v

.PHONY: coverage
coverage: bin/test
	bin/coverage run --source=src --omit=*tests* ./bin/test
	bin/coverage report
	bin/coverage html
	@echo
	@echo Now run:
	@echo
	@echo "    $ sensible-browser htmlcov/index.html"
	@echo

clean:
	rm -rvf bin src/*.egg-info .installed.cfg parts .venv
