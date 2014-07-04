from setuptools import setup, find_packages


setup(
    name='granoloader',
    version='0.1.0',
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
        "click>=2.3"
    ],
    tests_require=[],
    entry_points="""
        [console_scripts]
        granoloader=granoloader.command:load
    """,
)
