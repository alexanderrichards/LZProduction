DER_DIR=/cvmfs/lz.opensciencegrid.org/DER/release-{{ der_version }}
DER_LFN_DIR={{ der_lfn_dir }}

cd $DER_DIR
source $DER_DIR/DERenv.sh
time $DER_DIR/DER  --fileSeqNum DER --UserCheck false --SkipLargeDeltaT true --outDir ${OUTPUT_DIR}/ ${OUTPUT_DIR}/${MCTRUTH_OUTPUT_FILE}

cd $OUTPUT_DIR
DER_OUTPUT_FILE=$(basename $MCTRUTH_OUTPUT_FILE ._mctruth.root)_der.root
mv $(ls lz_*DER*.root) $DER_OUTPUT_FILE

dirac-dms-add-file $DER_LFN_DIR/$DER_OUTPUT_FILE $OUTPUT_DIR/$DER_OUTPUT_FILE $SE
