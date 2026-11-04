import FWCore.ParameterSet.Config as cms

from Configuration.Generator.Pythia8CommonSettings_cfi import pythia8CommonSettingsBlock
from Configuration.Generator.Pythia8PhotonFluxSettings_cfi import PhotonFlux_PbPb
from GeneratorInterface.EvtGenInterface.EvtGenSetting_cff import EvtGenExtraParticles
from GeneratorInterface.LHEInterface.ExternalLHEProducer_cfi import externalLHEProducer

externalLHEProducer = cms.EDProducer(
    "ExternalLHEProducer",
#    # FIXME: For official MC we need the gridpack hosted in this cvmfs path:
#    args = cms.vstring(
#        "/cvmfs/cms.cern.ch/phys_generator/gridpacks/RunIII/5p36TeV/..."
#    ),
#    scriptName = cms.FileInPath(
#        'GeneratorInterface/LHEInterface/data/run_generic_tarball_cvmfs.sh'
#    ),
    # Temp settings for private MC - gridpack accessed through xrootd path:
    args = cms.vstring(
        "root://xrootd-vanderbilt.sites.opensciencegrid.org//store/user/jdlang/CMSSW_MC_Gridpacks/helaconia_directCS_jpsi_dimuon_el9_amd64_gcc12_CMSSW_14_1_9_patch3_tarball.tar.gz"
    ),
    scriptName = cms.FileInPath(
        'GeneratorInterface/LHEInterface/data/run_generic_tarball_xrootd.sh'
    ),
    outputFile = cms.string('cmsgrid_final.lhe'),
    numberOfParameters = cms.uint32(1),
    nEvents = cms.untracked.uint32(1),
    generateConcurrently = cms.untracked.bool(True), # Should this be false or true?
    storeXML = cms.untracked.bool(False),
)

generator = cms.EDFilter(
    "Pythia8HadronizerFilter",
    maxEventsToPrint = cms.untracked.int32(1),
    pythiaPylistVerbosity = cms.untracked.int32(1),
    filterEfficiency = cms.untracked.double(1.0),
    pythiaHepMCVerbosity = cms.untracked.bool(False),
    comEnergy = cms.double(5362.),
    PhotonFlux = PhotonFlux_PbPb,
    ExternalDecays=cms.PSet(
        EvtGen130 = cms.untracked.PSet(
            decay_table = cms.string('GeneratorInterface/EvtGenInterface/data/DECAY_2020_NOLONGLIFE.DEC'),
            operates_on_particles = cms.vint32(),
            particle_property_file = cms.FileInPath('GeneratorInterface/EvtGenInterface/data/evt_2020.pdl'),
            user_decay_file = cms.vstring('GeneratorInterface/ExternalDecays/data/Onia_mumu.dec'),
            list_forced_decays = cms.vstring('MyJ/psi'),
            convertPythiaCodes = cms.untracked.bool(False),
        ),
        parameterSets=cms.vstring('EvtGen130'),
    ),
    # Requires the supplied Pythia8ExternalPhoton_141X compatibility patch.
    PythiaParameters=cms.PSet(
        pythia8CommonSettingsBlock,
        processParameters=cms.vstring(
            # CMSSW supplies the LHAup interface; do not set Beams:LHEF here.
            'PartonLevel:all = on',
            'Photon:ProcessType = 3',
            'Photon:sampleQ2 = off',
            'PDF:beamA2gamma = on',
            'PDF:beamB2gamma = off',
            'PDF:proton2gammaSet = 0',
            'PDF:pSetB = LHAPDF6:EPPS21nlo_CT18Anlo_Pb208',
            'MultipartonInteractions:pT0Ref = 3.0',
            'PDF:beam2gammaApprox = 2',
            'PDF:gammaFluxApprox2bMin = 13.272',
            'Photon:sampleQ2 = off',
        ),
        parameterSets=cms.vstring(
            'pythia8CommonSettings',
            'processParameters'
        ),
    ),
)
generator.PythiaParameters.processParameters.extend(EvtGenExtraParticles)

ProductionFilterSequence = cms.Sequence(generator)
