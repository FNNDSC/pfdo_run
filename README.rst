pfdo_run
========

.. image:: https://github.com/FNNDSC/pfdo_run/actions/workflows/ci.yml/badge.svg
    :target: https://github.com/FNNDSC/pfdo_run/actions/workflows/ci.yml

.. image:: https://img.shields.io/pypi/v/pfdo_run.svg
    :target: https://pypi.org/project/pfdo_run/

.. image:: https://img.shields.io/badge/python-3.11%2B-blue.svg
    :target: https://pypi.org/project/pfdo_run/

Run a command, written as a pftag template, in every directory of a tree.

.. contents:: Table of Contents

Overview
--------

``pfdo_run`` walks an input directory with ``pftree``, selects files in each directory with the ``pfdo`` filters and ``--analyzeFileIndex``, and runs the ``--exec`` command once per selected file. The command is a ``pftag`` template: ``%{inputWorkingDir}``, ``%{outputWorkingDir}`` and ``%{inputWorkingFile}`` name the directory being processed, its counterpart in the output tree, and the file; functions derive names, ``%{inputWorkingFile|rmext}.png``. The output tree mirrors the input tree, and each job leaves its command, stdout, stderr and return code beside its results. Directories run in parallel under ``--threads``.

The template is split like a shell command line and each argument has its tags resolved on its own, so a path with a space stays one argument and nothing a file name contains can change the command. The command runs without a shell.

Installation
------------

.. code:: bash

    pip install pfdo_run

Python 3.11 or newer; depends on ``pfdo`` and ``pftag``.

Command line
------------

.. code:: bash

    pfdo_run --inputDir /data --outputDir /png --fileFilter 'glob:*.jpg' --threads 4 \
        --exec "convert %{inputWorkingDir}/%{inputWorkingFile} %{outputWorkingDir}/%{inputWorkingFile|rmext}.png"

    pfdo_run --inputDir /dicom --outputDir /nifti --fileFilter 'glob:*.dcm' --analyzeFileIndex f \
        --exec "mri_convert %{inputWorkingDir}/%{inputWorkingFile} %{outputWorkingDir}/%{inputWorkingDir|basename}.nii.gz"

    pfdo_run --man

All of ``pftree``'s and ``pfdo``'s options apply. ``pfdo_run`` adds:

``--exec <commandTemplate>``
    The command to run per selected file. Tags: ``%{inputWorkingDir}``, ``%{outputWorkingDir}``, ``%{inputWorkingFile}``, every option by name (``%{outputDir}``), and pftag's core tags. Functions: ``rmext``, ``ext``, ``basename``, ``dirname``, ``replace``, ``re``, ``upper``, ``lower``, ``strip``, ``pad``, ``slice``, ``md5``, ``sha256``, ``strftime``, ``mask``. A tag that does not resolve fails that job before it runs.

``--noJobLogging``
    Do not write ``<file>-cmd``, ``<file>-stdout``, ``<file>-stderr`` and ``<file>-returncode`` beside each job's results.

A job whose command exits non-zero fails its directory; the run continues and the directory's record says why. ``--json`` prints the whole result, each directory's jobs included.

Library
-------

.. code:: python

    from pathlib import Path
    from pfdo_run import PfdoRun, PfdoRunOptions

    options = PfdoRunOptions(
        inputDir=Path("/data"), outputDir=Path("/png"), fileFilter="glob:*.jpg", threads=4,
        exec="convert %{inputWorkingDir}/%{inputWorkingFile} %{outputWorkingDir}/%{inputWorkingFile|rmext}.png",
    )
    result = PfdoRun(options).run()
    for key, stage in result.process.analyze.items():
        for job in stage.payload["jobs"]:
            print(key, job["file"], job["returncode"])

``pfdo_run.__main__`` exposes its parser and manual in parts (``parser_build(standalone=False)``, ``synopsis(command=...)``, ``CLI_DS``, ``ARGS_SYNOPSIS_DS``) so that a ChRIS plugin such as ``pl-shexec`` composes its own command around them.

Changes in 4.0
--------------

- Built on ``pfdo`` 6 and ``pftag`` 3; ``pfmisc``, ``pudb`` and ``Faker`` are no longer dependencies.
- The template grammar is pftag's: ``%{name}`` and ``%{name|fn(arg)}``. The 3.x forms ``%name`` and ``%_fn_name`` are gone; a bare ``%name`` of a known tag is reported as a 1.x template and fails the job.
- The command is split before substitution and run without a shell; 3.x substituted into the string and split on whitespace, so a path with a space broke it.
- Both output streams are captured to completion; 3.x read stdout line by line, dropped the last line, and could deadlock on stderr.
- Per-job logs are written by default and ``--noJobLogging`` exists; in 3.x the option was documented but undefined, so logs were never written.
- A non-zero exit status fails the job and its directory; the run's status is truthful (3.x reported False always).
- ``main(argv)`` honours ``argv``; ``--version``, ``--man`` and ``--synopsis`` exit 0; packaging is ``pyproject.toml`` only, published from CI on a ``v*`` tag.
