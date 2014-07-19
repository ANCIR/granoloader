import os
from setuptools import setup, find_packages

VERSION = os.path.join(os.path.dirname(__file__), 'VERSION')
VERSION = open(VERSION, 'r').read().strip()

setup(
    name='granoloader',
    version=VERSION,
    description="Import data to grano using CSV files.",
    long_description="",
    classifiers=[
        ],
    keywords='data client rest grano sna ddj journalism',
    author='Friedrich Lindenberg',
    author_email='friedrich@pudo.org',
    url='https://github.com/granoproject/granoloader',
    license='MIT',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    zip_safe=False,
    install_requires=[
        "grano-client>=0.3",
        "unicodecsv>=0.9.4",
        "click>=2.3",
        "thready>=0.1.4",
        "python-dateutil>=2.2"
    ],
    tests_require=[],
    entry_points="""
        [console_scripts]
        granoloader=granoloader.command:init
    """,
)
