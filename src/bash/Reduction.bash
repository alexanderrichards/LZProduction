LIBNEST_DIR=/cvmfs/lz.opensciencegrid.org/fastNEST/release-$libnest_version
REDUCTION_DIR=/cvmfs/lz.opensciencegrid.org/TDRAnalysis/release-$reduction_version

# reduce and then copy both to our central storage.
source $LIBNEST_DIR/libNEST/thislibNEST.sh
REDUCTION_OUTPUT_FILE=$(basename $SIM_OUTPUT_FILE .root)_analysis_tree.root
$REDUCTION_DIR/ReducedAnalysisTree/LZSim2AnalysisTree $SIM_OUTPUT_FILE $REDUCTION_OUTPUT_FILE

## FILE UPLOAD
######################################################################
#REDUCED_STORE_PATH=$DATA_STORE_PATH/LUXSim_$(basename $LUXSIM_DIR)_$G4VER/reduced_v$reduction_version/$(basename $MACRO_FILE _parametric.mac)
#dirac-dms-add-file $REDUCED_STORE_PATH/$OUTPUT_REDUCED_FILE $OUTPUT_DIR/$OUTPUT_REDUCED_FILE $DATA_STORE_SE
