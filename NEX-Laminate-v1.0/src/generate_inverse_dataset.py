#!/usr/bin/env python3
"""Generate NEX-Laminate v1.0.

This release deliberately separates:
1. Transcribed experimental summary statistics from the public NCAMP
   IM7/8552 qualification report.
2. Deterministic F0 numerical labels computed with Classical Lamination
   Theory (CLT).

No numerical row is represented as an experimental observation.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import itertools
import json
import math
import random
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

import numpy as np


VERSION = "1.0.0"
SEED = 20260729
ANGLES = (0, 45, -45, 90)
NCAMP_URL = (
    "https://www.wichita.edu/industry_and_defense/NIAR/Documents/"
    "Qual-CAM-RP-2009-015-Rev-B-Hexcel-8552-IM7-MPDR-04.16.19.pdf"
)
YORK_URL = "https://doi.org/10.17632/rys232ynhf.3"
DD_URL = "https://doi.org/10.17632/2xzwppwxrw.1"

KSI_TO_PA = 6_894_757.293168
MSI_TO_PA = 6_894_757_293.168


MATERIAL = {
    "material_id": "IM7_8552_NCAMP_RTD_MEASURED_V1",
    "material_name": "Hexcel 8552 / IM7 unidirectional prepreg",
    "condition": "RTD (room-temperature dry)",
    "E1_Pa": 23.51 * MSI_TO_PA,
    "E2_Pa": 1.30 * MSI_TO_PA,
    "G12_Pa": 0.68 * MSI_TO_PA,
    "nu12": 0.316,
    "Xt_Pa": 371.08 * KSI_TO_PA,
    "Xc_Pa": 251.13 * KSI_TO_PA,
    "Yt_Pa": 9.29 * KSI_TO_PA,
    "Yc_Pa": 41.44 * KSI_TO_PA,
    "S_Pa": 13.22 * KSI_TO_PA,
    "ply_thickness_m": 0.0072 * 0.0254,
    "density_kg_m3": 1580.0,
    "beam_reference_width_m": 0.025,
}


EXPERIMENTAL_SUMMARY = {
    "F1tu_from_LT_ksi": {
        "CTD": (357.39, 353.70),
        "RTD": (362.69, 371.08),
        "ETW": (333.50, 327.96),
    },
    "E1t_Msi": {
        "CTD": (22.57, 22.33),
        "RTD": (22.99, 23.51),
        "ETW": (24.00, 23.77),
    },
    "nu12t": {
        "CTD": (None, 0.270),
        "RTD": (None, 0.316),
        "ETW": (None, 0.393),
    },
    "F2tu_ksi": {
        "CTD": (None, 9.60),
        "RTD": (None, 9.29),
        "ETW": (None, 3.49),
    },
    "E2t_Msi": {
        "CTD": (None, 1.46),
        "RTD": (None, 1.30),
        "ETW": (None, 0.81),
    },
    "F1cu_ksi": {
        "CTD": (296.49, 291.99),
        "RTD": (248.94, 251.13),
        "ETD": (201.93, 199.50),
        "ETW": (173.00, 172.58),
    },
    "E1c_Msi": {
        "CTD": (20.68, 20.53),
        "RTD": (20.04, 20.44),
        "ETD": (20.25, 20.00),
        "ETW": (20.37, 20.65),
    },
    "nu12c": {
        "CTD": (None, 0.362),
        "RTD": (None, 0.356),
        "ETD": (None, 0.374),
        "ETW": (None, 0.383),
    },
    "F2cu_ksi": {
        "CTD": (None, 55.31),
        "RTD": (None, 41.44),
        "ETW": (None, 19.02),
    },
    "E2c_Msi": {
        "CTD": (None, 1.53),
        "RTD": (None, 1.41),
        "ETW": (None, 1.18),
    },
    "nu21c": {
        "CTD": (None, 0.028),
        "RTD": (None, 0.024),
        "ETW": (None, 0.018),
    },
    "F12s_0p2_ksi": {
        "CTD": (None, 11.29),
        "RTD": (None, 7.76),
        "ETW": (None, 3.31),
    },
    "F12s_max_ksi": {"CTD": (None, 16.56)},
    "F12s_5pct_ksi": {
        "RTD": (None, 13.22),
        "ETW": (None, 5.54),
    },
    "G12_Msi": {
        "CTD": (None, 0.86),
        "RTD": (None, 0.68),
        "ETW": (None, 0.31),
    },
    "SBS_ksi": {
        "CTD": (None, 21.04),
        "RTD": (None, 17.13),
        "ETD": (None, 11.23),
        "ETW": (None, 8.25),
    },
}


FIELD_META = {
    "record_id": ("string", "", "Stable release-local record identifier."),
    "canonical_layup_hash": ("string", "", "SHA-256 of the ordered full layup."),
    "equivalence_group_hash": (
        "string",
        "",
        "SHA-256 grouping a layup with its global +45/-45 sign mirror.",
    ),
    "layup_deg": (
        "string",
        "degree",
        "Outer-to-inner-to-outer ordered ply angles, separated by semicolons.",
    ),
    "n_plies": ("integer", "ply", "Total number of plies."),
    "thickness_mm": ("number", "mm", "Total nominal laminate thickness."),
    "areal_mass_kg_m2": ("number", "kg/m^2", "Density times total thickness."),
    "material_id": ("string", "", "Foreign key to material_card.csv."),
    "fidelity": ("category", "", "F0_CLT: deterministic analytical label."),
    "split": (
        "category",
        "",
        "Group-safe train, validation, test, or thickness OOD test partition.",
    ),
    "balanced": ("boolean", "", "True when +45 and -45 ply counts are equal."),
    "symmetric": ("boolean", "", "True when the stacking sequence is palindromic."),
    "max_contiguity": (
        "integer",
        "ply",
        "Maximum number of adjacent plies at the same angle.",
    ),
    "max_disorientation_deg": (
        "number",
        "degree",
        "Maximum minimum angular difference between adjacent plies.",
    ),
    "min_orientation_fraction": (
        "number",
        "fraction",
        "Smallest fraction among 0, +45, -45, and 90 degree orientations.",
    ),
    "rule_valid": (
        "boolean",
        "",
        "Symmetric, balanced, outer +/-45, max contiguity <=3, and >=10% each angle.",
    ),
    "count_0": ("integer", "ply", "Number of 0 degree plies."),
    "count_p45": ("integer", "ply", "Number of +45 degree plies."),
    "count_m45": ("integer", "ply", "Number of -45 degree plies."),
    "count_90": ("integer", "ply", "Number of 90 degree plies."),
    "xiA1": ("number", "", "Extensional lamination parameter <cos(2 theta)>."),
    "xiA2": ("number", "", "Extensional lamination parameter <cos(4 theta)>."),
    "xiA3": ("number", "", "Extensional lamination parameter <sin(2 theta)>."),
    "xiA4": ("number", "", "Extensional lamination parameter <sin(4 theta)>."),
    "xiD1": ("number", "", "Bending lamination parameter for cos(2 theta)."),
    "xiD2": ("number", "", "Bending lamination parameter for cos(4 theta)."),
    "xiD3": ("number", "", "Bending lamination parameter for sin(2 theta)."),
    "xiD4": ("number", "", "Bending lamination parameter for sin(4 theta)."),
    "A11_N_per_m": ("number", "N/m", "CLT extensional stiffness A11."),
    "A12_N_per_m": ("number", "N/m", "CLT extensional stiffness A12."),
    "A16_N_per_m": ("number", "N/m", "CLT extensional coupling stiffness A16."),
    "A22_N_per_m": ("number", "N/m", "CLT extensional stiffness A22."),
    "A26_N_per_m": ("number", "N/m", "CLT extensional coupling stiffness A26."),
    "A66_N_per_m": ("number", "N/m", "CLT in-plane shear stiffness A66."),
    "D11_N_m": ("number", "N*m", "CLT bending stiffness D11 per unit width."),
    "D12_N_m": ("number", "N*m", "CLT bending stiffness D12 per unit width."),
    "D16_N_m": ("number", "N*m", "CLT bending-twisting coupling D16."),
    "D22_N_m": ("number", "N*m", "CLT bending stiffness D22 per unit width."),
    "D26_N_m": ("number", "N*m", "CLT bending-twisting coupling D26."),
    "D66_N_m": ("number", "N*m", "CLT twisting stiffness D66 per unit width."),
    "Ex_GPa": ("number", "GPa", "Effective in-plane modulus in x."),
    "Ey_GPa": ("number", "GPa", "Effective in-plane modulus in y."),
    "Gxy_GPa": ("number", "GPa", "Effective in-plane shear modulus."),
    "nu_xy": ("number", "", "Effective major Poisson ratio."),
    "beam_EIx_N_m2": (
        "number",
        "N*m^2",
        "D11 times the declared 25 mm reference width.",
    ),
    "beam_EIy_N_m2": (
        "number",
        "N*m^2",
        "D22 times the declared 25 mm reference width.",
    ),
}

for _case, _unit, _desc in [
    ("Nx", "N/m", "unit x-direction membrane resultant"),
    ("Ny", "N/m", "unit y-direction membrane resultant"),
    ("Nxy", "N/m", "unit in-plane shear resultant"),
    ("Mx", "N", "unit x-direction bending moment resultant"),
    ("My", "N", "unit y-direction bending moment resultant"),
    ("Mxy", "N", "unit twisting moment resultant"),
]:
    FIELD_META[f"{_case}_tsai_hill_capacity_{_unit.replace('/', '_per_')}"] = (
        "number",
        _unit,
        f"First-ply load factor for {_desc}, Tsai-Hill criterion.",
    )
    FIELD_META[f"{_case}_max_stress_capacity_{_unit.replace('/', '_per_')}"] = (
        "number",
        _unit,
        f"First-ply load factor for {_desc}, maximum-stress criterion.",
    )


def angular_difference(a: int, b: int) -> int:
    delta = abs(a - b) % 180
    return int(min(delta, 180 - delta))


def max_contiguity(seq: tuple[int, ...]) -> int:
    return max(len(list(group)) for _, group in itertools.groupby(seq))


def is_valid(seq: tuple[int, ...]) -> bool:
    n = len(seq)
    counts = Counter(seq)
    return (
        seq == seq[::-1]
        and counts[45] == counts[-45]
        and abs(seq[0]) == 45
        and max_contiguity(seq) <= 3
        and min(counts[a] / n for a in ANGLES) >= 0.10
    )


def generate_sequences(targets: dict[int, int]) -> list[tuple[int, ...]]:
    rng = random.Random(SEED)
    all_sequences: list[tuple[int, ...]] = []
    for n_plies, target in targets.items():
        half_len = n_plies // 2
        found: set[tuple[int, ...]] = set()
        if half_len <= 10:
            for half in itertools.product(ANGLES, repeat=half_len):
                seq = tuple(half + half[::-1])
                if is_valid(seq):
                    found.add(seq)
        else:
            min_count = math.ceil(0.10 * half_len)
            count_vectors = []
            for balanced_count in range(min_count, half_len + 1):
                remaining = half_len - 2 * balanced_count
                for count_0 in range(min_count, remaining + 1):
                    count_90 = remaining - count_0
                    if count_90 >= min_count:
                        count_vectors.append(
                            {
                                0: count_0,
                                45: balanced_count,
                                -45: balanced_count,
                                90: count_90,
                            }
                        )
            attempts = 0
            max_attempts = max(2_000_000, target * 300)
            while len(found) < target and attempts < max_attempts:
                counts = rng.choice(count_vectors)
                half = []
                for angle in ANGLES:
                    half.extend([angle] * counts[angle])
                rng.shuffle(half)
                seq = tuple(half + half[::-1])
                if is_valid(seq):
                    found.add(seq)
                attempts += 1
        if len(found) < target:
            raise RuntimeError(
                f"Only {len(found)} valid {n_plies}-ply sequences; target={target}"
            )
        selected = sorted(found)
        if len(selected) > target:
            rng.shuffle(selected)
            selected = sorted(selected[:target])
        all_sequences.extend(selected)
    if len(set(all_sequences)) != sum(targets.values()):
        raise AssertionError("Sequence generation did not meet the unique target.")
    return all_sequences


def q_matrix(material: dict[str, float]) -> np.ndarray:
    E1 = material["E1_Pa"]
    E2 = material["E2_Pa"]
    G12 = material["G12_Pa"]
    nu12 = material["nu12"]
    nu21 = nu12 * E2 / E1
    den = 1.0 - nu12 * nu21
    return np.array(
        [
            [E1 / den, nu12 * E2 / den, 0.0],
            [nu12 * E2 / den, E2 / den, 0.0],
            [0.0, 0.0, G12],
        ],
        dtype=float,
    )


def qbar(Q: np.ndarray, theta_deg: int) -> np.ndarray:
    theta = math.radians(theta_deg)
    m = math.cos(theta)
    n = math.sin(theta)
    m2, n2 = m * m, n * n
    m4, n4 = m2 * m2, n2 * n2
    Q11, Q12, Q22, Q66 = Q[0, 0], Q[0, 1], Q[1, 1], Q[2, 2]
    qb11 = Q11 * m4 + 2 * (Q12 + 2 * Q66) * m2 * n2 + Q22 * n4
    qb22 = Q11 * n4 + 2 * (Q12 + 2 * Q66) * m2 * n2 + Q22 * m4
    qb12 = (Q11 + Q22 - 4 * Q66) * m2 * n2 + Q12 * (m4 + n4)
    qb16 = (Q11 - Q12 - 2 * Q66) * m**3 * n - (
        Q22 - Q12 - 2 * Q66
    ) * m * n**3
    qb26 = (Q11 - Q12 - 2 * Q66) * m * n**3 - (
        Q22 - Q12 - 2 * Q66
    ) * m**3 * n
    qb66 = (Q11 + Q22 - 2 * Q12 - 2 * Q66) * m2 * n2 + Q66 * (
        m4 + n4
    )
    return np.array(
        [[qb11, qb12, qb16], [qb12, qb22, qb26], [qb16, qb26, qb66]]
    )


@lru_cache(maxsize=4)
def material_qbar(theta_deg: int) -> np.ndarray:
    return qbar(q_matrix(MATERIAL), theta_deg)


@lru_cache(maxsize=4)
def strain_transform(theta_deg: int) -> np.ndarray:
    theta = math.radians(theta_deg)
    m, n = math.cos(theta), math.sin(theta)
    return np.array(
        [
            [m * m, n * n, m * n],
            [n * n, m * m, -m * n],
            [-2 * m * n, 2 * m * n, m * m - n * n],
        ]
    )


def laminate_matrices(
    seq: tuple[int, ...], material: dict[str, float]
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    t = material["ply_thickness_m"]
    h = len(seq) * t
    z = np.linspace(-h / 2, h / 2, len(seq) + 1)
    A = np.zeros((3, 3))
    B = np.zeros((3, 3))
    D = np.zeros((3, 3))
    for k, theta in enumerate(seq):
        qb = material_qbar(theta)
        A += qb * (z[k + 1] - z[k])
        B += 0.5 * qb * (z[k + 1] ** 2 - z[k] ** 2)
        D += (1.0 / 3.0) * qb * (z[k + 1] ** 3 - z[k] ** 3)
    return A, B, D, z


def lamination_parameters(
    seq: tuple[int, ...], z: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    h = z[-1] - z[0]
    xi_a = np.zeros(4)
    xi_d = np.zeros(4)
    for k, theta_deg in enumerate(seq):
        theta = math.radians(theta_deg)
        f = np.array(
            [
                math.cos(2 * theta),
                math.cos(4 * theta),
                math.sin(2 * theta),
                math.sin(4 * theta),
            ]
        )
        xi_a += ((z[k + 1] - z[k]) / h) * f
        xi_d += (
            4.0 * (z[k + 1] ** 3 - z[k] ** 3) / (h**3)
        ) * f
    return xi_a, xi_d


def failure_capacities(
    seq: tuple[int, ...],
    A: np.ndarray,
    B: np.ndarray,
    D: np.ndarray,
    z: np.ndarray,
    material: dict[str, float],
) -> dict[str, float]:
    ABD = np.block([[A, B], [B, D]])
    inv_abd = np.linalg.inv(ABD)
    Q = q_matrix(material)
    strengths = {
        "Xt": material["Xt_Pa"],
        "Xc": material["Xc_Pa"],
        "Yt": material["Yt_Pa"],
        "Yc": material["Yc_Pa"],
        "S": material["S_Pa"],
    }
    case_names = ("Nx", "Ny", "Nxy", "Mx", "My", "Mxy")
    eps0 = inv_abd[:3, :]
    kappa = inv_abd[3:, :]
    max_fi = np.zeros(6)
    min_ms = np.full(6, np.inf)
    for k, theta in enumerate(seq):
        transform = strain_transform(theta)
        for z_eval in (z[k], z[k + 1]):
            global_strain = eps0 + z_eval * kappa
            s1, s2, t12 = Q @ (transform @ global_strain)
            X = np.where(s1 >= 0, strengths["Xt"], strengths["Xc"])
            Y = np.where(s2 >= 0, strengths["Yt"], strengths["Yc"])
            S = strengths["S"]
            fi = (
                (s1 / X) ** 2
                - (s1 * s2) / (X * X)
                + (s2 / Y) ** 2
                + (t12 / S) ** 2
            )
            max_fi = np.maximum(max_fi, fi)
            with np.errstate(divide="ignore", invalid="ignore"):
                ratios = np.vstack(
                    [
                        np.where(np.abs(s1) > 0, X / np.abs(s1), np.inf),
                        np.where(np.abs(s2) > 0, Y / np.abs(s2), np.inf),
                        np.where(np.abs(t12) > 0, S / np.abs(t12), np.inf),
                    ]
                )
            min_ms = np.minimum(min_ms, np.min(ratios, axis=0))
    out = {}
    for index, case in enumerate(case_names):
        unit_token = "N_per_m" if case.startswith("N") else "N"
        out[f"{case}_tsai_hill_capacity_{unit_token}"] = 1.0 / math.sqrt(
            max(float(max_fi[index]), 1e-30)
        )
        out[f"{case}_max_stress_capacity_{unit_token}"] = float(min_ms[index])
    return out


def sequence_token(seq: tuple[int, ...]) -> str:
    return ";".join(str(x) for x in seq)


def sequence_hash(seq: tuple[int, ...]) -> str:
    return hashlib.sha256(sequence_token(seq).encode("utf-8")).hexdigest()


def equivalence_hash(seq: tuple[int, ...]) -> str:
    mirrored = tuple(-x if abs(x) == 45 else x for x in seq)
    token = min(sequence_token(seq), sequence_token(mirrored))
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def assign_split(n_plies: int, group_hash: str) -> str:
    if n_plies == 24:
        return "test_ood_thickness"
    bucket = int(group_hash[:8], 16) % 100
    if bucket < 70:
        return "train"
    if bucket < 85:
        return "validation"
    return "test"


def row_for_sequence(index: int, seq: tuple[int, ...]) -> dict[str, object]:
    A, B, D, z = laminate_matrices(seq, MATERIAL)
    h = len(seq) * MATERIAL["ply_thickness_m"]
    a = np.linalg.inv(A)
    xi_a, xi_d = lamination_parameters(seq, z)
    counts = Counter(seq)
    group_hash = equivalence_hash(seq)
    row: dict[str, object] = {
        "record_id": f"NEX-{index:06d}",
        "canonical_layup_hash": sequence_hash(seq),
        "equivalence_group_hash": group_hash,
        "layup_deg": sequence_token(seq),
        "n_plies": len(seq),
        "thickness_mm": h * 1e3,
        "areal_mass_kg_m2": MATERIAL["density_kg_m3"] * h,
        "material_id": MATERIAL["material_id"],
        "fidelity": "F0_CLT",
        "split": assign_split(len(seq), group_hash),
        "balanced": True,
        "symmetric": True,
        "max_contiguity": max_contiguity(seq),
        "max_disorientation_deg": max(
            angular_difference(x, y) for x, y in zip(seq, seq[1:])
        ),
        "min_orientation_fraction": min(counts[a_] / len(seq) for a_ in ANGLES),
        "rule_valid": is_valid(seq),
        "count_0": counts[0],
        "count_p45": counts[45],
        "count_m45": counts[-45],
        "count_90": counts[90],
        "xiA1": xi_a[0],
        "xiA2": xi_a[1],
        "xiA3": xi_a[2],
        "xiA4": xi_a[3],
        "xiD1": xi_d[0],
        "xiD2": xi_d[1],
        "xiD3": xi_d[2],
        "xiD4": xi_d[3],
        "A11_N_per_m": A[0, 0],
        "A12_N_per_m": A[0, 1],
        "A16_N_per_m": A[0, 2],
        "A22_N_per_m": A[1, 1],
        "A26_N_per_m": A[1, 2],
        "A66_N_per_m": A[2, 2],
        "D11_N_m": D[0, 0],
        "D12_N_m": D[0, 1],
        "D16_N_m": D[0, 2],
        "D22_N_m": D[1, 1],
        "D26_N_m": D[1, 2],
        "D66_N_m": D[2, 2],
        "Ex_GPa": 1.0 / (a[0, 0] * h) / 1e9,
        "Ey_GPa": 1.0 / (a[1, 1] * h) / 1e9,
        "Gxy_GPa": 1.0 / (a[2, 2] * h) / 1e9,
        "nu_xy": -a[0, 1] / a[0, 0],
        "beam_EIx_N_m2": D[0, 0] * MATERIAL["beam_reference_width_m"],
        "beam_EIy_N_m2": D[1, 1] * MATERIAL["beam_reference_width_m"],
    }
    row.update(failure_capacities(seq, A, B, D, z, MATERIAL))
    return row


def clean_value(value: object) -> object:
    if isinstance(value, (np.floating, float)):
        return f"{float(value):.10g}"
    return value


def write_experimental_summary(output_dir: Path) -> None:
    fields = [
        "source_record_id",
        "property_code",
        "condition",
        "normalized_value",
        "measured_value",
        "source_unit",
        "normalized_value_si",
        "measured_value_si",
        "si_unit",
        "source_url",
        "source_locator",
        "data_role",
    ]
    rows = []
    index = 1
    for property_code, conditions in EXPERIMENTAL_SUMMARY.items():
        if property_code.endswith("_ksi"):
            unit, si_unit, factor = "ksi", "Pa", KSI_TO_PA
        elif property_code.endswith("_Msi"):
            unit, si_unit, factor = "Msi", "Pa", MSI_TO_PA
        else:
            unit, si_unit, factor = "", "", 1.0
        for condition, (normalized, measured) in conditions.items():
            rows.append(
                {
                    "source_record_id": f"NCAMP-T2-1-{index:03d}",
                    "property_code": property_code,
                    "condition": condition,
                    "normalized_value": normalized,
                    "measured_value": measured,
                    "source_unit": unit,
                    "normalized_value_si": (
                        None if normalized is None else normalized * factor
                    ),
                    "measured_value_si": measured * factor,
                    "si_unit": si_unit,
                    "source_url": NCAMP_URL,
                    "source_locator": "CAM-RP-2009-015 Rev B, Table 2-1, page 28",
                    "data_role": "experimental_summary_statistic",
                }
            )
            index += 1
    path = output_dir / "data" / "experimental_ncamp_lamina_summary.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_material_card(output_dir: Path) -> None:
    selected = [
        ("E1", MATERIAL["E1_Pa"], "Pa", "E1t_Msi", "RTD measured mean"),
        ("E2", MATERIAL["E2_Pa"], "Pa", "E2t_Msi", "RTD measured mean"),
        ("G12", MATERIAL["G12_Pa"], "Pa", "G12_Msi", "RTD measured mean"),
        ("nu12", MATERIAL["nu12"], "", "nu12t", "RTD measured mean"),
        ("Xt", MATERIAL["Xt_Pa"], "Pa", "F1tu_from_LT_ksi", "RTD measured mean"),
        ("Xc", MATERIAL["Xc_Pa"], "Pa", "F1cu_ksi", "RTD measured mean"),
        ("Yt", MATERIAL["Yt_Pa"], "Pa", "F2tu_ksi", "RTD measured mean"),
        ("Yc", MATERIAL["Yc_Pa"], "Pa", "F2cu_ksi", "RTD measured mean"),
        ("S", MATERIAL["S_Pa"], "Pa", "F12s_5pct_ksi", "RTD measured mean"),
        (
            "ply_thickness",
            MATERIAL["ply_thickness_m"],
            "m",
            "nominal_CPT",
            "NCAMP normalization CPT",
        ),
        (
            "density",
            MATERIAL["density_kg_m3"],
            "kg/m^3",
            "laminate_density",
            "Representative physical-property value in report",
        ),
    ]
    fields = [
        "material_id",
        "property",
        "value_si",
        "unit_si",
        "experimental_property_code",
        "selection_basis",
        "source_url",
        "source_locator",
    ]
    with (output_dir / "data" / "material_card.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for prop, value, unit, code, basis in selected:
            writer.writerow(
                {
                    "material_id": MATERIAL["material_id"],
                    "property": prop,
                    "value_si": f"{value:.12g}",
                    "unit_si": unit,
                    "experimental_property_code": code,
                    "selection_basis": basis,
                    "source_url": NCAMP_URL,
                    "source_locator": "CAM-RP-2009-015 Rev B, Table 2-1 or physical-property table",
                }
            )


def write_data_dictionary(output_dir: Path, fieldnames: list[str]) -> None:
    path = output_dir / "metadata" / "data_dictionary.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["field", "type", "unit", "description"])
        for name in fieldnames:
            dtype, unit, description = FIELD_META[name]
            writer.writerow([name, dtype, unit, description])


def write_protocol(output_dir: Path) -> None:
    plan_path = output_dir / "protocols" / "minimum_experimental_plan.csv"
    fields = [
        "planned_design_id",
        "selection_stratum",
        "minimum_replicates",
        "test_family",
        "standard_reference",
        "required_raw_channels",
        "status",
    ]
    rows = []
    strata = [
        ("quasi_isotropic", "tension", "ASTM D3039/D3039M-17(2025)"),
        ("axial_dominant", "tension", "ASTM D3039/D3039M-17(2025)"),
        ("transverse_dominant", "tension", "ASTM D3039/D3039M-17(2025)"),
        ("shear_dominant", "in-plane shear", "ASTM D3518/D3518M-18(2025)"),
        ("high_D16", "flexure", "ASTM D7264/D7264M-21"),
        ("low_D16", "flexure", "ASTM D7264/D7264M-21"),
        ("high_D26", "flexure", "ASTM D7264/D7264M-21"),
        ("low_D26", "flexure", "ASTM D7264/D7264M-21"),
        ("high_failure_capacity", "flexure", "ASTM D7264/D7264M-21"),
        ("low_failure_capacity", "flexure", "ASTM D7264/D7264M-21"),
        ("pareto_mass_stiffness", "drop impact", "ASTM D7136/D7136M-25"),
        ("gan_generated_holdout", "application-specific", "Frozen pre-registration"),
    ]
    for index, (stratum, family, standard) in enumerate(strata, 1):
        rows.append(
            {
                "planned_design_id": f"EXP-D{index:02d}",
                "selection_stratum": stratum,
                "minimum_replicates": 3,
                "test_family": family,
                "standard_reference": standard,
                "required_raw_channels": "time;load;displacement;strain;temperature;failure_mode",
                "status": "planned_not_observed",
            }
        )
    with plan_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    schema_path = output_dir / "protocols" / "experimental_observation_schema.csv"
    schema_rows = [
        ("observation_id", "string", "", True),
        ("planned_design_id", "string", "", True),
        ("canonical_layup_hash", "string", "", True),
        ("specimen_id", "string", "", True),
        ("replicate", "integer", "", True),
        ("test_standard", "string", "", True),
        ("test_date", "date", "YYYY-MM-DD", True),
        ("operator_id_pseudonym", "string", "", True),
        ("batch_id", "string", "", True),
        ("cure_cycle_id", "string", "", True),
        ("measured_thickness_mm", "number", "mm", True),
        ("measured_density_kg_m3", "number", "kg/m^3", False),
        ("temperature_C", "number", "degree C", True),
        ("relative_humidity_pct", "number", "%", False),
        ("raw_data_path", "string", "", True),
        ("failure_mode", "category", "", False),
        ("exclusion_flag", "boolean", "", True),
        ("exclusion_reason", "string", "", False),
    ]
    with schema_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["field", "type", "unit_or_format", "required"])
        writer.writerows(schema_rows)


def write_provenance(output_dir: Path, targets: dict[int, int]) -> None:
    provenance = {
        "dataset": "NEX-Laminate",
        "version": VERSION,
        "generated_utc": "2026-07-29T00:00:00Z",
        "random_seed": SEED,
        "targets_by_ply_count": {str(k): v for k, v in targets.items()},
        "fidelity_definition": {
            "F0_CLT": (
                "Deterministic Classical Lamination Theory using an experimentally "
                "anchored RTD material card. Not a finite-element or experimental label."
            )
        },
        "material_source": {
            "title": "Hexcel 8552 IM7 Unidirectional Prepreg Material Property Data Report",
            "report": "CAM-RP-2009-015 Rev B",
            "url": NCAMP_URL,
            "distribution": "Approved for public release; distribution unlimited.",
        },
        "external_validation_sources": [
            {"role": "manufacturing-rule corpus", "url": YORK_URL},
            {"role": "independent CLT implementation", "url": DD_URL},
        ],
        "design_rules": {
            "angle_alphabet_deg": list(ANGLES),
            "symmetric": True,
            "balanced": True,
            "outer_ply": "+/-45",
            "maximum_contiguity": 3,
            "minimum_fraction_each_orientation": 0.10,
            "disorientation": (
                "Recorded but not restricted below 90 degrees in v1; users may filter."
            ),
        },
        "split_policy": {
            "group_key": "equivalence_group_hash",
            "id_distribution": "70/15/15 by deterministic group hash",
            "ood": "All 24-ply laminates are test_ood_thickness.",
        },
        "known_limitations": [
            "F0 labels omit geometric stress concentrations, contact, damage evolution, and impact dynamics.",
            "The NCAMP table provides condition-level means; raw coupon traces are not copied into this release.",
            "Density is a representative report value rather than a batch-specific measurement for each row.",
            "A future numerical-experimental v2 must add paired laminate/subcomponent tests; planned rows are not observations.",
        ],
    }
    (output_dir / "metadata" / "provenance.json").write_text(
        json.dumps(provenance, indent=2), encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output_dir = args.output.resolve()
    for subdir in ("data", "metadata", "protocols", "reports"):
        (output_dir / subdir).mkdir(parents=True, exist_ok=True)

    targets = {8: 12, 12: 212, 16: 3612, 20: 3164, 24: 3000}
    sequences = generate_sequences(targets)

    data_path = output_dir / "data" / "numerical_clt_v1.csv.gz"
    sample_path = output_dir / "data" / "numerical_clt_v1_sample.csv"
    split_counts: Counter[str] = Counter()
    ply_counts: Counter[int] = Counter()
    fieldnames: list[str] | None = None
    with gzip.open(data_path, "wt", newline="", encoding="utf-8") as gz_handle, sample_path.open(
        "w", newline="", encoding="utf-8"
    ) as sample_handle:
        writer = None
        sample_writer = None
        for index, seq in enumerate(sequences, 1):
            row = row_for_sequence(index, seq)
            if fieldnames is None:
                fieldnames = list(row)
                writer = csv.DictWriter(gz_handle, fieldnames=fieldnames)
                sample_writer = csv.DictWriter(sample_handle, fieldnames=fieldnames)
                writer.writeheader()
                sample_writer.writeheader()
            cleaned = {k: clean_value(v) for k, v in row.items()}
            writer.writerow(cleaned)
            if index <= 250:
                sample_writer.writerow(cleaned)
            split_counts[str(row["split"])] += 1
            ply_counts[int(row["n_plies"])] += 1

    assert fieldnames is not None
    write_experimental_summary(output_dir)
    write_material_card(output_dir)
    write_data_dictionary(output_dir, fieldnames)
    write_protocol(output_dir)
    write_provenance(output_dir, targets)

    build_report = {
        "dataset": "NEX-Laminate",
        "version": VERSION,
        "records": len(sequences),
        "records_by_ply_count": dict(sorted(ply_counts.items())),
        "records_by_split": dict(sorted(split_counts.items())),
        "seed": SEED,
        "numerical_file": str(data_path.name),
    }
    (output_dir / "reports" / "build_report.json").write_text(
        json.dumps(build_report, indent=2), encoding="utf-8"
    )
    print(json.dumps(build_report, indent=2))


if __name__ == "__main__":
    main()
