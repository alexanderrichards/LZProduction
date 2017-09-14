{% if not app_version %}
MCTRUTH_OUTPUT_FILE=$1
{% endif %}
DER_DIR=/cvmfs/lz.opensciencegrid.org/DER/release-{{ der_version }}
DER_LFN_DIR={{ der_lfn_outputdir }}


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
