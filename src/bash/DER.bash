DER_DIR=/cvmfs/lz.opensciencegrid.org/DER/release-{{ der_version }}
DER_LFN_DIR={{ der_lfn_dir }}

i_job=$((SEED-{{ seed0 }}))
livetimeperjob={{ livetimeperjob }}
DT=$(awk "BEGIN {print $i_job*$livetimeperjob+0.5; exit}")
let DDT=`echo $DT | cut -d. -f 1`
UNIXTIME=$(({{ unixtime }}+DDT))

cd $DER_DIR
source $DER_DIR/DERenv.sh
#time $DER_DIR/DER  --fileSeqNum DER --UserCheck false --SkipLargeDeltaT true --outDir ${OUTPUT_DIR}/ ${OUTPUT_DIR}/${MCTRUTH_OUTPUT_FILE}
$DER_DIR/DER --UserCheck false --SkipLargeDeltaT true --FileTimeStamp ${UNIXTIME} --fileSeqNum ${i_job} --SignalChain SAMPLED --outDir ${OUTPUT_DIR}/ ${OUTPUT_DIR}/${MCTRUTH_OUTPUT_FILE}
if [ $? -ne 0 ]
then
    echo "DER step failed with exit code: $?" >&2
    exit $?
fi
cd $OUTPUT_DIR
DER_OUTPUT_FILE=$(ls *_raw.root)
#DER_OUTPUT_FILE=$(basename $MCTRUTH_OUTPUT_FILE ._mctruth.root)_der.root
#mv $(ls lz_*DER*.root) $DER_OUTPUT_FILE

dirac-dms-add-file $DER_LFN_DIR/$DER_OUTPUT_FILE $OUTPUT_DIR/$DER_OUTPUT_FILE $SE
