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
