set --
#export GAUDI_HOME_DIR=/cvmfs/lz.opensciencegrid.org/Gaudi/Gaudi/
#export LCG_MOUNT=/cvmfs/sft.cern.ch/lcg/
#export LCG_HOME_DIR=/cvmfs/sft.cern.ch/lcg/releases/LCG_79
#export LZ_BUILD_CONFIG=x86_64-slc6-gcc48-opt

LZAP_PHYSICS_DIR=/cvmfs/lz.opensciencegrid.org/Physics/release-$physics_version
LZAP_DIR=/cvmfs/lz.opensciencegrid.org/LZap/release-$lzap_version

source $LZAP_DIR/LZap/setup.sh
PYTHONPATH=${LZAP_BASE_PYTHONPATH}

$LZAP_PHYSICS_DIR/PhotonDetection/lzap_project

VALIDATIONS_DIR=/cvmfs/lz.opensciencegrid.org/Physics/release-1.0.0/PhotonDetection/scripts/validations

for i in (PulseClassifierValidation PhotonCounterValidation PulseFinderValidation PodCalibratorValidation)
do
  sed "s:^selector\.InputFiles *= *.*$:selector.InputFiles = [$DER_OUTPUT_FILE]:g" <$VALIDATIONS_DIR/$i.py> $i.py
  $LZAP_DIR/scripts/lzap_execute $i.py
  mv $i.root ${i}_10k_DER_pdsf_grid.root
done

# OUTPUT_REDUCED_FILE=${OUTPUT_ROOT_FILE/".root"/"_analysis_tree.root"}


#dirac-dms-add-file $LZAP_PATH/$OUTPUT_LZAP_FILE1 $OUTPUT_DIR/$OUTPUT_LZAP_FILE1 $DATA_STORE_SE
#dirac-dms-add-file $LZAP_PATH/$OUTPUT_LZAP_FILE2 $OUTPUT_DIR/$OUTPUT_LZAP_FILE2 $DATA_STORE_SE
#dirac-dms-add-file $LZAP_PATH/$OUTPUT_LZAP_FILE3 $OUTPUT_DIR/$OUTPUT_LZAP_FILE3 $DATA_STORE_SE
#dirac-dms-add-file $LZAP_PATH/$OUTPUT_LZAP_FILE4 $OUTPUT_DIR/$OUTPUT_LZAP_FILE4 $DATA_STORE_SE
