"""pfdo_run: run a command in every directory of a tree.

The member of the pfdo family whose per-directory operation is a command the user
writes as a pftag template. ``%{inputWorkingDir}``, ``%{outputWorkingDir}`` and
``%{inputWorkingFile}`` name the current directory's paths and file; functions such as
``%{inputWorkingFile|rmext}`` derive output names.

Key components:
    - PfdoRun: the engine
    - PfdoRunOptions, FileJob: options in, job records out
    - __main__: the ``pfdo_run`` command and the parts pl-shexec composes its own from

Typical usage:
    pfdo_run --inputDir /data --outputDir /out --fileFilter 'glob:*.dcm' --analyzeFileIndex f \\
        --exec "mri_convert %{inputWorkingDir}/%{inputWorkingFile} %{outputWorkingDir}/T1.nii.gz"

Dependencies:
    - pfdo, pftag, hostlib
"""

from __future__ import annotations

__version__: str = "4.1.0"

from pfdo_run.models import DirNode, FileJob, JobResult, PfdoRunOptions, RunResult, StageResult
from pfdo_run.pfdo_run import PfdoRun, lookups_forJob, sink_build

__all__ = [
    "DirNode",
    "FileJob",
    "JobResult",
    "PfdoRun",
    "PfdoRunOptions",
    "RunResult",
    "StageResult",
    "__version__",
    "lookups_forJob",
    "sink_build",
]
