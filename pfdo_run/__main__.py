#!/usr/bin/env python3
#
# (c) 2021 Fetal-Neonatal Neuroimaging & Developmental Science Center
#                   Boston Children's Hospital
#
#              http://childrenshospital.org/FNNDSC/
#                        dev@babyMRI.org
#

import  sys, os
sys.path.insert(1, os.path.join(os.path.dirname(__file__), '../pfdo_run'))

import  pfdo.__main__       as pfdo_main
import  pfdo
try:
    from    .               import pfdo_run
    from    .               import __pkg, __version__
except:
    from pfdo_run           import pfdo_mgz2image
    from __init__           import __pkg, __version__

from    argparse            import RawTextHelpFormatter
from    argparse            import ArgumentParser
import  pudb

import  pfmisc
from    pfmisc._colors      import Colors
from    pfmisc              import other

str_desc = Colors.CYAN + """

                          __    _
                         / _|  | |
                   _ __ | |_ __| | ___   _ __ _   _ _ __
                  | '_ \|  _/ _` |/ _ \ | '__| | | | '_ \\
                  | |_) | || (_| | (_) || |  | |_| | | | |
                  | .__/|_| \__,_|\___/ |_|   \__,_|_| |_|
                  | |               ______
                  |_|              |______|



                          Path-File Do Run

        Recursively walk down a directory tree and run a CLI spec'd app
        on files in each directory (optionally filtered by some simple
        expression). Results of each operation are saved in an output tree
        that preserves the input directory structure.


                             -- version """ + \
             Colors.YELLOW + __version__ + Colors.CYAN + """ --

        'pfdo_run' demonstrates how to use ``pftree`` to transverse
        directory trees and execute some user specified CLI operation
        at each directory level (that optionally contains files of interest).

        As part of the "pf*" suite of applications, it is geared to IO as
        directories. Nested directory trees within some input directory
        are reconstructed in an output directory, preserving directory
        structure.


""" + Colors.NO_COLOUR

package_CLI = '''
                    --exec <CLIcmdToExec>                           \\
                    --analyzeFileIndex <N>                          \\'''+\
                    pfdo_main.package_CLI

package_argSynopsis = pfdo_main.package_argSynopsis + '''
        --exec <CLIcmdToExec>
        The command line expression to apply at each directory node of the
        input tree. See the CLI SPECIFICATION section for more information.

        [--analyzeFileIndex <someIndex>]
        An optional string to control which file(s) in a specific directory
        to which the analysis is applied. The default is "-1" which implies
        *ALL* files in a given directory. Other valid <someIndex> are:
            'm':   only the "middle" file in the returned file list
            "f":   only the first file in the returned file list
            "l":   only the last file in the returned file list
            "<N>": the file at index N in the file list. If this index
                   is out of bounds, no analysis is performed.
            "-1" means all files.

'''

def synopsis(ab_shortOnly = False):
    scriptName = os.path.basename(sys.argv[0])
    shortSynopsis =  """
    NAME

	    pfdo_run

    SYNOPSIS

        pfdo_run """ + package_CLI + """

    BRIEF EXAMPLE

        pfdo_run                                                \\
            --inputDir /var/www/html/data --fileFilter jpg      \\
            --outputDir /var/www/html/png                       \\
            --exec "convert %inputWorkingDir/%inputWorkingFile
            %outputWorkingDir/%_rmext_inputWorkingFile.png"     \\
            --threads 0 --printElapsedTime
    """

    description =  '''
    DESCRIPTION

        ``pfdo_run`` runs some user specified CLI at each path/file location
        in an input directory, storing results (and logs) at a corresponding
        dir location rooted in the output directory.

    ARGS ''' + package_argSynopsis + '''

    CLI SPECIFICATION

    Any text in the CLI prefixed with a percent char '%' is interpreted in one
    of two ways.

    First, any CLI to the ``pfdo_run`` itself can be accessed via '%'. Thus,
    for example a ``%outputDir`` in the ``--exec`` string will be expanded
    to the ``outputDir`` of the ``pfdo_run``.

    Secondly, three internal '%' variables are available:

        * '%inputWorkingDir'  - the current input tree working directory
        * '%outputWorkingDir' - the current output tree working directory
        * '%inputWorkingFile' - the current file being processed

    These internal variables allow for contextual specification of values. For
    example, a simple CLI touch command could be specified as

        --exec "touch %outputWorkingDir/%inputWorkingFile"

    or a command to convert an input ``png`` to an output ``jpg`` using the
    ImageMagick ``convert`` utility

        --exec "convert %inputWorkingDir/%inputWorkingFile
                        %outputWorkingDir/%inputWorkingFile.jpg"

    SPECIAL FUNCTIONS

    Furthermore, `pfdo_run` offers the ability to apply some interal functions
    to a tag. The template for specifying a function to apply is:

        %_<functionName>[|arg1|arg2|...]_<tag>

    thus, a function is identified by a function name that is prefixed and
    suffixed by an underscore and appears in front of the tag to process.
    Possible args to the <functionName> are separated by pipe "|" characters.

    For example a string snippet that contains

        %_strrepl|.|-_inputWorkingFile.txt

    will replace all occurences of '.' in the %inputWorkingFile with '-'.
    Also of interest, the trailing ".txt" is preserved in the final pattern
    for the result.

    The following functions are available:

        %_md5[|<len>]_<tagName>
        Apply an 'md5' hash to the value referenced by <tagName> and optionally
        return only the first <len> characters.

        %_strmsk|<mask>_<tagName>
        Apply a simple mask pattern to the value referenced by <tagName>. Chars
        that are "*" in the mask are passed through unchanged. The mask and its
        target should be the same length.

        %_strrepl|<target>|<replace>_<tagName>
        Replace the string <target> with <replace> in the value referenced by
        <tagName>.

        %_rmext_<tagName>
        Remove the "extension" of the value referenced by <tagName>. This
        of course only makes sense if the <tagName> denotes something with
        an extension!

        %_name_<tag>
        Replace the value referenced by <tag> with a name generated by the
        faker module.

    Functions cannot currently be nested.


    EXAMPLES

    Perform a `pfdo_run` down some input directory and convert all input
    ``jpg`` files to ``png`` in the output tree:

        pfdo_run                                                \\
            --inputDir /var/www/html/data --fileFilter jpg      \\
            --outputDir /var/www/html/png                       \\
            --exec "convert %inputWorkingDir/%inputWorkingFile
            %outputWorkingDir/%_rmext_inputWorkingFile.png"     \\
            --threads 0 --printElapsedTime

    The above will find all files in the tree structure rooted at
    /var/www/html/data that also contain the string "jpg" anywhere
    in the filename. For each file found, a `convert` conversion
    will be called, storing a converted file in the same tree location
    in the output directory as the original input.

    Note the special construct, %_rmext_inputWorkingFile.png -- the
    %_<func>_ designates a built in funtion to apply to the
    tag value. In this case, to "remove the extension" from the
    %inputWorkingFile string.

    Consider an example where only one file in a branched inputdir
    space is to be preserved:

        pfdo_run                                                \\
            --inputDir (pwd)/raw --outputDir (pwd)/out          \\
            --dirFilter 100307                                  \\
            --exec "cp %inputWorkingDir/brain.mgz
            %outputWorkingDir/brain.mgz"                        \\
            --threads 0 --verbosity 3 --noJobLogging

    Here, the input directory space is pruned for a directory leaf
    node that contains the string 100307. The exec command essentially
    copies the file `brain.mgz` in that target directory to the
    corresponding location in the output tree.

    Finally the elapsed time and a JSON output are printed.

    '''

    if ab_shortOnly:
        return shortSynopsis
    else:
        return shortSynopsis + description

parser              = pfdo_main.parser
parser.description  = str_desc

parser  = ArgumentParser(description = str_desc, formatter_class = RawTextHelpFormatter)

parser.add_argument("--exec",
                    help    = "command line execution string to perform",
                    dest    = 'exec',
                    default = '')
parser.add_argument("--analyzeFileIndex",
                    help    = "file index per directory to analyze",
                    dest    = 'analyzeFileIndex',
                    default = '-1')
def main(argv = None):
    args = parser.parse_args()

    if args.man or args.synopsis:
        print(str_desc)
        if args.man:
            str_help     = synopsis(False)
        else:
            str_help     = synopsis(True)
        print(str_help)
        return 1

    if args.b_version:
        print("Name:    %s\nVersion: %s" % (__pkg.name, __version__))
        sys.exit(1)

    args.str_version    = __version__
    args.str_desc       = synopsis(True)

    pf_do_shell         = pfdo_run.pfdo_run(vars(args))

    # And now run it!
    d_pfdo_shell        = pf_do_shell.run(timerStart = True)

    if args.printElapsedTime:
        pf_do_shell.dp.qprint(
                "Elapsed time = %f seconds" %
                d_pfdo_shell['runTime']
        )

    return 0

if __name__ == "__main__":
    sys.exit(main())