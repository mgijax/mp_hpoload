#!/bin/sh
#
#  mpHpoQC.sh
###########################################################################
#
#  Purpose:
#
#      This script is a wrapper around the process that does QC
#      checks for the MP/HPO mapping load
#
#  Usage:
#
#      mpHpoQC.sh  filename  
#
#      where
#          filename = full path to the input file
#
#  Env Vars:
#
#      See the configuration file
#
#  Inputs:
#	mpHpo input file
#
#  Outputs:
#
#      - QC report for the input file.
#
#      - Log file (${QC_LOGFILE})
#
#  Exit Codes:
#
#      0:  Successful completion
#      1:  Fatal initialization error occurred
#
#  Assumes:  Nothing
#
#  Implementation:
#
#      This script will perform following steps:
#
#      1) Validate the arguments to the script.
#      2) Validate & source the configuration files to establish the environment
#      3) Verify that the input file exists.
#      4) Initialize the log and report files.
#      5) Call mpHpoQC.py to generate the QC report.
#
#  Notes:  None
#
###########################################################################
#
#  Modification History:
#
#  Date        SE   Change Description
#  ----------  ---  -------------------------------------------------------
#
#  12/22/2015  sc  Initial development
#
###########################################################################
CURRENTDIR=`pwd`
BINDIR=`dirname $0`

USAGE='Usage: mpHpoQC.sh  filename'

# this is a QC check only run, set LIVE_RUN accordingly
LIVE_RUN=0; export LIVE_RUN

#
# Make sure an input file was passed to the script. If the optional "live"
# argument is given, that means that the output files are located in the
# /data/loads/... directory, not in the current directory.
#
CONFIG=`cd ${BINDIR}/..; pwd`/mp_hpoload.config

if [ $# -eq 1 ]
then
    INPUT_FILE=$1
elif [ $# -eq 2 -a "$2" = "live" ]
then
    INPUT_FILE=$1
    LIVE_RUN=1
else
    echo ${USAGE}; exit 1
fi
#
# Make sure the configuration file exists and source it.
#
if [ -f ${CONFIG} ]
then
    . ${CONFIG}
else
    echo "Missing configuration file: ${CONFIG}"
    exit 1
fi

#
# If this is not a "live" run, the output, log and report files should reside
# in the current directory, so mpHpo the default settings.
#
if [ ${LIVE_RUN} -eq 0 ]
then
	QC_RPT=${CURRENTDIR}/`basename ${QC_RPT}`
	QC_LOGFILE=${CURRENTDIR}/`basename ${QC_LOGFILE}`

fi
#
# Make sure the input file exists (regular file or symbolic link).
#
if [ "`ls -L ${INPUT_FILE} 2>/dev/null`" = "" ]
then
    echo "Missing input file: ${INPUT_FILE}"
    exit 1
fi

#
# Initialize the log file.
#
LOG=${QC_LOGFILE}
rm -rf ${LOG}
touch ${LOG}

#
# Convert the input file into a QC-ready version that can be used to run
# the sanity/QC reports against.
#
dos2unix ${INPUT_FILE} ${INPUT_FILE} 2>/dev/null
#
# Initialize the report files to make sure the current user can write to them.
#
rm -f ${QC_RPT}; >${QC_RPT}

#
# Run qc checks on the input file
#
echo "" >> ${LOG}
date >> ${LOG}
echo "Run QC checks on the input file" >> ${LOG}
echo '${PYTHON} ${LOAD_QC} ${INPUT_FILE}'
${PYTHON} ${LOAD_QC} ${INPUT_FILE}
STAT=$?
if [ ${STAT} -eq 0 ]
then
echo "No QC errors detected." | tee -a ${LOG}
    echo "" | tee -a ${LOG}
fi

if [ ${STAT} -eq 1 ]
then
    echo "Fatal initialization error. See ${LOG}" | tee -a ${LOG}
    echo "" | tee -a ${LOG}
    exit ${STAT}
fi

if [ ${STAT} -eq 2 ]
then
    echo "Non-fatal QC errors detected. See ${QC_RPT}" | tee -a ${LOG}
    echo "" | tee -a ${LOG}
fi

if [ ${STAT} -eq 3 ]
then
    echo "Fatal QC errors detected. See ${QC_RPT}" | tee -a ${LOG}
    echo "" | tee -a ${LOG}
    exit ${STAT}
fi

echo "" >> ${LOG}
date >> ${LOG}
echo "Finished running QC checks on the input file" >> ${LOG}

exit 0
