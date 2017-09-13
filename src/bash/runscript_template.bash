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

export OUTPUT_DIR=$(pwd)
SE={{ se }}
{% if app_version %}
## Simulation variables
####################
MACRO_FILE=$1
export SEED=$2 # an integer that will label the output file
APP_DIR=/cvmfs/lz.opensciencegrid.org/{{ app }}/release-{{ app_version }}
ROOT_DIR=/cvmfs/lz.opensciencegrid.org/ROOT/v{{ root_version }}/{{ root_arch }}/root
G4_DIR=/cvmfs/lz.opensciencegrid.org/geant4/
G4_VER=geant{{ g4_version }}
SIM_LFN_DIR={{ sim_lfn_outputdir }}
MCTRUTH_LFN_DIR={{ mctruth_lfn_outputdir }}
{% endif %}
{% if reduction_version %}
## Reduction variables
####################
{% if not app_version %}
SIM_OUTPUT_FILE=$1
{% endif %}
LIBNEST_DIR=/cvmfs/lz.opensciencegrid.org/fastNEST/release-{{ fastnest_version }}
REDUCTION_DIR=/cvmfs/lz.opensciencegrid.org/TDRAnalysis/release-{{ reduction_version }}
REDUCTION_LFN_DIR={{ reduction_lfn_outputdir }}
{% endif %}
{% if der_version %}
## DER variables
####################
{% if not app_version %}
MCTRUTH_OUTPUT_FILE=$1
{% endif %}
DER_DIR=/cvmfs/lz.opensciencegrid.org/DER/release-{{ der_version }}
DER_LFN_DIR={{ der_lfn_outputdir }}
{% endif %}


{% if app_version %}
## Simulation
####################
#extract the name of the output file from the LUXSim macro
{% if app == 'BACCARAT' %}
OUTPUT_FILE=$(awk '/^\/Bacc\/io\/outputName/ {print $2}' $1 | tail -1)$2.bin
{% else%}
OUTPUT_FILE=$(awk '/^\/{{ app }}\/io\/outputName/ {print $2}' $1 | tail -1)$2.bin
{% endif %}

# move into the LUXSim directory, set G4 env, and run the macro
# the executable must be run from within it's dir!
cd $APP_DIR
{% if app == 'BACCARAT' and app_version.startswith('2') %}
source setup.sh
stop_on_error $APP_DIR/bin/{{ app }}Executable $OUTPUT_DIR/$MACRO_FILE "Simulation step failed!"
{% else %}
source $G4_DIR/etc/geant4env.sh $G4_VER
stop_on_error $APP_DIR/{{ app }}Executable $OUTPUT_DIR/$MACRO_FILE "Simulation step failed!"
{% endif %}

cd $OUTPUT_DIR
# after macro has run, rootify
{% if app == 'BACCARAT' %}
{% if app_version.startswith('2') %}
stop_on_error $APP_DIR/bin/BaccRootConverter $OUTPUT_FILE "Failed Rootify step!"
{% else %}
source $ROOT_DIR/bin/thisroot.sh
stop_on_error $APP_DIR/tools/BaccRootConverter $OUTPUT_FILE "Failed Rootify step!"
{% endif %}
{% else %}
source $ROOT_DIR/bin/thisroot.sh
stop_on_error `ls $APP_DIR/tools/*RootReader` $OUTPUT_FILE "Failed Rootify step!"
{% endif %}
SIM_OUTPUT_FILE=$(basename $OUTPUT_FILE .bin).root

stop_on_error `ls $APP_DIR/tools/*MCTruth` $SIM_OUTPUT_FILE "MCTruth step failed!"
MCTRUTH_OUTPUT_FILE=$(ls *_mctruth.root)
{% endif %}
{% if reduction_version %}
## Reduction
####################
source $LIBNEST_DIR/libNEST/thislibNEST.sh
REDUCTION_OUTPUT_FILE=$(basename $SIM_OUTPUT_FILE .root)_analysis_tree.root

{% if app == 'BACCARAT' %}
export BACC_TOOLS=$APP_DIR/tools
export LD_LIBRARY_PATH=$APP_DIR/lib:$LD_LIBRARY_PATH
stop_on_error $REDUCTION_DIR/ReducedAnalysisTree/Bacc2AnalysisTree $SIM_OUTPUT_FILE $REDUCTION_OUTPUT_FILE "Reduction step failed!"
{% else %}
stop_on_error $REDUCTION_DIR/ReducedAnalysisTree/LZSim2AnalysisTree $SIM_OUTPUT_FILE $REDUCTION_OUTPUT_FILE "Reduction step failed!"
{% endif %}
{% endif %}
{% if der_version %}
## DER
####################
i_job=$((SEED-{{ seed }}))
livetimeperjob={{ livetimeperjob }}
DT=$(awk "BEGIN {print $i_job*$livetimeperjob+0.5; exit}")
let DDT=`echo $DT | cut -d. -f 1`
UNIXTIME=$(({{ unixtime }}+DDT))

cd $DER_DIR
source $DER_DIR/DERenv.sh
stop_on_error $DER_DIR/DER --UserCheck false --SkipLargeDeltaT true --FileTimeStamp ${UNIXTIME} --fileSeqNum ${i_job} --SignalChain SAMPLED --outDir ${OUTPUT_DIR}/ ${OUTPUT_DIR}/${MCTRUTH_OUTPUT_FILE} "DER step failed!"

cd $OUTPUT_DIR
DER_OUTPUT_FILE=$(ls *_raw.root)
{% endif %}
{% if lzap_version %}
## LZap
###########################
N0=0
Nlast=251
LZAP_LFN_DIR={{ lzap_lfn_outputdir }}
{% if not der_version %}
DER_OUTPUT_FILE=$1
{% endif %}

set --

export PHYS_DIR=/cvmfs/lz.opensciencegrid.org/Physics/release-{{ physics_version }}
source ${PHYS_DIR}/Physics/setup.sh
STEERING_DIR=${PHYS_DIR}/ProductionSteeringFiles
STEERING_FILE=${STEERING_DIR}/RunLZapMCTruthON.py
export LZAP_INPUT_FILES=${OUTPUT_DIR}/$(basename ${DER_OUTPUT_FILE})
export LZAP_OUTPUT_FILE=${OUTPUT_DIR}/$(basename ${DER_OUTPUT_FILE/"_raw.root"/"_lzap.root"})
N=$(echo $(basename ${LZAP_OUTPUT_FILE}) | grep -oP '(?<=_)\d+(?=\_lzap)')

if [ $N -ge $N0 ] && [ $N -lt $Nlast ]
then
stop_on_error ${LZAP_SCRIPTS_DIR}/lzap_execute ${STEERING_FILE} "Error running LZap!"
fi
{% endif %}
## Upload
###########################
ls -l *.root
{% if app_version %}
{% if sim_lfn_outputdir %}
stop_on_error dirac-dms-add-file -ddd $SIM_LFN_DIR/$SIM_OUTPUT_FILE $OUTPUT_DIR/$SIM_OUTPUT_FILE $SE "Failed to upload Simulation output!"
{% endif %}
{% if mctruth_lfn_outputdir %}
stop_on_error dirac-dms-add-file -ddd $MCTRUTH_LFN_DIR/$MCTRUTH_OUTPUT_FILE $OUTPUT_DIR/$MCTRUTH_OUTPUT_FILE $SE "Failed to upload MCTruth output!"
{% endif %}
{% endif %}
{% if reduction_version and reduction_lfn_outputdir %}
stop_on_error dirac-dms-add-file -ddd $REDUCTION_LFN_DIR/$REDUCTION_OUTPUT_FILE $OUTPUT_DIR/$REDUCTION_OUTPUT_FILE $SE "Failed to upload Reduction output!"
{% endif %}
{% if der_version and der_lfn_outputdir %}
stop_on_error dirac-dms-add-file -ddd $DER_LFN_DIR/$DER_OUTPUT_FILE $OUTPUT_DIR/$DER_OUTPUT_FILE $SE "Failed to upload DER output!"
{% endif %}
{% if lzap_version and lzap_lfn_outputdir %}
stop_on_error dirac-dms-add-file -ddd $LZAP_LFN_DIR/$(basename ${LZAP_OUTPUT_FILE}) $LZAP_OUTPUT_FILE $SE "Failed to upload LZap output!"
{% endif %}
