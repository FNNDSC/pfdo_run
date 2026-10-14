"""The data models of pfdo_run.

pfdo_run adds two options to pfdo's: the command template to run in every directory,
and whether each job's record is written beside its results. A job is one run of the
command for one file; its record names the file, the command as built, and carries the
hostlib envelope of the run when the command ran.

pfdo's and hostlib's models are re-exported here so that a tool built on pfdo_run
imports from pfdo_run alone.

Key components:
    - PfdoRunOptions: ``PfdoOptions`` plus ``exec`` and ``noJobLogging``
    - FileJob: one file's job: the command built for it and, if it ran, the run's envelope
    - DirNode, StageResult, ProcessResult, RunResult, PfdoOptions, TreeOptions: pfdo's models
    - JobResult, JobSpec, HostFacts: hostlib's models

Typical usage:
    options = PfdoRunOptions.fromDict(vars(args))
    PfdoRun(options).run()

Dependencies:
    - pfdo.models, hostlib.models
"""

from __future__ import annotations

from dataclasses import dataclass, field

from hostlib.models import HostFacts, JobResult, JobSpec
from pfdo.models import DirNode, PfdoOptions, ProcessResult, RunResult, StageResult, TreeOptions


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
class FileJob:
    """One file's job: the command built for it and, when it ran, the run.

    Attributes:
        file: the input file the job was built for.
        argv: the command as built, after tag substitution; the template's own
            arguments when it could not be resolved; empty when there was no template.
        status: the command was built, started and exited 0.
        errors: why not: a tag that did not resolve, a program that could not start,
            a non-zero exit status.
        run: hostlib's envelope of the run, with both streams, exit status, host facts
            and timing; ``None`` when the command was never run.

    Example:
        >>> FileJob("a.txt", ["true"], True).run is None
        True
    """

    file: str
    argv: list[str]
    status: bool
    errors: list[str] = field(default_factory=list)
    run: JobResult | None = None


__all__: list[str] = [
    "DirNode",
    "FileJob",
    "HostFacts",
    "JobResult",
    "JobSpec",
    "PfdoOptions",
    "PfdoRunOptions",
    "ProcessResult",
    "RunResult",
    "StageResult",
    "TreeOptions",
]
