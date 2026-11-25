#!/usr/bin/env python3
"""Adapt a complete HELAC CO run to CMSSW without reweighting it."""

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re


MODEL = "helac-direct-jpsi-co-1s0-shower-mpi-off"
SCHEMA = "helac-co-cmssw-lhe-v1"


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def number(value):
    value = float(str(value).replace("D", "E").replace("d", "e"))
    require(math.isfinite(value), "Non-finite LHE number")
    return value


def integer(value):
    parsed = number(value)
    require(parsed.is_integer(), "Expected an integer LHE field")
    return int(parsed)


def fields(block):
    return [line.split() for line in block.splitlines() if line.strip()]


def convert(contents, generation):
    """Return the adapted full LHE and audit summary; change only octet IDs.

    The deliberately narrow input contract matches RunHelacCO's events.lhe.
    Raw HELAC unit/residual-weight files, CS events and already converted files
    are rejected. The complete sample is kept, including shower-rejected
    attempts, so its cross-section denominator is not changed.
    """
    require(generation.get("model") == MODEL, "Expected a complete direct-CO run")
    require(generation.get("lhe_sha256") == sha256(contents),
            "Input LHE does not match generation.json")
    expected = {"lhe_octet_id": 9900441, "pythia_octet_id": 9941003,
                "physical_state": 443, "charm_mass_GeV": 1.6,
                "pair_mass_GeV": 3.2, "jpsi_mass_GeV": 3.0969,
                "physical_ldme_GeV3": 0.01, "helac_ldme_GeV3": 0.00125,
                "ldme_divisor": 8, "h1_tune_applied": False}
    hard = generation.get("hard_process", {})
    require(all(hard.get(key) == value for key, value in expected.items()),
            "Unexpected CO hard-process metadata")
    require(generation.get("pdf") == "EPPS21nlo_CT18Anlo_Pb208/0",
            "Expected the EPPS21 central target PDF")
    cut = generation.get("generation_cuts", {})
    require(cut.get("pt_min") in (1.0, 0.5) and
            cut.get("y_min") == -30 and cut.get("y_max") == 30,
            "Expected nominal 1 GeV or control 0.5 GeV hard-pT cutoff")

    text = contents.decode("ascii")
    require(text.strip().startswith('<LesHouchesEvents version="1.0">') and
            text.strip().endswith("</LesHouchesEvents>"), "Incomplete canonical LHE")
    init = re.findall(r"<init>\s*(.*?)\s*</init>", text, re.S)
    require(len(init) == 1, "Expected one LHE init block")
    init = fields(init[0])
    require(len(init) == 2 and len(init[0]) == 10 and len(init[1]) == 4,
            "Expected one LHE subprocess")
    beam, process = init
    require([integer(x) for x in beam[:2]] == [2212, 2212] and
            [number(x) for x in beam[2:4]] == [2681, 2681] and
            [integer(x) for x in beam[6:8]] == [904400, 904400],
            "Unexpected beam energy or PDF IDs")
    require(integer(beam[8]) == 4 and integer(beam[9]) == 1,
            "Use normalized standalone events.lhe with IDWTUP=4")
    sigma, error, maximum = map(number, process[:3])
    require(sigma > 0 and error >= 0 and maximum > 0, "Invalid LHE cross section")
    require(math.isclose(sigma, generation.get("sigma_pb", -1), rel_tol=1e-8),
            "Cross section disagrees with generation.json")
    events = list(re.finditer(r"<event>\s*(.*?)\s*</event>", text, re.S))
    require(len(events) == generation.get("events") and len(events) > 0,
            "Input is not the complete generated sample")
    require(text.count("<event>") == len(events) == text.count("</event>"),
            "Malformed event blocks")

    weights, transverse_momenta = [], []
    for index, match in enumerate(events):
        lines = fields(match.group(1))
        require(len(lines) == 5 and len(lines[0]) == 6,
                "Event %d: expected four undecayed hard particles" % index)
        header, particles = lines[0], lines[1:]
        require(integer(header[0]) == 4 and integer(header[1]) == integer(process[3]),
                "Invalid LHE event header")
        require(number(header[3]) > 0, "Shower scale must be positive and finite")
        number(header[4])
        number(header[5])
        weight = number(header[2])
        require(0 < weight <= maximum * (1 + 1e-8), "Invalid event weight")
        require(all(len(p) == 13 for p in particles), "Malformed particle record")
        require([integer(p[0]) for p in particles] == [22, 21, 9900441, 21] and
                [integer(p[1]) for p in particles] == [-1, -1, 1, 1],
                "Expected gamma g -> undecayed CO octet + g")
        require([[integer(p[2]), integer(p[3])] for p in particles] ==
                [[0, 0], [0, 0], [1, 2], [1, 2]], "Unexpected hard-process ancestry")
        balance, ends = Counter(), Counter()
        momentum = []
        for i, p in enumerate(particles):
            colour, anticolour = integer(p[4]), integer(p[5])
            require((colour == anticolour == 0) if i == 0 else
                    (colour > 0 and anticolour > 0 and colour != anticolour),
                    "Invalid octet/gluon colour tags")
            sign = -1 if i < 2 else 1
            if colour:
                balance[colour] += sign
                ends[colour] += 1
            if anticolour:
                balance[anticolour] -= sign
                ends[anticolour] += 1
            four = [number(x) for x in p[6:11]]
            px, py, pz, energy, mass = four
            require(energy > 0 and mass >= 0, "Invalid particle energy or mass")
            if i != 2:
                require(abs(mass) < 1e-6, "Photon and gluons must be massless")
            p2 = px * px + py * py + pz * pz
            require(abs(energy * energy - p2 - mass * mass) <=
                    1e-6 * max(1, energy * energy, p2, mass * mass),
                    "Particle is not on its declared mass shell")
            if i < 2:
                require(abs(px) < 1e-6 and abs(py) < 1e-6,
                        "Incoming partons must be collinear with the beams")
            momentum.append(four)
            number(p[11])
            number(p[12])
        require(len(ends) == 3 and all(ends[k] == 2 and balance[k] == 0 for k in ends),
                "Colour lines do not close")
        require(momentum[0][2] > 0 and momentum[1][2] < 0,
                "Expected the +z photon orientation")
        for axis in range(4):
            incoming = momentum[0][axis] + momentum[1][axis]
            outgoing = momentum[2][axis] + momentum[3][axis]
            require(abs(incoming - outgoing) <= 1e-6 * max(1, abs(incoming), abs(outgoing)),
                    "Four-momentum does not close")
        require(abs(momentum[2][4] - 3.2) < 1e-5, "Unexpected octet mass")
        pt = math.hypot(*momentum[2][:2])
        require(pt >= cut["pt_min"] - 1e-7, "Event violates the hard-pT cutoff")
        weights.append(weight)
        transverse_momenta.append(pt)

    total = math.fsum(weights)
    require(math.isclose(total / len(weights), sigma, rel_tol=1e-8),
            "Mean absolute event weight must equal XSECUP in pb")
    converted, count = re.subn(r"(?m)^([ \t]*)9900441(?=[ \t])", r"\g<1>9941003", text)
    require(count == len(events), "Unexpected number of octet ID replacements")
    # The inverse transformation is a byte-level preservation check.
    restored = re.sub(r"(?m)^([ \t]*)9941003(?=[ \t])", r"\g<1>9900441", converted)
    require(restored == text, "Conversion changed more than the octet particle ID")
    output = converted.encode("ascii")
    return output, dict(schema=SCHEMA, events=len(events), idwtup=4,
                        input_lhe_sha256=sha256(contents), output_lhe_sha256=sha256(output),
                        sigma_pb=sigma, integration_error_pb=error,
                        sum_weights_pb=total, min_weight_pb=min(weights), max_weight_pb=max(weights),
                        min_hard_pt_GeV=min(transverse_momenta), generation_cuts=cut,
                        conversion="9900441 -> 9941003; all other bytes unchanged",
                        normalization="Complete hard-event sample; no reweighting or event selection")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path,
                        help="Standalone RunHelacCO directory with events.lhe and generation.json")
    parser.add_argument("--output", required=True, type=Path,
                        help="New LHE file; a .json provenance sidecar is also written")
    args = parser.parse_args()
    output = args.output.resolve()
    sidecar = Path(str(output) + ".json")
    require(not output.exists() and not sidecar.exists(), "Output or sidecar already exists")
    run = args.run.resolve()
    generation_bytes = (run / "generation.json").read_bytes()
    generation = json.loads(generation_bytes)
    converted, report = convert((run / "events.lhe").read_bytes(), generation)
    report.update(source_run=str(run), generation_sha256=sha256(generation_bytes),
                  generation=generation)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as stream:
        stream.write(converted)
    with sidecar.open("x") as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({key: report[key] for key in
                      ("events", "sigma_pb", "sum_weights_pb", "output_lhe_sha256")}, indent=2))


if __name__ == "__main__":
    main()
