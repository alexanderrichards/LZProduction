LIBNEST_DIR=/cvmfs/lz.opensciencegrid.org/fastNEST/release-{{ fastnest_version }}
REDUCTION_DIR=/cvmfs/lz.opensciencegrid.org/TDRAnalysis/release-{{ reduction_version }}
REDUCTION_LFN_DIR={{ reduction_lfn_dir }}

# reduce and then copy both to our central storage.
source $LIBNEST_DIR/libNEST/thislibNEST.sh
REDUCTION_OUTPUT_FILE=$(basename $SIM_OUTPUT_FILE .root)_analysis_tree.root


{% if app == 'BACCARAT' %}
export BACC_TOOLS=/cvmfs/lz.opensciencegrid.org/BACCARAT/release-1.0.0/tools
export LD_LIBRARY_PATH=$BACC_TOOLS:$LD_LIBRARY_PATH
$REDUCTION_DIR/ReducedAnalysisTree/Bacc2AnalysisTree $SIM_OUTPUT_FILE $REDUCTION_OUTPUT_FILE
{% else %}
$REDUCTION_DIR/ReducedAnalysisTree/LZSim2AnalysisTree $SIM_OUTPUT_FILE $REDUCTION_OUTPUT_FILE
{% endif %}
ret=$?
if [ $ret -ne 0 ]
then
    echo "Reduction step failed with exit code: $ret" >&2
    exit $ret
fi

dirac-dms-add-file $REDUCTION_LFN_DIR/$REDUCTION_OUTPUT_FILE $OUTPUT_DIR/$REDUCTION_OUTPUT_FILE $SE
