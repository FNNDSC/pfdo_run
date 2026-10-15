"""Tests for the pfdo_run command line."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pfdo_run import __version__
from pfdo_run.__main__ import CLI_DS, CLI_FULL, main, manual_build, parser_build, synopsis


def tree_make(root: Path) -> tuple[Path, Path]:
    inputDir: Path = root / "in"
    outputDir: Path = root / "out"
    (inputDir / "s").mkdir(parents=True)
    (inputDir / "s/x.jpg").write_text("x\n")
    return inputDir, outputDir


def test_main_runsAndPrintsJson(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    inputDir, outputDir = tree_make(tmp_path)
    code: int = main(
        [
            "--inputDir",
            str(inputDir),
            "--outputDir",
            str(outputDir),
            "--relativeDir",
            "--verbosity",
            "0",
            "--exec",
            "cp %{inputWorkingDir}/%{inputWorkingFile} %{outputWorkingDir}/%{inputWorkingFile|rmext}.png",
            "--json",
            "--printElapsedTime",
        ]
    )
    assert code == 0
    out: str = capsys.readouterr().out
    payload = json.loads(out[: out.rindex("}") + 1])
    assert payload["status"] is True
    assert payload["process"]["analyze"]["s"]["payload"]["jobs"][0]["run"]["returncode"] == 0
    assert (outputDir / "s/x.png").exists()
    assert "Elapsed time" in out


def test_main_execRequired(tmp_path: Path) -> None:
    inputDir, outputDir = tree_make(tmp_path)
    with pytest.raises(SystemExit) as exc:
        main(["--inputDir", str(inputDir), "--outputDir", str(outputDir)])
    assert exc.value.code == 2


def test_main_failedJobsExitOne(tmp_path: Path) -> None:
    inputDir, outputDir = tree_make(tmp_path)
    code: int = main(
        ["--inputDir", str(inputDir), "--outputDir", str(outputDir), "--exec", "false", "--verbosity", "0"]
    )
    assert code == 1


def test_main_versionAndManual(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert f"pfdo_run {__version__}" in capsys.readouterr().out
    with pytest.raises(SystemExit) as exc:
        main(["--man"])
    assert exc.value.code == 0
    out: str = capsys.readouterr().out
    assert "Path-File Do Run" in out
    for text in (
        "--exec <commandTemplate>",
        "[--analyzeFileIndex <a|f|l|m|N>]",
        "[--fileFilter <token1,token2,...>]",
        "TAGS",
    ):
        assert text in out
    assert "%{inputWorkingFile|rmext}" in out
    assert "``" not in out


def test_synopsis_forAnotherCommand() -> None:
    text: str = synopsis(shortOnly=True, command="shexec")
    assert "shexec \\" in text and CLI_FULL in text
    assert "--inputDir" not in CLI_DS and "<inputDir>" in CLI_DS
    assert manual_build().command == "pfdo_run"


def test_parser_build_dsOmitsIoArguments() -> None:
    dsStyle = parser_build(standalone=False)
    with pytest.raises(SystemExit):
        dsStyle.parse_args(["--inputDir", "x"])
    args = dsStyle.parse_args(["--exec", "ls", "--noJobLogging", "--jobFiles", "--analyzeFileIndex", "f"])
    assert args.exec == "ls" and args.noJobLogging is True and args.jobFiles is True
    assert args.analyzeFileIndex == "f"


def test_help_namesTheTags(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        parser_build().parse_args(["--help"])
    helpText: str = capsys.readouterr().out
    assert "%{inputWorkingFile}" in helpText and "--man TAGS" in helpText


def test_parser_build_forAnotherCommand(capsys: pytest.CaptureFixture[str]) -> None:
    plugin = parser_build(standalone=False, command="shexec", version="9.9.9")
    with pytest.raises(SystemExit):
        plugin.parse_args(["--version"])
    assert capsys.readouterr().out.strip() == "shexec 9.9.9"
    with pytest.raises(SystemExit):
        plugin.parse_args(["--help"])
    assert "shexec --man" in capsys.readouterr().out


def test_parser_dsStyleManNeedsNoDirectories(capsys: pytest.CaptureFixture[str]) -> None:
    parser = parser_build(standalone=False, command="pl-x")
    parser.add_argument("inputdir")
    parser.add_argument("outputdir")
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["--synopsis"])
    assert exc.value.code == 0
    out: str = capsys.readouterr().out
    assert "Path-File Do Run" in out
    assert "DESCRIPTION" not in out
