# pyenv-mkenv

Simplify pyenv environment creation; script requires python 3.6+.

Do you use [pyenv](https://github.com/pyenv/pyenv)?

When you check out a new repository, the workflow looks something like this:

```sh
pyenv virtualenv $MY_PY_VERSION $MY_REPO_NAME
pyenv local $MY_REPO_NAME
pip install -U pip
pip install -r requirements.txt
```

There has to be a better way!

Now there is:

```sh
mkenv -r requirements.txt
```

This script does a number of things:

- Pick a python version (by preference, the most recent installed CPython version; see below)
- Create a pyenv-virtualenv using the directory name by default (controlled by `-n` / `--name`)
- Update pip
- Install requirements (multiple paths can be given)

## Installation

- From PyPI: `pip install pyenv-mkenv`
- From github: `pip install git+git://github.com/clbarnes/pyenv-mkenv.git`
- For development: `git clone git@github.com:clbarnes/pyenv-mkenv.git && cd pyenv-mkenv && pip install -e .`

Or just copy [`mkenv.py`](./mkenv.py); it's dependency-free.

## Usage

```help
usage: mkenv [-h] [-p] [-n NAME] [-r [REQUIREMENTS]] [-v] [--version]
             [py_version]

positional arguments:
  py_version            Python version. If this option starts with '/', the
                        rest will be interpreted as a regex; otherwise, a
                        simple match to the start of the version name will be
                        used. Empty string by default. By default, mkenv will
                        try to find the highest version matching the string
                        (use -p to see priority and pick) manually)

optional arguments:
  -h, --help            show this help message and exit
  -p, --pick            Prompt to select from matching versions
  -n NAME, --name NAME  Name for the environment (defaults to directory name)
  -r [REQUIREMENTS], --requirements [REQUIREMENTS]
                        Requirements files to install from. If option is used
                        with no path given, user will be prompted.
  -v, --verbose
  --version             show program's version number and exit
```

### Python version

pyenv-mkenv lists available python versions (i.e. non-symlink directories in `$PYENV_HOME/versions/`), and sorts them.
The sort order is intended to be somewhat intuitive:

- Prefer standard CPython distributions (i.e. starts with a digit)
- Prefer higher versions (i.e. substrings which look like versions are parsed and sorted descending)
- Non-standard distributions are sorted lexicographically without version numbers, and then by their version number (multiple version numbers, e.g. pypy3.6-7.3.0, are addressed left to right)

If no `py_version` argument is given, the first item on the list is chosen.
If a string is given, the first item on the list which starts with that string is chosen (e.g. `3.8 -> 3.8.1`).
If the given string starts with a `/`, treat the remainder as a regex which is searched for within each version name; the first matching name is used.

To make sure which version you're getting, use the `-p` / `--pick` option.
This will show versions which match the `py_version` argument (in sorted order), and allow you to select which one you want.

### Requirements

By default, `mkenv` does not install any requirements.
However, any number of requirements files can be added by using the `-r` option.
If `-r` is supplied without an argument, `mkenv` searches down into the directory tree, looking for anything matching the glob `requirements*.txt`, ignoring hidden directories, and prompts the user to select which ones they want to install.

## Disclaimer

This is not a pyenv plugin; it is a python script which assumes you have pyenv installed.
