#
# Copyright 2026 Robin Best
#

import os, os.path, fnmatch, sys, re, math

#absolute tolerance, can be set in AD_Test
abs_tol = 0.5

#check if a file exists
#print failure message if file not exists
def check_file_exists(fname, abort_if_not_exist=False):
    if not os.path.isfile(fname):
        print("FAIL: file " + fname + " does not exist.")
        if abort_if_not_exist:
            sys.exit('Aborted')
        return False
    return True

#the qa file has path for linux platform '/'
def fix_path_string(input_string):
    if os.name == 'nt':
        return input_string.replace('/', '\\')
    else:
        return input_string.replace('\\', '/')

def fix_path(input_path):
    output = input_path
    if os.name == 'nt':
        output = os.path.join(*input_path.split('/'))
    else:
        output = os.path.join(*input_path.split('\\'))
    return output

#--------------------------------------------------------------------------
#check if the string is a number, returns false if it's 'nan'
def is_number(s):
    if len(s) == 0:
        return False
    try:
        sf = float(s)
        if math.isnan(sf):
            return False
        elif math.isinf(sf):
            return False
        return True
    except ValueError:
        pass
    return False

#--------------------------------------------------------------------------
#returns [TF, abs diff, relative diff]
# TF=True if two numbers are equal within tolerance
#hard coded threshold values are used 
def compare_numbers(n1, n2, atol, rtol):
    #atol is absolute tolerance
    #rtol is relative tolerance
    adiff = abs(n1 - n2)
    if abs(n1) < 1.0e-5 and abs(n2) < 1.0e-5:
        return [True, adiff, 0.]

    #compute relative difference
    rdiff = 0.0
    average = abs(n1 + n2) / 2
    if adiff > 1.0e-6 and average > 1.0e-6:
        rdiff = adiff / average
    #Fail if both absolute difference and relative
    #difference are larger than threshold values
    #Note: Aries's output force varies in separate runs
    if rdiff > rtol and adiff > atol:
        #print("<--->", rdiff, adiff, n1, n2)
        return [False, adiff, rdiff]
    return [True, adiff, rdiff]

#--------------------------------------------------------------------------
#Compare 2 text files, print diff on screen
#Accomodate windows vs linux paths
#Accomodate numbers, floating point difference
#Returns the number of different lines
def compare_text_files(fname1, fname2, atol, rtol, verbose_diff):
    verbose = True
    fname1 = fix_path(fname1)
    fname2 = fix_path(fname2)

    # Open file for reading in text mode (default mode)
    f1 = open(fname1)
    f2 = open(fname2)

    if not check_file_exists(fname1) or not check_file_exists(fname2):
        return 1

    if verbose:
        # Print confirmation
        print("-----------------------------------")
        print("Comparing text files ")
        print(("   > " + fname1))
        print(("   < " + fname2))
        print("")

    # Read the first line from the files
    f1_line = f1.readline()
    f2_line = f2.readline()

    # Initialize counter for line number
    line_no = 1
    count_diff = 0
    count_same = 0
    #max absolute difference
    max_adiff = 0
    #max relative difference
    max_rdiff = 0

    # Loop if either file1 or file2 has not reached EOF
    while f1_line != '' or f2_line != '':

        # Strip the trailing white spaces
        f1_line = f1_line.rstrip()
        f2_line = f2_line.rstrip()

        # Compare the lines from both file
        # the text can contain paths hard coded for linux or windows
        if f1_line == f2_line or fix_path_string(f1_line) == f2_line or \
           fix_path_string(f2_line) == f1_line:
            #matched, do nothing
            count_same = count_same + 1
        else:
            really_diff = False
            #parse numbers and compare them
            #json file has numbers in quotes, "3.1415926"
            #delimiters: , space [ ] "
            #delim = ",| |\[|\]" + "|\"" + "|\{|\}|:"
            delim = r",| |\[|\]|\"|\{|\}|:"
            f1_words = re.split(delim, f1_line)
            f2_words = re.split(delim, f2_line)
            if len(f1_words) == len(f2_words):
                for k in range(len(f1_words)):
                    if f1_words[k] == f2_words[k]:
                        continue
                    if is_number(f1_words[k]) and is_number(f2_words[k]):
                        f1f = float(f1_words[k])
                        f2f = float(f2_words[k])
                        [vequal, adiff, rdiff] = compare_numbers(f1f, f2f, atol, rtol)
                        max_adiff = max(max_adiff, adiff)
                        max_rdiff = max(max_rdiff, rdiff)
                        really_diff = (not vequal) or really_diff
                    else:
                        really_diff = True
            else:
                really_diff = True

            if really_diff:
                count_diff = count_diff + 1
            else:
                count_same = count_same + 1

            if verbose_diff and really_diff:
                # If a line does not exist on file2 then mark the output with + sign
                if f2_line == '' and f1_line != '':
                    print((">+", "Line-%d" % line_no, f1_line))
                # otherwise output the line on file1 and mark it with > sign
                elif f1_line != '':
                    print((">", "Line-%d" % line_no, f1_line))

                # If a line does not exist on file1 then mark the output with + sign
                if f1_line == '' and f2_line != '':
                    print(("<+", "Line-%d" % line_no, f2_line))
                # otherwise output the line on file2 and mark it with < sign
                elif f2_line != '':
                    print(("<", "Line-%d" %  line_no, f2_line))

                # Print a blank line
                print()

        #Read the next line from the file
        f1_line = f1.readline()
        f2_line = f2.readline()

        #Increment line counter
        line_no += 1

    # Close the files
    f1.close()
    f2.close()

    if verbose:
        print(" Number of different lines: ", count_diff)
        print(" Max absolute difference in value: ", max_adiff)
        print(" Max relative difference in value: ", max_rdiff)
        print("-----------------------------------")
        print("")
    return count_diff

#--------------------------------------------------------------------------
#compare 2 csv files
def compare_csv_files(fname1, fname2, atol, rtol):
    verbose = True
    fname1 = fix_path(fname1)
    fname2 = fix_path(fname2)

    if not check_file_exists(fname1) or not check_file_exists(fname2):
        return 1

    # Open file for reading in text mode (default mode)
    f1 = open(fname1)
    f2 = open(fname2)

    if verbose:
        # Print confirmation
        print("-----------------------------------")
        print("Comparing csv files ")
        print(("   > " + fname1))
        print(("   < " + fname2))
        print("")

    # Read the first line from the files
    f1_line = f1.readline()
    f2_line = f2.readline()

    # Initialize counter for line number
    line_no = 1
    count_diff = 0
    #max absolute difference
    max_adiff = 0
    #max relative difference
    max_rdiff = 0

    # Loop if either file1 or file2 has not reached EOF
    while f1_line != '' or f2_line != '':

        # Strip the trailing white spaces and comma
        f1_line = f1_line.rstrip()
        f1_line = f1_line.rstrip(",")
        f2_line = f2_line.rstrip()
        f2_line = f2_line.rstrip(",")

        # Compare the lines from both file
        if not f1_line == f2_line:
            f1_nums = f1_line.split(",")
            f2_nums = f2_line.split(",")
            if not len(f1_nums) == len(f2_nums):
                count_diff = count_diff + 1
            else:
                #check numerical difference
                for i in range(len(f1_nums)):
                    if is_number(f1_nums[i]) and is_number(f2_nums[i]):
                        n1 = float(f1_nums[i])
                        n2 = float(f2_nums[i])
                        [vequal, adiff, rdiff] = compare_numbers(n1, n2, atol, rtol)
                    else:
                        vequal = False
                        adiff = 1.0
                        rdiff = 1.0
                    max_adiff = max(max_adiff, adiff)
                    max_rdiff = max(max_rdiff, rdiff)
                    if not vequal:
                        count_diff = count_diff + 1

        #Read the next line from the file
        f1_line = f1.readline()
        f2_line = f2.readline()

        #Increment line counter
        line_no += 1

    # Close the files
    f1.close()
    f2.close()

    if verbose:
        print(" Number of differences  : ", count_diff)
        print(" Max absolute difference in value: ", max_adiff)
        print(" Max relative difference in value: ", max_rdiff)
        print("-----------------------------------")
        print("")
    return count_diff

#----------------------------------------------------------
def histo_compare(im1, im2, alpha = .001):
    try:
        from PIL import Image
    except ModuleNotFoundError:
        print("Python Error: please install imagehash module")
        return 10
    if im1.size == im2.size and im1.mode == im2.mode:
        h1 = im1.histogram()
        h2 = im2.histogram()
        SumIm1 = 0.0
        SumIm2 = 0.0
        diff = 0.0
        for i in range(len(h1)):
            SumIm1 += h1[i]
            SumIm2 += h2[i]
            diff += abs(h1[i] - h2[i])
        maxSum = max(SumIm1, SumIm2)
        print("max sum = ", maxSum, ", diff = ", diff)
        if diff > alpha*maxSum:
            return False
        return True
    else:
        print("Images are different in size: ", im1.size, im2.size)
    return False

#----------------------------------------------------------
def hash_compare(im1, im2):
    try:
        from PIL import Image
        import imagehash
    except ModuleNotFoundError:
        print("Python Error: please install imagehash module")
        return 10

    hash1 = imagehash.average_hash(im1)
    hash2 = imagehash.average_hash(im2)
    print("aHash diff = ", hash1 - hash2)
    a_diff = hash1 - hash2
    
    #Modify hash_size from 8 to 16
    #This modification make image comparisons more precisely.
    hash1 = imagehash.phash(im1, hash_size = 8)
    hash2 = imagehash.phash(im2, hash_size = 8)
    print("pHash diff = ", hash1 - hash2)
    p_diff = hash1 - hash2
    #p_diff = 0

    hash1 = imagehash.dhash(im1)
    hash2 = imagehash.dhash(im2)
    print("dHash diff = ", hash1 - hash2)
    d_diff = hash1 - hash2

    return abs(a_diff) + abs(p_diff)

#----------------------------------------------------------
#returns true if two images are the same
def compare_image_files(file1, file2):
    try:
        from PIL import Image
    except ModuleNotFoundError:
        print("Python Error: please install imagehash module")
        return 10

    image1 = Image.open(file1)
    image2 = Image.open(file2)
    
    #Cut photo to wanted size(left, upper, right, lower)
    #cropped = image1.crop((0, 0, 989, 623))
    #cropped.save(file1)
    #Reopen the photo
    image1 = Image.open(file1)
    
    #scale and compare
    #image1s = image1.resize((1000, 1000))
    #image2s = image2.resize((1000, 1000))

    hash_diff = hash_compare(image1, image2)
    #print("Hash diff = ", hash_diff)
    if hash_diff <= 1:
        return True
    #if histo_compare(image1, image2, 0.0001):
    #    return True
    return False
