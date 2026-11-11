# HELAC-Onia 2.7.6 + Pythia 8.311 + EventGen 1.30
# Direct-Photon Color Octet (DirectCO), Pompt J/psi->mumu

import FWCore.ParameterSet.Config as cms

from Configuration.Generator.Pythia8CommonSettings_cfi import pythia8CommonSettingsBlock
from Configuration.Generator.Pythia8PhotonFluxSettings_cfi import PhotonFlux_PbPb
from GeneratorInterface.EvtGenInterface.EvtGenSetting_cff import EvtGenExtraParticles
#from GeneratorInterface.LHEInterface.ExternalLHEProducer_cfi import externalLHEProducer

# HELAC-Onia supplies gamma(+z) g(-z) -> ccbar[3S1(8)] g via LHE file.
# Outgoing LHE octet is mapped to PYTHIA 8 ID 9941003 by `prepare_lhe.py`.
# LHE sets the photon flux, target PDF, hard-process cuts and normalization.
externalLHEProducer = cms.EDProducer(
    "ExternalLHEProducer",
#    FIXME: For official MC we need the gridpack hosted on this cvmfs path:
#    "/cvmfs/cms.cern.ch/phys_generator/gridpacks/RunIII/5p36TeV/..."
    args = cms.vstring(
        "root://xrootd-vanderbilt.sites.opensciencegrid.org//store/user/jdlang/CMSSW_MC_Gridpacks/helaconia_directCO_jpsi_dimuon_beamA_el8_amd64_gcc12_CMSSW_14_1_9_patch3_tarball.tar.gz"
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

# Hadronization and decay is handled by Pythia + EvtGen (forcing J/psi->mumu)
generator = cms.EDFilter(
    "Pythia8HadronizerFilter",
    maxEventsToPrint = cms.untracked.int32(1),
    pythiaPylistVerbosity = cms.untracked.int32(1),
    filterEfficiency = cms.untracked.double(1.0),
    pythiaHepMCVerbosity = cms.untracked.bool(False),
    comEnergy = cms.double(5362.),
    nAttempts=cms.uint32(1),
    PhotonFlux = PhotonFlux_PbPb, # Requires Pythia8ExternalPhoton_141X compatibility patch
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
            # Retain the existing target shower PDF and UPC shower settings.
            # The LHE hard cross section must use the same target nPDF choice.
            'PDF:pSetB = LHAPDF6:EPPS21nlo_CT18Anlo_Pb208',
            'MultipartonInteractions:pT0Ref = 3.0',
            'PDF:beam2gammaApprox = 2',
            'PDF:gammaFluxApprox2bMin = 13.272',
            # These last two settings control a sampling approximation, not
            # the physical flux. The LHE must already contain the original
            # Nucleus2gamma2 Pb flux: Z=82, R=6.636 fm, bmin=2R.
            # The compatibility patch installs PhotonFlux_PbPb for external
            # partons too. Pythia does not reweight the LHE hard cross section.
        ),
        parameterSets=cms.vstring(
            'pythia8CommonSettings',
            'processParameters'
        ),
    ),
)
generator.PythiaParameters.processParameters.extend(EvtGenExtraParticles)

# Experimental octet transition settings; the paper does not specify these switches.
# EvtGen handles the physical J/psi decay. No H1 tune or event reweight is applied.
generator.PythiaParameters.processParameters.extend(cms.vstring(
    "PartonLevel:MPI = off",
    "OniaShower:all = off",
    "CharmoniumShower:all = off",
    "BottomoniumShower:all = off",
    "OniaShower:octetSplit = 1",
    "Onia:forceMassSplit = off",
    "Onia:massSplit = 0.1031",
    "443:m0 = 3.0969",
    "443:mWidth = 0",
    "443:mMin = 3.0969",
    "443:mMax = 3.0969",
    "9941003:m0 = 3.2",
    "9941003:mWidth = 0",
    "9941003:mMin = 3.2",
    "9941003:mMax = 3.2",
    "9941003:oneChannel = 1 1.0 0 443 21",
    "9941003:mayDecay = on",
))

# Keep every successfully showered event; acceptance cuts belong in the analysis.
ProductionFilterSequence = cms.Sequence(generator)
