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
{% if simulation %}
## Simulation variables
####################
MACRO_FILE=$1
export SEED=$2 # an integer that will label the output file
APP_DIR=/cvmfs/lz.opensciencegrid.org/{{ app }}/release-{{ app_version }}
ROOT_DIR=/cvmfs/lz.opensciencegrid.org/ROOT/v{{ root_version }}/{{ root_arch }}/root
G4_DIR=/cvmfs/lz.opensciencegrid.org/geant4/
G4_VER=geant{{ g4_version }}
SIM_LFN_DIR={{ sim_lfn_dir }}
MCTRUTH_LFN_DIR={{ mctruth_lfn_dir }}
SE={{ se }}
{% endif %}
{% if reduction %}
## Reduction variables
####################
LIBNEST_DIR=/cvmfs/lz.opensciencegrid.org/fastNEST/release-{{ fastnest_version }}
REDUCTION_DIR=/cvmfs/lz.opensciencegrid.org/TDRAnalysis/release-{{ reduction_version }}
REDUCTION_LFN_DIR={{ reduction_lfn_dir }}
{% endif %}
{% if der %}
## DER variables
####################
DER_DIR=/cvmfs/lz.opensciencegrid.org/DER/release-{{ der_version }}
DER_LFN_DIR={{ der_lfn_dir }}
{% endif %}


{% if simulation %}
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
source $G4_DIR/etc/geant4env.sh $G4_VER
stop_on_error $APP_DIR/{{ app }}Executable $OUTPUT_DIR/$MACRO_FILE "Simulation step failed!"

cd $OUTPUT_DIR
# after macro has run, rootify
source $ROOT_DIR/bin/thisroot.sh
{% if app == 'BACCARAT' %}
$APP_DIR/tools/BaccRootConverter $OUTPUT_FILE
{% else %}
`ls $APP_DIR/tools/*RootReader` $OUTPUT_FILE
{% endif %}
SIM_OUTPUT_FILE=$(basename $OUTPUT_FILE .bin).root

stop_on_error `ls $APP_DIR/tools/*MCTruth` $SIM_OUTPUT_FILE "MCTruth step failed!"
MCTRUTH_OUTPUT_FILE=$(ls *_mctruth.root)
{% endif %}
{% if reduction %}
## Reduction
####################
# reduce and then copy both to our central storage.
source $LIBNEST_DIR/libNEST/thislibNEST.sh
REDUCTION_OUTPUT_FILE=$(basename $SIM_OUTPUT_FILE .root)_analysis_tree.root

{% if app == 'BACCARAT' %}
export BACC_TOOLS=/cvmfs/lz.opensciencegrid.org/BACCARAT/release-1.0.0/tools
export LD_LIBRARY_PATH=$BACC_TOOLS:$LD_LIBRARY_PATH
stop_on_error $REDUCTION_DIR/ReducedAnalysisTree/Bacc2AnalysisTree $SIM_OUTPUT_FILE $REDUCTION_OUTPUT_FILE "Reduction step failed!"
{% else %}
stop_on_error $REDUCTION_DIR/ReducedAnalysisTree/LZSim2AnalysisTree $SIM_OUTPUT_FILE $REDUCTION_OUTPUT_FILE "Reduction step failed!"
{% endif %}
{% endif %}
{% if der %}
## DER
####################
i_job=$((SEED-{{ seed0 }}))
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

## Upload
###########################
ls -l *.root
{% if simulation %}
#stop_on_error dirac-dms-add-file -ddd $SIM_LFN_DIR/$SIM_OUTPUT_FILE $OUTPUT_DIR/$SIM_OUTPUT_FILE $SE "Failed to upload Simulation output!"
stop_on_error dirac-dms-add-file -ddd $MCTRUTH_LFN_DIR/$MCTRUTH_OUTPUT_FILE $OUTPUT_DIR/$MCTRUTH_OUTPUT_FILE $SE "Failed to upload MCTruth output!"
{% endif %}
{% if reduction %}
stop_on_error dirac-dms-add-file -ddd $REDUCTION_LFN_DIR/$REDUCTION_OUTPUT_FILE $OUTPUT_DIR/$REDUCTION_OUTPUT_FILE $SE "Failed to upload Reduction output!"
{% endif %}
{% if der %}
stop_on_error dirac-dms-add-file -ddd $DER_LFN_DIR/$DER_OUTPUT_FILE $OUTPUT_DIR/$DER_OUTPUT_FILE $SE "Failed to upload DER output!"
{% endif %}
