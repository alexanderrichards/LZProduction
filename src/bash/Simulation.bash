#!/bin/bash
#Prepare some variables based on the inputs
MACRO_FILE=$1
export SEED=$2 # an integer that will label the output file
APP_DIR=/cvmfs/lz.opensciencegrid.org/$app/release-$app_version
ROOT_DIR=/cvmfs/lz.opensciencegrid.org/ROOT/v$root_version/$root_arch/root
G4_DIR=/cvmfs/lz.opensciencegrid.org/geant4/
G4_VER=geant$g4_version

#extract the name of the output file from the LUXSim macro
export OUTPUT_DIR=$(pwd)
OUTPUT_FILE=$(awk '/^\/$app\/io\/outputName/ {print $2}' $1 | tail -1)$2.bin
if [ "$app" == "BACCARAT" ]; then
    OUTPUT_FILE=$(awk '/^\/Bacc\/io\/outputName/ {print $2}' $1 | tail -1)$2.bin
fi


# move into the LUXSim directory, set G4 env, and run the macro
# the executable must be run from within it's dir!
cd $APP_DIR
source $G4_DIR/etc/geant4env.sh $G4_VER
$APP_DIR/${app}Executable $OUTPUT_DIR/$MACRO_FILE

cd $OUTPUT_DIR
# after macro has run, rootify
source $ROOT_DIR/bin/thisroot.sh
if [ "$app" == "BACCARAT" ]; then
    $APP_DIR/tools/BaccRootConverter $OUTPUT_FILE
else
    $APP_DIR/tools/LUXRootReader $OUTPUT_FILE
fi
#SIM_OUTPUT_FILE=$(basename $OUTPUT_FILE .bin).root

# get MC truth
#`ls $APP_DIR/tools/*MCTruth` $SIM_OUTPUT_FILE
#MCTRUTH_OUTPUT_FILE=$(ls *_mctruth.root)

## FILE UPLOAD
######################################################################
#DATA_STORE_PATH=/lz/data
#DATA_STORE_SE=UKI-LT2-IC-HEP-disk
#BIGROOT_STORE_PATH=$DATA_STORE_PATH/LUXSim_$(basename $LUXSIM_DIR)_$G4VER/$(basename $MACRO_FILE _parametric.mac)
#dirac-dms-add-file $BIGROOT_STORE_PATH/$OUTPUT_ROOT_FILE $OUTPUT_DIR/$OUTPUT_ROOT_FILE $DATA_STORE_SE
