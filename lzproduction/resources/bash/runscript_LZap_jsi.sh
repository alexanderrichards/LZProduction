#!/bin/bash

function stop_on_error {
    ${@:1:(($#-1))}
    ret=$?
    if [ $ret -ne 0 ]
    then
	echo ${@:$#} "exit code: $ret" >&2
	exit $ret
    fi
}


BACCVER=3.16.0
DERVER=7.4.7
DER_Path=$1
HOUR=$2
Physics_release={{physics_version}}
LZAP_release={{lzap_version}}


TYPE=$(echo $DER_Path  |cut -d"/" -f5)
DAY=$(echo $DER_Path  |cut -d"/" -f7)
echo $TYPE $DAY  $HOUR


DATA_STORE_PATH=/lz/data
DATA_STORE_SE=UKI-LT2-IC-HEP-disk
LZAPPATH=$DATA_STORE_PATH/MDC2/${TYPE}/LZAP-${LZAP_release}-PHYSICS-${Physics_release}/${DAY}/

MDC2_MAIN_DIR=root://gfe02.grid.hep.ph.ic.ac.uk//pnfs/hep.ph.ic.ac.uk/data/lz
dirac-dms-find-lfns Path=$DER_Path|grep lz_${DAY}${HOUR} > list.txt
cat list.txt

string=""
i=0   
while read name
do
i=$((i+1))

string1=,$MDC2_MAIN_DIR$name

if [ "$i" -eq 1 ]
then
  string1=$MDC2_MAIN_DIR$name                                                                                                                                    
fi

string="${string}${string1}"
done <list.txt
rm list.txt

set --

LZAP_INPUT_FILES=$string
#echo $LZAP_INPUT_FILES

export PHYS_DIR=/cvmfs/lz.opensciencegrid.org/Physics/release-${Physics_release}
source ${PHYS_DIR}/Physics/setup.sh

LZAP_OUTPUT_DIR=$(pwd)

STEERING_DIR=${PHYS_DIR}/ProductionSteeringFiles
STEERING_FILE=${STEERING_DIR}/RunLZapMDC2wXYnoMCT.py
lzap_output_file=lz_${DAY}${HOUR}_lzap.root
#lzap_output_file=lz_${day}_${HOUR}_lzap.root
echo $lzap_output_file
export LZAP_OUTPUT_FILE=${LZAP_OUTPUT_DIR}/${lzap_output_file}
                                                                                                                                                         

echo $LZAP_INPUT_FILES
export LZAP_INPUT_FILES
stop_on_error ${LZAP_SCRIPTS_DIR}/lzap_execute ${STEERING_FILE} "LZAP failed"


stop_on_error ls $LZAP_OUTPUT_FILE "OUTPUT_LZAP_FILE does not exist"

dirac-dms-remove-files ${LZAPPATH}/$lzap_output_file
dirac-dms-add-file  ${LZAPPATH}/$lzap_output_file $LZAP_OUTPUT_DIR/$lzap_output_file $DATA_STORE_SE 
