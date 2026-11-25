#!/usr/bin/env bash
set -euo pipefail

arg1=${1:-"helaconia_build"}
arg2=${2:-"HELAC-Onia-2.7.6.tar.gz"}

build_dir=$(realpath -m -- "$arg1")
helaconia_tarball=$(realpath -m -- "$arg2")
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source_root=$(cd "$script_dir/.." && pwd)

echo $build_dir
echo $helaconia_tarball

# Validate that the architecture and CMSSW version are correct:
if [[ $arg1 == --help ]]; then
    echo "Usage: build_helac.sh <new_build_dir> [HELAC-Onia-2.7.6.tar.gz]"
    exit 2
fi
if [[ ${CMSSW_VERSION:-} != CMSSW_14_1_9_patch3 || ${SCRAM_ARCH:-} != el8_amd64_gcc12 ]]; then
    echo "Activate CMSSW_14_1_9_patch3 with el8_amd64_gcc12 architecture first." >&2
    exit 1
fi

# Validate the build directory:
if [[ -e $build_dir ]]; then
    echo "Build directory must be new." >&2
    exit 1
elif [[ $build_dir == *[[:space:]]* ]]; then
    echo "Upstream HELAC makefiles need a path without whitespace." >&2
    exit 1
fi

# If the HELAC-Onia 2.7.6 tarball is not already downloaded, download it:
mkdir -p "$build_dir"
archive=$build_dir/HELAC-Onia-2.7.6.tar.gz
if [[ $arg2 == *.tar.gz ]]; then
    cp -- "$arg2" "$archive"
    wait
else
    curl --fail --location --retry 3 --connect-timeout 30 \
        https://www.lpthe.jussieu.fr/~hshao/download/HELAC-Onia-2.7.6.tar.gz -o "$archive"
    wait
fi

# Perform a checksum to make sure the downloaded version matches this script:
echo "8386bcdf0316845345f59e2a5d5983c54893461541d7f59c632ae817fccb678a  $archive" | sha256sum --check

# Unpack HELAC-Onia from the source tarball:
tar -xzf "$archive" -C "$build_dir"
wait
rm $archive
helac_dir=$build_dir/HELAC-Onia-2.7.6

# We must apply a fix to HELAC-Onia before building that ensures the
# line endings are UNIX formatted for four source scripts.
python3 - "$helac_dir" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
for name in ['src/photon_PDFs.f90', 'src/Helac_unwei.f90', 'src/Helac_ranmar.f90',
             'analysis/heptoptagger/heptoptagger_fjcore_interface.cc']:
    f = p / name
    f.write_text(f.read_text())
PY

# Prepare the Fortran compiler for HELAC-Onia:
compiler=$(command -v gfortran)
if [[ $compiler != /cvmfs/cms.cern.ch/el8_amd64_gcc12/* ]]; then
    echo "Use the CMS GCC12 gfortran, not a mixed host compiler: $compiler" >&2; exit 1;
fi

# Compile the extension to use CMS PbPb-based photon flux and apply it:
"$compiler" -c "$script_dir/cms_pb_flux_extension.f90" -o "$build_dir/cms_pb_flux_extension.o"
python3 - "$build_dir/gfortran-cms" "$compiler" "$helac_dir/bin/Helac-Onia" "$build_dir/cms_pb_flux_extension.o" <<'PY'
from pathlib import Path
import shlex, sys
p = Path(sys.argv[1])
p.write_text('#!/usr/bin/env bash\nset -e\nextra=()\nprevious=\n' +
             'for argument in "$@"; do\n' +
             '  if [[ $previous == -o && $argument == ' + shlex.quote(sys.argv[3]) + ' ]]; then\n' +
             '    extra=(' + shlex.quote(sys.argv[4]) + ' -Wl,--wrap=__photon_pdfs_MOD_epa_ion)\n' +
             '  fi\n  previous=$argument\ndone\n' +
             'exec ' + shlex.quote(sys.argv[2]) +
             ' -fallow-argument-mismatch -fallow-invalid-boz "$@" "${extra[@]}"\n')
p.chmod(0o755)
PY

# Update the configuration file with the compiler and lhapdf source info:
cat > "$helac_dir/input/ho_configuration.txt" <<EOF
fortran_compiler = $build_dir/gfortran-cms
lhapdf = $(command -v lhapdf-config)
run_mode = 0
nb_core = 1
EOF

# Build the patched version of HELAC-Onia:
# (Note: HEPTopTagger is optional and absent from the generator link)
cd "$helac_dir"
MAKEFLAGS='MAKEMORE=makefile_fjcore' bash ./config > "$build_dir/build.log" 2>&1
wait

# Validate the compiled Helac-Onia binary:
chmod 755 bin/Helac-Onia
test -x bin/Helac-Onia
dependencies=$(ldd bin/Helac-Onia)
if [[ $dependencies == *"not found"* ]]; then
    echo "Missing runtime library; inspect $build_dir/build.log" >&2
    exit 1
fi

# Construct the build manifest for gridpack validation:
python3 "$script_dir/build_manifest.py" "$helac_dir"
echo "Built source: $helac_dir"
echo "Build manifest: $helac_dir/build_manifest.json"
