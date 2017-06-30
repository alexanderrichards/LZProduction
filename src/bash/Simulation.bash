#Prepare some variables based on the inputs
MACRO_FILE=$1
export SEED=$2 # an integer that will label the output file
APP_DIR=/cvmfs/lz.opensciencegrid.org/{{ app }}/release-{{ app_version }}
ROOT_DIR=/cvmfs/lz.opensciencegrid.org/ROOT/v{{ root_version }}/{{ root_arch }}/root
G4_DIR=/cvmfs/lz.opensciencegrid.org/geant4/
G4_VER=geant{{ g4_version }}
SIM_LFN_DIR={{ sim_lfn_dir }}
MCTRUTH_LFN_DIR={{ mctruth_lfn_dir }}
SE={{ se }}

#extract the name of the output file from the LUXSim macro
export OUTPUT_DIR=$(pwd)
{% if app == 'BACCARAT' %}
OUTPUT_FILE=$(awk '/^\/Bacc\/io\/outputName/ {print $2}' $1 | tail -1)$2.bin
{% else%}
OUTPUT_FILE=$(awk '/^\/{{ app }}\/io\/outputName/ {print $2}' $1 | tail -1)$2.bin
{% endif %}


# move into the LUXSim directory, set G4 env, and run the macro
# the executable must be run from within it's dir!
cd $APP_DIR
source $G4_DIR/etc/geant4env.sh $G4_VER
$APP_DIR/{{ app }}Executable $OUTPUT_DIR/$MACRO_FILE
ret=$?
if [ $ret -ne 0 ]
then
    echo "Simulation step failed with exit code: $ret" >&2
    exit $ret
fi

cd $OUTPUT_DIR
# after macro has run, rootify
source $ROOT_DIR/bin/thisroot.sh
{% if app == 'BACCARAT' %}
$APP_DIR/tools/BaccRootConverter $OUTPUT_FILE
{% else %}
`ls $APP_DIR/tools/*RootReader` $OUTPUT_FILE
{% endif %}
SIM_OUTPUT_FILE=$(basename $OUTPUT_FILE .bin).root
`ls $APP_DIR/tools/*MCTruth` $SIM_OUTPUT_FILE
ret=$?
if [ $ret -ne 0 ]
then
    echo "MCTruth step failed with exit code: $ret" >&2
    exit $ret
fi
MCTRUTH_OUTPUT_FILE=$(ls *_mctruth.root)

# get MC truth
#`ls $APP_DIR/tools/*MCTruth` $SIM_OUTPUT_FILE
#MCTRUTH_OUTPUT_FILE=$(ls *_mctruth.root)

#dirac-dms-add-file $SIM_LFN_DIR/$SIM_OUTPUT_FILE $OUTPUT_DIR/$SIM_OUTPUT_FILE $SE
ls -l *.root
dirac-dms-add-file -ddd $MCTRUTH_LFN_DIR/$MCTRUTH_OUTPUT_FILE $OUTPUT_DIR/$MCTRUTH_OUTPUT_FILE $SE
