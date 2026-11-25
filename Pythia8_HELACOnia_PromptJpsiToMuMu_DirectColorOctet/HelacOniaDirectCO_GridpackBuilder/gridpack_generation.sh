#!/bin/sh
# Gridpack for HELAC-Onia: Color OCTET

fail_exit() { echo "$@"; exit 1; }

#Set main directory
PARENT_DIR=`pwd`
if [[ ! -f "${PARENT_DIR}/gridpack_generation.sh" ]] ; then
    echo "Cannot locate gridpack_generation.sh in current path"
    exit 1
fi

PREP_DIR="${PARENT_DIR}/tarball_prep"
HELACONIA="HELAC-Onia-2.7.6"
HELACONIA_BINARY_DIR="${PARENT_DIR}/../HelacOniaDirectCO_BinaryBuilder/helaconia_build/$HELACONIA"
HELACONIA_MODS_DIR="${PARENT_DIR}/helaconia_mods"
GRIDPACK_COMMON_DIR="${PARENT_DIR}/../Gridpack_Common"


create_setup(){
    echo "Using scram_arch: ${SCRAM_ARCH}"
    echo "Using cmssw_version: ${CMSSW_VERSION}"
    
    [[ -d "${PREP_DIR}" ]] && rm -rf ${PREP_DIR}
    mkdir -p ${PREP_DIR} && cd ${PREP_DIR}

    #Set up environment and working directory 
    export VO_CMS_SW_DIR=/cvmfs/cms.cern.ch
    source ${VO_CMS_SW_DIR}/cmsset_default.sh
    scram project -n ${CMSSW_VERSION} CMSSW ${CMSSW_VERSION} 
    cd ${CMSSW_VERSION} && mkdir -p work && cd work
    eval `scram runtime -sh`
    WORK_DIR=`pwd -P`
}

copy_helaconia(){
    cd ${PARENT_DIR}
    
    if [[ ! -e "${HELACONIA_BINARY_DIR}/bin/Helac-Onia" ]]; then
        echo "[ERROR] Could not find Helac-Onia binary!"
        echo "Build from HelacOniaDirectCO_BinaryBuilder first, then rerun gridpack_generation.sh"
        exit 2
    fi
    
    cd ${WORK_DIR}
    
    echo "Copying compiled binary to ${WORK_DIR}"
    mkdir -p runtime/bin/
    mkdir -p runtime/input/
    wait
    cp -f  ${HELACONIA_BINARY_DIR}/bin/Helac-Onia       runtime/bin/
    cp -f  ${HELACONIA_BINARY_DIR}/build_manifest.json  runtime/
    cp -f  ${HELACONIA_BINARY_DIR}/input/*.inp          runtime/input/
    cp -rf ${HELACONIA_BINARY_DIR}/input/lhapdf         runtime/input/
    cp -rf ${HELACONIA_BINARY_DIR}/pdf                  runtime/
    cp -rf ${HELACONIA_BINARY_DIR}/nuclear              runtime/
    wait
    
    echo "Copying modifications and run scripts to ${WORK_DIR}"
    # Copy the common gridpack scripts:
    cp -rf ${GRIDPACK_COMMON_DIR}/GeneratorInterface    .
    cp -f  ${GRIDPACK_COMMON_DIR}/validate_ho_output.py .
    chmod 755 validate_ho_output.py
    wait
    # Copy from CS gridpack builder:
    cp -f  ${PARENT_DIR}/input/decay_user.inp           runtime/input/
    cp -f  ${PARENT_DIR}/input/process.inp              runtime/input/
    cp -f  ${PARENT_DIR}/input/user.inp                 runtime/input/
    cp -f  ${PARENT_DIR}/runcmsgrid_${PHOTON_SIDE}.sh   ./runcmsgrid.sh
    chmod 755 runcmsgrid.sh
    wait
    
    echo "Copied to working directory!"
}

make_tarball(){
    # Set tarball name:
    prefix="directCO_jpsi_dimuon_$PHOTON_SIDE"
    TARBALL=helaconia_${prefix}_${SCRAM_ARCH}_${CMSSW_VERSION}_tarball.tar.gz
    
    echo "Creating tarball"
    cd ${WORK_DIR}
    tar -czf ${TARBALL} ./*
    wait
    
    sleep 1
    rm ${PARENT_DIR}/$TARBALL
    wait
    mv ${WORK_DIR}/${TARBALL} ${PARENT_DIR}/
    wait
    echo "Tarball created successfully at ${PARENT_DIR}/${TARBALL}"
}

copy_tarball_xrootd(){
#    xrdcp --force --cksum auto ${PARENT_DIR}/${TARBALL} root://xrootd-vanderbilt.sites.opensciencegrid.org//store/user/jdlang/CMSSW_MC_Gridpacks/${TARBALL}

    xrdcp --force --cksum auto ${PARENT_DIR}/${TARBALL} root://eoscms.cern.ch//store/group/phys_heavyions/jdlang/gridpacks/${TARBALL}
    wait
}

#Set photon direction:
DIRECTION=${1}
if [[ ${DIRECTION,,} == "beama" ]]; then
    PHOTON_SIDE="beamA"
    echo "Using configs for photon from Beam A"
elif [[ ${DIRECTION,,} == "beamb" ]]; then
    PHOTON_SIDE="beamB"
    echo "Using configs for photon from Beam B"
else
    echo "Run this script with the following arguments:"
    echo "bash gridpack_generation.sh <direction>"
    echo "<direction> = BeamA, BeamB"
    exit 1
fi

#Set scram_arch
if [ -n "$2" ]; then
    SCRAM_ARCH=${2}
else
    # sync default cmssw with the current OS
    export SYSTEM_RELEASE=`cat /etc/redhat-release`
    if [[ $SYSTEM_RELEASE == *"release 8"* ]]; then
        SCRAM_ARCH=el8_amd64_gcc12
#    elif [[ $SYSTEM_RELEASE == *"release 9"* ]]; then
#        SCRAM_ARCH=el9_amd64_gcc12
    else
        echo "No default scram_arch for current OS"
        exit 1
    fi
fi
export SCRAM_ARCH=${SCRAM_ARCH}

#Set cmssw
if [ -n "$3" ]; then
    CMSSW_VERSION=${3}
else
    if [[ $SYSTEM_RELEASE == *"release 8"* ]]; then
        CMSSW_VERSION=CMSSW_14_1_9_patch3
#    elif [[ $SYSTEM_RELEASE == *"release 9"* ]]; then
#        CMSSW_VERSION=CMSSW_14_1_9_patch3
    else
        echo "No default CMSSW for current OS"
        exit 1
    fi
fi
export CMSSW_VERSION=${CMSSW_VERSION}

#Create set up
create_setup

#Setup helaconia
copy_helaconia

#Create tarball
make_tarball

#Copy the tarball to xrootd location
copy_tarball_xrootd

#Clean up
sleep 1
echo "Removing "${PREP_DIR}
rm -rf ${PREP_DIR}
wait

echo "End of job on " `date`
exit 0
