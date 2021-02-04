# Turn off all logging for modules.
import logging
logging.disable(logging.CRITICAL)


# System imports
import      json
import      os
import      pathlib
import      logging
from        argparse            import  Namespace

# Project specific imports
import      pfmisc
from        pfmisc._colors      import  Colors
from        pfmisc              import  other
from        pfmisc              import  error
from        faker               import  Faker

import      pfdo
import      subprocess
import      hashlib
import      math
import      re
import      pudb
import      pftree

class pfdo_run(pfdo.pfdo):
    """

    A class for navigating down a dir tree and providing
    hooks for some (subclass) analysis

    """

    # Turn off logging for the 'faker' module and create a class instance
    # of the object
    fakelogger              = logging.getLogger('faker')
    fakelogger.propagate    = False
    fake                    = Faker()

    _dictErr = {
        'outputDirFail'   : {
            'action'        : 'trying to check on the output directory, ',
            'error'         : 'directory not specified. This is a *required* input.',
            'exitCode'      : 1},
        'outputFileExists'   : {
            'action'        : 'attempting to write an output file, ',
            'error'         : 'it seems a file already exists. Please run with --overwrite to force overwrite.',
            'exitCode'      : 2}
        }


    def declare_selfvars(self):
        """
        A block to declare self variables
        """

        #
        # Object desc block
        #
        self.str_desc                   = ''
        self.__name__                   = "pfdo_run"

    def __init__(self, *args, **kwargs):
        """
        Constructor for pfdo_run.

        This basically just calls the parent constructor and
        adds some child-specific data.
        """

        super().__init__(*args, **kwargs)

        pfdo_run.declare_selfvars(self)

        # Set some "special" flags for contextual expansion in the
        # analyzeCallback method
        self.args['inputWorkingDir']    = ""
        self.args['outputWorkingDir']   = ""
        self.args['inputWorkingFile']   = ""

    def inputReadCallback(self, *args, **kwargs):
        """
        This method does not actually read in any files, but
        exists to preserve the list of files associated with a
        given input directory.

        By preserving and returning this file list, the next
        callback function in this pipeline is able to receive an
        input path and a list of files in that path.
        """
        str_path            : str       = ''
        l_fileProbed        : list      = []
        b_status            : bool      = True
        filesProbed         : int       = 0
        str_outputWorkingDir: str       = ""

        if len(args):
            at_data         = args[0]
            str_path        = at_data[0]
            l_fileProbed    = at_data[1]

        # Need to create the output dir appropriately here!
        str_outputWorkingDir    = str_path.replace(
                                        self.args['inputDir'],
                                        self.args['outputDir']
        )
        self.dp.qprint("mkdir %s" % str_outputWorkingDir,
                        level = 3)
        other.mkdir(str_outputWorkingDir)

        if not len(l_fileProbed): b_status = False
        l_fileProbed.sort()

        return {
            'status':           b_status,
            'l_fileProbed':     l_fileProbed,
            'str_path':         str_path,
            'filesProbed':      filesProbed
        }

    def inputAnalyzeCallback(self, *args, **kwargs):
        """
        Callback stub for doing actual work. Since the `med2image`
        is a mostly stand-apart module, the inputRead and outputWrite
        callbacks are not applicable here, since calling the
        `med2image` module appropriately reads an input and saves
        an output.
        """

        def l_fileToAnalyze_determine(l_fileProbed):
            """
            Return the list of files to process, based on l_fileProbed
            and self.args['analyzeFileIndex']
            """

            def middleIndex_find(l_lst):
                """
                Return the middle index in a list.

                If list has no length, return None.
                """
                middleIndex     = None
                if len(l_lst):
                    if len(l_lst) == 1:
                        middleIndex = 0
                    else:
                        middleIndex = round(len(l_lst)/2+0.01)
                return middleIndex

            def nIndex_find(l_lst, str_index):
                """
                For a string index, say "2", return the index at l_lst[2].

                If index is out of bounds return None.
                """
                index:  int = 0
                try:
                    index   = int(str_index)
                    if len(l_lst):
                        if index >= -1 and index < len(l_lst):
                            return index
                except:
                    pass
                return None

            l_fileToAnalyze:    list    = []
            if len(l_fileProbed):
                if self.args['analyzeFileIndex'] == 'f': l_fileToAnalyze.append(l_fileProbed[0])
                if self.args['analyzeFileIndex'] == 'l': l_fileToAnalyze.append(l_fileProbed[-1])
                if self.args['analyzeFileIndex'] == 'm':
                    if middleIndex_find(l_fileProbed) >= 0:
                        self.dp.qprint(l_fileProbed, level = 5)
                        l_fileToAnalyze.append(l_fileProbed[middleIndex_find(l_fileProbed)])
                nIndex  = nIndex_find(l_fileProbed, self.args['analyzeFileIndex'])
                if nIndex:
                    if nIndex == -1:
                        l_fileToAnalyze = l_fileProbed
                    else:
                        l_fileToAnalyze.append(nIndex)
            return l_fileToAnalyze

        b_status            : bool  = False
        l_fileProbed        : list  = []
        d_inputReadCallback : dict  = {}
        d_convert           : dict  = {}
        str_cmd             : str   = ""
        str_file            : str   = ""
        str_outputWorkingDir: str   = ""

        for k, v in kwargs.items():
            if k == 'path':         str_path    = v

        if len(args):
            at_data             = args[0]
            str_path            = at_data[0]
            d_inputReadCallback = at_data[1]

        # pudb.set_trace()

        l_fileProbed            = d_inputReadCallback['l_fileProbed']
        str_outputWorkingDir    = str_path.replace(
                                        self.args['inputDir'],
                                        self.args['outputDir']
        )
        for str_file in l_fileToAnalyze_determine(l_fileProbed):
            d_tagProcess    = self.tagsInString_process(self.args['exec'],
                                        inputWorkingDir   = str_path,
                                        inputWorkingFile  = str_file,
                                        outputWorkingDir  = str_outputWorkingDir
                                )
            if d_tagProcess['status']:
                str_cmd     = d_tagProcess['str_result']

                # Run the job and provide realtime stdout
                # and post-run stderr
                self.dp.qprint(str_cmd, level = 5)
                self.job_stdwrite(
                    self.job_run(str_cmd), str_outputWorkingDir, str_file + '-'
                )


        return {
            'status':           b_status,
            'str_path':         str_path,
            'l_fileProbed':     l_fileProbed,
            'd_convert':        d_convert
        }

    def exec(self) -> dict:
        """
        The main entry point for connecting methods of this class
        to the appropriate callbacks of the `pftree.tree_process()`.
        Note that the return json of each callback is available to
        the next callback in the queue as the second tuple value in
        the first argument passed to the callback.
        """
        d_exec     : dict    = {}

        other.mkdir(self.args['outputDir'])
        d_exec     = self.pf_tree.tree_process(
                            inputReadCallback       = self.inputReadCallback,
                            analysisCallback        = self.inputAnalyzeCallback,
                            outputWriteCallback     = None,
                            persistAnalysisResults  = False
        )
        return d_exec

    def tagsInString_process(self, astr, *args, **kwargs):
        """
        This method substitutes tags in the user CLI exec that are '%'-tagged
        in a %<template> pattern. <template> can be any variable in the
        internal self.args dictionary.

        Additionally, the following special <templates> are processed:

        * '%inputWorkingDir'  - the current input tree working directory
        * '%outputWorkingDir' - the current output tree working directory
        * '%inputWorkingFile' - the current file being processed

        Furthermore, leveraging similar code used elsewhere, it is also
        possible to apply certain permutations/functions to a tag. For example,
        a function is identified by an underscore prefixed and suffixed string
        as part of the CLI exec string. If found, this function is applied to
        the tag value. For example a string snippet that contains

            %_strrepl|.,-_inputWorkingFile.txt

        will replace all occurences of '.' in the %inputWorkingFile with '-'.
        Also of interest, the trailing ".txt" is preserved in the final pattern
        for the result.

        Note the template for specifying a function to apply is:

            %_<functionName>[|comma-separated-arglist]_<tag>

        So, to remove the extension from an %inputWorkingFile, do

            %_rmext_inputWorkingFile

        Functions cannot currently be nested.

        """

        def md5_process(func, str_replace):
            """
            md5 mangle the <str_replace>.
            """
            nonlocal    astr
            l_funcTag   = []        # a function/tag list
            l_args      = []        # the 'args' of the function
            chars       = ''        # the number of resultant chars from func
                                    # result to use
            str_replace = hashlib.md5(str_replace.encode('utf-8')).hexdigest()
            l_funcTag   = func.split('_')[1:]
            func        = l_funcTag[0]
            l_args      = func.split('|')
            if len(l_args) > 1:
                chars   = l_args[1]
                str_replace     = str_replace[0:int(chars)]
            astr        = astr.replace('_%s_' % func, '')
            return astr, str_replace

        def strmsk_process(func, str_replace):
            """
            string mask
            """
            nonlocal    astr
            l_funcTag   = []        # a function/tag list
            l_funcTag   = func.split('_')[1:]
            func        = l_funcTag[0]
            str_msk     = func.split('|')[1]
            l_n = []
            for i, j in zip(list(str_replace), list(str_msk)):
                if j == '*':    l_n.append(i)
                else:           l_n.append(j)
            str_replace = ''.join(l_n)
            astr        = astr.replace('_%s_' % func, '')
            return astr, str_replace

        def strrepl_process(func, str_replace):
            """
            find and replace spaces in string
            """
            nonlocal    astr
            l_funcTag   = []        # a function/tag list
            l_args      = []        # the 'args' of the function
            l_funcTag   = func.split('_')[1:]
            func        = l_funcTag[0]
            l_args      = func.split('|')
            str_char    = ''
            if len(l_args) > 1:
                str_find = l_args[1]
                str_repl = l_args[2]
            # strip out all non-alphnumeric chars and
            # replace with space
            str_replace = re.sub(r'\W+', ' ', str_replace)
            # replace all spaces with str_char
            str_replace = str_char.join(str_replace.split())
            astr        = astr.replace('_%s_' % func, '')
            return astr, str_replace

        def rmext_process(func, str_replace):
            """
            Remove the extension from <str_replace>.

                %_rmext|_inputWorkingFile

            """
            nonlocal    astr
            l_funcTag   = []        # a function/tag list
            l_args      = []        # the 'args' of the function
            l_funcTag   = func.split('_')[1:]
            func        = l_funcTag[0]
            l_args      = func.split('|')
            str_char    = ''
            str_replace = os.path.splitext(str_replace)[0]
            astr        = astr.replace('_%s_' % func, '')
            return astr, str_replace

        def convertToNumber (s):
            return int.from_bytes(s.encode(), 'little')

        def convertFromNumber (n):
            return n.to_bytes(math.ceil(n.bit_length() / 8), 'little').decode()

        def name_process(func, str_replace):
            """
            replace str_replace with a name.

            Note this sub-function can take as an argument a seed, which
            is then used to seed the name caller assuring that subsequent
            calls to the name generation result in the same output.

            This is a WIP!
            """
            # pudb.set_trace()
            nonlocal    astr
            l_funcTag   = []        # a function/tag list
            l_args      = []        # the 'args' of the function
            l_funcTag   = func.split('_')[1:]
            func        = l_funcTag[0]
            l_args      = func.split('|')
            if len(l_args) > 1:
                str_argTag  = l_args[1]
                str_argTag  = re.sub('([a-zA-Z])', lambda x: x.groups()[0].upper(), str_argTag, 1)
                randSeed    = convertToNumber(str_argTag)
                Faker.seed(randSeed)
            str_firstLast   = pfdo_run.fake.name()
            l_firstLast     = str_firstLast.split()
            str_first       = l_firstLast[0]
            str_last        = l_firstLast[1]
            str_replace     = '%s^%s' % (str_last.upper(), str_first.upper())
            astr            = astr.replace('_%s_' % func, '')
            return astr, str_replace

        def tag_lookup(astr_tag, **kwargs) -> str:
            """
            Return the tag value of the %<string> -- this is either
            a static lookup from one of the internal self.args keys,
            or one of the "dynamic" tag values.
            """
            str_value   : str       = ""

            # First, set the return value based off the static self.args
            str_value   = self.args[astr_tag]

            # now, if however the tag is in the **kwargs, use that value
            # instead
            if astr_tag in kwargs.keys():   str_value   = kwargs[astr_tag]

            return str_value


        b_tagsFound     : bool  = False
        str_replace     : str   = ''        # The lookup/processed tag value
        l_tags          : list  = []        # The input string split by '%'
        l_tagsToSub     : list  = []        # Remove any noise etc from each tag
        func            : str   = ''        # the function to apply
        tag             : str   = ''        # the tag in the funcTag combo

        if '%' in astr:
            # pudb.set_trace()
            l_tags          = astr.split('%')[1:]
            # Now, from the possible mangled l_tag strings, make a "clean"
            # list of actual correct tags to sub
            l_tagsToSub     = [i for b in l_tags for i in self.args if i in b]
            for tag, func in zip(l_tagsToSub, l_tags):
                b_tagsFound     = True
                str_replace     = tag_lookup(tag, **kwargs)
                if 'md5'    in func: astr, str_replace   = md5_process(     func, str_replace)
                if 'strmsk' in func: astr, str_replace   = strmsk_process(  func, str_replace)
                if 'strrepl'  in func: astr, str_replace   = strrepl_process(   func, str_replace)
                if 'name'   in func: astr, str_replace   = name_process(    func, str_replace)
                if 'rmext'  in func: astr, str_replace   = rmext_process(   func, str_replace)
                astr  = astr.replace('%' + tag, str_replace, 1)

        return {
            'status':       True,
            'b_tagsFound':  b_tagsFound,
            'str_result':   astr
        }

    def job_run(self, str_cmd):
        """
        Running some CLI process via python is cumbersome. The typical/easy
        path of
                            os.system(str_cmd)

        is deprecated and prone to hidden complexity. The preferred
        method is via subprocess, which has a cumbersome processing
        syntax. Still, this method runs the `str_cmd` and returns the
        stderr and stdout strings as well as a returncode.
        Providing readtime output of both stdout and stderr seems
        problematic. The approach here is to provide realtime
        output on stdout and only provide stderr on process completion.
        """
        d_ret       : dict = {
            'stdout':       "",
            'stderr':       "",
            'cmd':          "",
            'cwd':          "",
            'returncode':   0
        }
        str_stdoutLine  : str   = ""
        str_stdout      : str   = ""

        p = subprocess.Popen(
                    str_cmd.split(),
                    stdout      = subprocess.PIPE,
                    stderr      = subprocess.PIPE,
        )

        # Realtime output on stdout
        str_stdoutLine  = ""
        str_stdout      = ""
        while True:
            stdout      = p.stdout.readline()
            if p.poll() is not None:
                break
            if stdout:
                str_stdoutLine = stdout.decode()
                if int(self.args['verbosity']):
                    print(str_stdoutLine, end = '')
                str_stdout      += str_stdoutLine
        d_ret['cmd']        = str_cmd
        d_ret['cwd']        = os.getcwd()
        d_ret['stdout']     = str_stdout
        d_ret['stderr']     = p.stderr.read().decode()
        d_ret['returncode'] = p.returncode
        if int(self.args['verbosity']) and len(d_ret['stderr']):
            print('\nstderr: \n%s' % d_ret['stderr'])
        return d_ret

    def job_stdwrite(self, d_job, str_outputDir, str_prefix):
        """
        Capture the d_job entries to respective files.
        """
        if not self.args['noJobLogging']:
            for key in d_job.keys():
                with open(
                    '%s/%s%s' % (str_outputDir, str_prefix, key), "w"
                ) as f:
                    f.write(str(d_job[key]))
                    f.close()
        return {
            'status': True
        }

    def run(self, *args, **kwargs) -> dict:
        """
        This base run method should be called by any descendent classes
        since this contains the calls to the first `pftree` prove as well
        as any (overloaded) file filtering.
        """
        b_status        : bool  = False
        b_timerStart    : bool  = False
        d_pfdo          : dict  = {}
        d_exec          : dict  = {}

        self.dp.qprint(
                "Starting pfdo_run... (please be patient while running)",
                level = 1
        )

        for k, v in kwargs.items():
            if k == 'timerStart':   b_timerStart    = bool(v)

        if b_timerStart:    other.tic()
        d_pfdo          = super().run(
                            JSONprint   = False,
                            timerStart  = False
        )

        if d_pfdo['status']:
            d_exec     = self.exec()

        d_ret = {
            'status':           b_status,
            'd_pfdo':           d_pfdo,
            'd_exec':           d_exec,
            'runTime':          other.toc()
        }

        if self.args['json']:
            self.ret_dump(d_ret, **kwargs)
        else:
            self.dp.qprint('Returning from pfdo_run...', level = 1)

        return d_ret
