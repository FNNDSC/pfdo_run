"""The ``pfdo_run`` command line and its manual.

The parser and the manual are assembled from pftree's and pfdo's parts plus
pfdo_run's own, and are exposed in parts again for pl-shexec.

Key components:
    - CLI_SELF, ARGS_SYNOPSIS_SELF, TAG_HELP, EXAMPLES: pfdo_run's manual pieces
    - CLI_FULL, CLI_DS, ARGS_SYNOPSIS_FULL, ARGS_SYNOPSIS_DS: the assembled pieces
    - synopsis, manual_build: the manual
    - parserSelf_build / parser_build: the parsers
    - main: the entry point

Typical usage:
    pfdo_run --inputDir /in --outputDir /out --fileFilter jpg \\
        --exec "convert %{inputWorkingDir}/%{inputWorkingFile} %{outputWorkingDir}/out.png"
    pfdo_run --man

Dependencies:
    - pftree, pfdo (their CLI parts and the manual renderer)
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from pfdo.__main__ import ARGS_SYNOPSIS_SELF as PFDO_ARGS_SYNOPSIS_SELF
from pfdo.__main__ import CLI_SELF as PFDO_CLI_SELF
from pfdo.__main__ import parserSelf_build as pfdoParserSelf_build
from pftree.__main__ import (
    ARGS_SYNOPSIS_CORE,
    ARGS_SYNOPSIS_DS,
    ARGS_SYNOPSIS_IO,
    CLI_CORE,
    CLI_DS_IO,
    CLI_IO_CORE,
    logging_configure,
    parserCore_build,
    parserIO_build,
)
from pftree.manual import Manual, manual_print

from pfdo_run import __version__
from pfdo_run.models import PfdoRunOptions, RunResult
from pfdo_run.pfdo_run import PfdoRun

BANNER_ART: str = r"""

                          __    _
                         / _|  | |
                   _ __ | |_ __| | ___   _ __ _   _ _ __
                  | '_ \|  _/ _` |/ _ \ | '__| | | | '_ \
                  | |_) | || (_| | (_) || |  | |_| | | | |
                  | .__/|_| \__,_|\___/ |_|   \__,_|_| |_|
                  | |               ______
                  |_|              |______|

"""

BANNER_TITLE: str = "Path-File Do Run"

BANNER_TEXT: str = """
                            Path-File Do Run

        Recursively walk down a directory tree and run a CLI spec'd app
        on files in each directory (optionally filtered by some simple
        expression). Results of each operation are saved in an output tree
        that preserves the input directory structure.

                             -- version {version} --

        'pfdo_run' demonstrates how to use pftree to traverse
        directory trees and execute some user specified CLI operation
        at each directory level (that optionally contains files of interest).

        As part of the "pf*" suite of applications, it is geared to IO as
        directories. Nested directory trees within some input directory
        are reconstructed in an output directory, preserving directory
        structure.

"""

CLI_SELF: str = """
        --exec <commandTemplate>                                                \\
        [--noJobLogging] [--jobFiles]                                            \\"""

ARGS_SYNOPSIS_SELF: str = """
        --exec <commandTemplate>
        The command to run for each selected file of each directory in the
        input tree, written as a pftag template. See the TAGS section. The
        template is split like a shell command line, each argument has its
        tags resolved, and the result is run directly, without a shell: a
        path with a space in it stays one argument, and shell features such
        as pipes and redirection are not available.

        [--noJobLogging]
        Keep no record of the jobs in the output tree. Usually each job that
        runs appends one line to jobs.jsonl in its output directory: the
        command, its stdout and stderr complete, its return code, the host,
        and when it started and ended, as JSON. ``pflog read`` prints such
        files as a table; a log collector indexes them by field.

        [--jobFiles]
        Also write each job as four files beside its results:

                <inputWorkingFile>-cmd
                <inputWorkingFile>-stdout
                <inputWorkingFile>-stderr
                <inputWorkingFile>-returncode

        The stream files are written as the command runs and, when it ends,
        rendered as a terminal would have shown them: a progress bar redrawn
        a hundred times is one line. For the case where someone will open a
        job's output in an editor; the JSON line already holds all four.

        At --verbosity 2 and above each command's output is also streamed to
        the console while it runs, so a long job can be watched. Under
        --threads the streams of concurrent jobs interleave.
"""

TAG_HELP: str = """
    TAGS

        The --exec template is resolved by pftag (see pftag --man or the
        pftag docs/tags.adoc). A tag is %{name}, optionally piped through
        functions: %{name|function|function(arg, arg)}. Three tags describe
        the job:

            %{inputWorkingDir}    the input directory being processed
            %{outputWorkingDir}   its counterpart in the output tree
            %{inputWorkingFile}   the file being processed

        and every option of pfdo_run is a tag by name, so %{outputDir} is
        the output tree's root. The core tags %{timestamp}, %{date},
        %{hostname}, %{platform}, %{user} and %{pid} are available too.

        Functions derive one name from another:

            %{inputWorkingFile|rmext}             brain.nii.gz -> brain.nii
            %{inputWorkingFile|rmext|rmext}.jpg   brain.nii.gz -> brain.jpg
            %{inputWorkingFile|replace(.,-)}      a.b.c -> a-b-c
            %{inputWorkingFile|re([0-9]+,N)}      im001.dcm -> imN.dcm
            %{inputWorkingDir|basename}           the directory's own name
            %{inputWorkingFile|sha256(8)}         a stable hash of the name

        Nothing outside %{...} is a tag, so a literal % in the command is
        fine. A tag that does not resolve fails that job before it runs;
        the job's record says why.
"""

EXAMPLES: str = """

    EXAMPLES

    Convert every jpg in a tree to png in a parallel tree:

        pfdo_run                                                                \\
            --inputDir /var/www/html/data --fileFilter 'glob:*.jpg'             \\
            --outputDir /var/www/html/png                                       \\
            --exec "convert %{inputWorkingDir}/%{inputWorkingFile}
                            %{outputWorkingDir}/%{inputWorkingFile|rmext}.png"  \\
            --threads 4 --printElapsedTime

    Each conversion's command, stdout, stderr, return code and timing are one
    line in the directory's jobs.jsonl; `pflog read /var/www/html/png/**/jobs.jsonl`
    lists them. Add --verbosity 2 to watch the conversions as they run.

    Run one command per DICOM series, started on the first file:

        pfdo_run                                                                \\
            --inputDir /data --outputDir /out                                   \\
            --fileFilter 'glob:*.dcm' --analyzeFileIndex f                      \\
            --exec "mri_convert %{inputWorkingDir}/%{inputWorkingFile}
                                %{outputWorkingDir}/%{inputWorkingDir|basename}.nii.gz"

    Copy one file out of each directory whose path names a subject:

        pfdo_run                                                                \\
            --inputDir $PWD/raw --outputDir $PWD/out                            \\
            --dirFilter 100307                                                  \\
            --exec "cp %{inputWorkingDir}/brain.mgz %{outputWorkingDir}/brain.mgz" \\
            --analyzeFileIndex f --noJobLogging --json

"""

CLI_FULL: str = CLI_IO_CORE + CLI_SELF + PFDO_CLI_SELF + CLI_CORE
ARGS_SYNOPSIS_FULL: str = ARGS_SYNOPSIS_IO + ARGS_SYNOPSIS_SELF + PFDO_ARGS_SYNOPSIS_SELF + ARGS_SYNOPSIS_CORE
CLI_DS: str = CLI_DS_IO + CLI_SELF + PFDO_CLI_SELF + CLI_CORE
ARGS_SYNOPSIS_DS: str = ARGS_SYNOPSIS_DS + ARGS_SYNOPSIS_SELF + PFDO_ARGS_SYNOPSIS_SELF + ARGS_SYNOPSIS_CORE

DESCRIPTION: str = """
    DESCRIPTION

        ``pfdo_run`` walks the input tree with pftree, selects files in each
        directory with the pfdo filters and --analyzeFileIndex, and runs the
        --exec command once per selected file, with the command's tags
        resolved against that directory and file. The output tree mirrors
        the input tree; each directory's results and job logs land in its
        counterpart. Directories run in parallel under --threads.
"""


def synopsis(shortOnly: bool = False, command: str = "pfdo_run") -> str:
    """Assemble the manual text.

    Args:
        shortOnly: NAME, SYNOPSIS and a brief example only.
        command: the command name shown, for a package built on pfdo_run.

    Returns:
        The manual text, without the banner.
    """
    shortSynopsis: str = (
        f"""
    NAME

        {command}

    SYNOPSIS

        {command} \\"""
        + CLI_FULL
        + f"""

    BRIEF EXAMPLE

        {command}                                                                \\
            --inputDir /var/www/html/data --fileFilter jpg                      \\
            --outputDir /var/www/html/png                                       \\
            --exec "convert %{{inputWorkingDir}}/%{{inputWorkingFile}}
                            %{{outputWorkingDir}}/%{{inputWorkingFile|rmext}}.png"  \\
            --threads 4 --printElapsedTime
    """
    )
    if shortOnly:
        return shortSynopsis
    return shortSynopsis + DESCRIPTION + "\n    ARGS " + ARGS_SYNOPSIS_FULL + TAG_HELP + EXAMPLES


def manual_build() -> Manual:
    """The pfdo_run manual page."""
    return Manual(
        command="pfdo_run",
        art=BANNER_ART,
        title=BANNER_TITLE,
        text=BANNER_TEXT,
        version=__version__,
        synopsisShort=synopsis(shortOnly=True),
        synopsisFull=synopsis(shortOnly=False),
    )


def parserSelf_build() -> argparse.ArgumentParser:
    """pfdo_run's own options.

    Returns:
        A parent parser with ``--exec``, ``--noJobLogging`` and ``--jobFiles``.
    """
    parser: argparse.ArgumentParser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--exec",
        dest="exec",
        default="",
        help=(
            "the command to run per file, a pftag template (required): "
            "%%{inputWorkingDir}, %%{inputWorkingFile}, %%{outputWorkingDir}; "
            "functions pipe, as %%{inputWorkingFile|rmext}; every tag under --man TAGS"
        ),
    )
    parser.add_argument(
        "--noJobLogging",
        dest="noJobLogging",
        action="store_true",
        help="keep no record of the jobs; the default is one JSON line per job in jobs.jsonl",
    )
    parser.add_argument(
        "--jobFiles",
        dest="jobFiles",
        action="store_true",
        help="also write each job as <file>-cmd, -stdout, -stderr, -returncode beside its result",
    )
    return parser


def parser_build(
    standalone: bool = True, command: str = "pfdo_run", version: str = __version__
) -> argparse.ArgumentParser:
    """Assemble the full parser.

    Args:
        standalone: include ``--inputDir`` / ``--outputDir``. A ChRIS DS plugin
            passes False and adds its own positional directories.
        command: the program's name, for ``--help`` and ``--version``; a package
            built on pfdo_run passes its own.
        version: the version ``--version`` prints, with ``command``.

    Returns:
        The parser.
    """
    parents: list[argparse.ArgumentParser] = [
        parserCore_build(command, version),
        pfdoParserSelf_build(),
        parserSelf_build(),
    ]
    if standalone:
        parents.insert(0, parserIO_build())
    return argparse.ArgumentParser(
        prog=command,
        description=(
            "Run a command template in every directory of a tree; "
            f"%{{...}} tags name the file and directories in hand. Full manual: {command} --man"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=parents,
    )


def options_fromArgs(args: argparse.Namespace) -> PfdoRunOptions:
    """Turn parsed arguments into options."""
    return PfdoRunOptions.fromDict(vars(args))


def result_report(args: argparse.Namespace, result: RunResult) -> None:
    """Print what the arguments asked for."""
    if args.json:
        print(json.dumps(result.toDict(), indent=4, sort_keys=True))
    if args.printElapsedTime:
        print(f"Elapsed time = {result.runTime:.6f} seconds")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command.

    Args:
        argv: arguments without the program name; ``None`` reads ``sys.argv``.

    Returns:
        0 when at least one directory's jobs all succeeded (pftree's stage rule);
        1 when the run failed everywhere or could not start; 2 on bad arguments.
    """
    parser: argparse.ArgumentParser = parser_build()
    args: argparse.Namespace = parser.parse_args(argv)
    if args.man or args.synopsis:
        manual_print(manual_build(), shortOnly=not args.man)
        return 0
    if not args.inputDir:
        parser.error("--inputDir is required")
    if not args.exec:
        parser.error("--exec is required")
    try:
        options: PfdoRunOptions = options_fromArgs(args)
    except ValueError as err:
        parser.error(str(err))
    logging_configure(options.verbosity)
    result: RunResult = PfdoRun(options).run()
    result_report(args, result)
    if result.error:
        print(result.error, file=sys.stderr)
    return 0 if result.status else 1


if __name__ == "__main__":
    sys.exit(main())
