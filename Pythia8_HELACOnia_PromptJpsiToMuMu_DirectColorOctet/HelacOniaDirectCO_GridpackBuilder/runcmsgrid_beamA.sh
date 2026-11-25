#!/bin/bash

fail_exit() { echo "$@"; exit 1; }
digest() { sha256sum "$1" | awk '{print $1}'; }

echo "   ______________________________________     "
echo "            Running HELAC-Onia                "
echo "   ______________________________________     "

# Take in standard parameters from the CMSSW LHE script.
# DO NOT CHANGE THESE! These are defaults for CMSSW LHE handlers:

nevt=${1}
echo "%MSG-HELAC-Onia number of events requested = $nevt"

rnum=${2}
echo "%MSG-HELAC-Onia random seed used for the run = $rnum"

ncpu=${3}
echo "%MSG-HELAC-Onia number of cpus for the run = $ncpu"

use_gridpack_env=true
if [ "$4" = false ]; then
    use_gridpack_env=$4
fi

lhe_main_dir=`pwd -P`
helaconia_runtime="${lhe_main_dir}/runtime"
work_dir="${lhe_main_dir}/workdir"

# Note: This block is modified from the original runcmsgrid.sh template.
if [ "$use_gridpack_env" = true ]; then
    if [[ "$5" == *[_]* ]]; then
        scram_arch_version=${5}
    else
        scram_arch_version=el8_amd64_gcc12
    fi
    echo "%MSG-HELAC-Onia SCRAM_ARCH version = $scram_arch_version"

    if [[ "$6" == CMSSW_* ]]; then
        cmssw_version=${6}
    else
        cmssw_version=CMSSW_14_1_9_patch3
    fi
    echo "%MSG-HELAC-Onia CMSSW version = $cmssw_version"

    export VO_CMS_SW_DIR=/cvmfs/cms.cern.ch
    source $VO_CMS_SW_DIR/cmsset_default.sh

    eval `scramv1 unsetenv -sh`
    export SCRAM_ARCH=${scram_arch_version}
    scramv1 project CMSSW ${cmssw_version}
    cd ${cmssw_version}/src
    # Add patches to CMSSW and rebuild:
    cp -rf ${lhe_main_dir}/GeneratorInterface/ .
    eval `scramv1 runtime -sh`
    wait
fi

echo "*** STARTING HELAC-ONIA PRODUCTION ***"
cd ${lhe_main_dir}

# Set the generation parameters before running:
unwevt=$nevt
nmc=$((nevt * 500 + 30000)) # 5x more than needed per event, plus warmup
seed=$rnum
sed -i -r "s|unwevt\s+[0-9]*|unwevt $unwevt|" ${helaconia_runtime}/input/user.inp
sed -i -r "s|nmc\s+[0-9]*|nmc $nmc|" ${helaconia_runtime}/input/user.inp

echo "$seed" > ${helaconia_runtime}/input/seed.input
wait

# Make necessary directories:
[[ -d "$work_dir" ]] && rm -rf $work_dir
mkdir -p $work_dir
mkdir -p "${work_dir}/output"
mkdir -p "${work_dir}/tmp"
mkdir -p "${work_dir}/input/paths"
cp -r ${helaconia_runtime}/input ${work_dir}/
wait

# Build simlinks to runtime directory:
[[ -d "${helaconia_runtime}/pdf" ]] && ln -s "${helaconia_runtime}/pdf" "${work_dir}/pdf"
[[ -d "${helaconia_runtime}/lib" ]] && ln -s "${helaconia_runtime}/lib" "${work_dir}/lib"
[[ -d "${helaconia_runtime}/nuclear" ]] && ln -s "${helaconia_runtime}/nuclear" "${work_dir}/nuclear"

echo $(lhapdf-config --datadir) > "${work_dir}/input/paths/lhapdf_data"

# Run HELAC-Onia:
cd $work_dir
${helaconia_runtime}/bin/Helac-Onia 1> helaconia.log 2>&1
run_status=$?
wait

# Preserve original diagnostics into the job log before cleanup:
[[ -f "${work_dir}/helaconia.log" ]] && cat ${work_dir}/helaconia.log;

# Check that Helac-Onia ran without errors:
if [[ $run_status -ne 0 ]]; then
    echo "[ERROR] Helac-Onia failed with error code $run_status!"
    echo "Rejecting this run. Inspect helaconia.log"
    exit 10
fi

# Check that there is only one output .lhe file:
lhe_files=( $(ls ${work_dir}/output/*.lhe) )
if [[ ${#lhe_files[@]} -ne 1 ]]; then
    echo "[ERROR] Multiple LHE files found in output directory!"
    echo "Rejecting this run. Inspect helaconia.log"
    exit 11
fi
raw_lhe=${lhe_files[0]}

# Run the validator script to check that the output is good:
python3 "$lhe_main_dir/validate_ho_output.py" \
    --runtime "$helaconia_runtime" \
    --work-dir "$work_dir" \
    --raw-lhe "$raw_lhe" \
    --model "CO" \
    --events "$unwevt" \
    --seed "$seed"
validation_status=$?
wait

if [[ $validation_status -ne 0 ]]; then
    echo "[ERROR] Validation of HELAC-Onia output failed with code $validation_status!"
    echo "Rejecting this run. Inspect helaconia.log"
    exit $validation_status
fi

cd $lhe_main_dir
cp ${work_dir}/cmsgrid_final.lhe cmsgrid_final.lhe
cp ${work_dir}/generation.json generation.json

echo "***HELAC-ONIA COMPLETE***"

echo "Output ready: $(ls cmsgrid_final.lhe)"
echo "End of job on "`date`
exit 0
