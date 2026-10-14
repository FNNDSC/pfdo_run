"""Tests for PfdoRun: command building, running, logging, failure handling."""

from __future__ import annotations

import json
from pathlib import Path

from pfdo_run.models import JobResult, PfdoRunOptions
from pfdo_run.pfdo_run import JOB_LOG_SUFFIXES, PfdoRun, lookups_forJob


def tree_make(root: Path) -> tuple[Path, Path]:
    inputDir: Path = root / "in"
    outputDir: Path = root / "out"
    for rel, names in {
        "sub-01/anat": ["a.nii.gz", "b.nii.gz"],
        "sub-02/anat": ["c.nii.gz"],
        "notes": ["r.txt"],
    }.items():
        (inputDir / rel).mkdir(parents=True)
        for name in names:
            (inputDir / rel / name).write_text(f"{rel}/{name}\n")
    (inputDir / "sub-02/anat/my file.nii.gz").write_text("spaced\n")
    return inputDir, outputDir


def options_make(inputDir: Path, outputDir: Path, exec: str, **extra: object) -> PfdoRunOptions:
    values: dict[str, object] = {
        "inputDir": inputDir,
        "outputDir": outputDir,
        "exec": exec,
        "verbosity": 0,
        "relativeDir": True,
    }
    values.update(extra)
    return PfdoRunOptions.fromDict(values)


COPY: str = "cp %{inputWorkingDir}/%{inputWorkingFile} %{outputWorkingDir}/%{inputWorkingFile|rmext}.copy"


def test_copy_everyFile_withLogs(tmp_path: Path) -> None:
    inputDir, outputDir = tree_make(tmp_path)
    result = PfdoRun(options_make(inputDir, outputDir, COPY, fileFilter="glob:*.nii.gz")).run()
    assert result.status
    assert result.process is not None
    assert result.process.filesAnalyzed == 4
    assert (outputDir / "sub-01/anat/a.nii.copy").read_text() == "sub-01/anat/a.nii.gz\n"
    assert (outputDir / "sub-02/anat/my file.nii.copy").read_text() == "spaced\n"
    assert not (outputDir / "notes").exists()
    for suffix in JOB_LOG_SUFFIXES:
        assert (outputDir / f"sub-01/anat/a.nii.gz-{suffix}").exists()
    assert (outputDir / "sub-01/anat/a.nii.gz-returncode").read_text() == "0\n"
    assert "a.nii.copy" in (outputDir / "sub-01/anat/a.nii.gz-cmd").read_text()


def test_noJobLogging(tmp_path: Path) -> None:
    inputDir, outputDir = tree_make(tmp_path)
    PfdoRun(options_make(inputDir, outputDir, COPY, fileFilter="nii", noJobLogging=True)).run()
    assert (outputDir / "sub-01/anat/a.nii.copy").exists()
    assert not list((outputDir / "sub-01/anat").glob("*-stdout"))


def test_analyzeFileIndex_firstOnly(tmp_path: Path) -> None:
    inputDir, outputDir = tree_make(tmp_path)
    PfdoRun(options_make(inputDir, outputDir, COPY, fileFilter="nii", analyzeFileIndex="f")).run()
    assert (outputDir / "sub-01/anat/a.nii.copy").exists()
    assert not (outputDir / "sub-01/anat/b.nii.copy").exists()


def test_stdout_capturedAndLogged(tmp_path: Path) -> None:
    inputDir, outputDir = tree_make(tmp_path)
    result = PfdoRun(
        options_make(inputDir, outputDir, "echo hello %{inputWorkingFile}", dirFilter="notes")
    ).run()
    assert result.status
    assert (outputDir / "notes/r.txt-stdout").read_text() == "hello r.txt\n"
    assert result.process is not None
    jobs = result.process.analyze["notes"].payload["jobs"]
    assert jobs[0]["stdout"] == "hello r.txt\n" and jobs[0]["returncode"] == 0


def test_failingCommand_failsDirectoryRunContinues(tmp_path: Path) -> None:
    inputDir, outputDir = tree_make(tmp_path)
    exec_: str = "sh -c 'test %{inputWorkingDir|basename} = notes || exit 3'"
    result = PfdoRun(options_make(inputDir, outputDir, exec_, analyzeFileIndex="f")).run()
    assert result.process is not None
    assert result.process.analyze["notes"].status is True
    assert result.process.analyze["sub-01/anat"].status is False
    assert result.status  # one directory succeeded, so the stage did
    assert (outputDir / "sub-01/anat/a.nii.gz-returncode").read_text() == "3\n"
    assert set(result.tree) == {"notes"}


def test_unresolvedTag_jobNotRun(tmp_path: Path) -> None:
    inputDir, outputDir = tree_make(tmp_path)
    result = PfdoRun(
        options_make(inputDir, outputDir, "touch %{outputWorkingDir}/%{nope}", dirFilter="notes")
    ).run()
    assert not result.status
    assert result.process is not None
    job = result.process.analyze["notes"].payload["jobs"][0]
    assert job["returncode"] is None and job["status"] is False
    assert "unknown tag" in job["errors"][0]
    assert not list((outputDir / "notes").glob("%{nope}"))


def test_legacyTemplate_isAnError(tmp_path: Path) -> None:
    inputDir, outputDir = tree_make(tmp_path)
    result = PfdoRun(options_make(inputDir, outputDir, "touch %outputWorkingDir/x", dirFilter="notes")).run()
    assert not result.status
    job = result.process.analyze["notes"].payload["jobs"][0]  # type: ignore[union-attr]
    assert "1.x tag" in job["errors"][0]


def test_missingProgram_isAFailedJob(tmp_path: Path) -> None:
    inputDir, outputDir = tree_make(tmp_path)
    result = PfdoRun(
        options_make(inputDir, outputDir, "no-such-program-xyz %{inputWorkingFile}", dirFilter="notes")
    ).run()
    assert not result.status
    job = result.process.analyze["notes"].payload["jobs"][0]  # type: ignore[union-attr]
    assert job["returncode"] is None and "cannot run" in job["errors"][0]


def test_optionsAreTags(tmp_path: Path) -> None:
    inputDir, outputDir = tree_make(tmp_path)
    exec_: str = "sh -c 'echo %{outputDir} %{options.analyzeFileIndex} > %{outputWorkingDir}/opts.txt'"
    PfdoRun(options_make(inputDir, outputDir, exec_, dirFilter="notes", analyzeFileIndex="l")).run()
    assert (outputDir / "notes/opts.txt").read_text() == f"{outputDir} l\n"


def test_threads_sameResults(tmp_path: Path) -> None:
    inputDir, outputDir = tree_make(tmp_path)
    single = PfdoRun(options_make(inputDir, outputDir, COPY, fileFilter="nii")).run()
    outputDir2: Path = tmp_path / "out2"
    threaded = PfdoRun(options_make(inputDir, outputDir2, COPY, fileFilter="nii", threads=3)).run()
    assert threaded.status and single.status
    assert threaded.process is not None and single.process is not None
    assert threaded.process.filesAnalyzed == single.process.filesAnalyzed
    assert sorted(p.name for p in outputDir2.rglob("*.copy")) == sorted(
        p.name for p in outputDir.rglob("*.copy")
    )


def test_lookups_forJob(tmp_path: Path) -> None:
    inputDir, outputDir = tree_make(tmp_path)
    tool = PfdoRun(options_make(inputDir, outputDir, "true"))
    tool.tree_construct(tool.tree_probe())
    node = tool.nodes["notes"]
    lookups = lookups_forJob(tool.options, node, "r.txt")
    assert lookups["pfdo"] == {
        "inputWorkingDir": str(node.path),
        "outputWorkingDir": str(outputDir / "notes"),
        "inputWorkingFile": "r.txt",
    }
    assert lookups["options"]["outputDir"] == str(outputDir)
    assert "exec" not in lookups["options"]


def test_emptyExec_failsJobs(tmp_path: Path) -> None:
    inputDir, outputDir = tree_make(tmp_path)
    result = PfdoRun(options_make(inputDir, outputDir, "", dirFilter="notes")).run()
    assert not result.status
    job: dict[str, object] = result.process.analyze["notes"].payload["jobs"][0]  # type: ignore[union-attr]
    assert job["errors"] == ["--exec is empty"]


def test_jobResult_isJsonReady(tmp_path: Path) -> None:
    inputDir, outputDir = tree_make(tmp_path)
    result = PfdoRun(options_make(inputDir, outputDir, "true", dirFilter="notes")).run()
    json.dumps(result.toDict())
    assert JobResult("f", ["true"], 0, "", "", True).status
