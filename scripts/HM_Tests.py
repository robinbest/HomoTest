#
# Copyright 2026 Robin Best
#
# HomoTest/                <-- Repo root folder
#    scripts/              <-- this script and HM_Compare.py
#    tests/                <-- test root folder
#       config.xml
#       sub_folders/       <-- all test cases
#
# How to run:
# 1. run command "python3 path/HM_Tests.py", this will actually run all test cases
# 2. check screen output
#

import os, os.path, glob, fnmatch, subprocess, sys
import argparse, socket
from shutil import copyfile
from datetime import date, datetime, timedelta
import xml.etree.ElementTree as aXML
import HM_Compare as ADC

myVersion = 'v1.0'

#global test configuration
class tConfig:
    #set from config.xml
    product = "no_name"
    #absolute tolerance abs(n1-n2)
    tolerance = 1.0e-4
    #relative tolerance abs(n1-n2)/abs((n1+n2)/2)
    #tricky when n1+n2=0
    relative_tol = 0.002
    #global options to run executable
    mesher_options = ""
    solver_options = ""

    mesher_exe = "not_defined"
    solver_exe = "not_defined"
    #solver version
    executable_version = ""
    my_dir = "not_defined" #where config.xml is

    update_qa = False
    run_folder = ["."]
    exclude_folder = [""]
    test_case = "all"
    ignore_platform = False
    verbose = False
    email_recipients=""

    def set_dir(self, cmdDir):
        self.my_dir = cmdDir
        return

    def parse_args(self, args):
        #default folder is the root of test folder (all cases will be run)
        self.run_folder = ["."]
        if not args.folder is None:
            #all run folders should be relative to current location
            self.run_folder = [x.strip() for x in args.folder.split(',')]
            ffld = []
            for a_folder in self.run_folder:
                if os.path.exists(a_folder):
                    ffld.append(a_folder)
                else:
                    print('  Skip nonexistent folder ' + a_folder)
            self.run_folder = ffld
            print("  Specified folder(s): ", self.run_folder)
            if len(self.run_folder) == 0:
                sys.exit("Error: no valid folders are specified!")
        if not args.exclude is None:
            self.exclude_folder = [x.strip() for x in args.exclude.split(',')]
            for a_folder in self.exclude_folder:
                if not os.path.exists(a_folder):
                    sys.exit('Error:  try to exclude nonexistent folder ' + a_folder)
            print("  Excluded folder: ", self.exclude_folder)
        if not args.type is None:
            self.test_type = args.type
            self.check_type()
        if not args.case is None:
            self.test_case = args.case
            print("  Specified case: ", self.test_case)
        if args.update_qa:
            self.update_qa = True
            print("  Updating qa files ")
        if args.ignore_platform:
            self.ignore_platform = True
            print("  Ignore platform (run all tests)")
        self.verbose = args.verbose

    def parse_xml(self, xfile):
        root = aXML.parse(xfile).getroot()
        product = root.find('product')
        self.product = product.get('name')
        qa = root.find('qa')
        self.tolerance = float(qa.get('absolute_tol'))
        if 'relative_tol' in qa.attrib:
            self.relative_tol = float(qa.get('relative_tol'))
        else:
            self.relative_tol = 0.002
        if 'mesher_options' in qa.attrib:
            self.mesher_options = qa.get('mesher_options')
        else:
            self.mesher_options = ""
        if 'solver_options' in qa.attrib:
            self.solver_options = qa.get('solver_options')
        else:
            self.solver_options = ""

        print("Test configuration")
        print("  product    : ", self.product)
        print("  tolerance  : ", self.tolerance)
        print("  mesher options: ", self.mesher_options)
        print("  solver options: ", self.solver_options)
        print()
        return

    def get_exe(self, cmdDir):
        #project root, relative to cmdDir (where config.xml is)
        #two ways to find projRoot
        #1. cmdDir + root_dir, config.xml is in a deeper subfolder
        #2. cmdDir + ../, config.xml is under projRoot/TestRoot/
        if self.root_dir == 'not_defined':
            projRoot = os.path.abspath(os.path.join(cmdDir, ".."))
        else:
            #check #2.
            projRoot = os.path.abspath(os.path.join(cmdDir, self.root_dir))
            installd = os.path.join(projRoot, self.install_dir)
            solverExe = os.path.join(installd, self.executable)
            if not os.path.isfile(solverExe):
                #not found, use #1.
                projRoot = os.path.abspath(os.path.join(cmdDir, ".."))

        #if solverExe is not valid, caller will error
        installd = os.path.join(projRoot, self.install_dir)
        solverExe = os.path.join(installd, self.executable)
        return [projRoot, solverExe, self.executable_options]

global_conf = tConfig()

#settings parameters for a test case
class testPM:
    def __init__(self):
        self.options = "skip_test"
        self.platform = "all"

        #specify each compare
        #<image_compare output="f1" gold="f2" relative_tol="0.2">
        #relative_tol is optional
        self.csv_compare = []
        self.text_compare = []

    def should_compare(self):
        if  len(self.csv_compare) == 0 and len(self.text_compare) == 0:
            return False
        return True

    def parse_compare(self, cmp):
        output = cmp.get("output", "")
        gold = cmp.get("gold", "")
        #tolerance for this comparison, use global if it's not specified
        if 'relative_tol' in cmp.attrib:
            rtol = float(cmp.get('relative_tol'))
        else:
            rtol = global_conf.relative_tol
        if 'absolute_tol' in cmp.attrib:
            atol = float(cmp.get('absolute_tol'))
        else:
            atol = global_conf.tolerance

        #returns a tuple of 4 values
        return (output,gold,atol,rtol)

    def parse_xml(self, xtag):
        self.options = xtag.get('options', "skip_test")
        self.platform = xtag.get('platform', "all")

        #both output file and gold file are specified
        #csv
        csvComps = xtag.findall("csv_compare")
        for csvcmp in csvComps:
            tuple = self.parse_compare(csvcmp)
            self.csv_compare.append(tuple)
        #text
        txtComps = xtag.findall("text_compare")
        for txcmp in txtComps:
            tuple = self.parse_compare(txcmp)
            self.text_compare.append(tuple)

    def match_platform(self):
        if global_conf.ignore_platform:
            return True
        if os.name == "posix" and \
            (self.platform.find("all") >= 0 or self.platform.find("linux") >= 0):
            return True
        elif os.name == "nt" and \
            (self.platform.find("all") >= 0 or self.platform.find("windows") >= 0):
            return True
        return False

    #returns True if os is matched
    def match_test(self):
        if self.options == "skip_test":
            return False
        return (self.match_platform())

#data structure for one test case
#a case can have 3 types of tests
class tCase:
    def __init__(self):
        self.input_file = "not_defined"
        #3 test types, load from xml
        self.mesher_test = testPM()
        self.solver_test= testPM()
        #setup for current test
        self.should_run    = False   #whether to run the job
        self.curr_job      = "not_defined" #the job to run, usually the input file
        self.csv_tolerance = 1.0e-3

    def parse_xml(self, acase):
        #acase is an xml node
        self.input_file = acase.get('input_file')
        #if not found, this test will not be run for the type of test
        t1 = acase.find('mesher_test')
        if not (t1 is None):
            self.mesher_test.parse_xml(t1)
        t2 = acase.find('solver_test')
        if not (t2 is None):
            self.solver_test.parse_xml(t2)

    #based on current test type and platform, determine if this
    #case should be run or not. if running, update the qa
    #subfolder for the current test type
    def setup_test(self):
        self.should_run = False
        #if a case name is specified
        if not global_conf.test_case == "all":
            test_case = global_conf.test_case.split('\\')[-1]
            if not self.input_file == test_case:
                return

        self.curr_job = self.input_file
        self.should_run = True
        return

def get_immediate_subdirectories(a_dir):
    return [name for name in os.listdir(a_dir)
        if os.path.isdir(os.path.join(a_dir, name))]

def find(pattern, path):
    result = []
    for root, dirs, files in os.walk(path):
        for name in files:
            if fnmatch.fnmatch(name, pattern):
                result.append(os.path.join(root, name))
    return result

def solver_version(solverExe, solverOptions):
    pp = subprocess.Popen(solverExe + " " + solverOptions + " -help", shell=True,\
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    retval = "no_version"
    for line in pp.stdout.readlines():
        aLine = line.strip(b'\n').decode("utf-8")
        print(aLine)
        #HomoGen Solver v1.10
        if aLine.find("Solver") >= 0 or aLine.find("Mesher") >= 0:
            phrases = line.split(b' ')
            for i in range(len(phrases)):
                if (phrases[i] == b"Solver") or (phrases[i] == b"Mesher"):
                    if i+1 < len(phrases):
                        retval = phrases[i+1].rstrip().decode("utf-8")
                    break
            break

    retval2 = retval.rstrip("\r\n")
    return retval2

def run_solver(theCmd):
    theCmd = ADC.fix_path(theCmd)
    print(' ')
    print('-------------------------------------------------------')
    print('**Running: ', theCmd)
    ppn = subprocess.Popen(theCmd, shell=True, \
              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    successful = False
    while True:
        nextline = ppn.stdout.readline()
        #sys.stdout.write(str(nextline) + "+++\n")
        if nextline == b'' and ppn.poll() is not None:
            break
        if os.name == "nt":
            #on windows, there is a blank line after each print
            #remove all trailing white spaces, add one line return
            ssline = nextline.rstrip()
            if len(ssline) > 0:
                #sys.stdout.write(str(ssline) + "---\n")
                #sys.stdout.write(ssline.decode("utf-8") + "\n")
                sys.stdout.write(ssline.decode("gbk", errors="ignore").encode("utf-8").decode("utf-8") + "\n")
        else:
            sys.stdout.write(nextline.decode("utf-8"))
        sys.stdout.flush()
        if len(nextline) < 2:
            continue

    #process returns 0
    return (successful or ppn.returncode == 0)

#-------------------------------------------------------------
def compare_qa_files(qa_fn, out_fn):
    #old method, text comparison, numerical comparison
    num_diff = 0
    print("-----------------------------------")
    print("****Files specified by qa lines****")
    print(qa_fn)
    print(out_fn)
    if os.path.isfile(qa_fn):
        print(qa_fn + " VS " + out_fn)
        if qa_fn.endswith(".csv"):
            num_diff = num_diff + ADC.compare_csv_files(qa_fn, out_fn, \
                       global_conf.tolerance, global_conf.relative_tol)
        else:
            num_diff = num_diff + ADC.compare_text_files(qa_fn, out_fn, \
                       global_conf.tolerance, global_conf.relative_tol, True)
    else:
        print("Error: cannot find qa file " + qa_fn)
        num_diff = num_diff + 1

    return num_diff

#-------------------------------------------------------------
def compare_two_files(fcmp, filetype):
    #rfile: result file, gfile gold file
    rfile = fcmp[0]
    gfile = fcmp[1]
    num_diff = 0
    if global_conf.update_qa:
        #copy output file as the new gold file
        if os.path.isfile(rfile):
            copyfile(rfile, gfile)
            print('Copied : ' + rfile + " to " + gfile)
        else:
            print('Error: result file ' + rfile + " does not exist")
            num_diff = 1
        return num_diff

    if not os.path.isfile(rfile):
        num_diff = num_diff + 1
        print("Missing result file: " + rfile)
    elif not os.path.isfile(gfile):
        num_diff = num_diff + 1
        print("Missing gold file: " + gfile)
    else:
        if filetype == 'text':
            dcount = ADC.compare_text_files(rfile, gfile, fcmp[2], fcmp[3], True)
            if dcount == 0:
                print("Text files are the same")
            else:
                num_diff = num_diff + 1
                print("Text files are not the same")
        elif filetype == 'csv':
            dcount = ADC.compare_csv_files(rfile, gfile, fcmp[2], fcmp[3])
            if dcount == 0:
                print("CSV files are the same")
            else:
                num_diff = num_diff + 1
                print("CSV files are not the same")
        elif filetype == 'image':
            ret = ADC.compare_image_files(rfile, gfile)
            if ret:
                print("Images are the same")
            else:
                num_diff = num_diff + 1
                print("Images are not the same")

    print()
    return num_diff

#-------------------------------------------------------------
def compare_results(current_test, current_job):
    #count total num of differences
    num_diff = 0
    num_compare = 0

    #compare csv files
    for ccmp in current_test.csv_compare:
        num_diff = num_diff + compare_two_files(ccmp, 'csv')
        num_compare = num_compare+1

    #compare text files
    for tcmp in current_test.text_compare:
        num_diff = num_diff + compare_two_files(tcmp, 'text')
        num_compare = num_compare+1

    if num_compare == 0:
        print("Error: nothing was checked for case \'", current_job,"\'")
        num_diff = 1
    return num_diff

#-------------------------------------------------------------
def run_test_case(qaFile):
    retval = ["first"]
    job_lines = []

    qaRoot = aXML.parse(qaFile).getroot()
    allCases = qaRoot.findall('case')
    for aCase in allCases:
        atest = tCase()
        #load settings in xml
        atest.parse_xml(aCase)
        #get current test based on global settings
        atest.setup_test()
        if (not atest.should_run):
            if global_conf.verbose:
                print()
                print('---------------------------------------------')
                print("  ", atest.curr_job, " is skipped")
            continue

        #run the test case
        t_elapsed = timedelta(seconds=0)
        mesh_successful = True
        solver_successful = True
        total_diff = 0

        if not atest.mesher_test.match_test():
            if global_conf.verbose:
                print()
                print('---------------------------------------------')
                print("  ", atest.curr_job, " meshing test is skipped")
        elif mesherExe is not None:
            mesherOptions = global_conf.mesher_options + " " + atest.mesher_test.options
            theCmd = mesherExe + " " + mesherOptions + " " + atest.curr_job
            t_start = datetime.now()
            mesh_successful = run_solver(theCmd)
            t_elapsed += datetime.now() - t_start

            if not mesh_successful:
                result = "FAIL: (incomplete) " + atest.curr_job
                print(result)
                retval.append(result)
            elif not atest.mesher_test.should_compare():
                result = "PASS: (no compare) " + atest.curr_job
            else:
                #total num of differences
                total_diff += compare_results(atest.mesher_test, atest.curr_job)

        if not atest.solver_test.match_test() or not mesh_successful:
            if global_conf.verbose:
                print()
                print('---------------------------------------------')
                print("  ", atest.curr_job, " solver test is skipped")
        elif solverExe is not None:
            solverOptions = global_conf.solver_options + " " + atest.solver_test.options
            theCmd = solverExe + " " + solverOptions + " " + atest.curr_job
            t_start = datetime.now()
            solver_successful = run_solver(theCmd)
            t_elapsed += datetime.now() - t_start

            if not solver_successful:
                result = "FAIL: (incomplete) " + atest.curr_job
            elif not atest.solver_test.should_compare():
                result = "PASS: (no compare) " + atest.curr_job
            else:
                #total num of differences
                total_diff += compare_results(atest.solver_test, atest.curr_job)

        if total_diff > 0 or not mesh_successful or not solver_successful:
            result = "FAIL: " + atest.curr_job
        else:
            result = "PASS: " + atest.curr_job
        #append solver time usage
        result = result + " [" + str(t_elapsed.total_seconds()) + "s]"
        print(result)
        retval.append(result)

    retval.pop(0)
    return retval

def run_dir(out_file):
    try:
        #qa file in current directory
        qaFile = "qa.xml"
        if os.path.isfile(qaFile):
            if global_conf.verbose:
                print("----------------------------------------------")
                print("Running subdirectory: ", os.getcwd())
            test_result = run_test_case(qaFile)
            for line in test_result:
                out_file.write(line)
                out_file.write("\n")

        fullDirList = get_immediate_subdirectories(".")
        aDirList = [a_folder for a_folder in fullDirList if a_folder not in global_conf.exclude_folder]
        #print aDirList
        for subdir in aDirList:
            os.chdir(subdir)
            #recursion into the sub folders
            run_dir(out_file)
            os.chdir("..")
            #break
    except Exception as e:
        print("Unable to run dir: ", e)

def get_solver_mesher(args):
    #get executables and versions
    solverExe = args.solver
    if args.solver is None:
        print("  No solver executable specified, skip")
    else:
        print("  Specified solver: ", solverExe)
        if not os.path.isfile(solverExe):
            print("")
            print("FAIL: cannot find ", solverExe)
            sys.exit("Aborted!")

    mesherExe = args.mesher
    if args.mesher is None:
        print("  No mesher executable specified, skip")
    else:
        print("  Specified mesher: ", mesherExe)
        if not os.path.isfile(mesherExe):
            print("")
            print("FAIL: cannot find ", mesherExe)
            sys.exit("Aborted!")

    if solverExe is None:
        solverVersion = "no_version"
    else:
        solverVersion = solver_version(solverExe, "")
    if mesherExe is None:
        mesherVersion = "no_version"
    else:
        mesherVersion = solver_version(mesherExe, "")
    return solverExe, solverVersion, mesherExe, mesherVersion

#main entry
if __name__ == '__main__':
    print("---HomoGen testing (%s)---" % myVersion)
    print(str(datetime.now()))
    print()

    #this is where this script is executed
    cmdDir = os.getcwd()
    print("Current dir: ", cmdDir)

    parser = argparse.ArgumentParser()
    parser.add_argument('-verbose', dest='verbose', action='store_true', \
            help='print more information to the screen')
    parser.add_argument('-folder', required=False, \
            help='specify folders (full paths, separated by ,) to test (default: run all folders)')
    parser.add_argument('-exclude', required=False, \
            help = 'exclude folder')
    parser.add_argument('-case', required=False, \
            help='specify a case to test (default: run all cases)')
    parser.add_argument('-solver', required=False, \
            help='specify the solver executable')
    parser.add_argument('-mesher', required=False, \
            help='specify the mesher executable')
    parser.add_argument('-type', required=False, \
            help='specify test type: commit full (default: commit)')
    parser.add_argument('-ignore_platform', action='store_true', \
            help='run all tests, ignore windows/linux platform control')
    parser.add_argument('-update_qa', action='store_true', \
            help='run tests and update qa files (no comparison)')
    args = parser.parse_args()

    global_conf.parse_args(args)

    #abort if config file does not exist
    ADC.check_file_exists('config.xml', True)
    global_conf.parse_xml('config.xml')

    #this is where this script is located
    scriptDir = os.path.dirname(os.path.realpath(__file__))
    #repository root dir
    projRoot = os.path.abspath(os.path.join(cmdDir, ".."))

    global_conf.set_dir(cmdDir)

    # set environment variable for dynamic libraries, if needed
    if os.name == "posix":
        os.environ["LD_LIBRARY_PATH"] = '/usr/local/lib64'

    #get executables
    solverExe, solverVersion, mesherExe, mesherVersion = get_solver_mesher(args)
    global_conf.mesher_exe = mesherExe
    global_conf.solver_exe = solverExe
    solverOptions = global_conf.solver_options
    mesherOptions = global_conf.mesher_options
    if len(solverVersion) < 1:
        global_conf.solver_version = "no_version"
    else:
        global_conf.solver_version = solverVersion
    if len(mesherVersion) < 1:
        global_conf.mesher_version = "no_version"
    else:
        global_conf.mesher_version = mesherVersion

    #create summary folder if not exist
    summaryDir = os.path.join(cmdDir, "summary")
    if not os.path.isdir(summaryDir):
        os.mkdir(summaryDir)
    #output file name: solver version + date + sequence
    iii = 1
    out_stem = global_conf.product + "_" + solverVersion + "_" + str(date.today())
    outfn = out_stem + "." + str(iii) + ".csv"
    outfn = os.path.join(summaryDir, outfn)
    sumfn = os.path.join(summaryDir, "AD_Tests.csv")
    while os.path.exists(outfn):
        outfn = out_stem + "." + str(iii) + ".csv"
        outfn = os.path.join(summaryDir, outfn)
        iii = iii + 1

    print("Project root dir: ", projRoot)
    print("Mesher          : ", mesherExe)
    print("Mesher options  : ", mesherOptions)
    print("Mesher version  : ", mesherVersion)
    print("Solver          : ", solverExe)
    print("Solver options  : ", solverOptions)
    print("Solver version  : ", solverVersion)
    print("Test output     : ", outfn)

    out_file = open(outfn, "w")
    #out_file.write(solverVersion)
    os.chdir(cmdDir)

    #run tests
    t_tests_start = datetime.now()
    for a_folder in global_conf.run_folder:
        os.chdir(cmdDir)
        os.chdir(a_folder)
        run_dir(out_file)
    t_tests_elapsed = datetime.now() - t_tests_start

    #return to the original directory
    os.chdir(cmdDir)

    out_file.close()

    #separate passed and failed cases
    tmpf = open(outfn, 'r')
    tmpfLines = tmpf.readlines()
    tmpf.close()
    failedCases = []
    passedCases = []
    for line in tmpfLines:
        if "FAIL:" in line:
            failedCases.append(line)
        else:
            passedCases.append(line)

    #write summary file
    sum_file = open(sumfn, "w")
    sum_file.write("Failed:\n")
    #failed cases
    if failedCases:
        for case in failedCases:
            sum_file.write("  " + case)
        sum_file.write("  total " + str(len(failedCases)) + "\n")
    else:
        sum_file.write("  none\n")
    sum_file.write("\nPassed:\n")
    #passed cases
    if passedCases:
        for case in passedCases:
            sum_file.write("  " + case)
        sum_file.write("  total " + str(len(passedCases)) + "\n")
    else:
        sum_file.write("  none\n")
    #summary
    sum_file.write("\nTotal " + str(len(tmpfLines)) + " cases: ")
    if (not failedCases):
        sum_file.write("all passed\n")
    elif (not passedCases):
        sum_file.write("all failed\n")
    else:
        sum_file.write(str(len(failedCases)) + " failed, ")
        sum_file.write(str(len(passedCases)) + " passed\n")
    sum_file.close()

    #print summary file on screen
    print("")
    print("----------------------------------------------")
    print("Test summary:")
    print("")
    sum_file = open(sumfn, "r")
    print(sum_file.read())
    sum_file.close()
    print("Total time usage: " + str(t_tests_elapsed.total_seconds()) + "s")
    print("")
    print("test completed!")
    print("----------------------------------------------")
    #flush the last message on screen before exit
    print(str(datetime.now()), flush = True)
    os._exit(0)
