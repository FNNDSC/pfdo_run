"""pfdo_run: run a command in every directory of a tree.

The member of the pfdo family whose per-directory operation is a command the user
writes as a pftag template. ``%{inputWorkingDir}``, ``%{outputWorkingDir}`` and
``%{inputWorkingFile}`` name the current directory's paths and file; functions such as
``%{inputWorkingFile|rmext}`` derive output names.

Key components:
    - PfdoRun: the engine
    - PfdoRunOptions, JobResult: options in, job records out
    - __main__: the ``pfdo_run`` command and the parts pl-shexec composes its own from

Typical usage:
    pfdo_run --inputDir /data --outputDir /out --fileFilter 'glob:*.dcm' --analyzeFileIndex f \\
        --exec "mri_convert %{inputWorkingDir}/%{inputWorkingFile} %{outputWorkingDir}/T1.nii.gz"

Dependencies:
    - pfdo, pftag
"""

from __future__ import annotations

__version__: str = "4.0.0"

from pfdo_run.models import JobResult, PfdoRunOptions
from pfdo_run.pfdo_run import JOB_LOG_SUFFIXES, PfdoRun, lookups_forJob

__all__ = [
    "JOB_LOG_SUFFIXES",
    "JobResult",
    "PfdoRun",
    "PfdoRunOptions",
    "__version__",
    "lookups_forJob",
]
