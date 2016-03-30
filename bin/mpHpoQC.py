#!/usr/local/bin/python
#
#  mpHpoQC.py
###########################################################################
#
#  Purpose:
#
#	This script will generate a QC report for the
#	    MP/HPO Mapping Load file
#
#  Usage:
#
#      mpHpoQC.py  filename
#
#      where:
#          filename = path to the input file
#
#  Env Vars:
#
#      The following environment variables are set by the configuration
#      files that are sourced by the wrapper script:
#
#          QC_RPT
#	   
#  Inputs:
# 	MP/HPO input file
#	Columns:
#	1. MP ID
#	2. MP Term
#	3. HPO ID
#	4. HPO Term
#
#  Outputs:
#
#      - QC report (${QC_RPT})
#
#  Exit Codes:
#
#      0:  Successful completion
#      1:  Fatal initialization error occurred
#      2:  Non-fatal QC errors detected in the input files
#      3:  Fatal QC errors detected in the input file
#      4:  Warning QC
#
#  Assumes:
#
#  Implementation:
#
#      This script will perform following steps:
#
#      1) Validate the arguments to the script.
#      2) Perform initialization steps.
#      3) Run the QC checks.
#      5) Close input/output files.
#
#  Notes:  None
#
###########################################################################

import sys
import os
import string
import re
import mgi_utils
import db

#
#  CONSTANTS
#
TAB = '\t'
CRT = '\n'

USAGE = 'Usage: mpHpoQC.py  inputFile'

#
#  GLOBALS
#

# Report file name
qcRptFile = os.environ['QC_RPT']

# file with records to load 
inputFileToLoad = os.environ['INPUT_FILE_TOLOAD']

# minimum number of lines expected in the input file
minLines = int(os.environ['MIN_LINES'])

# {mpID:key, ...}
mpHeaderLookup = {}

# {hpoID:key, ...}
hpoLookup = {}

# input lines with missing data
missingDataList = []

# input lines with < 4 columns
missingColumnsList = []

# input lines with no MP ID
missingMpIdList = []

# input MP header IDs not in the database
invalidMpHeaderList = []

# input MP header term does not match term in the database
invalidMpTermList = []

# input HPO IDs not in the database
invalidHpoList = []

# input HPO term does not match term in the database
invalidHpoTermList = []

# all passing QC (non-fatal, non-skip)
linesToLoadList = []

# Counts reported when no fatal errors
loadCt = 0
skipCt = 0

# flags for errors
hasQcErrors = 0
hasFatalErrors = 0

#
# Purpose: Validate the arguments to the script.
# Returns: Nothing
# Assumes: Nothing
# Effects: sets global variable
# Throws: Nothing
#
def checkArgs ():
    global inputFile

    if len(sys.argv) != 2:
        print USAGE
        sys.exit(1)

    inputFile = sys.argv[1]

    return

# end checkArgs() -------------------------------------

#
# Purpose: Perform initialization steps.
# Returns: Nothing
# Assumes: Nothing
# Effects: opens files
# Throws: Nothing
#
def init ():
    global hpoLookup, mpHeaderLookup 

    openFiles()
   
    # load lookups 
    # lookup of MP header terms
    results = db.sql('''select a.accid, t.term
	from DAG_Node n, VOC_Term t, ACC_Accession a
	where n._Label_key = 3
	and n._Object_key = t._Term_key
	and t._Vocab_key = 5
	and t.isObsolete = 0
	and t._Term_key = a._Object_key
	and a._MGIType_key = 13
	and a._LogicalDB_key = 34
	and a.preferred = 1''', 'auto')
 
    for r in results:
        mpId = string.lower(r['accid'])
	term = string.lower(r['term'])
	mpHeaderLookup[mpId] = term

    # load lookup of HPO terms
    results = db.sql('''select a.accid, t.term 
	from VOC_Term t, ACC_Accession a
	where t._Vocab_key = 106
	and t._Term_key = a._Object_key
	and a._MGIType_key = 13
        and a._LogicalDB_key = 180''', 'auto')

    for r in results:
	hpoId = string.lower(r['accid'])
        term = string.lower(r['term'])
	hpoLookup[hpoId] = term

    return

# end init() -------------------------------------

# Purpose: Open input and output files.
# Returns: Nothing
# Assumes: Nothing
# Effects: Sets global variables.
# Throws: Nothing
#
def openFiles ():
    global fpInfile, fpToLoadFile, fpQcRpt

    # curator input file
    try:
        fpInfile = open(inputFile, 'r')
    except:
        print 'Cannot open input file: %s' % inputFile
        sys.exit(1)
    
    # all lines that pass QC
    try:
        fpToLoadFile = open(inputFileToLoad, 'w')
    except:
        print 'Cannot open input file: %s' % inputFileToLoad
        sys.exit(1)

    # QC report file
    try:
        fpQcRpt = open(qcRptFile, 'w')
    except:
        print 'Cannot open report file: %s' % qcRptFile
        sys.exit(1)

    return

# end openFiles() -------------------------------------

#
# Purpose: run the QC checks
# Returns: Nothing
# Assumes: Nothing
# Effects: sets global variables, write report to file system
# Throws: Nothing
#
def runQcChecks ():

    global hasQcErrors, hasFatalErrors, loadCt, skipCt

    lineNum = 1 # count header

    # throw away header
    header = fpInfile.readline()
    for line in fpInfile.readlines():
	lineNum += 1
	line = string.strip(line)
	# can't do this or won't detect missing data in first column
        #tokens = map(string.strip, string.split(line, TAB))
	tokens = string.split(line, TAB)
	#print '\n'
	#print 'lineNum: %s tokens: %s' % (lineNum, tokens)
	# skip blank lines
	if  len(tokens) == 1 and tokens[0] == '':
	    skipCt += 1
	    continue
	if len(tokens) < 4:
	    # if the first token is an MP ID, then we are missing columns
	    if string.find(tokens[0], 'MP:') >= 0: 
		#print 'missing columns line: %s' % lineNum
		hasFatalErrors = 1
		missingColumnsList.append('Line %s: %s%s' % (lineNum, line, CRT))
		continue
	    # otherwise we just have a missing MP ID, which is OK, just skip
	    else:
		#print 'missing MP ID: %s' % lineNum
		hasQcErrors = 1
		missingMpIdList.append('Line %s: %s%s' % (lineNum, line, CRT))
                continue

	mpId = string.strip(tokens[0])
	mpTerm = string.strip(tokens[1])
	hpoId = string.strip(tokens[2])
	hpoTerm = string.strip(tokens[3])
	#print string.lower(mpId)
	#print string.lower(mpTerm)
	#print string.lower(hpoId)
	#print string.lower(hpoTerm)
	if mpId == '' or mpTerm == '' or hpoId == '' or hpoTerm == '':
	    missingDataList.append('Line %s: "%s"%s' % (lineNum, line, CRT))
	    #print 'hasFatalErrors missing data'
	    hasFatalErrors = 1
	    continue
	hasIdErrors = 0
	if not mpHeaderLookup.has_key(string.lower(mpId)):
	    invalidMpHeaderList.append('Line %s: "%s"%s' % (lineNum, line, CRT))
	    hasIdErrors = 1
	else:
	    if not mpHeaderLookup[string.lower(mpId)] == string.lower(mpTerm):
		invalidMpTermList.append('Line %s: "%s"  In database: %s%s' % (lineNum, line, mpHeaderLookup[string.lower(mpId)], CRT))
		hasIdErrors = 1
	if not hpoLookup.has_key(string.lower(hpoId)):
	    invalidHpoList.append('Line %s: "%s"%s' % (lineNum, line, CRT))
            hasIdErrors = 1
	else:
	    #print hpoLookup[string.lower(hpoId)]
	    #print 'should match:'
	    #print string.lower(hpoTerm)
	    if not hpoLookup[string.lower(hpoId)] == string.lower(hpoTerm):
		invalidHpoTermList.append('Line %s: "%s"  In database: %s%s' % (lineNum, line, hpoLookup[string.lower(hpoId)], CRT))
		hasIdErrors = 1

	if hasIdErrors:
	    #print 'print hasFatalErrors hasIdErrors'
	    hasFatalErrors = 1
	    skipCt += 1
	    continue
	# If we get here, we have a good record, write it out to the load file
	loadCt +=1
	fpToLoadFile.write('%s%s' % (line, CRT))

    #
    # Report any fatal errors and exit - if found in published file, the load 
    # will not run
    #

    if lineNum < minLines:
	fpQcRpt.write('\nFatal Error: input file has < %s lines. Total lines: %s\n' % (minLines, lineNum))
	closeFiles()
	sys.exit(3)
    if hasFatalErrors:
	fpQcRpt.write('\nThe following errors must be fixed before publishing; if present, the load will not run\n\n')
	    
	if len(missingColumnsList):
	    fpQcRpt.write('\nInput lines with missing columns:\n')
	    fpQcRpt.write('-----------------------------\n')
	    for line in missingColumnsList:
		fpQcRpt.write(line)
	    fpQcRpt.write('\n')

	if len(missingDataList):
	    fpQcRpt.write('\nInput lines with missing data:\n')
	    fpQcRpt.write('-----------------------------\n')
	    for line in missingDataList:
		fpQcRpt.write(line)
	    fpQcRpt.write('\n')

        if len(invalidMpHeaderList):
            fpQcRpt.write('\nInput lines with invalid MP header IDs:\n')
            fpQcRpt.write('-----------------------------\n')
            for line in invalidMpHeaderList:
                fpQcRpt.write(line)
            fpQcRpt.write('\n')

	if len(invalidMpTermList):
	    fpQcRpt.write('\nInput lines where MP term does not match term in the database:\n')
            fpQcRpt.write('-----------------------------\n')
            for line in invalidMpTermList:
                fpQcRpt.write(line)
            fpQcRpt.write('\n')

        if len(invalidHpoList):
            fpQcRpt.write('\nInput lines with invalid HPO IDs:\n')
            fpQcRpt.write('-----------------------------\n')
            for line in invalidHpoList:
                fpQcRpt.write(line)
            fpQcRpt.write('\n')

	if len(invalidHpoTermList):
            fpQcRpt.write('\nInput lines where HPO term does not match term in the database:\n')
            fpQcRpt.write('-----------------------------\n')
            for line in invalidHpoTermList:
                fpQcRpt.write(line)
            fpQcRpt.write('\n')

	closeFiles()
        sys.exit(3)
    #
    # Report any non-fatal errors
    #
    if hasQcErrors:
	fpQcRpt.write('\nThe following errors are non-fatal. These records will be skipped.\n\n')
	if len(missingMpIdList):
	    fpQcRpt.write('\nInput lines with missing MP header terms:\n')
            fpQcRpt.write('-----------------------------\n')
            for line in missingMpIdList:
                fpQcRpt.write(line)
            fpQcRpt.write('\n')

    print '%sNumber with non-fatal QC errors, these will not be processed: %s' % (CRT, skipCt)
    
    print 'Number with no QC errors, these will be loaded: %s%s' % ( loadCt, CRT)
	#closeFiles()
	#sys.exit(2)

    return

# end runQcChecks() -------------------------------------
	
#
# Purpose: Close the files.
# Returns: Nothing
# Assumes: Nothing
# Effects: Nothing
# Throws: Nothing
#
def closeFiles ():
    global fpInfile, fpToLoadFile, fpQcRpt
    fpInfile.close()
    fpToLoadFile.close()
    fpQcRpt.close()
    return

# end closeFiles() -------------------------------------

#
# Main
#
#print 'checkArgs'
checkArgs()
#print 'init'
init()
#print 'runQcChecks'
runQcChecks()
#print 'closeFiles'
closeFiles()
if hasQcErrors: 
    sys.exit(2)
else:
    sys.exit(0)
