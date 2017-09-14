{% if not app_version %}
SIM_OUTPUT_FILE=$1
{% endif %}
LIBNEST_DIR=/cvmfs/lz.opensciencegrid.org/fastNEST/release-{{ fastnest_version }}
REDUCTION_DIR=/cvmfs/lz.opensciencegrid.org/TDRAnalysis/release-{{ reduction_version }}
REDUCTION_LFN_DIR={{ reduction_lfn_outputdir }}

source $LIBNEST_DIR/libNEST/thislibNEST.sh
REDUCTION_OUTPUT_FILE=$(basename $SIM_OUTPUT_FILE .root)_analysis_tree.root

{% if app == 'BACCARAT' %}
export BACC_TOOLS=$APP_DIR/tools
export LD_LIBRARY_PATH=$APP_DIR/lib:$LD_LIBRARY_PATH
stop_on_error $REDUCTION_DIR/ReducedAnalysisTree/Bacc2AnalysisTree $SIM_OUTPUT_FILE $REDUCTION_OUTPUT_FILE "Reduction step failed!"
{% else %}
stop_on_error $REDUCTION_DIR/ReducedAnalysisTree/LZSim2AnalysisTree $SIM_OUTPUT_FILE $REDUCTION_OUTPUT_FILE "Reduction step failed!"
{% endif %}
