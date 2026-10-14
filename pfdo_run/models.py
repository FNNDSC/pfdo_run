"""The data models of pfdo_run.

pfdo_run adds two options to pfdo's: the command template to run in every directory,
and whether each job's output is logged beside its results. A job is one run of the
command for one file; its record carries the command as run, its exit status and its
output.

Key components:
    - PfdoRunOptions: ``PfdoOptions`` plus ``exec`` and ``noJobLogging``
    - JobResult: one command run, or one command that could not be built

Typical usage:
    options = PfdoRunOptions.fromDict(vars(args))
    PfdoRun(options).run()

Dependencies:
    - pfdo.models
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pfdo.models import PfdoOptions


@dataclass
class PfdoRunOptions(PfdoOptions):
    """pfdo's options plus pfdo_run's own.

    Attributes:
        exec: the command template, a pftag template split like a shell command.
            Its tags name the current directory's paths and file:
            ``%{inputWorkingDir}``, ``%{outputWorkingDir}``, ``%{inputWorkingFile}``,
            plus every option by name, ``%{outputDir}``.
        noJobLogging: do not write each job's command, stdout, stderr and return code
            beside its results.

    Example:
        >>> PfdoRunOptions.fromDict({"inputDir": "/in", "exec": "ls %{inputWorkingDir}"}).exec
        'ls %{inputWorkingDir}'
    """

    exec: str = ""
    noJobLogging: bool = False


@dataclass
class JobResult:
    """One run of the command for one file.

    Attributes:
        file: the input file the job was built for.
        argv: the command as run, after tag substitution; empty when it could not be built.
        returncode: the process's exit status; ``None`` when it did not run.
        stdout: what the process wrote to standard output.
        stderr: what the process wrote to standard error.
        status: the command was built and exited 0.
        errors: why the command could not be built, or that it exited non-zero.

    Example:
        >>> JobResult("a.txt", ["true"], 0, "", "", True).status
        True
    """

    file: str
    argv: list[str]
    returncode: int | None
    stdout: str
    stderr: str
    status: bool
    errors: list[str] = field(default_factory=list)
