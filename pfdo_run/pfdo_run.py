"""pfdo_run: run a command in every directory of a tree.

``PfdoRun`` is the member of the pfdo family whose per-directory operation is a command
written by the user as a pftag template. For every file the directory's
``--analyzeFileIndex`` selects, the template is split like a shell command, each
argument has its tags resolved against that directory's paths and the file, and the
result is run through hostlib: without a shell, both streams read as they arrive, the
record kept beside the results and, at ``--verbosity 2`` and above, streamed to the
console while the command runs.

Key components:
    - PfdoRun: the engine; ``job_run`` builds and runs one command
    - lookups_forJob: the tags a job can use
    - sink_build: where a job's output goes while it runs

Typical usage:
    PfdoRun(PfdoRunOptions(inputDir=Path("/in"), outputDir=Path("/out"),
            exec="convert %{inputWorkingDir}/%{inputWorkingFile} "
                 "%{outputWorkingDir}/%{inputWorkingFile|rmext}.jpg")).run()

Dependencies:
    - pfdo, pftag, hostlib
"""

from __future__ import annotations

import dataclasses
import logging
import shlex

from hostlib.proc.run import job_run as host_jobRun
from hostlib.sink import JOBS_FILE, ConsoleSink, FileSink, JobSink, JsonSink, NullSink, TeeSink
from pfdo.pfdo import Pfdo
from pftag.models import ArgvResult, TagOptions
from pftag.pftag import Pftag

from pfdo_run.models import DirNode, FileJob, JobResult, JobSpec, PfdoRunOptions, StageResult

logger: logging.Logger = logging.getLogger("pfdo_run")

OPTIONS_LOOKUP: str = "options"
JOB_LOOKUP: str = "pfdo"
STREAM_VERBOSITY: int = 2
TAG_OPEN: str = "%{"


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


def sink_build(options: PfdoRunOptions, node: DirNode, fileName: str) -> JobSink:
    """Where one job's output goes while it runs.

    Args:
        options: ``noJobLogging`` keeps no record; ``jobFiles`` adds the four files
            beside the result; ``verbosity`` of ``STREAM_VERBOSITY`` or more streams
            to the console.
        node: the directory; the record lands in its ``outputPath``.
        fileName: the file; its job is one line in ``<outputPath>/jobs.jsonl`` and,
            with ``jobFiles``, ``<file>-cmd``, ``-stdout``, ``-stderr``, ``-returncode``,
            the stream files rendered as a terminal would show them.

    Returns:
        A JSON-line sink, with a file sink and a console sink as asked, or nothing.
    """
    sinks: list[JobSink] = []
    if not options.noJobLogging:
        sinks.append(JsonSink(node.outputPath / JOBS_FILE))
        if options.jobFiles:
            sinks.append(FileSink(node.outputPath / fileName, rendered=True))
    if options.verbosity >= STREAM_VERBOSITY:
        sinks.append(ConsoleSink())
    if not sinks:
        return NullSink()
    return sinks[0] if len(sinks) == 1 else TeeSink(*sinks)


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

    def __init__(self, options: PfdoRunOptions) -> None:
        super().__init__(options)
        self.options: PfdoRunOptions = options
        self.argvTemplate: list[str] = shlex.split(options.exec) if options.exec else []
        self.template_check()

    def template_check(self) -> None:
        """Warn when the template carries no tag, since the same command would then run for every file."""
        if self.options.exec and TAG_OPEN not in self.options.exec:
            logger.warning(
                "--exec has no %{...} tag; the same command runs for every file. "
                "Name the file with %{inputWorkingFile}, see pfdo_run --man TAGS"
            )

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
            The files run, with every FileJob in ``payload["jobs"]``; ``status`` is
            True only when every job was built, started and exited 0.
        """
        jobs: list[FileJob] = [self.job_run(node, fileName) for fileName in self.filesToAnalyze(node)]
        return StageResult(
            status=bool(jobs) and all(job.status for job in jobs),
            files=[job.file for job in jobs],
            payload={"jobs": [dataclasses.asdict(job) for job in jobs]},
        )

    def job_run(self, node: DirNode, fileName: str) -> FileJob:
        """Build and run the command for one file.

        The template's tags are resolved per argument, so a path with a space stays
        one argument; the command then runs through hostlib, without a shell, its
        output going to the sink ``sink_build`` chooses while it runs.

        Args:
            node: the directory.
            fileName: the file the command is built for.

        Returns:
            The job's record. A template that fails to resolve is a job that was
            never run; a program that cannot start or exits non-zero is a failed run.
        """
        if not self.argvTemplate:
            return FileJob(fileName, [], False, ["--exec is empty"])
        tagger: Pftag = Pftag(TagOptions(lookups=lookups_forJob(self.options, node, fileName), strict=True))
        resolved: ArgvResult = tagger.argv_process(self.argvTemplate)
        if not resolved.status:
            logger.error("%s/%s: %s", node.relPath, fileName, "; ".join(resolved.errors()))
            return FileJob(fileName, resolved.argv, False, resolved.errors())
        logger.debug("%s/%s: %s", node.relPath, fileName, shlex.join(resolved.argv))
        sink: JobSink = sink_build(self.options, node, fileName)
        run: JobResult = host_jobRun(JobSpec(argv=resolved.argv), sink=sink)
        if not run.status:
            logger.warning("%s/%s: %s", node.relPath, fileName, "; ".join(run.errors))
        return FileJob(fileName, resolved.argv, run.status, list(run.errors), run)
