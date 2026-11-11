"""Pareto surface for Ragu as a split-accumulation PCD scheme: Pedersen-IPA today against
Akita under five field/modulus choices, and against the hash-based schemes (WHIR over Pasta,
Goldilocks and a limb hybrid, a Plonky3-style FRI, the Flock/Binius-style binary-field family,
BitZ), each with ARC accumulation and with its own recursion.

Every point is one configuration. Its coordinates are compressed proof bytes and two cost
proxies, defined in PROXIES below. The numbers come from:
  - ragu-size-model.py: the compressed Pedersen-IPA proof, counted from Ragu's structs and
    pinned by the `encoded_len_matches_the_shape` test (7,460 bytes at the checked-in
    configuration), and the circuit budget: the internal circuits' measured gate counts,
    which bound the endoscalings per step and the binders at each rank;
  - the Akita planner runs in estimates/ and work/akita-pasta-out/groups/: opening sizes per
    number of separately committed groups, at each width variant (pasta-proof-size.md §8);
  - the WHIR reference implementation's sweep in estimates/whir-sweep-grind.tsv, Ulrich
    Haböck's FRI-Binius proof-size optimizer (frib_optimizer.py), and the BitZ and Plonky3
    benchmarks described at their families below.

Writes pareto.html next to this script: a self-contained page with the data inlined.
"""
import functools, itertools, json, math, pathlib
import frib_optimizer as frib

HERE = pathlib.Path(__file__).resolve().parent
_model = {}
exec((HERE / "ragu-size-model.py").read_text().split("CHECKED_IN = ")[0], _model)
size, fixed_counts = _model["size"], _model["fixed_counts"]
max_endoscalings, min_binders = _model["max_endoscalings"], _model["min_binders"]
gates_per_merge, gate_budget = _model["gates_per_merge"], _model["gate_budget"]

# Akita opening bytes for one final group of 2^14 coefficients plus K separately committed
# groups of 2^14, from catalog_reprice on the planner's outputs (K=0: the shipped schedule
# re-planned under the matching pricing; K>0: groups/q64-k<K>).
AKITA_K = [0, 1, 2, 4, 8, 12]
AKITA = {
    "fp128":      [65074, 69044, 71066, 69492, 68485, 70404],
    "goldilocks": None,  # fp64 geometry: 61,050 at K=0; scaled below by fp128's growth
    "pasta_q64":  [70725, 74212, 75562, 76804, 77445, 78580],
    "pasta_sis":  [83234, 87844, 90090, 89924, 89669, 91700],
    "pasta":      [101441, 115108, 119146, 116164, 114117, 117940],

}
AKITA["goldilocks"] = [round(61050 * v / 65074) for v in AKITA["fp128"]]

# Bytes per doubling of the polynomial, from the 2^14 -> 2^16 rows of the same runs.
SLOPE = {"fp128": 563, "goldilocks": 476, "pasta_q64": 1743, "pasta_sis": 2094, "pasta": 2139}
DIGITS = {"fp128": 43, "goldilocks": 22, "pasta_q64": 85, "pasta_sis": 85, "pasta": 85}

# Prover work in native 64-bit word multiplications, for the commitments of one step.
#
# Pedersen over Pasta: a size-n multi-scalar multiplication with 255-bit scalars by Pippenger
# costs about 255/log2(n) mixed point additions per point, each about 11 field
# multiplications, each about 32 word multiplications (4x4 limb products plus a Montgomery
# reduction). So per coefficient: 255/log2(n) * 11 * 32.
#
# Ajtai over R_q with ring dimension d and scalar_rows rows, by NTT: per digit about
# scalar_rows/d pointwise multiplications plus log2(d)/2 for the digit's share of the NTT,
# each at the modulus width: 32 word multiplications at 255 bits, 8 at 128, 2 at 64 (and
# Goldilocks's reduction is cheaper still, taken as 1.5). Rows are Akita's estimator at the
# unmasked collision bound (pasta-proof-size.md §5.5): 143 at Pasta, 284 at 128 bits, 567 at
# 64 bits, the same bits throughout. Per coefficient: digits * that.
RING_D = 64
ROWS = {"fp128": 284, "goldilocks": 567, "pasta_q64": 567, "pasta_sis": 143, "pasta": 143}
WORD_MULTS = {"fp128": 8, "goldilocks": 1.5, "pasta_q64": 2, "pasta_sis": 32, "pasta": 32}

# The zero-knowledge option masks the accumulator witness by rejection sampling at the user's
# fold (zk-fiat-shamir-with-aborts.md §5): the one accumulator that fold produces is about nine
# times longer, and the accumulation matrix's Module-SIS rank is about 2.4 times higher, since
# the note's extraction argument needs that matrix binding at the masked bound and every
# accumulator is committed under it. Akita's internal fold levels and its terminal commit the
# final accumulator's ordinary witness under their own matrices, whose bounds the mask does
# not change, so the opening proof is nearly unaffected: the accumulation matrix's larger
# images enter the first level only as lower-order auxiliary digits. The length stays at the
# zero-knowledge layer: the aggregator's first fold on a masked accumulator range-checks its
# nine digit slices and folds them back to the ordinary length with its other inputs, as every
# lattice fold decomposes and folds, so the merges above and the decider's opening see witnesses
# of the usual size. The merge priced here is one at the zero-knowledge layer, the costlier
# kind: each of its two sum-checks gains three rounds (log2 of the length factor) of three
# elements. Merges above that layer pay the rank's rows term only.
#
# The masked bound follows the note's §5.3: the digit vector has N = 2^22 digits of size at most
# 4, so ‖s‖₂ ≤ 2^13; a challenge of ℓ1 norm MASK_CHALLENGE_L1 gives ‖cs‖₂ ≤ that times 2^13; the
# Gaussian mask has width σ = MASK_ALPHA · ‖cs‖₂, the accepted response ‖z‖₂ ≈ 2σ√N, and the
# relaxed opening that extraction yields needs binding at 2 · ‖c − c'‖₁ · 2 · ‖z‖₂, with ‖c − c'‖₁
# at most twice the challenge's norm. The rank grows as the square of log2 of that bound against
# the unmasked 2^27 (§5.2, §5.5). The page takes α = 12 with weight-20 ternary challenges in the
# accumulation matrix's ring dimension of 512 (‖c‖₁ = 20), which give 2^40.2 and a factor of
# 2.22; the note's §5.3 example used weight 32 in dimension 128, 2.37, and its §5.6 prices the
# alternatives. The masked coordinates are at most 14σ, which sets the slices: base-8 digits per
# coordinate.
MASK_ALPHA = 12
MASK_CHALLENGE_L1 = 20
MASK_LOG_S, MASK_LOG_N, MASK_UNMASKED_LOG_BETA = 13, 22, 27

def masked_log_beta(alpha=MASK_ALPHA, c_l1=MASK_CHALLENGE_L1):
    log_sigma = math.log2(alpha) + math.log2(c_l1) + MASK_LOG_S
    log_z = 1 + log_sigma + MASK_LOG_N / 2
    return 1 + math.log2(2 * c_l1) + 1 + log_z

MASK_RANK = (masked_log_beta() / MASK_UNMASKED_LOG_BETA) ** 2
MASK_LENGTH = math.ceil((math.log2(14) + math.log2(MASK_ALPHA) + math.log2(MASK_CHALLENGE_L1) + MASK_LOG_S) / 3)
MASK_SUMCHECK_ATOMS = 2 * round(math.log2(MASK_LENGTH)) * 3

def ajtai_per_coefficient(variant, zk=False, rank_scale=1.0):
    rows = ROWS[variant] * (MASK_RANK if zk else 1) * rank_scale
    per_digit = (rows / RING_D + math.log2(RING_D) / 2) * WORD_MULTS[variant]
    return DIGITS[variant] * per_digit

def pedersen_per_coefficient(rank):
    return 255 / rank * 11 * 32

# The user's masking fold, for the page's transaction measure: the expected rejection-sampling
# attempts, exp(12/α + 1/(2α²)), each a commitment of a mask of N coordinates under the masked
# accumulation matrix and N Gaussian samples by Karney's exact method at about 300 ns a
# coordinate, 900 word-multiplication equivalents at 3e9 per second; N is the accumulator's
# digits, K groups of 2^rank coefficients (zk-fiat-shamir-with-aborts.md §5.4). The fold's own
# merge is added at the point. §5.8 of the note moves the attempts off the device's critical
# path, so this is total work, not latency.
MASK_ATTEMPTS = math.exp(12 / MASK_ALPHA + 1 / (2 * MASK_ALPHA ** 2))
MASK_SAMPLE_WORD_MULTS = 900

def mask_fold(variant, K, rank, rank_scale):
    digits = DIGITS[variant] * K * 2 ** rank
    per_digit = ajtai_per_coefficient(variant, True, rank_scale) / DIGITS[variant]
    return MASK_ATTEMPTS * digits * (per_digit + MASK_SAMPLE_WORD_MULTS)

# Base-field atoms the merge circuit absorbs per compressed commitment (128 bytes).
ATOMS_PER_COMMITMENT = {"fp128": 8, "goldilocks": 16, "pasta_q64": 6, "pasta_sis": 4, "pasta": 4}
SUMCHECK_ATOMS = 120  # two range/norm sum-checks of about 20 rounds and 3 elements, per merge

# ---- Hashes in circuits --------------------------------------------------------------
# Every in-circuit hash on the page is one of two. The conventional hash is BLAKE3, at
# 14,900 gates per 64-byte compression in a lookup-free R1CS over Pasta or Goldilocks (the
# recovery-circuit note's count: 56 quarter-rounds at 262 gates plus the output XORs) and
# 200 word multiplications natively. The arithmetic hash is Poseidon 1.1 over the circuit's
# own field: 72 gates per absorbed atom for the Akita transcript (four elements per 288-gate
# Pasta permutation) and the per-variant figures in HASH_VARIANTS for the Merkle trees. The
# page's default is the conventional hash, for future-proofing; the option allows the
# arithmetic one, which is what Ragu's checked-in circuits and Tachyon use, so the
# Pedersen-IPA rows exist only under that option. The 𝔽₂ family and BitZ hash with BLAKE3
# natively and appear under both. A point's `hashes` is the policy it was priced under, or
# "any".
HASH_POLICIES = ("blake3", "poseidon")
BLAKE3_GATES = 14900
BLAKE3_BLOCK = 64
HASH_LABEL = {"blake3": ", BLAKE3", "poseidon": ", Poseidon"}

# The lattice merge circuit, estimated. Its stage polynomials are committed separately, as
# today's native stages are, and every step circuit's witness goes into one more group, since
# Akita opens a batch of polynomials at the cost of one. Gates: the transcript hashing at the
# policy's price, over the atoms that the merge absorbs (Poseidon) or over their bytes
# (BLAKE3); folding a child's 128-byte commitment image needs a modular reduction, taken as
# one gate per bit; the sum-check verifier's arithmetic is small.
STAGES = 5
HASH_GATES_PER_ATOM = 72
FOLD_GATES_PER_IMAGE = 1024
SUMCHECK_GATES = 400

# Each step circuit's polynomial carries its own evaluation claim: one claim-field element
# in the proof, one atom absorbed per merge, and a few gates to fold it. This is what makes
# a larger rank, and so fewer circuits, cheaper for Akita. Under BLAKE3 the claim's hashing,
# about 3,700 gates for a 16-byte claim and 7,500 for a 32-byte one, can exceed what a small
# rank's budget holds per circuit, and then no number of circuits suffices: the merge needs a
# larger rank, or the claims aggregated before absorption, which is a design change.
CLAIM_BYTES = {"fp128": 16, "goldilocks": 16, "pasta_q64": 32, "pasta_sis": 32, "pasta": 32}
CLAIM_GATES = 4

def akita_atoms(variant, K, circuits, zk):
    return SUMCHECK_ATOMS + K * ATOMS_PER_COMMITMENT[variant] + circuits + (MASK_SUMCHECK_ATOMS if zk else 0)

def akita_absorbed_bytes(variant, K, circuits, zk):
    """The bytes the merge absorbs: the sum-check elements and the claims at the claim
    field's width, and the K commitment images of 128 bytes."""
    return (SUMCHECK_ATOMS + circuits + (MASK_SUMCHECK_ATOMS if zk else 0)) * CLAIM_BYTES[variant] + K * 128

def akita_hash_gates(variant, K, circuits, zk, hp):
    if hp == "poseidon":
        return HASH_GATES_PER_ATOM * akita_atoms(variant, K, circuits, zk)
    return akita_absorbed_bytes(variant, K, circuits, zk) / BLAKE3_BLOCK * BLAKE3_GATES

def akita_merge_gates(variant, K, circuits, zk, hp):
    return (akita_hash_gates(variant, K, circuits, zk, hp) + 2 * K * FOLD_GATES_PER_IMAGE
            + SUMCHECK_GATES + CLAIM_GATES * circuits)

def akita_circuits(variant, K, rank, zk, hp):
    """The step circuits a merge needs at this rank: the gate estimate, which grows with the
    circuit count through each circuit's claim, divided by the budget, at its fixed point;
    None where each circuit adds more gates than the budget holds, so that no count
    converges."""
    per_circuit = akita_merge_gates(variant, K, 2, zk, hp) - akita_merge_gates(variant, K, 1, zk, hp)
    if per_circuit >= gate_budget(rank):
        return None
    circuits = 1
    for _ in range(2000):
        new = math.ceil(akita_merge_gates(variant, K, circuits, zk, hp) / gate_budget(rank))
        if new == circuits:
            return circuits
        circuits = new
    return circuits

LABEL = {
    "pedersen": "Pedersen-IPA (not post‑quantum)",
    "fp128": "Akita, 128‑bit field",
    "goldilocks": "Akita, Goldilocks",
    "pasta_q64": "Akita, Pasta claims, 64‑bit commitments",
    "pasta_sis": "Akita, Pasta, inner images at SIS size",
    "pasta": "Akita, Pasta for everything",
    "whir": "WHIR with ARC, Pasta, hash-based",
    "whir_gold": "WHIR with ARC, Goldilocks, hash-based",
    "whir_hybrid": "WHIR with ARC, Pasta claims, 64‑bit limbs, hash-based",
    "plonky3": "Plonky3-style FRI with ARC, Goldilocks, hash-based",
    "flock": "Flock/Binius-style over 𝔽₂ with ARC, hash-based",
    "whir_rec": "WHIR, recursive, Pasta, hash-based",
    "whir_gold_rec": "WHIR, recursive, Goldilocks, hash-based",
    "whir_hybrid_rec": "WHIR, recursive, Pasta claims, 64‑bit limbs, hash-based",
    "plonky3_rec": "Plonky3-style FRI, recursive, Goldilocks, hash-based",
    "flock_rec": "Flock/Binius-style over 𝔽₂, recursive, hash-based",
    "bitz": "BitZ with ARC, Pasta claims over committed bits, hash-based",
    "bitz_rec": "BitZ, recursive, Pasta claims over committed bits, hash-based",
    "bits_q64": "BitZ over Akita, 64‑bit commitments, Pasta claims (draft frontend)",

}

def akita_bytes(variant, K, log_len):
    """Opening bytes with K extra committed groups and a batched witness of 2^log_len
    coefficients, from the planner's rows at 2^14 and the per-doubling slope."""
    xs, ys = AKITA_K, AKITA[variant]
    if K >= xs[-1]:
        y = ys[-1] + (ys[-1] - ys[-2]) / (xs[-1] - xs[-2]) * (K - xs[-1])
    else:
        i = max(j for j in range(len(xs) - 1) if xs[j] <= K)
        t = (K - xs[i]) / (xs[i + 1] - xs[i])
        y = ys[i] + t * (ys[i + 1] - ys[i])
    return round(y + SLOPE[variant] * (log_len - 14))

# ---- Verifier work ---------------------------------------------------------------
# The decider's verification, in the same 64-bit word-multiplication equivalents as the
# prover, at 3e9 per second of one core. Pedersen-IPA: the two IPAs each need a multi-scalar
# multiplication of 2^rank points, plus a scalar multiplication per folded commitment to
# combine the instance (about 255 doublings and additions of 11 field multiplications).
# Akita: the paper's single-thread measurements (Table 16, one thread, 2^27 bits): 4.2 ms at
# the 128-bit field and 3.9 ms on Goldilocks, growing 0.45 and 0.35 ms per doubling of the
# witness (2^27 to 2^29 bits); the Pasta variants are taken at four times the 128-bit figure,
# the ratio of word multiplications per field multiplication, since the verifier's work is
# sum-check arithmetic in the claim field; the masked witness adds three rounds to each
# sum-check of about twenty. Hash-based: the WHIR verifier's hashes at the witness size, at
# the variant's native permutation cost, plus about a million for the arithmetic; FRI has
# 2.07 times the hashes. 𝔽₂: Flock's Ligerito verifier, 1.3 ms in the same table.
WORD_MULTS_PER_MS = 3e6
SCALAR_MULT_WORD_MULTS = 255 * 2 * 11 * 32
AKITA_VERIFY_MS = {"fp128": (4.2, 0.45, 20), "goldilocks": (3.9, 0.35, 21)}

def akita_verify(variant, log_len, zk, rank_scale=1.0):
    base, slope, ref = AKITA_VERIFY_MS["goldilocks" if variant == "goldilocks" else "fp128"]
    ms = base + slope * (log_len - ref)
    if variant not in ("fp128", "goldilocks"):
        ms *= 4
    # With zero knowledge the final accumulator is at the ordinary length, so the sum-checks
    # are unchanged; the masked rank arrives in rank_scale, composed by the caller.
    return round(ms * rank_scale * WORD_MULTS_PER_MS)

def pedersen_verify(rank, nat, nes):
    return round(2 * 2 ** rank * pedersen_per_coefficient(rank) + 2 * (nat + nes + 5) * SCALAR_MULT_WORD_MULTS)

points = []

# Pedersen-IPA: the checked-in cycle design, over the configurations the circuit budget
# allows at each rank, with the fixed circuits as today or packed into the rank's budget.
for rank in (13, 14, 15, 16):
    for packing in (False, True):
        Fn, Fm = fixed_counts(rank, packing)
        if packing and (Fn, Fm) == (19, 14):
            continue
        Emax = max_endoscalings(rank)
        for E in sorted({e for e in (4, 6, 8, 12, 16, 24, 32, Emax) if e <= Emax}):
            for binders in range(min_binders(rank), 6):
                for H in (2, 4):
                    r = size(Fn, Fm, binders, E, E, rank, H)
                    if r is None:
                        continue
                    total, nat, nes = r
                    commitments = nat + 2 + nes + 2
                    # Rank, endoscalings per step and header are constants in the code; a
                    # binder that binds more than two challenges, or merged fixed circuits,
                    # are code changes within the protocol.
                    change = "code" if (packing or binders < 5) else "none"
                    # Shown at the 128-bit floor only: about 126 classical bits, no post-quantum
                    # security (see the security-floor section below).
                    points.append(dict(
                        family="pedersen", pq=False, rank=rank, E=E, binders=binders, H=H, floor=128,
                        groups=None, packing=packing, circuits=nat + nes, change=change, zk=None, hashes="poseidon",
                        bytes=total,
                        prover=round(commitments * 2 ** rank * pedersen_per_coefficient(rank)),
                        step_prover=round(2 ** rank * pedersen_per_coefficient(rank)), fold=0,
                        accumulation=2 * (nat + nes + 5),         # base-field atoms absorbed per merge
                        gates=gates_per_merge(binders, E, E, nat, nes),
                        verify=pedersen_verify(rank, nat, nes),
                        folded=nat + nes + 5,
                        label=f"rank {rank}, {E} endoscalings/step, {binders} binder{'s' if binders != 1 else ''}, header {H}"
                            + (", packed" if packing else ""),
                    ))

# ---- Security floor ----------------------------------------------------------------
# Akita's catalog and ARC's openings are sized at a 128-bit floor under the ADPS16 quantum
# core-SVP model. For a 150-bit floor, Akita's commitment ranks are re-derived from width
# tables generated at that floor by Akita's own estimator with a 150-bit policy
# (work/akita-150-tables.sh; tables in work/akita-150-out/, 2026-10-15). For each of the 115
# weakest Module-SIS instances in the shipped catalog's security report
# (work/akita-pasta-out/catalog-security.tsv), the smallest module rank whose maximum secure
# width covers the instance's width is taken at both floors, with the instance mapped through
# the modulus that the variant commits over. The ratio of the summed ranks is the factor.
# With the catalog's own mix of q128, q64 and q32 cells the ranks sum to 121 at 128 bits and
# 154 at 150 bits, factor 1.27: 32 instances go from rank 1 to 2 and one from 2 to 3. Over a
# 64-bit modulus (q64 and Goldilocks give identical tables for these cells) the sums are 185
# and 215, factor 1.16: 12 go from 1 to 2, 17 from 2 to 3, one from 4 to 5. Over Pallas the
# sums are 117 and 118, factor 1.01: one instance goes from 1 to 2, the rest sit at the width
# cap at both floors. The factor is applied to the prover's rows term and to the inner images'
# share of the opening and of the verifier's work (IMAGE_SHARE below). The figures are not re-planned:
# the planner's policy and its runtime tables are fixed at 128 bits, and the compression
# maps, which reach 147 bits, are assumed to hold at rank one. WHIR's proofs are 18% larger
# at 150 bits over both fields (work/whir-sweep-150.log); ARC's openings scale with the floor.
# Pedersen-IPA over Pasta has about 126 classical bits (Pollard rho on a group of order near
# 2^254) and no post-quantum security, so it is shown at the 128-bit floor only, as the
# conventional pre-quantum baseline, and drops out at 150 bits.
RANK_SCALE_150 = {"fp128": 1.27, "goldilocks": 1.16, "pasta_q64": 1.16, "pasta_sis": 1.01, "pasta": 1.01}
RANK_SCALE = {128: {v: 1.0 for v in RANK_SCALE_150}, 150: RANK_SCALE_150}
WHIR_SCALE = {128: 1.0, 150: 1.18}
FLOORS = (128, 150)
# The share of the opening, and of the verifier's work, that scales with the commitment rank:
# the terminal's clear inner images t_i, n_A d_A coordinates per block, 1,344 at the shipped
# 2^14 geometry (seven blocks of rank 3 over ring dimension 64; pasta-proof-size.md §6.1). The
# bits of t are set by Module-SIS, so at a 64-bit modulus twice the coordinates at half the
# width cost the same bytes, and the variant with Pasta images at SIS size prices them at 128
# bits; the "Pasta for everything" variant reveals them as 32-byte field elements. The
# non-terminal images are compressed to 128 bytes and do not scale. The verifier's work is
# taken to divide as the message does. Over the opening at K = 0: 33% at the 128-bit field,
# 35% on Goldilocks, 30% with 64-bit commitments, 26% with Pasta images at SIS size, and 42%
# with Pasta for everything.
IMAGE_COORDS = 1344
IMAGE_COORD_BYTES = {"fp128": 16, "goldilocks": 16, "pasta_q64": 16, "pasta_sis": 16, "pasta": 32}
IMAGE_SHARE = {v: IMAGE_COORDS * IMAGE_COORD_BYTES[v] / AKITA[v][0] for v in IMAGE_COORD_BYTES}

def rank_factor_share(variant, factor):
    """The multiplier on the opening, or on the verifier's work, when the rank grows by `factor`."""
    return 1 + IMAGE_SHARE[variant] * (factor - 1)

def floor_label(floor):
    return ", 150‑bit" if floor == 150 else ""

# Akita: no cycle, so endoscalings and binders do not exist. The committed groups are the
# stages plus one batch of every step circuit's witness; the number of step circuits follows
# from the merge circuit's gate estimate and the rank's budget.
for variant, hp in itertools.product(("fp128", "goldilocks", "pasta_q64", "pasta_sis", "pasta"), HASH_POLICIES):
    K = STAGES + 1
    for floor in FLOORS:
        for zk in (False, True):
            for rank in (13, 14, 15, 16):
                circuits = akita_circuits(variant, K, rank, zk, hp)
                if circuits is None:
                    continue  # the per-circuit claim's hashing exceeds this rank's budget
                gates = akita_merge_gates(variant, K, circuits, zk, hp)
                atoms = akita_atoms(variant, K, circuits, zk)
                log_len = rank + math.log2(circuits)  # the decider's accumulator is at the ordinary length, masked or not
                for H in (2, 4):
                    rank_scale = RANK_SCALE[floor][variant]
                    # The floor's factor enters the opening and the verifier through the inner
                    # images' share of each. The masked rank does not: it binds the accumulation
                    # matrix, whose rows term the prover pays in ajtai_per_coefficient, while the
                    # terminal's images are under the terminal's own matrix (see MASK_RANK).
                    opening = akita_bytes(variant, K - 1, log_len) * rank_factor_share(variant, rank_scale)
                    instance = K * 128 + 2 * K * 32 + 2 * H * 32 + 4 + circuits * CLAIM_BYTES[variant]
                    # The 128-bit and Goldilocks variants are Akita's published parameter sets;
                    # the Pasta variants need a modulus profile Akita lacks, and the 64-bit
                    # commitment variant a decoupled commitment modulus.
                    change = "none" if variant in ("fp128", "goldilocks") else "design"
                    points.append(dict(
                        family=variant, pq=True, rank=rank, E=None, binders=None, H=H, floor=floor, hashes=hp,
                        groups=K, packing=None, circuits=circuits, change=change, zk=zk,
                        bytes=round(opening + instance),
                        prover=round(circuits * 2 ** rank * ajtai_per_coefficient(variant, zk, rank_scale)),
                        step_prover=round(2 ** rank * ajtai_per_coefficient(variant, zk, rank_scale)),
                        fold=round(mask_fold(variant, K, rank, rank_scale) + circuits * 2 ** rank * ajtai_per_coefficient(variant, zk, rank_scale)) if zk else 0,
                        accumulation=atoms,
                        gates=gates,
                        verify=akita_verify(variant, log_len, zk, rank_factor_share(variant, rank_scale)),
                        folded=K,
                        label=f"rank {rank}, {circuits} circuit{'s' if circuits != 1 else ''}, {K} groups, header {H}"
                            + HASH_LABEL[hp] + (", ZK" if zk else "") + floor_label(floor),
                    ))

# WHIR (ePrint 2024/1586), hash-based, over a 255-bit field such as Pasta's, which is FFT
# friendly. Measured with the reference implementation (WizardOfMenlo/whir at afec1fa; the
# rows are in estimates/whir-sweep.tsv): 128-bit security in the proven Johnson regime, since
# the capacity conjectures were refuted over large fields in 2025 (ePrint 2026/1367 §5.4);
# 20 bits of grinding; folding factor 4. Per rate: proof bytes at 2^17, the growth per
# doubling of the witness, the verifier's hashes at 2^17, and the queries over all rounds,
# which is also the growth in hashes per doubling, one more Merkle level per query.
# The measurements are in estimates/whir-sweep-grind.tsv (2026-10-21, the same binary, --reps
# 3): both fields, rates 1/2 to 1/64, and a maximum proof-of-work of 0, 16, 20 or 24 bits in
# the query phase, at 2^17 and 2^18. The rate-1/8, 20-bit rows reproduce the earlier sweep
# (122.7 and 128.0 KiB over the 256-bit field). Over Goldilocks the claims are in its cubic
# extension, which 128-bit security needs (the quadratic extension cannot reach it).
RATES = ("1/2", "1/4", "1/8", "1/16", "1/32", "1/64")
GRIND_DEFAULT = 16  # the default of the functions below; the page picks per row
WHIR_MEAS = {}
with (HERE / "estimates" / "whir-sweep-grind.tsv").open() as f:
    header = f.readline().rstrip("\n").split("\t")
    for line in f:
        row = dict(zip(header, line.rstrip("\n").split("\t")))
        key = ("pasta" if row["field"] == "Field256" else "gold", int(row["pow_max"]), row["rate"])
        WHIR_MEAS.setdefault(key, {})[int(row["log2_size"])] = dict(
            bytes=float(row["proof_KiB"]) * 1024, hashes=float(row["verifier_khashes"]) * 1000,
            queries=int(row["queries"]), first=int(row["first_samples"]))

# The grinding settings are the ones measured for both fields at 2^17 and 2^20.
GRINDS = tuple(sorted({g for (s, g, r), m in WHIR_MEAS.items() if 17 in m and 20 in m
                       if all((s2, g, r2) in WHIR_MEAS and 20 in WHIR_MEAS[(s2, g, r2)]
                              for s2 in ("pasta", "gold") for r2 in RATES)}))

def whir_meas(sizes, grind, rate):
    """(bytes at 2^17, bytes per doubling, verifier hashes at 2^17, queries over all rounds).
    The slope is taken over the three doublings to 2^20, since the page extrapolates up to
    seven doublings and a one-doubling slope carries its measurement noise into every row."""
    m = WHIR_MEAS[(sizes, grind, rate)]
    m17 = m[17]
    far, span = (m[20], 3) if 20 in m else (m[18], 1)
    return m17["bytes"], (far["bytes"] - m17["bytes"]) / span, m17["hashes"], m17["queries"]

# Three hash-based variants. Pasta: the witness, the trees and the merge circuit all over the
# 255-bit field, Poseidon at 288 gates and 35,000 word multiplications per permutation, a leaf
# of 16 elements in four permutations. Goldilocks: everything over the 64-bit field, with a
# width-12 Poseidon of rate 8 at about 480 gates (118 x^7 boxes of four multiplications) and
# 7,200 word multiplications (the matrix multiplications included), a leaf of 16 elements in
# two permutations, and multiplications at 1.5 words. Hybrid: a Pasta witness committed as
# four 64-bit limbs per coefficient and tested over Goldilocks, with the merge circuit over
# Pasta, so the trees use Pasta's Poseidon over limbs packed three to an element, 16 limbs to
# a leaf in two permutations; a Goldilocks Poseidon verified non-natively in a Pasta circuit
# would cost about 75 times more per node.
# Plonky3 is a STARK toolkit whose commitment layer is univariate FRI over a small prime
# field (BabyBear, KoalaBear, Mersenne31 or Goldilocks) with Poseidon2 hashing. It is priced
# here over Goldilocks for comparability, under the same ARC accumulation, with Poseidon rather
# than Poseidon2 (its default), and with FRI's decider proof at 1.95 times WHIR's: the WHIR
# paper's measured ratio at matched field, rate and 128-bit security (306 against 157 KiB at
# 2^24, rate 1/2), which follows from FRI's queries scaling as lambda log d against WHIR's
# lambda log log d. Its deployed parameters target about 100 bits under conjectures.
HASH_VARIANTS = {
    "whir":        dict(sizes="pasta", gates=288, native=35000, leaf_perms=4, leaf_bytes=512, elems=1, mult=32, size_factor=1),
    "whir_gold":   dict(sizes="gold", gates=480, native=7200, leaf_perms=2, leaf_bytes=128, elems=1, mult=1.5, size_factor=1),
    "whir_hybrid": dict(sizes="gold", gates=288, native=35000, leaf_perms=2, leaf_bytes=128, elems=4, mult=1.5, size_factor=1),
    "plonky3":     dict(sizes="gold", gates=480, native=7200, leaf_perms=2, leaf_bytes=128, elems=1, mult=1.5, size_factor=1.95),
}

def hv(variant, hp):
    """The variant's hash figures under the policy: its Poseidon (`gates` and `native` per
    permutation, `leaf_perms` permutations per first-round leaf), or BLAKE3 at one
    compression per node, with the leaf's bytes (16 elements of the witness's field: 32-byte
    Pasta elements, or 8-byte Goldilocks words or limbs) in 64-byte blocks."""
    v = HASH_VARIANTS[variant]
    if hp == "poseidon":
        return v
    return dict(v, gates=BLAKE3_GATES, native=BLAKE3_NATIVE, leaf_perms=v["leaf_bytes"] / BLAKE3_BLOCK)

def whir_bytes(variant, rate, log_elems, grind=GRIND_DEFAULT):
    v = HASH_VARIANTS[variant]
    b17, slope, _, _ = whir_meas(v["sizes"], grind, rate)
    return (b17 + slope * (log_elems - 17)) * v["size_factor"]

# A hash commitment is not homomorphic, so Ragu's split accumulation does not apply. ARC
# (ePrint 2024/1731) accumulates Reed-Solomon proximity claims instead: its verifier checks
# t = 2 lambda / log2(1/rate) Merkle openings per input in the proven, Johnson-bound regime
# (the factor 2 goes away only under the list-decoding conjectures refuted in 2025), each a
# path through the accumulator's tree over N/rate elements, plus a few field operations per
# opening. A merge has two inputs. A Merkle node is one Poseidon permutation, 288 gates in the
# circuit and about 35,000 word multiplications natively over a 255-bit field, with the
# S-boxes and the matrix multiplications all full multiplications. The accumulation prover
# encodes the step's witness by FFT over N/rate points and builds the Merkle trees of the
# witness and of the new accumulator, N/(16 rate) leaves each, four permutations per leaf and
# one per inner node. The decider checks the final accumulator with a WHIR proof, which is
# the compressed proof; at the root nobody has yet combined the two child accumulators with
# the root's own witness, so the decider's proof opens those three oracles in its first
# round, each under its own Merkle root (Ulrich Haböck), and two first-round trees are added
# to the measured stand-alone proof at its first-round sample count, with pruned paths, in
# bytes and in the verifier's hashes. WARP (ePrint 2025/753) has the same opening count for Reed-Solomon
# codes, (1 + l^2) t against ARC's l t for l inputs, and a linear-time prover only with
# linear-time codes, which does not help here, since the cost is the hashing, not the encoding.
ARC_ATOMS = 40  # the accumulators' roots and claims, absorbed per merge

# Grinding (Ulrich Haböck, 2026-10-21): g bits of proof of work in the query phase let the
# queries carry lambda - g bits, so t = 2 (lambda - g) / log2(1/rate). The prover pays 2^g
# evaluations of the grinding hash per merge, and the merge circuit checks one per input. The
# grinding hash is taken as the variant's own Merkle hash, so that the check is one node in the
# circuit: for the Poseidon variants 2^16 permutations are under a percent of the merge's
# prover and 2^20 about five percent; for the BLAKE3 families 2^20 compressions are about half
# a merge's prover, so 16 bits is the setting at which the prover does not appreciably pay.
BLAKE3_NATIVE = 200  # word multiplications per compression natively, about 70 ns at 3e9

def arc_openings(rate, floor=128, grind=GRIND_DEFAULT):
    return math.ceil(2 * (floor - grind) / math.log2(int(rate.split("/")[1])))

def arc_merge_gates(variant, rate, log_len, floor=128, grind=GRIND_DEFAULT, hp="blake3"):
    v = hv(variant, hp)
    inv = int(rate.split("/")[1])
    depth = log_len + math.log2(v["elems"]) + math.log2(inv)  # path nodes plus the leaf's permutations
    t = arc_openings(rate, floor, grind)
    hashes = 2 * t * depth + (2 if grind else 0)  # plus the grinding check per input
    return hashes * v["gates"] + 2 * t * 16 + 2000

def arc_circuits(variant, rate, rank, floor=128, grind=GRIND_DEFAULT, hp="blake3"):
    circuits = 1
    for _ in range(30):
        new = math.ceil(arc_merge_gates(variant, rate, rank + math.log2(circuits), floor, grind, hp) / gate_budget(rank))
        if new == circuits:
            return circuits
        circuits = new
    return circuits

def grind_prover(native, grind):
    """The grinding's word multiplications per merge: 2^g evaluations of the grinding hash."""
    return 2 ** grind * native if grind else 0

def arc_per_coefficient(variant, rate, log_len, hp="blake3"):
    """Word multiplications per Pasta-sized coefficient of the step's witness: the encoding
    FFT over the committed elements divided by the rate, and the Merkle trees of the witness
    and of the new accumulator."""
    v = hv(variant, hp)
    inv = int(rate.split("/")[1])
    log_elems = log_len + math.log2(v["elems"])
    fft = v["elems"] * inv * 0.5 * (log_elems + math.log2(inv)) * v["mult"]
    tree = v["elems"] * inv / 16 * (v["leaf_perms"] + 1) * v["native"]
    return fft + 2 * tree

# Zero knowledge for WHIR and FRI, measured with Plonky3's HVZK-WHIR (eprint 2026/391 composed
# into a hiding commitment: interleaved zero-knowledge encoding, masked sumchecks, HVZK code
# switching, a masked base case), its `zk_overhead` benchmark at commit f98331687 on one core:
# KoalaBear with a quintic extension, folding 4, rate 1/4, 100 bits per phase under the
# capacity bound, 16 bits of grinding; masks of message length 16 at rate 1/32. Proofs: 30,914
# against 103,583 bytes at 2^16 and 37,490 against 110,139 at 2^18, an additive 73 KB; prover
# on mains with the native CPU flag 30.7 against 53.0 ms at 2^16 and 121.1 against 139.5 ms at
# 2^18, an additive 19 to 22 ms, 15% at 2^18 and halving per doubling (a first run on battery
# without the flag gave 12%). The additive bytes are mask spot checks, 21 per mask
# group with about five groups and paths of about twelve levels (the hiding security report),
# about 1,300 hash checks per proof, which the recursive merge and the decider pay; they are
# scaled with the floor as queries are. Over Pasta the mask symbols are larger than the
# measured 20-byte extension elements, which is not applied. Whether ARC's accumulation
# preserves zero knowledge has not been examined; its merge is left unchanged.
ZK_BYTES = 73000
ZK_HASHES = 1300
ZK_PROVER = (0.15, 18)

def zk_bytes(floor, zk):
    return ZK_BYTES * floor / 100 if zk else 0

def zk_hashes(floor, zk):
    return ZK_HASHES * floor / 100 if zk else 0

def zk_prover(log_elems, zk):
    return 1 + ZK_PROVER[0] * 2 ** (ZK_PROVER[1] - log_elems) if zk else 1

def whir_verify_hashes(variant, rate, log_elems, floor, grind=GRIND_DEFAULT):
    _, _, hashes, queries = whir_meas(HASH_VARIANTS[variant]["sizes"], grind, rate)
    return ((hashes + queries * (log_elems - 17))
            * (1.15 if floor == 150 else 1) * (2.07 if variant == "plonky3" else 1))

ARC_DECIDER_TREES = 3  # the decider's first round opens the two child accumulators and the root's witness
WHIR_FOLD = 16  # the reference implementation's folding factor: elements per first-round leaf
ELEM_BYTES = {"pasta": 32, "gold": 24}  # a committed element: the 255-bit field; Goldilocks's cubic extension

def whir_extra_trees(variant, rate, log_elems, grind=GRIND_DEFAULT, hp="blake3"):
    """(bytes, hashes) that the decider's batched first round adds to a stand-alone proof: the
    extra oracles' opened leaves and paths at the measured first-round sample count, the paths
    pruned as a multiproof (the optimizer's expected count, which also stands in for a Merkle
    cap)."""
    v = hv(variant, hp)
    m = WHIR_MEAS[(v["sizes"], grind, rate)][17]
    height = round(log_elems + math.log2(int(rate.split("/")[1])) - math.log2(WHIR_FOLD))
    path_hashes = frib.expected_multiproof_hashes(height, m["first"])
    extra = ARC_DECIDER_TREES - 1
    return (extra * (m["first"] * WHIR_FOLD * ELEM_BYTES[v["sizes"]] + path_hashes * 32) * v["size_factor"],
            extra * (path_hashes + m["first"] * v["leaf_perms"]))

for variant, hp in itertools.product(HASH_VARIANTS, HASH_POLICIES):
    for grind in GRINDS:
        for floor in FLOORS:
            for zk in (False, True):
                for rate in RATES:
                    for rank in (13, 14, 15, 16):
                        circuits = arc_circuits(variant, rate, rank, floor, grind, hp)
                        log_len = rank + math.log2(circuits)
                        log_elems = log_len + math.log2(HASH_VARIANTS[variant]["elems"])
                        native = hv(variant, hp)["native"]
                        extra_bytes, extra_hashes = whir_extra_trees(variant, rate, log_elems, grind, hp)
                        for H in (2, 4):
                            points.append(dict(
                                family=variant, pq=True, rank=rank, E=None, binders=None, H=H, floor=floor, grind=grind, hashes=hp,
                                groups=2, packing=None, circuits=circuits, change="design", zk=zk, rate=rate,
                                bytes=round((whir_bytes(variant, rate, log_elems, grind) + extra_bytes) * WHIR_SCALE[floor] + zk_bytes(floor, zk) + 2 * 32 + 10 * 32 + 2 * H * 32 + 4),
                                prover=round(2 ** log_len * arc_per_coefficient(variant, rate, log_len, hp) * zk_prover(log_elems, zk) + grind_prover(native, grind)),
                                step_prover=round(2 ** rank * arc_per_coefficient(variant, rate, log_len, hp) * zk_prover(log_elems, zk)), fold=0,
                                accumulation=ARC_ATOMS,
                                gates=round(arc_merge_gates(variant, rate, log_len, floor, grind, hp)),
                                verify=round((whir_verify_hashes(variant, rate, log_elems, floor, grind) + extra_hashes + zk_hashes(floor, zk)) * native + 1e6),
                                folded=2,
                                label=f"rank {rank}, rate {rate}, {arc_openings(rate, floor, grind)} openings/input, {circuits} circuits, header {H}" + HASH_LABEL[hp] + (", ZK" if zk else "") + floor_label(floor),
                            ))

# Binary-field systems: Flock (arXiv 2607.27491) and Binius64 on the FRI-Binius and Ligerito
# commitments, Boolean R1CS over 𝔽₂ with claims in 𝔽₂^128 and a bit-oriented hash. They have
# no Pasta circuits, so the merge is priced in its own terms: ARC's openings as for the other
# hash-based variants, each path node a BLAKE3 compression of about 2^13 AND gates, so the
# merge is a Boolean witness of that many gates, and there is no rank. Proof bytes come from
# Ulrich Haböck's FRI-Binius proof-size optimizer (frib_optimizer.sage, ported beside it as
# frib_optimizer.py): the floor's security in the list-decoding regime with the largest list
# that the correlated-agreement bound allows, up to 2^15, the row's grinding, and the folding
# schedule that minimises the compressed proof with Merkle-cap multiproofs, interpolated
# between the whole witness sizes around the merge's. Three designs: the witness packed into
# 𝔽₂^256, which is also the field of the folding and sum-check challenges; the witness
# packed into 𝔽₂^64 with the challenges drawn from its cubic extension 𝔽₂^192, which is the
# field that the agreement bound sees, as Plonky3's FRI pairs a base field with an extension;
# and the witness packed straight into GF(2^191), a prime-degree field with a trinomial and
# no subfields (Ulrich Haböck's suggestion, for the arithmetic). Ring switching (ePrint
# 2024/504, §1.3) packs 2^kappa bits into each element and assumes a power-of-two degree over
# 𝔽₂, which 192 and 191 are not, so the second design packs into 𝔽₂^64 (kappa = 6) and needs
# the ring-switching sum-check restated over L tensor 𝔽₂^64, and the third lays the witness
# out as 191 columns that the PIOP batches and switches in one step of degree 191; both are
# design changes that the paper does not write down. A 128-bit field cannot reach 128 bits
# in any regime at these sizes. The first-round oracle has the same bytes under any packing,
# so a query opens 32 bytes per 256 witness bits there and the challenge field's bytes per
# element after it. The prover is counted in word multiplications, a 64-bit carry-less
# multiplication as one: Flock's measured 82,100 BLAKE3 compressions per second on one core
# for the PIOP (its Table 5: witness generation 5%, zero-check and lincheck 46%, which run
# over 𝔽₂^128 and are scaled by half the challenge field's multiplication cost over 𝔽₂^128's);
# and for the commitment the additive NTT, the first tree, the ring-switching products, the
# folds, the folded trees, and the sum-checks, counted in carry-less multiplications, hashes,
# and word XORs, and scaled to the FRI-Binius paper's single-threaded 144 ms commitment and
# 160 ms opening at 2^28 bits, rate 1/2, over 𝔽₂^128 (its Table 2). The ARC rows pay the NTT,
# two trees, and the ring switching; the recursive rows a full proof. The decider's verifier
# is the proof's authentication and leaf hashes at BLAKE3's native cost plus its field
# multiplications. Zero knowledge comes in two variants. The full mask is Diamond's
# binary-field construction (ePrint 2025/1015), which is the optimizer's own zk option: a
# random polynomial of witness size under the same Merkle root as the witness, opened with it
# in an extra first round, and the commitment doubled. The Zook-style variant (ePrint
# 2026/391) is derived, not measured: the main oracle's zero-knowledge encoding costs nothing
# in the proof (its random coefficients fit the witness padding); each folding round's
# sum-check variables get a group of masks of four coefficients (the round polynomials'
# degree plus one), each with its own zero-knowledge randomness, encoded at rate 1/256 and
# spot-checked floor/8 times through a pruned multiproof; the ring-switching claim's revealed
# element of the tensor algebra gets a mask of 2^kappa coefficients; and the terminal's base
# case is a full mask of the terminal's size. FRI-Binius has no code switching and no
# out-of-domain samples, which are what make WHIR's Zook masks large (their message holds the
# previous encoding's randomness, Theorem 10.2), so its masks are small; they belong to the
# proof, not to the oracles, so the ARC decider's three trees do not multiply them. The
# ring-switching mask is this page's design, not the paper's; the ARC merge is left unchanged,
# as for WHIR.
# The designs, keyed by the challenge field's bits: the packing degree over 𝔽₂ (what the ring
# switching handles, in one step or two), the NTT twiddle's cost in carry-less
# multiplications (a 32-bit subfield twiddle in the tower fields, one per 64-bit limb; a
# full-field twiddle in GF(2^191), which has no subfield to hold the evaluation domain), and
# the row's label. A GF(2^191) multiplication is six limb products and one cheap reduction by
# the trinomial x^191 + x^9 + 1, against the tower's six limb products, six limb reductions
# and a cubic reduction; the limb counts are the same.
F2_DESIGNS = {
    256: dict(pack=256, twiddle=4, label="256-bit field"),
    192: dict(pack=64, twiddle=1, label="64-bit packing, 192-bit field"),
    191: dict(pack=191, twiddle=7, label="191-bit field, direct packing"),
}
F2_LIST_CAP = 15
F2_FIRST_BYTES = 32  # opened bytes per 256 witness bits in the first round, under any packing
CLMULS = {64: 1, 128: 4, 191: 7, 192: 8, 256: 11}  # 64-bit carry-less multiplications per field multiplication: Karatsuba over the limbs, plus the reductions
KARATSUBA_ANDS = {128: 3 ** 7, 191: 6 * 3 ** 6, 192: 6 * 3 ** 6, 256: 3 ** 8}  # AND gates per field multiplication in a Boolean circuit

def elem_bytes(bits):
    return (bits + 7) // 8

def limbs(bits):
    return (bits + 63) // 64
XOR_WEIGHT = 1 / 8  # a 64-bit word XOR against a word multiplication: the vector units do several per cycle
NTT_STAGES_SAVED = 4  # butterfly stages that the paper's interleaving saves in the commitment (§5)
FLOCK_PIOP_SHARE = (0.05, 0.464)  # of Flock's prover: witness generation; zero-check and lincheck (Table 5, BLAKE3)
FRIB_MEASURED_MS = (144, 160)  # FRI-Binius Table 2: single-threaded commit and open at 2^28 bits, rate 1/2, 𝔽₂^128
BLAKE3_ANDS = 8192
BLAKE3_PER_SECOND = 82100
WORD_MULTS_PER_SECOND = 3e9
ZK_LABEL = {None: "", "mask": ", ZK, full mask", "zook": ", ZK, Zook-style, derived"}
ZOOK_MASK_COEFFS = 4  # a sum-check mask: the round polynomials' degree plus one
ZOOK_MASK_RATE_BITS = 8  # the mask code's rate, 1/256

def clmuls(a, b):
    """Carry-less multiplications for the product of an a-bit and a b-bit field element."""
    return CLMULS[a] if a == b else limbs(a) * limbs(b)

def zook_masks(rounds, terminal, floor, chal, pack):
    """(bytes, hashes, prover word multiplications) of Zook-style masking: per folding round a
    group of one mask per folded variable, the ring-switching claim's mask of 2^kappa
    coefficients, each mask with floor/8 random coefficients of its own, encoded at rate
    1/256 and spot-checked floor/8 times with pruned paths, plus the masks' claimed sums and
    the terminal's full mask; the prover encodes and hashes the masks."""
    tzk = math.ceil(floor / ZOOK_MASK_RATE_BITS)
    elem = elem_bytes(chal)
    groups = [(r["ell"], ZOOK_MASK_COEFFS) for r in rounds] + [(1, pack)]  # (masks per leaf, message length)
    bytes_, hashes, ops = terminal * elem, 0, 0
    for masks, length in groups:
        positions = (length + tzk) << ZOOK_MASK_RATE_BITS
        height = math.ceil(math.log2(positions))
        paths = frib.expected_multiproof_hashes(height, tzk)
        bytes_ += tzk * masks * elem + paths * 32 + masks * elem
        hashes += paths + tzk
        ops += masks * positions * height / 2 * limbs(chal) + positions * masks * elem / 64 * BLAKE3_NATIVE
    return bytes_, hashes, ops

def f2_ops(bits, rate_bits, chal, pack, rounds, twiddle):
    """Operation counts of the FRI-Binius prover on `bits` witness bits, in word
    multiplications: the additive NTT of the first oracle, at `twiddle` carry-less
    multiplications per butterfly; its tree; the ring switching (two passes of a
    challenge-field element by each bit, the tensor expansion and its sum-check over the
    packed coefficients); and the folds (the first step of the first round over the packing
    field), the folded trees, and the BaseFold sum-check."""
    first_bytes = bits * 2 ** rate_bits / 8
    n = first_bytes * 8 / pack
    ntt = n * (math.log2(n) - NTT_STAGES_SAVED) / 2 * twiddle
    tree = (first_bytes / 64 + first_bytes / (F2_FIRST_BYTES << rounds[0]["ell"])) * BLAKE3_NATIVE
    packed = bits / pack
    switch = 2 * bits * limbs(chal) * XOR_WEIGHT + 4 * packed * CLMULS[chal]
    fold = 3 * packed * CLMULS[chal]
    for i, r in enumerate(rounds):
        units = 2 ** (r["height"] + r["ell"])  # the round's oracle, in 256-bit units
        if i == 0:
            symbols = units * 256 / pack
            fold += symbols / 2 * (clmuls(pack, chal) + CLMULS[chal])
        else:
            fold += units * CLMULS[chal] + (units * elem_bytes(chal) / 64 + units / 2 ** r["ell"]) * BLAKE3_NATIVE
    return dict(ntt=ntt, tree=tree, switch=switch, fold=fold)

FRIB_CALIB_ROUNDS = [dict(ell=2, height=m - 2 + 1) for m in range(20, 0, -2)]  # the paper's folding factor 4
_calib = f2_ops(2 ** 28, 1, 128, 128, FRIB_CALIB_ROUNDS, twiddle=2)
F2_SCALE = (FRIB_MEASURED_MS[0] * WORD_MULTS_PER_MS / (_calib["ntt"] + _calib["tree"]),
            FRIB_MEASURED_MS[1] * WORD_MULTS_PER_MS / (_calib["switch"] + _calib["fold"]))

def f2_piop(bits, chal):
    """Flock's measured prover less its commitment, per witness bit (one per AND gate), with
    the zero-check and lincheck scaled by half the challenge field's multiplication cost over
    𝔽₂^128's."""
    per_gate = WORD_MULTS_PER_SECOND / BLAKE3_PER_SECOND / BLAKE3_ANDS
    gen, check = FLOCK_PIOP_SHARE
    return bits * per_gate * (gen + check * (1 + (CLMULS[chal] / CLMULS[128] - 1) / 2))

@functools.lru_cache(maxsize=None)
def frib_at(w, rate_bits, floor, grind, chal, trees, zk):
    """The optimizer's proof of 2^w witness bits in the design with the challenge field
    `chal`, opening `trees` oracles in its first round, with the full mask if `zk`, with the
    largest list that its agreement check admits: compressed bytes, queries, the list's log,
    authentication hashes, opened bytes, the verifier's field multiplications (the ring
    switching, the folds per query, the sum-checks, the mask's combination), and the prover's
    counts over the folding rounds (the mask's commitment is charged in `f2_prover`)."""
    pack, twiddle = F2_DESIGNS[chal]["pack"], F2_DESIGNS[chal]["twiddle"]
    lb = next((lb for lb in range(F2_LIST_CAP, 0, -1)
               if frib.CAT_bits(w + rate_bits, lb, chal) <= -floor), 0)
    out = frib.optimize(w, rate_bits, floor, lb, grind, zk="true" if zk else "false", field_bits=chal,
                        first_bytes=F2_FIRST_BYTES, first_trees=trees)
    rounds = out["rounds"]
    folds = rounds[1:] if zk else rounds  # the mask's opening round folds nothing
    packed_log = w - math.log2(pack)
    return dict(bytes=out["compressed"], queries=out["queries"], lb=lb,
                auth=sum(r["uncompressed_auth_bytes"] for r in rounds) / frib.HASH_BYTES,
                opened=sum(r["opened_bytes"] for r in rounds),
                field_mults=2 * packed_log * pack + out["queries"] * (sum(2 ** r["ell"] for r in folds) + (1 if zk else 0)) + 6 * packed_log,
                ops=f2_ops(2 ** w, rate_bits, chal, pack, folds, twiddle),
                zook=zook_masks(folds, out["terminal_elements"], floor, chal, pack))

def frib_proof(bits, rate, floor, grind, chal, trees, zk=False):
    """The same for a witness of `bits` bits, interpolated between the whole sizes around it:
    bytes, hashes and multiplications linearly in the logarithm, the prover's counts
    geometrically; the queries and the list are the larger size's."""
    rate_bits = int(math.log2(int(rate.split("/")[1])))
    w = math.log2(bits)
    w0 = math.floor(w)
    f = w - w0
    a = frib_at(w0, rate_bits, floor, grind, chal, trees, zk)
    b = frib_at(w0 + 1, rate_bits, floor, grind, chal, trees, zk) if f else a
    lin = lambda k: a[k] + (b[k] - a[k]) * f
    return dict(bytes=lin("bytes"), auth=lin("auth"), opened=lin("opened"), field_mults=lin("field_mults"),
                queries=b["queries"], lb=b["lb"],
                ops={k: a["ops"][k] * (b["ops"][k] / a["ops"][k]) ** f for k in a["ops"]},
                zook=tuple(x + (y - x) * f for x, y in zip(a["zook"], b["zook"])))

def f2_bytes(p, zk):
    """The proof's bytes, with the Zook-style masks when that variant is chosen."""
    return p["bytes"] + (p["zook"][0] if zk == "zook" else 0)

def f2_prover(bits, rate, floor, grind, chal, recursive, zk=None):
    """Word multiplications of the 𝔽₂ prover: Flock's PIOP, the scaled commitment (the NTT
    and two trees with the ring switching for an ARC step; a full proof for a recursive
    step), under zero knowledge the mask's commitment of witness size or the Zook-style
    masks' encoding, and the grinding."""
    p = frib_proof(bits, rate, floor, grind, chal, 1 if recursive else ARC_DECIDER_TREES, zk == "mask")
    ops = p["ops"]
    mask = 2 if zk == "mask" else 1
    if recursive:
        pcs = F2_SCALE[0] * mask * (ops["ntt"] + ops["tree"]) + F2_SCALE[1] * (ops["switch"] + ops["fold"])
    else:
        pcs = F2_SCALE[0] * (mask * (ops["ntt"] + ops["tree"]) + ops["tree"]) + F2_SCALE[1] * ops["switch"]
    if zk == "zook":
        pcs += F2_SCALE[0] * p["zook"][2]
    return f2_piop(bits, chal) + pcs + grind_prover(BLAKE3_NATIVE, grind)

def f2_verify(p, grind, chal, zk=None):
    """The decider's word multiplications: the proof's authentication and leaf hashes, the
    grinding check, the Zook-style masks' spot checks, and its field multiplications."""
    return ((p["auth"] + p["opened"] / 64 + (2 if grind else 0) + (p["zook"][1] if zk == "zook" else 0)) * BLAKE3_NATIVE
            + p["field_mults"] * CLMULS[chal])

def f2_merge(rate, floor, grind=GRIND_DEFAULT):
    """(hashes, AND gates) of a merge: two inputs, ARC's openings, paths through the tree of
    the 𝔽₂^128-packed witness divided by the rate, at its fixed point, plus the grinding
    check per input."""
    inv = int(rate.split("/")[1])
    t = arc_openings(rate, floor, grind)
    hashes = 2 * t * 30
    for _ in range(40):
        ands = hashes * BLAKE3_ANDS
        depth = math.log2(ands / 128 * inv / 16) + 4  # path nodes, plus four compressions for a 256-byte leaf
        new = 2 * t * depth + (2 if grind else 0)
        if abs(new - hashes) < 1:
            break
        hashes = new
    return round(hashes), round(hashes * BLAKE3_ANDS)

# A Pasta gate as committed bits in BitZ's arithmetization, a 255-bit value and a 255-bit
# quotient (see the BitZ section below); the 𝔽₂ family's transaction pricing borrows it.
BITZ_GATE_BITS = 510

for grind in GRINDS:
    for floor in FLOORS:
        for rate in RATES:
            hashes, ands = f2_merge(rate, floor, grind)
            for chal, design in F2_DESIGNS.items():
                for zk in ZK_LABEL:
                    p = frib_proof(ands, rate, floor, grind, chal, ARC_DECIDER_TREES, zk == "mask")
                    for H in (2, 4):
                        points.append(dict(
                            family="flock", pq=True, rank=None, E=None, binders=None, H=H, floor=floor, grind=grind,
                            groups=2, packing=None, circuits=None, change="design", zk=zk is not None, zkv=zk, rate=rate, field=chal,
                            bytes=round(f2_bytes(p, zk) + 2 * 32 + 10 * 16 + 2 * H * 32 + 4),
                            prover=round(f2_prover(ands, rate, floor, grind, chal, False, zk)),
                            # The family has no rank: the transaction measure prices its application as BitZ's,
                            # 510 committed bits per Pasta gate, in steps of 2^13 gates at the merge's per-bit cost.
                            step_prover=round(BITZ_GATE_BITS * 2 ** 13 * f2_prover(ands, rate, floor, grind, chal, False, zk) / ands), fold=0,
                            accumulation=ARC_ATOMS,
                            gates=ands,
                            verify=round(f2_verify(p, grind, chal, zk)),
                            folded=2,
                            label=f"rate {rate}, {design['label']}, list 2^{p['lb']}, {p['queries']} queries, {arc_openings(rate, floor, grind)} openings/input, {hashes:,} BLAKE3, {ands / 1e6:.1f}M AND gates, header {H}" + ZK_LABEL[zk] + floor_label(floor),
                        ))

# ---- Native recursion in place of ARC (Quang Dao, 2026-10-15) ---------------------------
# Each hash-based scheme is also priced with full recursive verification, beside its ARC
# rows: the merge circuit verifies its two input proofs, each step emits a full proof, and
# the decider verifies one proof. The merge's hashing is twice the verifier's Merkle hashes
# at the proof's witness size (the WHIR sweep measured the hashes at 2^17 and the queries
# per doubling), and the witness is the step's circuits, which hold the application at the
# rank and the two verifiers, at a fixed point. The prover makes a full proof: the encoding
# and the tree of the witness, then the folding rounds, each an encoding and a tree of the
# folded polynomial, a geometric series in the folding factor 4, so four thirds of the
# encode-and-commit work against ARC's two trees. The decider's cost is the same verifier.
REC_ARITH_GATES = 10000  # the verifier's sum-check and folding arithmetic, per input proof

def rec_hashes(variant, rate, log_elems, floor, zk=False, grind=GRIND_DEFAULT):
    return whir_verify_hashes(variant, rate, log_elems, floor, grind) + zk_hashes(floor, zk)

def rec_merge_gates(variant, rate, log_len, floor, zk=False, grind=GRIND_DEFAULT, hp="blake3"):
    v = hv(variant, hp)
    log_elems = log_len + math.log2(v["elems"])
    return 2 * rec_hashes(variant, rate, log_elems, floor, zk, grind) * v["gates"] + 2 * REC_ARITH_GATES

def rec_circuits(variant, rate, rank, floor, zk=False, grind=GRIND_DEFAULT, hp="blake3"):
    circuits = 1
    for _ in range(30):
        new = math.ceil(rec_merge_gates(variant, rate, rank + math.log2(circuits), floor, zk, grind, hp) / gate_budget(rank))
        if new == circuits:
            return circuits
        circuits = new
    return circuits

def rec_per_coefficient(variant, rate, log_len, hp="blake3"):
    v = hv(variant, hp)
    inv = int(rate.split("/")[1])
    log_elems = log_len + math.log2(v["elems"])
    fft = v["elems"] * inv * 0.5 * (log_elems + math.log2(inv)) * v["mult"]
    tree = v["elems"] * inv / 16 * (v["leaf_perms"] + 1) * v["native"]
    return (fft + tree) * 4 / 3

for variant, hp in itertools.product(HASH_VARIANTS, HASH_POLICIES):
    for grind in GRINDS:
        for floor in FLOORS:
            for zk in (False, True):
                for rate in RATES:
                    for rank in (13, 14, 15, 16):
                        circuits = rec_circuits(variant, rate, rank, floor, zk, grind, hp)
                        log_len = rank + math.log2(circuits)
                        log_elems = log_len + math.log2(HASH_VARIANTS[variant]["elems"])
                        native = hv(variant, hp)["native"]
                        for H in (2, 4):
                            points.append(dict(
                                family=variant + "_rec", pq=True, rank=rank, E=None, binders=None, H=H, floor=floor, grind=grind, hashes=hp,
                                groups=2, packing=None, circuits=circuits, change="design", zk=zk, rate=rate,
                                bytes=round(whir_bytes(variant, rate, log_elems, grind) * WHIR_SCALE[floor] + zk_bytes(floor, zk) + 2 * 32 + 2 * H * 32 + 4),
                                prover=round(2 ** log_len * rec_per_coefficient(variant, rate, log_len, hp) * zk_prover(log_elems, zk) + grind_prover(native, grind)),
                                step_prover=round(2 ** rank * rec_per_coefficient(variant, rate, log_len, hp) * zk_prover(log_elems, zk)), fold=0,
                                accumulation=ARC_ATOMS,
                                gates=round(rec_merge_gates(variant, rate, log_len, floor, zk, grind, hp)),
                                verify=round(rec_hashes(variant, rate, log_elems, floor, zk, grind) * native + 1e6),
                                folded=2,
                                label=f"rank {rank}, rate {rate}, {round(rec_hashes(variant, rate, log_elems, floor, zk, grind)):,} hashes/input, {circuits} circuits, header {H}" + HASH_LABEL[hp] + (", ZK" if zk else "") + floor_label(floor),
                            ))

# Ligerito's verifier, for the recursion of BitZ: Flock's instantiation (arXiv 2607.27491,
# Appendix C and §5) folds two variables per level, five levels at rates 1/2, 1/4, 1/8, 1/16,
# 1/32 with 218, 106, 71, 53, 43 queries at 100 bits, the queries linear in the security level
# (Remark 10). A query opens a column of four 𝔽₂^128 elements, one hash compression, through a
# path of the level's depth. The nodes are priced as BLAKE3 compressions of about 2^13 AND
# gates, as the 𝔽₂ family's rows price them.
# Flock's implementation hashes with SHA-256 (§2), 31,400 witness bits per compression in its
# arithmetization (BitZ, Table 2) at 42,100 per second: 3.8 times the merge bits and half
# the throughput, for every row of these families alike. BitZ reports that proving many
# hashes with a binary-field SNARK beats its 7,144-bit CM arithmetization, so the hybrid
# merge takes the former. Ligerito's levels have their own rates, so a row's rate applies to
# its proof bytes and, in the ARC rows, to the accumulator's openings, not to the verifier.
LIGERITO_LEVELS = [(2, 218), (4, 106), (8, 71), (16, 53), (32, 43)]
HASH_BITS = BLAKE3_ANDS
HASH_PER_SECOND = BLAKE3_PER_SECOND

def ligerito_hashes(log_bits, floor):
    m = log_bits - 7  # 𝔽₂^128 elements
    total = 0
    for inv, queries in LIGERITO_LEVELS:
        total += queries * floor / 100 * (m - 2 + math.log2(inv) + 1)
        m -= 2
    return total

def ligerito_first_share(log_bits):
    """The first level's share of Ligerito's opened columns and paths, a column as two
    hashes; what the decider's extra first-round trees multiply in the BitZ ARC rows."""
    m = log_bits - 7
    parts = []
    for inv, queries in LIGERITO_LEVELS:
        parts.append(queries * (2 + m - 2 + math.log2(inv) + 1))
        m -= 2
    return parts[0] / sum(parts)

# The 𝔽₂ family's recursive merge verifies the step's own FRI-Binius proof twice: its hashes
# as BLAKE3 compressions and its field multiplications by Karatsuba, at the fixed point.
def f2_rec_merge(rate, floor, grind, chal, zk=None):
    """(hashes, witness bits) of the recursive merge, plus the grinding check per input."""
    bits = 2 ** 25
    hashes = 0
    for _ in range(40):
        p = frib_proof(bits, rate, floor, grind, chal, 1, zk == "mask")
        hashes = 2 * (p["auth"] + p["opened"] / 64 + (p["zook"][1] if zk == "zook" else 0)) + (2 if grind else 0)
        new = hashes * BLAKE3_ANDS + 2 * p["field_mults"] * KARATSUBA_ANDS[chal]
        if abs(new - bits) < 1:
            break
        bits = new
    return round(hashes), round(bits)

for grind in GRINDS:
    for floor in FLOORS:
        for rate in RATES:
            for chal, design in F2_DESIGNS.items():
                for zk in ZK_LABEL:
                    hashes, bits = f2_rec_merge(rate, floor, grind, chal, zk)
                    p = frib_proof(bits, rate, floor, grind, chal, 1, zk == "mask")
                    for H in (2, 4):
                        points.append(dict(
                            family="flock_rec", pq=True, rank=None, E=None, binders=None, H=H, floor=floor, grind=grind,
                            groups=2, packing=None, circuits=None, change="design", zk=zk is not None, zkv=zk, rate=rate, field=chal,
                            bytes=round(f2_bytes(p, zk) + 2 * 32 + 2 * H * 32 + 4),
                            prover=round(f2_prover(bits, rate, floor, grind, chal, True, zk)),
                            step_prover=round(BITZ_GATE_BITS * 2 ** 13 * f2_prover(bits, rate, floor, grind, chal, True, zk) / bits), fold=0,
                            accumulation=ARC_ATOMS,
                            gates=bits,
                            verify=round(f2_verify(p, grind, chal, zk)),
                            folded=2,
                            label=f"rate {rate}, {design['label']}, list 2^{p['lb']}, {p['queries']} queries, {hashes:,} hashes/merge, {bits / 1e6:.0f}M witness bits, header {H}" + ZK_LABEL[zk] + floor_label(floor),
                        ))

# BitZ (ePrint 2026/2141): a hash-based PCS over any finitely generated ring through binary
# fields. The witness is bit-decomposed and committed packed over 𝔽₂^128 with Flock's
# Ligerito; a claim over a ring R is lifted to the integers (a random prime where R is
# large) and proved in the exponent of 𝔽₂^128 by GKR grand products, so the cost is per bit
# and independent of R. With the Universal Constraint Systems of Zinc+ (ePrint 2026/855) the
# application is native over Pasta's field: integer witnesses with ideal membership modulo
# p, projected to a random prime field for the PIOP, so a Pasta gate is a 255-bit value and a
# 255-bit quotient, 510 committed bits. The merge is a hybrid circuit: the two Ligerito
# verifications as SHA-256 over 𝔽₂, and the GKR and PIOP verifiers native over 𝔽₂^128 and the
# projection field, a few thousand constraints that are not counted. The PCS costs are the
# paper's Table 10 (rate 1/2, 100 bits, one thread of a MacBook Air M5) at the committed
# bits, interpolated in their logarithm: prover, verifier, and the proof's non-Ligerito and
# Ligerito parts. The paper's benchmark (albert-garreta/BitZ-PoC at 8ced3b98, one thread,
# this machine on battery, work/bitz-out/) reproduces Table 10's bytes exactly at 2^25 to
# 2^27 and gives the ratios used here. Its Johnson-regime profile cannot reach 128 bits (the
# validator wants more out-of-domain samples), so 128 bits is the unique-decoding regime with
# fold grinding, the paper's own choice above 100 bits: the Ligerito part of the proof is 1.8
# times the 100-bit one, the non-Ligerito part 1.05, the verifier 1.17, the prover the same.
# Rate 1/8 at 128 bits has 0.83 of the Ligerito bytes and 1.25 times the prover of rate 1/2.
# (Confirmed on mains, one and ten threads, 2^25 to 2^28, work/bitz-out/overnight/: this M4
# Max is 1.3 times the paper's M5 on one thread and matches it on ten.)
# Beyond 128 bits the Ligerito bytes and the verifier scale with the floor, as queries do. The
# prover is the grand-product GKR: 120 of the 150 ms at 2^25, with Ligerito at 10 to 30 ms
# (Quang Dao: the prover with grand-product GKR is just really expensive). The PIOP of Zinc+
# adds, per its Table 4, 1.6 times the PCS prover's time on the application's share, 2 ms of
# verifier, and 36 KB of proof. The pairs are (prover ms, verifier ms, non-Ligerito KB,
# Ligerito KB).
BITZ_T10 = {20: (7.31, 0.82, 17.3, 84.1), 21: (12.0, 1.08, 18.2, 92.8), 22: (17.1, 1.46, 19.2, 103),
            23: (24.3, 1.51, 27.7, 120), 24: (47.3, 2.22, 28.7, 133), 25: (79.9, 2.42, 45.8, 144),
            26: (151, 3.38, 46.6, 162), 27: (298, 5.72, 47.6, 176), 28: (537, 6.02, 81.2, 190),
            29: (1094, 9.95, 82.0, 210), 30: (2121, 11.1, 148, 225), 31: (4271, 21.0, 150, 238)}

BITZ_RATE = {"1/2": (1.0, 1.0), "1/8": (0.83, 1.25)}  # (Ligerito bytes, prover) against rate 1/2, measured at 128 bits
BITZ_128 = dict(lig=1.8, nonlig=1.05, verify=1.17, prover=1.0)  # measured, 128 against 100 bits
BITZ_PIOP = dict(prover=1.6, verify_ms=2.0, bytes=36000)

def bitz_t10(log_bits):
    n = min(max(log_bits, 20), 31)
    lo = int(math.floor(n))
    hi = min(lo + 1, 31)
    t = n - lo
    return [a + t * (b - a) for a, b in zip(BITZ_T10[lo], BITZ_T10[hi])]

def bitz_point(mode, rate, rank, floor, H, grind=None):
    app_bits = 2 ** rank * BITZ_GATE_BITS
    inv = int(rate.split("/")[1])
    bits = app_bits + 2 ** 25
    hashes = 0
    for _ in range(40):
        if mode == "rec":
            hashes = 2 * ligerito_hashes(math.log2(bits), floor)
        else:
            depth = math.log2(bits / 128 * inv) + 1
            hashes = 2 * arc_openings(rate, floor, grind or 0) * depth + (2 if grind else 0)
        new = app_bits + hashes * HASH_BITS
        if abs(new - bits) < 1:
            break
        bits = new
    log_bits = math.log2(bits)
    prover_ms, verify_ms, nonlig, lig = bitz_t10(log_bits)
    lig_scale, prover_scale = BITZ_RATE[rate]
    prover_ms *= prover_scale * BITZ_128["prover"] * (1 + BITZ_PIOP["prover"] * app_bits / bits)
    # the decider's extra first-round trees, on the Ligerito part and, as a bound, on the whole verifier
    extra = (ARC_DECIDER_TREES - 1) * ligerito_first_share(log_bits) if mode == "arc" else 0
    proof = (nonlig * BITZ_128["nonlig"] + lig * lig_scale * BITZ_128["lig"] * floor / 128 * (1 + extra)) * 1000 + BITZ_PIOP["bytes"]
    verify_ms = verify_ms * BITZ_128["verify"] * floor / 128 * (1 + extra)
    return dict(
        family="bitz_rec" if mode == "rec" else "bitz", pq=True, rank=rank, E=None, binders=None, H=H,
        floor=floor, grind=grind, groups=2, packing=None, circuits=None, change="design", zk=False, rate=rate,
        bytes=round(proof + 2 * 32 + (10 * 32 if mode == "arc" else 0) + 2 * H * 32 + 4),
        prover=round(prover_ms * WORD_MULTS_PER_MS + grind_prover(BLAKE3_NATIVE, grind or 0)),
        step_prover=round(BITZ_GATE_BITS * 2 ** rank * prover_ms * WORD_MULTS_PER_MS / bits), fold=0,
        accumulation=ARC_ATOMS,
        gates=round(hashes * HASH_BITS),
        verify=round((verify_ms + BITZ_PIOP["verify_ms"]) * WORD_MULTS_PER_MS),
        folded=2,
        label=f"rank {rank}, rate {rate}, {round(hashes):,} hashes/merge, 2^{log_bits:.1f} bits, header {H}" + floor_label(floor),
    )

for mode in ("arc", "rec"):
    for grind in (GRINDS if mode == "arc" else (None,)):
        for floor in FLOORS:
            for rate in ("1/2", "1/8"):
                for rank in (13, 14, 15, 16):
                    for H in (2, 4):
                        points.append(bitz_point(mode, rate, rank, floor, H, grind))

# A bit-decomposed witness over Akita (an internal research draft of 2026-09-23 on Booleanity
# checking via structured modular projections, provisional): the application's values are
# committed one bit per digit over Akita's 64-bit modulus, with Pasta claims through the
# decoupled commitment as the page's 64-bit Akita variant has them, so the same open soundness
# obligation. BitZ's exponent-lift GKR is not needed: Booleanity of the committed table is
# certified over the prime field by one unweighted quadratic identity plus an integer norm
# bound, which a structured random projection supplies by revealing 160 coordinates. The
# draft's single-thread measurements at 2^27 bits over 2^64 - 59 on an M4 Max: the projection
# prover 113 ms, the optimized conventional Booleanity sumcheck 438 ms; verifiers 0.85 and
# 0.023 ms; reduction payloads 2,592 and 1,744 bytes; no commitment opening or hiding. Per
# bit that is 2.5 and 9.8 word multiplications, beside Akita's own 23.7 per digit at the 64-bit
# modulus. The projection verifier scans 3.1 million sampled coefficients, at least a gate
# each in a Pasta merge circuit, so under recursion the sumcheck form is the usable one; the
# projection form is shown for its prover. A value is 255 digits against 85 for the 64-bit
# variant's three-bit digits, so the batched polynomial is three times longer. Revealing the
# projection gives no zero knowledge, and the draft's certificates are conditional and not
# yet formalized.
BITS_PER_VALUE = 255
BOOL_CHECK = {  # (word multiplications per bit, payload bytes, verifier ms, merge gates)
    "projection": (113 / 2 ** 27 * WORD_MULTS_PER_MS, 2592, 0.85, 3_109_760),
    "sumcheck": (437.7 / 2 ** 27 * WORD_MULTS_PER_MS, 1744, 0.023, 3000),

}
for (check, (bool_mults, bool_bytes, bool_verify_ms, bool_gates)), hp in itertools.product(BOOL_CHECK.items(), HASH_POLICIES):
    K = STAGES + 1
    for floor in FLOORS:
        for rank in (13, 14, 15, 16):
            circuits = akita_circuits("pasta_q64", K, rank, False, hp)
            if circuits is None:
                continue
            gates = akita_merge_gates("pasta_q64", K, circuits, False, hp) + bool_gates
            atoms = akita_atoms("pasta_q64", K, circuits, False)
            log_len = rank + math.log2(circuits)
            rank_scale = RANK_SCALE[floor]["pasta_q64"]
            per_digit = ajtai_per_coefficient("pasta_q64", False, rank_scale) / DIGITS["pasta_q64"]
            for H in (2, 4):
                opening = akita_bytes("pasta_q64", K - 1, log_len + math.log2(BITS_PER_VALUE / DIGITS["pasta_q64"])) * rank_factor_share("pasta_q64", rank_scale)
                instance = K * 128 + 2 * K * 32 + 2 * H * 32 + 4 + circuits * CLAIM_BYTES["pasta_q64"]
                points.append(dict(
                    family="bits_q64", pq=True, rank=rank, E=None, binders=None, H=H, floor=floor, hashes=hp,
                    groups=K, packing=None, circuits=circuits, change="design", zk=False,
                    bytes=round(opening + instance + bool_bytes),
                    prover=round(circuits * 2 ** rank * BITS_PER_VALUE * (per_digit + bool_mults)),
                    step_prover=round(2 ** rank * BITS_PER_VALUE * (per_digit + bool_mults)), fold=0,
                    accumulation=atoms,
                    gates=gates,
                    verify=akita_verify("pasta_q64", log_len, False, rank_factor_share("pasta_q64", rank_scale)) + round(bool_verify_ms * WORD_MULTS_PER_MS),
                    folded=K,
                    label=f"rank {rank}, {circuits} circuit{'s' if circuits != 1 else ''}, {K} groups, header {H}, Booleanity by {check}" + HASH_LABEL[hp] + floor_label(floor),
                ))

# Endoscaling capacity beyond the points to walk changes nothing; keep the smallest E of
# each set of identical Pedersen-IPA results.
for p in points:
    p.setdefault("hashes", "any")  # the 𝔽₂ family and BitZ hash with BLAKE3 natively, under either policy

seen, deduped = set(), []
for p in points:
    key = (p["family"], p["rank"], p["binders"], p["H"], p["packing"], p["floor"], p["hashes"], p["bytes"], p["prover"], p["accumulation"])
    if key in seen:
        continue
    seen.add(key)
    deduped.append(p)

points = deduped

# Whether a family supports the Pasta base field natively, which the Ironwood recovery circuit
# needs. It enters the dominance test as a requirement: a configuration that supports Pasta is
# dominated only by one that also does, while one over another field can be dominated by any.
PASTA = {"pedersen": True, "fp128": False, "goldilocks": False, "pasta_q64": True, "pasta_sis": True,
         "pasta": True, "whir": True, "whir_gold": False, "whir_hybrid": True, "plonky3": False,
         "flock": False, "whir_rec": True, "whir_gold_rec": False, "whir_hybrid_rec": True,
         "plonky3_rec": False, "flock_rec": False, "bitz": True, "bitz_rec": True, "bits_q64": True}

for p in points:
    p["pasta"] = PASTA[p["family"]]

def pareto(pts):
    keep = []
    for p in pts:
        dominated = any(q is not p and q["bytes"] <= p["bytes"] and q["prover"] <= p["prover"]
                        and q["accumulation"] <= p["accumulation"] and q["pasta"] >= p["pasta"]
                        and (q["bytes"], q["prover"], q["accumulation"]) != (p["bytes"], p["prover"], p["accumulation"])
                        for q in pts)
        keep.append(not dominated)
    return keep

# ---- Grinding chosen per row ---------------------------------------------------------
# Each bit of grinding removes about one opening in a hundred, so about a percent of the
# circuits and of the prover, while the grinding's own cost doubles; the prover is least where
# the two cross, at 17 to 19 bits for the Poseidon families and 12 to 14 for the BLAKE3 ones,
# and the minimum is shallow. "best per row" takes, for every hash-based configuration, the
# measured setting with the smallest prover; the fixed settings stay selectable.
def grind_key(p):
    return (p["family"], p["floor"], p["zk"], p.get("rate"), p["rank"], p["H"], p.get("packing"), p.get("field"), p.get("zkv"), p["hashes"])

best = {}
for p in points:
    if p.get("grind") is None:
        continue
    k = grind_key(p)
    if k not in best or p["prover"] < best[k]["prover"]:
        best[k] = p

for p in list(best.values()):
    q = dict(p, grind="auto", label=p["label"] + f", {p['grind']}-bit grinding")
    points.append(q)

for (cls, zk, floor), hp in itertools.product(((True, False, 128), (True, True, 128), (True, False, 150), (True, True, 150), (False, None, 128)), HASH_POLICIES):
    for grind in (None, "auto", *GRINDS):
        sub = [p for p in points if p["pq"] == cls and p["zk"] in (zk, None) and p["floor"] == floor
               and p["hashes"] in (hp, "any") and p.get("grind") in (None, grind)]
        for p, on in zip(sub, pareto(sub)):
            p["frontier"] = p.get("frontier", False) or on

for p in points:
    p["family_label"] = LABEL[p["family"]]

budget = [dict(rank=r, gates=gate_budget(r), endoscalings=max_endoscalings(r), binders=min_binders(r),
               fixed=fixed_counts(r, True)) for r in (13, 14, 15, 16)]

data = dict(points=points, labels=LABEL, akita_table=dict(K=AKITA_K, **AKITA), budget=budget, proxies=dict(
    prover="native 64-bit word multiplications for one step's commitments, dense polynomials assumed; see the page",
    per_coefficient={v: round(ajtai_per_coefficient(v)) for v in DIGITS} | {"pedersen_rank14": round(pedersen_per_coefficient(14))},
    accumulation="base-field atoms the merge circuit absorbs per fold: 2 per Pedersen commitment; for Akita 120 sum-check elements plus the compressed images at the variant's atom width",
    gates="gates synthesized across every circuit of one merge: measured for Pedersen-IPA, estimated for Akita",
    verify="the decider's verification in word-multiplication equivalents at 3e9 per second: modelled for Pedersen-IPA, measured for Akita and the hash-based verifiers, see the page",

))
template = (HERE / "pareto-template.html").read_text()
html = template.replace("/*DATA*/", json.dumps(data, separators=(",", ":")))
(HERE / "pareto.html").write_text(html)
pre = [p for p in points if not p["pq"]]
post = [p for p in points if p["pq"] and p["zk"] is not True and p["floor"] == 128]
post_zk = [p for p in points if p["pq"] and p["zk"] is not False and p["floor"] == 128]
print(f"{len(points)} points: {len(pre)} Pedersen-IPA with {sum(p['frontier'] for p in pre)} on its frontier, "
      f"{len(post)} post-quantum with {sum(p['frontier'] for p in post)} on its frontier, "
      f"{len(post_zk)} post-quantum zero-knowledge with {sum(p['frontier'] for p in post_zk)}; wrote pareto.html")

for p in sorted([p for p in points if p["frontier"] and p["floor"] != 150], key=lambda p: (p["pq"], p["hashes"], p["bytes"])):
    print(f"  {p['family']:10} {p['label']}: {p['bytes']:,} B, prover {p['prover']:.3g}, atoms {p['accumulation']}, gates {p['gates']:,}")
