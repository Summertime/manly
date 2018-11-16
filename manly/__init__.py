#!/usr/bin/env python

"""
    manly
    ~~~~~
    This script is used (through its' cli) to extract information from
    manual pages. More specifically, it tells the user, how the given
    flags modify a command's behaviour.

    In the code "options" refer to options for manly and "flags" refer
    to options for the given command.
"""


from __future__ import print_function


__author__ = "Carl Bordum Hansen"
__version__ = "0.3.3"


import re
import subprocess
import sys


# A python3.5 backport to cover differences between 2/3.4 and 3.5
class CalledProcessError(subprocess.CalledProcessError):
    def __init__(self, returncode, cmd, output=None, stderr=None):
        self.returncode = returncode
        self.cmd = cmd
        self.output = output
        self.stderr = stderr


_ANSI_BOLD = "%s"
if sys.stdout.isatty():
    _ANSI_BOLD = "\033[1m%s\033[0m"


def parse_flags(raw_flags, single_dash=False):
    """Return a list of flags.

    If *single_dash* is False, concatenated flags will be split into
    individual flags (eg. '-la' -> '-l', '-a').
    """
    flags = []
    for flag in raw_flags:
        if flag.startswith("--") or single_dash:
            flags.append(flag)
        elif flag.startswith("-"):
            for char in flag[1:]:
                flags.append("-" + char)
    return flags


def parse_manpage(page, flags):
    """Return a list of blocks that match *flags* in *page*."""
    current_section = []
    output = []

    for line in page.splitlines():
        if line:
            current_section.append(line)
            continue

        section = "\n".join(current_section)
        section_top = section.strip().split("\n")[:2]
        first_line = section_top[0].split(",")

        segments = [seg.strip() for seg in first_line]
        try:
            segments.append(section_top[1].strip())
        except IndexError:
            pass

        for flag in flags:
            for segment in segments:
                if segment.startswith(flag):
                    output.append(
                        re.sub(r"(^|\s)%s" % flag, _ANSI_BOLD % flag, section).rstrip()
                    )
                    break
        current_section = []
    return output


def manly(command):
    if isinstance(command, str):
        command = command.split(" ")
    program = command[0]
    flags = command[1:]

    # we set MANWIDTH, so we don't rely on the users terminal width
    # try `export MANWIDTH=80` -- makes manuals more readable imo :)
    try:
        process = subprocess.Popen(
            ["man", "--", program],
            env={"MANWIDTH": "80"},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        out, err = (s.decode('utf-8') for s in process.communicate())
        # emulate subprocess.run of py3.5, for easier changing in the future
        if process.returncode:
            raise CalledProcessError(
                process.returncode,
                ["man", "--", program],
                out,
                err,
            )
    except OSError as e:
        print("Couldn't execute 'man'", file=sys.stderr)
        print(e, file=sys.stderr)
        sys.exit(127)
    except CalledProcessError as e:
        print(e.stderr.strip(), file=sys.stderr)
        sys.exit(e.returncode)

    manpage = out

    # commands such as `clang` use single dash names like "-nostdinc"
    uses_single_dash_names = bool(re.search(r"\n\n\s+-\w{2,}", manpage))
    flags = parse_flags(flags, single_dash=uses_single_dash_names)
    output = parse_manpage(manpage, flags)
    title = _ANSI_BOLD % (
        re.search(r"(?<=^NAME\n\s{5}).+", manpage, re.MULTILINE).group(0).strip()
    )

    return title, output
