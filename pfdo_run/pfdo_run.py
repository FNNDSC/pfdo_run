"""pfdo_run: run a command in every directory of a tree.

``PfdoRun`` is the member of the pfdo family whose per-directory operation is a shell
command written by the user as a pftag template. For every file the directory's
``--analyzeFileIndex`` selects, the template is split like a shell command, each
argument has its tags resolved against that directory's paths and the file, and the
result is run without a shell. The process's output and exit status are kept beside
its results in the output tree.

Key components:
    - PfdoRun: the engine; ``job_run`` builds and runs one command
    - lookups_forJob: the tags a job can use
    - JOB_LOG_SUFFIXES: the files written per job

Typical usage:
    PfdoRun(PfdoRunOptions(inputDir=Path("/in"), outputDir=Path("/out"),
            exec="convert %{inputWorkingDir}/%{inputWorkingFile} "
                 "%{outputWorkingDir}/%{inputWorkingFile|rmext}.jpg")).run()

Dependencies:
    - pfdo, pftag
"""

from __future__ import annotations

import dataclasses
import logging
import shlex
import subprocess
from pathlib import Path

from pfdo.pfdo import Pfdo
from pftag.models import ArgvResult, TagOptions
from pftag.pftag import Pftag
from pftree.models import DirNode, ProcessResult, StageResult

from pfdo_run.models import JobResult, PfdoRunOptions

logger: logging.Logger = logging.getLogger("pfdo_run")

OPTIONS_LOOKUP: str = "options"
JOB_LOOKUP: str = "pfdo"
JOB_LOG_SUFFIXES: tuple[str, ...] = ("cmd", "stdout", "stderr", "returncode")


def lookups_forJob(options: PfdoRunOptions, node: DirNode, fileName: str) -> dict[str, dict[str, str]]:
    """The tag dictionaries one job can resolve against.

    Args:
        options: the run's options; every field becomes a tag in the ``options``
            dictionary, so ``%{outputDir}`` works.
        node: the directory being processed.
        fileName: the file the job is built for.

    Returns:
        ``options`` and ``pfdo`` (``inputWorkingDir``, ``outputWorkingDir``,
        ``inputWorkingFile``), the latter also reachable qualified.
    """
    optionTags: dict[str, str] = {
        name: str(value) for name, value in dataclasses.asdict(options).items() if name not in ("exec",)
    }
    jobTags: dict[str, str] = {
        "inputWorkingDir": str(node.path),
        "outputWorkingDir": str(node.outputPath),
        "inputWorkingFile": fileName,
    }
    return {OPTIONS_LOOKUP: optionTags, JOB_LOOKUP: jobTags}


class PfdoRun(Pfdo):
    """Run a command template in every directory of the input tree.

    Attributes:
        options: the PfdoRunOptions in force.
        argvTemplate: the ``--exec`` template split like a shell command, once.

    Example:
        >>> tool = PfdoRun(PfdoRunOptions(inputDir=Path("."), outputDir=Path("/tmp/o"), exec="true"))
        >>> tool.argvTemplate
        ['true']
    """

    processAlways: bool = True

    def __init__(self, options: PfdoRunOptions) -> None:
        super().__init__(options)
        self.options: PfdoRunOptions = options
        self.argvTemplate: list[str] = shlex.split(options.exec) if options.exec else []

    def inputRead_callback(self, node: DirNode) -> StageResult:
        """Create the directory's output path and pass its files on.

        Args:
            node: the directory.

        Returns:
            Success with the files; failure if there are none.
        """
        node.outputPath.mkdir(parents=True, exist_ok=True)
        return StageResult(status=bool(node.files), files=list(node.files))

    def inputAnalyze_callback(self, node: DirNode, read: StageResult) -> StageResult:
        """Run the command for every file ``--analyzeFileIndex`` selects.

        Args:
            node: the directory.
            read: the read stage's result.

        Returns:
            The files run, with every JobResult in ``payload["jobs"]``; ``status`` is
            True only when every job was built and exited 0.
        """
        jobs: list[JobResult] = [self.job_run(node, fileName) for fileName in self.filesToAnalyze(node)]
        for job in jobs:
            if not self.options.noJobLogging:
                self.job_log(node, job)
        return StageResult(
            status=bool(jobs) and all(job.status for job in jobs),
            files=[job.file for job in jobs],
            payload={"jobs": [dataclasses.asdict(job) for job in jobs]},
        )

    def job_run(self, node: DirNode, fileName: str) -> JobResult:
        """Build and run the command for one file.

        The template's tags are resolved per argument, so a path with a space stays
        one argument; the command runs without a shell, with both output streams
        captured to completion.

        Args:
            node: the directory.
            fileName: the file the command is built for.

        Returns:
            The job's record. A template that fails to resolve, or a command that
            cannot be started, is a failed job that was never run.
        """
        if not self.argvTemplate:
            return JobResult(fileName, [], None, "", "", False, ["--exec is empty"])
        tagger: Pftag = Pftag(TagOptions(lookups=lookups_forJob(self.options, node, fileName), strict=True))
        resolved: ArgvResult = tagger.argv_process(self.argvTemplate)
        if not resolved.status:
            logger.error("%s/%s: %s", node.relPath, fileName, "; ".join(resolved.errors()))
            return JobResult(fileName, resolved.argv, None, "", "", False, resolved.errors())
        logger.debug("%s/%s: %s", node.relPath, fileName, shlex.join(resolved.argv))
        try:
            completed: subprocess.CompletedProcess[str] = subprocess.run(
                resolved.argv, capture_output=True, text=True, check=False
            )
        except OSError as err:
            logger.error("%s/%s: cannot run %s: %s", node.relPath, fileName, resolved.argv[0], err.strerror)
            return JobResult(
                fileName, resolved.argv, None, "", "", False, [f"cannot run {resolved.argv[0]}: {err}"]
            )
        status: bool = completed.returncode == 0
        errors: list[str] = [] if status else [f"exit status {completed.returncode}"]
        if not status:
            logger.warning("%s/%s: exit status %d", node.relPath, fileName, completed.returncode)
        return JobResult(
            fileName, resolved.argv, completed.returncode, completed.stdout, completed.stderr, status, errors
        )

    def job_log(self, node: DirNode, job: JobResult) -> None:
        """Write a job's command, stdout, stderr and return code beside its results.

        Args:
            node: the directory; files go under its ``outputPath``.
            job: the job.
        """
        node.outputPath.mkdir(parents=True, exist_ok=True)
        contents: dict[str, str] = {
            "cmd": shlex.join(job.argv) + "\n",
            "stdout": job.stdout,
            "stderr": job.stderr,
            "returncode": f"{job.returncode}\n",
        }
        for suffix in JOB_LOG_SUFFIXES:
            target: Path = node.outputPath / f"{job.file}-{suffix}"
            target.write_text(contents[suffix])

    def callbacks_run(self) -> ProcessResult:
        """Run the read and analyze stages; pfdo_run has no write stage of its own."""
        return self.tree_process(
            inputRead_callback=self.inputRead_callback,
            inputAnalyze_callback=self.inputAnalyze_callback,
        )
