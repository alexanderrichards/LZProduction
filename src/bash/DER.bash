#!/bin/bash
#Prepare some variables based on the inputs
MACRO_FILE=$1
export SEED=$2 # an integer that will label the output file
LUXSIM_DIR=/cvmfs/lz.opensciencegrid.org/LUXSim/release-4.4.6/
ROOT_DIR=/cvmfs/lz.opensciencegrid.org/ROOT/v5.34.32/slc6_gcc44_x86_64/root/
G4_DIR=/cvmfs/lz.opensciencegrid.org/geant4/
G4VER=geant4.9.5.p02

DER_DIR=/cvmfs/lz.opensciencegrid.org/DER/release-$der_version

source $DER_DIR/DERenv.sh
$DER_DIR/DER  --SignalChain TPC --fileSeqNum DER --outDir ${PWD} ${MCTRUTH_OUTPUT_FILE}

DER_OUTPUT_FILE=$(basename $SIM_OUTPUT_FILE .root)_DER.root
mv $(ls lz_2016*.root) $DER_OUTPUT_FILE


#####OUTPUT UPLOADING
#############################################################
#DATA_STORE_PATH=/lz/data
#DATA_STORE_SE=UKI-LT2-IC-HEP-disk
#BIGROOT_STORE_PATH=$DATA_STORE_PATH/LUXSim_$(basename $LUXSIM_DIR)_$G4VER/$(basename $MACRO_FILE _parametric.mac)
#MCTRUTH_PATH=$DATA_STORE_PATH/LUXSim_$(basename $LUXSIM_DIR)_$G4VER//MC_TRUTH/$(basename $MACRO_FILE _parametric.mac)
#DER_PATH=$DATA_STORE_PATH/LUXSim_$(basename $LUXSIM_DIR)_$G4VER/DER_$der_version/$(basename $MACRO_FILE _parametric.mac)

# OUTPUT_REDUCED_FILE=${OUTPUT_ROOT_FILE/".root"/"_analysis_tree.root"}
#dirac-dms-add-file $BIGROOT_STORE_PATH/$OUTPUT_MCTRUTH_FILE $OUTPUT_DIR/$OUTPUT_MCTRUTH_FILE $DATA_STORE_SE
#dirac-dms-add-file $MCTRUTH_PATH/$OUTPUT_MCTRUTH_FILE  $OUTPUT_DIR/$OUTPUT_MCTRUTH_FILE $DATA_STORE_SE
#dirac-dms-add-file $DER_PATH/$OUTPUT_DER_FILE $OUTPUT_DIR/$OUTPUT_DER_FILE $DATA_STORE_SE
