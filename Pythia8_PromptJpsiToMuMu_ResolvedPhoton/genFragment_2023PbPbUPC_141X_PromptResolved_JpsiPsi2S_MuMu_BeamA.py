import FWCore.ParameterSet.Config as cms
from Configuration.Generator.Pythia8CommonSettings_cfi import *
from GeneratorInterface.EvtGenInterface.EvtGenSetting_cff import *
from Configuration.Generator.Pythia8PhotonFluxSettings_cfi import PhotonFlux_PbPb

generator = cms.EDFilter(
    "Pythia8GeneratorFilter",
    maxEventsToPrint = cms.untracked.int32(1),
    pythiaPylistVerbosity = cms.untracked.int32(1),
    filterEfficiency = cms.untracked.double(1.0),
    pythiaHepMCVerbosity = cms.untracked.bool(False),
    comEnergy = cms.double(5362.),
    PhotonFlux = PhotonFlux_PbPb,
    ExternalDecays = cms.PSet(
        EvtGen130 = cms.untracked.PSet(
            decay_table = cms.string('GeneratorInterface/EvtGenInterface/data/DECAY_2020_NOLONGLIFE.DEC'),
            operates_on_particles = cms.vint32(),
            particle_property_file = cms.FileInPath('GeneratorInterface/EvtGenInterface/data/evt_2020.pdl'),
            user_decay_file = cms.vstring('GeneratorInterface/ExternalDecays/data/Onia_mumu.dec'),
            list_forced_decays = cms.vstring('MyJ/psi'),
            convertPythiaCodes = cms.untracked.bool(False),
        ),
        parameterSets = cms.vstring('EvtGen130')
    ),
    PythiaParameters = cms.PSet(
        pythia8CommonSettingsBlock,
        processParameters = cms.vstring(
            # Set this to 0 for inclusive photons:
            'Photon:ProcessType = 0',
            'Photon:sampleQ2 = off',
            # Have the photon coming from beam A:
            'PDF:beamA2gamma = on',
            'PDF:beamB2gamma = off',
            'PDF:proton2gammaSet = 0',
            'PDF:gammaFluxApprox2bMin = 13.272',
            'PDF:beam2gammaApprox = 2',
            # add nuclear modifications to beam B:
            'PDF:pSetB = LHAPDF6:EPPS21nlo_CT18Anlo_Pb208',
            'MultipartonInteractions:pT0Ref = 3.0',
            # Allow feed-down:
            'Charmonium:all = on'
        ),
        parameterSets = cms.vstring(
            'pythia8CommonSettings',
            'processParameters'
        )
    )
)

generator.PythiaParameters.processParameters.extend(EvtGenExtraParticles)

# Filter on J/psi in event
oniafilter = cms.EDFilter(
    "MCMultiParticleFilter",
    ParticleID = cms.vint32(443),
    Status = cms.vint32(2),
    PtMin = cms.vdouble(0.0),
    PMin = cms.vdouble(0.0),
    EtaMin = cms.vdouble(-9999),
    EtaMax = cms.vdouble(9999),
    NumRequired = cms.int32(1),
    AcceptMore = cms.bool(True)
)

ProductionFilterSequence = cms.Sequence(generator*oniafilter)
