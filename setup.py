###############################################################################
#
# Copyright 2014 by Shoobx, Inc.
#
###############################################################################
import os
from setuptools import setup, find_packages


def read_file(filename):
    return open(os.path.join(os.path.dirname(__file__), filename)).read()


setup(
    name="migrant",
    version="1.5.0",
    author="Shoobx, Inc.",
    author_email="dev@shoobx.com",
    description="Database Migration Engine",
    long_description=read_file("README.rst") + "\n\n" + read_file("CHANGES.rst"),
    keywords="migration version database",
    license="MIT",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: Implementation :: CPython",
        "Natural Language :: English",
        "Operating System :: OS Independent",
    ],
    packages=find_packages("src"),
    package_dir={"": "src"},
    namespace_packages=[],
    include_package_data=True,
    zip_safe=False,
    extras_require=dict(test=["coverage", "mock"],),
    package_data = {'migrant': ['py.typed']},
    install_requires=[
        "configparser ; python_version<'3.0'",  # Py3 configparser backport.
        "setuptools",
    ],
    entry_points={
        "console_scripts": ["migrant = migrant.cli:main",],
        "migrant": ["noop = migrant.backend:NoopBackend"],
    },
)
