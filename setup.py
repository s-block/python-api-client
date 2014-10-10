import os
from setuptools import setup, find_packages


# Utility function to read the README file.
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name="python_api_client",
    version="0.0.1",
    author="Josh Rowe",
    author_email="josh@s-block.com",
    description="Python client for REST api.",
    license="BSD",
    keywords="python REST api client",
    url="",
    packages=find_packages(exclude=['tests']),
    long_description=read('README.md'),
    classifiers=[
        "Development Status :: 3 - Alpha",
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules'
        "License :: OSI Approved :: GNU GENERAL PUBLIC LICENSE",
    ],
    install_requires=[
        "requests >= 2.3.0",
        "six >= 1.7.3",
        "pytz >= 2013b",
        "python-dateutil >= 2.2",
    ]
)
