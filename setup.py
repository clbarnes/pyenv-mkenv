import re
from setuptools import setup

with open("README.md") as f:
    desc = f.read()

version_re = r'VERSION = "(.+)"'
with open("mkenv.py") as f:
    script = f.read()
    match = re.search(version_re, script)
    version = match.groups()[0]

setup(
    name="pyenv-mkenv",
    version=version,
    description="Simple script to help create and use pyenv virtualenvs",
    long_description=desc,
    long_description_content_type="text/markdown",
    url="https://github.com/clbarnes/pyenv-mkenv",
    author="Chris L. Barnes",
    author_email="chrislloydbarnes@gmail.com",
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    keywords="pyenv virtualenv venv requirements",
    py_modules=["mkenv"],
    python_requires=">=3.6",
    entry_points={"console_scripts": ["mkenv=mkenv:main"]},
)
