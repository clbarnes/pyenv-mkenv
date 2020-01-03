#!/usr/bin/env python3
"""
Simple script to help create and use pyenv virtualenvs

Originally released by Chris L. Barnes at https://github.com/clbarnes/pyenv-mkenv , MIT license.
"""
import logging
import os
import re
import subprocess as sp
import textwrap
import warnings
from argparse import ArgumentParser
from pathlib import Path
from string import digits
from typing import List, NamedTuple
import sys

logger = logging.getLogger(__name__)

VERSION = "1.0.0"

CWD = Path.cwd()


def add_log_level(level_name, level_num, method_name=None):
    """
    Adapted from https://stackoverflow.com/a/35804945/2700168

    Comprehensively adds a new logging level to the `logging` module and the
    currently configured logging class.
    `level_name` becomes an attribute of the `logging` module with the value
    `level_num`. `method_name` becomes a convenience method for both `logging`
    itself and the class returned by `logging.getLoggerClass()` (usually just
    `logging.Logger`). If `methodName` is not specified, `levelName.lower()` is
    used.
    To avoid accidental clobberings of existing attributes, this method will
    raise an `AttributeError` if the level name is already an attribute of the
    `logging` module or if the method name is already present
    Example
    -------
    >>> addLoggingLevel('TRACE', logging.DEBUG - 5)
    >>> logging.getLogger(__name__).setLevel("TRACE")
    >>> logging.getLogger(__name__).trace('that worked')
    >>> logging.trace('so did this')
    >>> logging.TRACE
    5
    """
    if not method_name:
        method_name = level_name.lower()

    if hasattr(logging, level_name):
        raise AttributeError("{} already defined in logging module".format(level_name))
    if hasattr(logging, method_name):
        raise AttributeError("{} already defined in logging module".format(method_name))
    if hasattr(logging.getLoggerClass(), method_name):
        raise AttributeError("{} already defined in logger class".format(method_name))

    # This method was inspired by the answers to Stack Overflow post
    # http://stackoverflow.com/q/2183233/2988730, especially
    # http://stackoverflow.com/a/13638084/2988730
    def log_for_level(self, message, *args, **kwargs):
        if self.isEnabledFor(level_num):
            self._log(level_num, message, args, **kwargs)

    def log_to_root(message, *args, **kwargs):
        logging.log(level_num, message, *args, **kwargs)

    logging.addLevelName(level_num, level_name)
    setattr(logging, level_name, level_num)
    setattr(logging.getLoggerClass(), method_name, log_for_level)
    setattr(logging, method_name, log_to_root)


add_log_level("STDERR", 6)
add_log_level("STDOUT", 3)


def get_pyenv_root():
    try:
        root = Path(os.environ["PYENV_ROOT"])
    except KeyError:
        msg = "PYENV_ROOT not set - is pyenv installed?"
    else:
        if root.is_dir():
            return root
        else:
            msg = "PYENV_ROOT is not a directory - is pyenv installed?"

    raise RuntimeError(msg)


PYENV_ROOT = get_pyenv_root()

ver_re = re.compile(r"(?P<major>\d+)\.(?P<minor>\d+)(\.(?P<patch>\d+))?")


def sort_key(s):
    """Sort python version strings.

    Numeric only (i.e. baseline CPython) sorts first, in descending version order.
    Versions starting with strings sort lexicographically with all numbers removed, then in descending version order.
    """
    key = []
    if s[0] in digits:
        key.append(0)
    else:
        key.append(1)
        key.append(ver_re.sub("", s))

    for match in ver_re.finditer(s):
        groups = match.groupdict()
        patch = groups.get("patch")
        if patch is None:
            patch = -1
        key.append((-int(groups["major"]), -int(groups["minor"]), -int(patch)))

    return tuple(key)


def get_pyenv_versions():
    vdir = PYENV_ROOT / "versions"
    versions = sorted(
        (v.name for v in vdir.iterdir() if not v.is_symlink()), key=sort_key
    )
    logger.debug("Found versions %s", versions)
    return versions


class Arguments(NamedTuple):
    py_version: str
    name: str
    requirements: List[str]

    @classmethod
    def from_parsed(cls, namespace):
        matching_versions = list(filter_versions(namespace.py_version))
        if namespace.pick:
            version = pick_versions(matching_versions)
        else:
            version = matching_versions[0]

        if namespace.requirements == [None]:
            reqs = list(pick_requirements())
        else:
            reqs = namespace.requirements

        return Arguments(version, namespace.name, reqs)


def parse_args(args=None):
    parser = ArgumentParser()
    parser.add_argument(
        "py_version",
        nargs="?",
        help="Python version. If this option starts with '/', the rest will be interpreted as a regex; otherwise, a simple match to the start of the version name will be used. Empty string by default. By default, mkenv will try to find the highest version matching the string (use -p to see priority and pick) manually)",
        default="",
    )
    parser.add_argument(
        "-p",
        "--pick",
        action="store_true",
        help="Prompt to select from matching versions",
    )
    parser.add_argument(
        "-n",
        "--name",
        help="Name for the environment (defaults to directory name)",
        default=CWD.name,
    )
    parser.add_argument(
        "-r",
        "--requirements",
        nargs="?",
        action="append",
        const=None,
        help="Requirements files to install from. If option is used with no path given, user will be prompted.",
    )
    parser.add_argument("-v", "--verbose", action="count", default=0)
    parser.add_argument("--version", action="version", version=VERSION)

    return parser.parse_args(args)


def filter_versions(filter_str):
    versions = get_pyenv_versions()

    if filter_str.startswith("/"):
        filter_str = filter_str[1:]
        logger.info("Filtering %s versions with regex '%s'", len(versions), filter_str)
        regex = re.compile(filter_str)
        for v in versions:
            if regex.search(v):
                yield v
    else:
        logger.info(
            "Filtering %s versions by starting string '%s'", len(versions), filter_str
        )
        for v in versions:
            if v.startswith(filter_str):
                yield v


QUIT_SIGNAL = object()


def picker(options, prompt="Select an option:", sep=". ", nargs=1, allow_quit=False):
    multioption = (isinstance(nargs, int) and nargs > 1) or nargs in tuple("+*")

    s = prompt + "\n"

    allows_empty = nargs in tuple("?*")

    opt_dict = dict(enumerate(options, 1))
    highest_n = max(opt_dict)
    n_length = len(f"  {highest_n}{sep}")

    for idx, option in opt_dict.items():
        s += f"  {idx}{sep}".ljust(n_length) + f"{option}\n"
    if allow_quit:
        s += "q: quit\n"

    s += (
        {
            "?": "Type an option or leave empty",
            "*": "Type any number of comma-separated options",
            "+": "Type one or more comma-separated options",
        }.get(nargs, f"Type {nargs} option{'s' if multioption else ''}")
        + ", and press enter: "
    )

    counter = 1
    while True:
        logger.info("User selection attempt %s", counter)
        counter += 1
        response = input(s).strip()
        if not response:
            if allows_empty:
                responses = []
                break
            else:
                print("No option given")
                continue

        if multioption:
            responses = [r.strip() for r in response.split(",")]
        else:
            responses = [response]

        if allow_quit and "q" in (r.lower() for r in responses):
            logger.debug("Quit signal found")
            return QUIT_SIGNAL

        out = []
        for r in responses:
            try:
                out.append(opt_dict[int(response)])
            except ValueError:
                print(f"Response '{response}' is not a valid command or integer")
                break
            except KeyError:
                print(f"{response} does not correspond to an option")
                break
        else:
            if not multioption:
                logger.debug("Returning single option")
                out = out[0]
            else:
                logger.debug("Returning multiple options")
            return out


def pick_versions(versions):
    logger.debug("Getting user selection for python version")
    out = picker(versions, prompt="Pick python version: ", allow_quit=True)
    if out is QUIT_SIGNAL:
        sys.exit(0)
    return out


def pick_requirements():
    logger.debug("Getting user selection for requirements files to install")
    reqs = []
    for root, dnames, fnames in os.walk(CWD):
        for fname in sorted(fnames):
            if not fname.startswith("requirements") or not fname.endswith(".txt"):
                continue
            reqs.append(os.path.join(root, fname))
        dnames[:] = (d for d in dnames if not d.startswith("."))

    return picker(reqs, "Select which requirements to install: ", nargs="*")


def create_environment(version, name, requirements_files=None):
    print(f"Creating environment called '{name}' for python version '{version}'...")
    pyenv_path = str(PYENV_ROOT / "bin" / "pyenv")
    creation = sp.run(
        [pyenv_path, "virtualenv", version, name], capture_output=True, text=True
    )
    logger.stdout(creation.stdout)
    if creation.returncode:
        raise RuntimeError(
            f"Could not create pyenv environment (status code {creation.returncode})\n"
            + textwrap.indent(creation.stderr, "  ")
        )
    else:
        logger.stderr(creation.stderr)

    print("Setting as local version...")
    localise = sp.run(
        [pyenv_path, "local", name], capture_output=True, text=True, check=True
    )
    logger.stdout(localise.stdout)
    logger.stderr(localise.stderr)

    print("Updating pip...")
    pip_path = str(PYENV_ROOT / "versions" / name / "bin" / "pip")
    update = sp.run(
        [pip_path, "install", "-U", "pip"], capture_output=True, text=True, check=True
    )
    logger.stdout(update.stdout)
    logger.stderr(update.stderr)

    if requirements_files:
        for req in requirements_files:
            print(f"Installing requirements from {req}...")
            install = sp.run(
                [pip_path, "install", "-r", req], capture_output=True, text=True
            )
            logger.stdout(install.stdout)
            if install.returncode:
                warnings.warn(
                    f"Could not install requirements from (status code {install.returncode}): {req}\n"
                    + textwrap.indent(install.stderr, "  ")
                )
            else:
                logger.stderr(install.stderr)

    print("Done!")


def main():
    parsed = parse_args()
    level = {
        0: logging.WARN,
        1: logging.INFO,
        2: logging.DEBUG,
        3: logging.STDERR,
        4: logging.STDOUT,
    }.get(parsed.verbose, logging.STDOUT)
    logging.basicConfig(level=level)
    args = Arguments.from_parsed(parsed)
    create_environment(*args)


if __name__ == "__main__":
    main()
