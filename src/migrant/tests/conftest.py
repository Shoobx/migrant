###############################################################################
#
# Copyright 2014 by Shoobx, Inc.
#
###############################################################################

import logging

import pytest
import mock

@pytest.fixture
def migrant_backend():
    """Fixture to set up backend
    """

    class BackendSetter:
        def __init__(self, mocked_get_backend):
            self.mocked_get_backend = mocked_get_backend

        def set(self, backend):
            self.mocked_get_backend.return_value = lambda cfg: backend

    with mock.patch("migrant.backend.get_backend") as get_backend:
        yield BackendSetter(get_backend)


def pytest_configure(config):
    logging.root.addHandler(logging.NullHandler())
