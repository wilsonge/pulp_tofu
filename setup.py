#!/usr/bin/env python3

from setuptools import find_packages, setup

with open("requirements.txt") as requirements:
    requirements = requirements.readlines()

setup(
    name="pulp-tofu",
    version="0.1.0a1.dev",
    description="pulp-tofu plugin for the Pulp Project",
    license="GPLv2+",
    author="George Wilson",
    url="http://georges.website/",
    python_requires=">=3.10",
    install_requires=requirements,
    extra_require={"ci": []},
    include_package_data=True,
    packages=find_packages(exclude=["tests", "tests.*"]),
    classifiers=[
        "License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)",
        "Operating System :: POSIX :: Linux",
        "Framework :: Django",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    entry_points={"pulpcore.plugin": ["pulp_tofu = pulp_tofu:default_app_config"]},
)
