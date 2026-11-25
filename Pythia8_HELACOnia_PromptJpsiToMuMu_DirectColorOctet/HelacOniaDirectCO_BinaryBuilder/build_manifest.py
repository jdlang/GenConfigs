#!/usr/bin/env python3
"""Record the independently built CO runtime and exact source patch."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    root = Path(sys.argv[1]).resolve()
    source = Path(__file__).resolve().parent
    binary = root / 'bin/Helac-Onia'
    expected = {
        'src/SinglePro.f90': 'xwgtup=MAX(1d0,w1/umax)',
        'src/unweight_lhe.f90': '5200 FORMAT(1P,2I6,E25.17,3E14.6)'
    }
    for name, marker in expected.items():
        if (root / name).read_text().count(marker) != 1:
            raise ValueError('CO weight patch missing: ' + name)
    symbols = subprocess.check_output(['nm', str(binary)], universal_newlines=True)
    if '__wrap___photon_pdfs_MOD_epa_ion' not in symbols:
        raise ValueError('Missing CMS photon flux extension')
    report = dict(
        schema='helac-co-runtime-v1',
        helac_version='2.7.6',
        source_archive_sha256='8386bcdf0316845345f59e2a5d5983c54893461541d7f59c632ae817fccb678a',
        cmssw='CMSSW_14_1_9_patch3',
        scram_arch='el8_amd64_gcc12',
        seed_mapping='IJKL=54217137+10*seed',
        weight_contract='residual=max(1,w/umax); preserve positive rejection weights',
        binary_sha256=sha(binary),
        patched_source_sha256={name: sha(root / name) for name in expected},
        build_script_sha256=sha(source / 'build_helaconia.sh'),
        flux_extension_sha256=sha(source / 'cms_pb_flux_extension.f90'))
    (root / 'build_manifest.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
