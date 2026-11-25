#!/usr/bin/env python3
"""Record the independently built CS runtime and exact source patch."""
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
    symbols = subprocess.check_output(['nm', str(binary)], universal_newlines=True)
    if '__wrap___photon_pdfs_MOD_epa_ion' not in symbols:
        raise ValueError('Missing CMS photon flux extension')
    report = dict(
        schema='helac-cs-runtime-v1',
        helac_version='2.7.6',
        source_archive_sha256='8386bcdf0316845345f59e2a5d5983c54893461541d7f59c632ae817fccb678a',
        cmssw='CMSSW_14_1_9_patch3',
        scram_arch='el8_amd64_gcc12',
        seed_mapping='IJKL=54217137+10*seed',
        weight_contract='unweighted',
        inary_sha256=sha(binary),
        uild_script_sha256=sha(source / 'build_helaconia.sh'),
        lux_extension_sha256=sha(source / 'cms_pb_flux_extension.f90')
    )
    (root / 'build_manifest.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
