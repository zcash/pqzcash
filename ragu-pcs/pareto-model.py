"""Pareto surface for Ragu as a split-accumulation PCD scheme: Pedersen-IPA today against
Akita under five field/modulus choices, and against the hash-based schemes (WHIR over Pasta,
Goldilocks and a limb hybrid, a Plonky3-style FRI, the Flock/Binius-style binary-field family,
BitZ), each with ARC accumulation and with its own recursion, a draft of BitZ's
arithmetization over Akita, and Flock-style Boolean circuits over Akita's binary groups;
each priced with a conventional hash (BLAKE3) in its circuits and, as an option, with
Poseidon 1.1 (HASH_POLICIES).

Every point is one configuration. Its coordinates are compressed proof bytes, prover commitment work,
and a third measure: the merge circuit's gates or the atoms it absorbs, the decider's
verification work, or the prover's work for a whole transaction; the `proxies` of the page's
data define them. The numbers come from:
  - ragu-size-model.py: the compressed Pedersen-IPA proof, counted from Ragu's structs and
    checked against Ragu's wire format, `CompressedProof::encoded_len` (7,908 bytes of payload
    at the checked-in configuration, 7,936 with the 28-byte envelope, at tachyon-zcash/ragu
    8109a41c), and the circuit budget: the internal circuits' measured gate counts,
    which bound the endoscalings per step and the binders at each rank;
  - the Akita planner runs in estimates/ and work/akita-pasta-out/groups/: opening sizes per
    number of separately committed groups, at each width variant (pasta-proof-size.md §8);
  - the WHIR reference implementation's sweep in estimates/whir-sweep-grind.tsv, Ulrich
    Haböck's FRI-Binius proof-size optimizer (frib_optimizer.py), and the BitZ and Plonky3
    benchmarks described at their families below.

Writes pareto.html next to this script: a self-contained page with the data inlined.
"""

import csv, functools, hashlib, itertools, json, math, pathlib, re, statistics, subprocess, sys
import frib_optimizer as frib


def ceil_div(a, b):
    """a / b rounded up to a whole number, for counts of whole things: the compressions that
    hash a transcript, the words of a byte string, the queries at a floor. A share of a larger
    whole, such as one claim's bytes within a merge's transcript, stays a plain quotient."""
    return int(-(-a // b))


HERE = pathlib.Path(__file__).resolve().parent
# The page's default security floor, in quantum bits under the ADPS16 core-SVP model (the
# user, 2026-11-23); FLOORS below lists both. Pedersen-IPA and the binary-groups row exist at
# the 128-bit floor alone, so their figures name it.
DEFAULT_FLOOR = 147
_model = {}
exec((HERE / "ragu-size-model.py").read_text().split("CHECKED_IN = ")[0], _model)
size, fixed_counts = _model["size"], _model["fixed_counts"]
max_endoscalings, min_binders = _model["max_endoscalings"], _model["min_binders"]
gates_per_merge, gate_budget = _model["gates_per_merge"], _model["gate_budget"]

# Akita opening bytes for one final group of 2^14 coefficients plus K separately committed
# groups of 2^14, from catalog_reprice on the planner's outputs, by security floor. At 128
# bits: the shipped schedule re-planned under the matching pricing (K = 0) and the per-K
# group runs (K > 0); Goldilocks is the fp64 geometry's 61,050 at K = 0, scaled by fp128's
# growth. At 147 bits: the re-plan of 2026-11-12 in a checkout whose single policy, runtime
# width tables and compression cells are retargeted to that floor, the Goldilocks rows
# planned in the fp64 geometry.
RANKS = (12, 13, 14, 15, 16, 17)  # step circuits of 2^(rank-2) gates
HASH_RANKS = (
    13,
    14,
    15,
    16,
)  # the WHIR-type rows depend on the rank only through their circuit count
# The bit arithmetizations' steps commit 2^rank bits or digits, and their merge is nearly a
# fixed cost, so the transaction measure falls with the rank until one step holds the whole
# application: the recovery circuit's 8.4 million bits at rank 24 for BitZ, its 4.7 million
# digits at rank 23 for Kishu. The ranks stop there.
BITZ_RANKS = tuple(range(12, 25))
FRONTEND_RANKS = tuple(range(12, 24))
AKITA_K = [0, 1, 2, 4, 8, 12]
AKITA_128 = {
    "fp128": [65074, 69044, 71066, 69492, 68485, 70404],
    "goldilocks": None,  # fp64 geometry: 61,050 at K=0; scaled below by fp128's growth
    "pasta_q64": [70725, 74212, 75562, 76804, 77445, 78580],
    "pasta_sis": [83234, 87844, 90090, 89924, 89669, 91700],
    "pasta": [101441, 115108, 119146, 116164, 114117, 117940],
}
AKITA_128["goldilocks"] = [round(61050 * v / 65074) for v in AKITA_128["fp128"]]
AKITA_147 = {
    "fp128": [72443, 76559, 76972, 80721, 76019, 82521],
    "goldilocks": [65669, 68584, 68734, 69530, 69646, 69810],
    "pasta_q64": [77227, 78863, 82236, 83233, 83859, 86697],
    "pasta_sis": [91755, 95439, 97916, 100961, 98515, 104425],
    "pasta": [110106, 128591, 129276, 136417, 127827, 139881],
}
AKITA = {128: AKITA_128, 147: AKITA_147}

# Bytes per doubling of the polynomial, from the 2^14 and 2^24 rows of the same runs: the
# growth is concave (fp128: 1,126 per doubling from 2^14 to 2^16, 459 from 2^16 to 2^24, 229
# beyond), and the page extrapolates from 2^14 to about 2^23, so the slope over those ten
# doublings is the one to use; at 128 bits Goldilocks takes fp128's, scaled as its table is,
# and at 147 bits its own 2^14 and 2^26 rows.
SLOPE = {
    128: {"fp128": 592, "goldilocks": 555, "pasta_q64": 953, "pasta_sis": 1112, "pasta": 1371},
    147: {"fp128": 584, "goldilocks": 662, "pasta_q64": 1104, "pasta_sis": 1118, "pasta": 1175},
}
DIGITS = {"fp128": 43, "goldilocks": 22, "pasta_q64": 85, "pasta_sis": 85, "pasta": 85}

# Prover commitment work in native 64-bit word multiplications, for the commitments of one step.
#
# Pedersen over Pasta: a size-n multi-scalar multiplication with 255-bit scalars by Pippenger
# costs about 255/log2(n) mixed point additions per point, so the cost per coefficient falls
# as 1/rank. The constant is measured (2026-11-14). Ragu's fuse of its production step at
# rank 13 (tachyon-zcash/ragu 8109a41c) commits the step's own circuit and the Standard
# profile's 91 circuits with their four stage polynomials: 96 commitments of 2^13
# coefficients. It takes 1.46 s on one core of an Apple M4 Max with rustc 1.100.0 and no
# assembly, and 1.27 s with udon's AArch64 assembly, which Ragu does not enable. At the
# page's rate that is about 5,570 word multiplications per coefficient at rank 13. The
# earlier estimate, 11 field multiplications of 32 word multiplications per addition, gave
# 6,900, 24 percent more.
#
# Ajtai over R_q = Z_q[X]/(X^d + 1) by NTT, with the accumulation matrix shaped as Akita's
# catalog shapes its own: a module of `rank` rows over a ring of degree d, 512 or 1024 (the
# catalog's accumulation matrix is rank one at degree 512 at the 2^14 geometry and 1024 above
# it, its bound certified on the coefficient ℓ∞ route). Per digit: `rank` pointwise ring
# products and log2(d)/2 butterflies for the digit's share of the transform, each a
# multiplication at the modulus width: 32 word multiplications at 255 bits, 8 at 128, 2 at 64
# (Goldilocks's reduction is cheaper still, taken as 1.5). The rank and degree are the
# cheapest that Akita's ℓ∞ estimator certifies at the floor for the row's bound and width,
# accumulation_matrix below, from the estimator's tables at the catalog's bound ladder
# (estimates/linf-accumulation-widths.tsv, written by scripts/linf-accumulation-widths.py;
# REGENERATING.md). The 64-bit commitment and Goldilocks variants read the 64-bit modulus's
# table, which the Goldilocks table coincides with. The Euclidean route of the zero-knowledge
# note's §5.5, 143, 284 and 567 scalar rows at the 2^27 bound, stays as ROWS for the note's
# own figures.
WORD_MULTS = {"fp128": 8, "goldilocks": 1.5, "pasta_sis": 32, "pasta_q64": 2, "pasta": 32}
ROWS = {"fp128": 284, "goldilocks": 567, "pasta_q64": 567, "pasta_sis": 143, "pasta": 143}
MODULUS = {
    "fp128": "q128",
    "goldilocks": "q64",
    "pasta_q64": "q64",
    "pasta_sis": "pallas",
    "pasta": "pallas",
}
ACCUMULATION_DEGREES = (512, 1024)
ACCUMULATION_MAX_RANK = 6


def load_linf_widths():
    """{(modulus, floor): {(degree, rank): [(bound, width), ...]}}: the largest width in ring
    elements that the ℓ∞ estimator certifies at each bound of the ladder, in bound order."""
    table = {}
    with (HERE / "estimates" / "linf-accumulation-widths.tsv").open() as f:
        for r in csv.DictReader(f, delimiter="\t"):
            cells = table.setdefault((r["modulus"], int(r["floor"])), {})
            cells.setdefault((int(r["d"]), int(r["rank"])), []).append(
                (int(r["bound"]), int(r["max_width"]))
            )
    for cells in table.values():
        for ladder in cells.values():
            ladder.sort()
    return table


LINF_WIDTHS = load_linf_widths()


@functools.lru_cache(maxsize=None)
def accumulation_matrix(variant, floor, log_beta, log_n):
    """The cheapest accumulation matrix that Akita's ℓ∞ estimator certifies at `floor` as
    binding at the coefficient bound 2^log_beta for vectors of 2^log_n digits: its field
    multiplications a digit, rank + log2(d)/2, its rank, its degree, and the ladder bound it is
    certified at, the first at or above the bound."""
    cells = LINF_WIDTHS[(MODULUS[variant], floor)]
    best = None
    for d in ACCUMULATION_DEGREES:
        width = 2**log_n / d
        for rank in range(1, ACCUMULATION_MAX_RANK + 1):
            bound, certified = next(
                ((b, w) for b, w in cells[(d, rank)] if b >= 2**log_beta), (None, 0)
            )
            if bound is None:
                raise ValueError(f"a bound of 2^{log_beta:.1f} is beyond the estimator's ladder")
            if certified >= width:
                cost = rank + math.log2(d) / 2
                if best is None or cost < best[0]:
                    best = (cost, rank, d, bound)
                break
    if best is None:
        raise ValueError(f"no accumulation matrix of rank up to {ACCUMULATION_MAX_RANK}: {variant}")
    return best


# The accumulator memory measure: what the prover holds between fuses, in bytes. For the
# lattice rows it is the folded digit vector, the accumulator's coefficients (the batch group's
# circuits × 2^rank and the stage groups' values, accumulator_coefficients below) in digits, each
# digit stored at the width of its accumulator's norm bound. The certified l2 bound at the
# handoff is about 2^19 (zk-fiat-shamir-with-aborts.md's ledger), which bounds every entry, so
# 20 bits and a sign. Each fold multiplies the entries by up to 40, so a level below the top
# needs five bits fewer. The measure is of the top level. The sum-checks expand a digit to an
# element of the commitment field on the fly (8 bytes at 64 bits, 16 at 128, 32 at Pasta's
# modulus), which is not storage. Pedersen's
# is the uncompressed proof, every committed polynomial's 2^rank Pasta coefficients (26.5 MB
# measured at rank 13 against the 24.9 MB counted). The hash-based rows under ARC hold the
# accumulator's codeword, the witness over the rate in the field's elements, and its Merkle
# tree; under their own recursion only the previous proof. BitZ and the 𝔽₂ family hold the
# packed codeword with a tree of 256-byte leaves, and the binary-groups row the packed bits.
PACKED_DIGIT_BITS = 1 + 20  # a sign and the handoff accumulator's bound of about 2^19 per entry


def accumulator_bytes(variant, coefficients, digits=None):
    digits = DIGITS[variant] if digits is None else digits
    return coefficients * digits * PACKED_DIGIT_BITS / 8


# The zero-knowledge option masks the accumulator witness by rejection sampling at the user's
# fold (zk-fiat-shamir-with-aborts.md §5): the one accumulator that fold produces is several
# times longer, nine slices a coordinate at the note's parameters, and the accumulation matrix
# must be binding at the masked bound, since the note's extraction argument needs it there and
# every accumulator is committed under it; where that bound and the row's width ask for it, the
# ℓ∞ estimator gives the masked matrix a rank or a degree above the unmasked one's
# (accumulation_matrix). Akita's internal fold levels and its terminal commit the final
# accumulator's ordinary witness under their own matrices, whose bounds the mask does not
# change, so the opening proof is nearly unaffected: the accumulation matrix's larger images
# enter the first level only as lower-order auxiliary digits. The length stays at the
# zero-knowledge layer: the aggregator's first fold on a masked accumulator range-checks its
# digit slices and folds them back to the ordinary length with its other inputs, as every
# lattice fold decomposes and folds, so the merges above and the decider's opening see witnesses
# of the usual size. The merge priced here is one at the zero-knowledge layer, the costlier
# kind: each of its two sum-checks gains three rounds (log2 of the length factor) of three
# elements. Merges above that layer pay the masked matrix's rate only.
#
# The mask and the bounds follow the note's §5.1 to §5.3 at each row's own accumulator, its
# coefficients (accumulator_coefficients) in digits; MASK_LOG_N = 22 is the note's N, for the
# note's own figures. The digits are at most DIGIT_MAX in size, balanced base 8 for the Akita
# variants and for Kishu's integer-word digits (its bit positions are smaller, so its bound is
# conservative), so ‖s‖₂ ≤ DIGIT_MAX √N; a challenge of ℓ1 norm MASK_CHALLENGE_L1
# gives ‖cs‖₂ ≤ that times ‖s‖₂; the Gaussian mask has width σ = MASK_ALPHA ‖cs‖₂; and the
# accepted response's coordinates are at most MASK_TAIL σ, which sets the bits a coordinate is
# stored in and the base-8 slices it is handed over as. The relaxed opening that extraction
# yields needs the matrix binding at 2 · ‖c − c'‖₁ · 2 · ‖z‖, with ‖c − c'‖₁ at most twice the
# challenge's norm (§5.2): on the coefficient ℓ∞ route that is EXTRACTION_SLACK · ‖z‖∞, where
# ‖z‖∞ is the response's MASK_TAIL σ under the mask, and without it a fold's output, the two
# children at the challenge's weight and the step's own digits. The page's α = 48 with
# weight-20 ternary challenges in the accumulation matrix's ring, 2^138 challenges in degree
# 512, is the page's choice: the zero-knowledge section's sweep shows that the matrix does
# not move across its widths, so the width trades attempts against the coordinates' bits and
# slices, which the transaction measure does not price; the note's §5.6 prices the
# alternatives. The note's own Euclidean route (masked_log_beta, mask_rank), where the rank
# grows as the square of the bound's log against the unmasked 2^27, stays for its figures.
MASK_ALPHA = 48
MASK_CHALLENGE_L1 = 20
MASK_TAIL = 14
MASK_LOG_N = 22
DIGIT_MAX = {v: 4 for v in DIGITS} | {"kishu": 4}
EXTRACTION_SLACK = 2 * (2 * MASK_CHALLENGE_L1) * 2


def log_s2(log_n, digit_max=4):
    """Log of the ℓ2 norm of 2^log_n digits of size at most digit_max."""
    return math.log2(digit_max) + log_n / 2


def mask_log_sigma(alpha=MASK_ALPHA, c_l1=MASK_CHALLENGE_L1, log_n=MASK_LOG_N, digit_max=4):
    return math.log2(alpha) + math.log2(c_l1) + log_s2(log_n, digit_max)


def masked_log_beta_inf(alpha=MASK_ALPHA, c_l1=MASK_CHALLENGE_L1, log_n=MASK_LOG_N, digit_max=4):
    """Log of the coefficient ℓ∞ bound the masked accumulation matrix must be binding at."""
    return (
        math.log2(EXTRACTION_SLACK)
        + math.log2(MASK_TAIL)
        + mask_log_sigma(alpha, c_l1, log_n, digit_max)
    )


def masked_log_beta_inf_l2(log_l2, alpha=MASK_ALPHA, c_l1=MASK_CHALLENGE_L1):
    """As masked_log_beta_inf, from the log of the vector's exact ℓ2 norm in place of
    DIGIT_MAX √N, for a vector of mixed digit widths."""
    return (
        math.log2(EXTRACTION_SLACK)
        + math.log2(MASK_TAIL)
        + math.log2(alpha)
        + math.log2(c_l1)
        + log_l2
    )


def unmasked_log_beta_inf(c_l1=MASK_CHALLENGE_L1, digit_max=4):
    """Log of the coefficient ℓ∞ bound the unmasked accumulation matrix must be binding at."""
    return math.log2(EXTRACTION_SLACK) + math.log2((2 * c_l1 + 1) * digit_max)


def mask_coordinate_bits(alpha=MASK_ALPHA, c_l1=MASK_CHALLENGE_L1, log_n=MASK_LOG_N, digit_max=4):
    """Bits of a masked coordinate stored compactly, its width MASK_TAIL σ."""
    return math.ceil(math.log2(MASK_TAIL) + mask_log_sigma(alpha, c_l1, log_n, digit_max))


def mask_length(alpha=MASK_ALPHA, c_l1=MASK_CHALLENGE_L1, log_n=MASK_LOG_N, digit_max=4):
    """Base-8 slices per masked coordinate."""
    return math.ceil(mask_coordinate_bits(alpha, c_l1, log_n, digit_max) / 3)


def mask_sumcheck_atoms(slices):
    """The zk-layer merge's extra sum-check elements: three rounds of three in each of the
    fold's two sum-checks, for six to eleven slices a coordinate."""
    rounds = round(math.log2(slices))
    assert rounds == 3, slices
    return 2 * rounds * 3


# The zero-knowledge note's own example, N = 2^22 base-8 digits with ‖s‖₂ ≤ 2^13, on the
# Euclidean route of its §5.2, where the rank grows as the square of the bound's log against
# the unmasked 2^27.
MASK_LOG_S = log_s2(MASK_LOG_N)
MASK_UNMASKED_LOG_BETA = 27


def masked_log_beta(alpha=MASK_ALPHA, c_l1=MASK_CHALLENGE_L1, log_n=MASK_LOG_N):
    """Log of the note's Euclidean masked bound for a mask over 2^log_n digits at the note's
    σ, since ‖z‖₂ ≈ 2σ√N (its §5.3)."""
    log_z = 1 + mask_log_sigma(alpha, c_l1) + log_n / 2
    return 1 + math.log2(2 * c_l1) + 1 + log_z


def mask_rank(alpha=MASK_ALPHA, c_l1=MASK_CHALLENGE_L1, log_n=MASK_LOG_N):
    """The note's masked rows over its unmasked, the square of the bounds' log ratio (§5.2)."""
    return (masked_log_beta(alpha, c_l1, log_n) / MASK_UNMASKED_LOG_BETA) ** 2


MASK_RANK = mask_rank()
MASK_LENGTH = mask_length()
MASK_SUMCHECK_ATOMS = mask_sumcheck_atoms(MASK_LENGTH)
MASK_COORDINATE_BITS = mask_coordinate_bits()


# The peak fuse memory measure: what a fuse holds at its peak, in bytes. For the lattice rows
# it is the two children's accumulators, with the output overwriting one of them as the linear
# combination is computed; the fold's second-round sum-check table, half the accumulator's
# digits as claim-field elements, since the first round can stream over the packed digits; and
# under zero knowledge the mask, the accumulator's digits at the row's coordinate width
# (mask_coordinate_bits) each. The new step's witness and the commitment's working set are
# small beside these. The other rows hold two accumulators (the default below the points).
def peak_fuse_bytes(accumulator_bytes_, digits, table_element_bytes, zk, mask_bits):
    table = digits / 2 * table_element_bytes
    mask = digits * mask_bits / 8 if zk else 0
    return 2 * accumulator_bytes_ + table + mask


def ajtai_per_coefficient(
    variant, zk=False, floor=DEFAULT_FLOOR, alpha=MASK_ALPHA, log_n=MASK_LOG_N, digit_max=4
):
    """Word multiplications to commit one coefficient's digits under the accumulation matrix
    that the floor's ℓ∞ table certifies for a vector of 2^log_n digits at the bound in force:
    the masked bound at α under zero knowledge, the fold's otherwise."""
    log_beta = (
        masked_log_beta_inf(alpha, MASK_CHALLENGE_L1, log_n, digit_max)
        if zk
        else unmasked_log_beta_inf(MASK_CHALLENGE_L1, digit_max)
    )
    cost = accumulation_matrix(variant, floor, log_beta, log_n)[0]
    return DIGITS[variant] * cost * WORD_MULTS[variant]


PEDERSEN_FUSE_SECONDS = 1.46  # Ragu's fuse at the checked-in configuration, one core, no assembly
PEDERSEN_FUSE_COMMITMENTS = 96  # the step's circuit, the Standard profile's 91 and four stages
PEDERSEN_FUSE_RANK = 13


def pedersen_per_coefficient(rank):
    per_coefficient_measured = (
        PEDERSEN_FUSE_SECONDS
        * 1000
        * WORD_MULTS_PER_MS
        / (PEDERSEN_FUSE_COMMITMENTS * 2**PEDERSEN_FUSE_RANK)
    )
    return per_coefficient_measured * PEDERSEN_FUSE_RANK / rank


# The user's masking fold, for the page's transaction measure: the expected rejection-sampling
# attempts, exp(12/α + 1/(2α²)), each a commitment of a mask of N coordinates under the masked
# accumulation matrix and N Gaussian samples; N is the accumulator's digits, its coefficients
# (accumulator_coefficients) in digits (zk-fiat-shamir-with-aborts.md §5.4). The handoff's
# merge is added at the point (handoff_merge_cost, handoff_merge_digits): under the note's §5.8
# deferral the user's merge checks the challenge derivation, the commitment identity and the
# claim fold, and the aggregator's first fold does the decomposition and the range and norm
# proofs. A bare leaf handed over without a fuse (LEAF_HANDOFF) masks its own 2^rank digits
# instead, the row's fold_leaf. §5.8 also moves the attempts off the device's critical path, so
# this is total work, not latency.
#
# The page's sampler is a rounded continuous Gaussian at MASK_SAMPLE_NS a coordinate, measured
# with scripts/sampler-bench.c on one core of an Apple M4 Max on mains (2026-11-20, the median
# of three runs of 32 × 2^22 coordinates at σ = 2^22.9): AES-128-CTR randomness through
# CommonCrypto on the AES instructions, two 53-bit uniforms per Box–Muller pair in doubles,
# Sheppard's correction, the scaling, the tail check |x| ≤ 14σ and the rounding;
# MASK_SAMPLE_RNG_NS of it is the randomness. With ChaCha20 in plain C the same path is
# MASK_SAMPLE_CHACHA_NS, MASK_SAMPLE_CHACHA_RNG_NS of it the randomness. For comparison,
# Hülsing, Lange and Smeets' AVX Box-Muller sampler (PKC 2018, ePrint 2017/1025, Table 5.1)
# takes 27,672 cycles per 1,024 coordinates, 47,576 with its ChaCha20 randomness, on a 3.5 GHz
# Haswell. With Sheppard's correction σ = s − 1/(24s) the rounded Gaussian is a discrete
# Gaussian of parameter s to a Rényi divergence of order a of 1 + 73aN/(33177600 s^8) (Jeudy,
# ePrint 2026/2583, Theorem 3.1), negligible at this width, so the rejection-sampling argument
# carries over; what double precision cannot do is round exactly: a coordinate's absolute error
# is up to its size times 2^-53, so about 2 τσ 2^-53 of the coordinates lie within it of a
# half-integer, which is also the paper's §5.2 worst-case bound on the divergence per
# coordinate. Refining those few in higher precision makes the rounding exact. The exact
# alternative, Karney's method, is KARNEY_SAMPLE_WORD_MULTS, 300 ns a coordinate (Du, Fan and
# Wei measured Karney's RandomLib sampler at 2.1 to 3.5 million samples a second on an
# i7-8550U, arXiv 2008.03855 Table 1); the note's §5.4 quotes it as the alternative.
def mask_attempts(alpha=MASK_ALPHA):
    return math.exp(12 / alpha + 1 / (2 * alpha**2))


MASK_ATTEMPTS = mask_attempts()
MASK_SAMPLE_NS = 7.1
MASK_SAMPLE_RNG_NS = 1.5
MASK_SAMPLE_CHACHA_NS = 14.0
MASK_SAMPLE_CHACHA_RNG_NS = 7.7
MASK_SAMPLE_WORD_MULTS = round(MASK_SAMPLE_NS * 3)  # at 3 word multiplications a nanosecond
KARNEY_SAMPLE_WORD_MULTS = 900


def mask_fold(variant, coefficients, floor):
    """The masking fold over `coefficients` of the variant: the masked vector's digits set
    its own σ and bound."""
    digits = DIGITS[variant] * coefficients
    per_digit = (
        ajtai_per_coefficient(variant, True, floor, log_n=math.log2(digits)) / DIGITS[variant]
    )
    return MASK_ATTEMPTS * digits * (per_digit + MASK_SAMPLE_WORD_MULTS)


# The accumulation prover: the fold's two norm and range sum-checks run over the accumulator,
# its coefficients (accumulator_coefficients) in digits. A sum-check pass costs about five field
# multiplications per digit, from Kishu's measured Booleanity sum-check: 437.7 ms
# for 2^27 bits on one core, 9.8 word multiplications per 64-bit digit (BOOL_CHECK below). The
# page's accumulation prover measure adds that work to the merge's commitments for the lattice
# rows, with the fold's own linear combination of the digit vectors, one multiplication per
# digit. The other rows add nothing: Pedersen-IPA's fuse is measured whole and its native
# folding, the batching of about 95 polynomials and a 100-point linear combination, is about
# one percent of it; the hash-based rows' ARC step hashes the new accumulator already; and the
# binary-groups row's measured opening includes its sum-checks.
ACCUMULATION_SUMCHECKS = 2
SUMCHECK_FIELD_MULTS_PER_DIGIT = 5
FOLD_FIELD_MULTS_PER_DIGIT = 1

# The sum-checks run in the CLAIM field, which for the decoupled Pasta-claims variant is
# Pasta's field (pasta-proof-size.md §6.3: every sum-check message is an F_p value), not the
# 64-bit commitment modulus; Kishu's claims are in the 64-bit field itself (its Pasta values
# come from 32-bit limbs), so it passes the commitment field's rate.
CLAIM_WORD_MULTS = {"fp128": 8, "goldilocks": 1.5, "pasta_sis": 32, "pasta_q64": 32, "pasta": 32}


def accumulation_sumchecks(variant, coefficients, digits=None, word_mults=None):
    """Word multiplications of the fold's sum-checks and linear combination over an
    accumulator of `coefficients` coefficients of `digits` digits each (the variant's, or one
    per bit), at the claim field's multiplication cost unless given."""
    digits = DIGITS[variant] if digits is None else digits
    word_mults = CLAIM_WORD_MULTS[variant] if word_mults is None else word_mults
    per_digit = ACCUMULATION_SUMCHECKS * SUMCHECK_FIELD_MULTS_PER_DIGIT + FOLD_FIELD_MULTS_PER_DIGIT
    return per_digit * word_mults * coefficients * digits


# Base-field atoms the merge circuit absorbs per compressed commitment (128 bytes).
# Kishu is not an Akita variant (VARIANTS lists those) but shares the tables where its claim
# field, the quadratic extension of the 64-bit field at 16 bytes an element, sets the figure.
ATOMS_PER_COMMITMENT = {
    "fp128": 8,
    "goldilocks": 16,
    "pasta_q64": 6,
    "pasta_sis": 4,
    "pasta": 4,
    "kishu": 8,
}
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
CLAIM_BYTES = {
    "fp128": 16,
    "goldilocks": 16,
    "pasta_q64": 32,
    "pasta_sis": 32,
    "pasta": 32,
    "kishu": 16,
}
CLAIM_GATES = 4

# The accumulator's length. Its K = STAGES + 1 groups are the fuse's stage polynomials and one
# batch of every step circuit's witness: one committed vector of circuits × 2^rank coefficients,
# since the merge absorbs one image for the batch and the decider opens it at that length, with
# each circuit's claim an evaluation of its own slice. So the batch is about the merge's size
# at every rank at which the merge needs more than one circuit. A stage polynomial is
# sparse. In Ragu the trace splits by wire position: a stage holds its values at the a and d
# wires of its reserved gates and is zero elsewhere, and bonding circuits enforce that the
# stages do not overlap. So a stage's zeros are structural and public, and what is committed
# and folded is its support. Ragu 8109a41c's native stages (each stage's values() under
# crates/ragu_pcd/src/internal/native/stages/) hold the counts below at the Standard profile.
# The preamble holds, for each of the two children, three values an entry of the header, the
# six online openings twice, a circuit id and the 39 unified wires; it alone depends on the
# header, taken at STAGE_HEADER entries, the largest the page offers. A lattice fuse's stages,
# an estimate, carry the same kinds of values, each a claim-field element: one coefficient
# where a coefficient is a claim-field element, two over Goldilocks, whose claims are in a
# quadratic extension, and the element's bits where the witness is bits (Kishu and the binary
# groups). Akita's grouped opening admits groups of different sizes: every group uses the fold
# level's opening method "though the groups' dimensions and points may differ" (the paper's
# §5), and its planner sizes groups separately. So the mask, the fold's sum-checks and the
# accumulator's memory run over accumulator_coefficients, the batch plus the stages' values,
# not K × 2^rank. The merge absorbs K images and folds K groups, and the opening bytes come
# from the planner's runs with K groups of 2^14 coefficients, which overstate the small stage
# groups.
STAGE_HEADER = 9
STAGE_VALUES = {
    "preamble": 2 * (3 * STAGE_HEADER + 2 * 6 + 1 + 39),
    "query": 172,
    "eval": 122,
    "inner_error": 90,
    "outer_error": 42,
}
assert len(STAGE_VALUES) == STAGES
STAGE_VALUES_TOTAL = sum(STAGE_VALUES.values())
STAGE_VALUE_COEFFICIENTS = {
    "fp128": 1,
    "goldilocks": 2,
    "pasta_q64": 1,
    "pasta_sis": 1,
    "pasta": 1,
    "kishu": None,  # a claim-field element as tribits, set below E_MULT_DIGITS
    "bits_akita": CLAIM_BYTES["fp128"] * 8,
}


def accumulator_coefficients(variant, rank, circuits):
    """The accumulator's coefficients: the batch group's circuits × 2^rank and the stage
    groups' values, each as the variant commits a claim-field element."""
    return circuits * 2**rank + STAGE_VALUES_TOTAL * STAGE_VALUE_COEFFICIENTS[variant]


def akita_atoms(variant, K, circuits, zk):
    return (
        SUMCHECK_ATOMS
        + K * ATOMS_PER_COMMITMENT[variant]
        + circuits
        + (MASK_SUMCHECK_ATOMS if zk else 0)
    )


def akita_absorbed_bytes(variant, K, circuits, zk):
    """The bytes the merge absorbs: the sum-check elements and the claims at the claim
    field's width, and the K commitment images of 128 bytes."""
    return (SUMCHECK_ATOMS + circuits + (MASK_SUMCHECK_ATOMS if zk else 0)) * CLAIM_BYTES[
        variant
    ] + K * 128


def akita_hash_gates(variant, K, circuits, zk, hp):
    if hp == "poseidon":
        return HASH_GATES_PER_ATOM * akita_atoms(variant, K, circuits, zk)
    return ceil_div(akita_absorbed_bytes(variant, K, circuits, zk), BLAKE3_BLOCK) * BLAKE3_GATES


def circuit_slope(cost):
    """What one more circuit adds to a merge whose cost is `cost(circuits)`: the slope over
    BLAKE3_BLOCK circuits from 2 * BLAKE3_BLOCK + 1. Over that span the circuits' claims fill
    whole hash blocks at any claim width, and the count stays between two powers of two, so
    the slope holds neither a compression that one claim happened to start nor a round added
    to the merge's sum-check. A difference of two neighbouring counts could hold either, or
    come out zero."""
    lo = 2 * BLAKE3_BLOCK + 1
    slope = (cost(lo + BLAKE3_BLOCK) - cost(lo)) / BLAKE3_BLOCK
    assert slope > 0
    return slope


def akita_merge_gates(variant, K, circuits, zk, hp):
    return (
        akita_hash_gates(variant, K, circuits, zk, hp)
        + 2 * K * FOLD_GATES_PER_IMAGE
        + SUMCHECK_GATES
        + CLAIM_GATES * circuits
    )


def akita_circuits(variant, K, rank, zk, hp):
    """The step circuits a merge needs at this rank: the gate estimate, which grows with the
    circuit count through each circuit's claim, divided by the budget, at its fixed point;
    None where each circuit adds more gates than the budget holds, so that no count
    converges."""
    per_circuit = circuit_slope(lambda c: akita_merge_gates(variant, K, c, zk, hp))
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
    "pedersen": "Pedersen-IPA",
    "fp128": "Akita, 128‑bit field",
    "goldilocks": "Akita, Goldilocks",
    "pasta_q64": "Akita, Pasta claims, 64‑bit commitments",
    "pasta_sis": "Akita, Pasta, inner images at SIS size",
    "pasta": "Akita, Pasta for everything",
    "whir": "WHIR with ARC, Pasta",
    "whir_gold": "WHIR with ARC, Goldilocks",
    "whir_hybrid": "WHIR with ARC, Pasta claims, 64‑bit limbs",
    "plonky3": "Plonky3-style FRI with ARC, Goldilocks",
    "flock": "Flock/Binius-style over 𝔽₂ with ARC",
    "whir_rec": "WHIR, recursive, Pasta",
    "whir_gold_rec": "WHIR, recursive, Goldilocks",
    "whir_hybrid_rec": "WHIR, recursive, Pasta claims, 64‑bit limbs",
    "plonky3_rec": "Plonky3-style FRI, recursive, Goldilocks",
    "flock_rec": "Flock/Binius-style over 𝔽₂, recursive",
    "bitz": "BitZ with ARC, Pasta claims over committed bits",
    "bitz_rec": "BitZ, recursive, Pasta claims over committed bits",
    "bits_q64": "Kishu: BitZ over Akita, 64‑bit commitments, Pasta claims, BLAKE3 (draft)",
    "bits_q64_poseidon": "Kishu: BitZ over Akita, 64‑bit commitments, Pasta claims, Poseidon (draft)",
    "bits_akita": "Flock/Binius-style over Akita's binary groups (experimental)",
}


# The planner's smallest geometry, 2^14 coefficients. Below it the opening and the decider are
# taken at 2^14: both are lines fitted above it (the opening at the planner's rows there, the
# decider at the paper's 2^27 bits), and the decider's line would go negative fourteen
# doublings down, at the size of a one-compression leaf.
AKITA_MIN_LOG_LEN = 14


def akita_bytes(variant, K, log_len, floor=DEFAULT_FLOOR):
    """Opening bytes with K extra committed groups and a batched witness of 2^log_len
    coefficients, from the planner's rows at 2^14 and the per-doubling slope, at the floor's
    plan, and at 2^14 below it."""
    log_len = max(log_len, AKITA_MIN_LOG_LEN)
    xs, ys = AKITA_K, AKITA[floor][variant]
    if K >= xs[-1]:
        y = ys[-1] + (ys[-1] - ys[-2]) / (xs[-1] - xs[-2]) * (K - xs[-1])
    else:
        i = max(j for j in range(len(xs) - 1) if xs[j] <= K)
        t = (K - xs[i]) / (xs[i + 1] - xs[i])
        y = ys[i] + t * (ys[i + 1] - ys[i])
    return round(y + SLOPE[floor][variant] * (log_len - 14))


# ---- Decider work ----------------------------------------------------------------
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
    ms = base + slope * (max(log_len, AKITA_MIN_LOG_LEN) - ref)
    if variant not in ("fp128", "goldilocks"):
        ms *= 4
    # With zero knowledge the final accumulator is at the ordinary length, so the sum-checks
    # are unchanged; the masked rank arrives in rank_scale, composed by the caller.
    return round(ms * rank_scale * WORD_MULTS_PER_MS)


def pedersen_verify(rank, nat, nes):
    return round(
        2 * 2**rank * pedersen_per_coefficient(rank) + 2 * (nat + nes + 5) * SCALAR_MULT_WORD_MULTS
    )


# ---- Multiplication in a Boolean circuit ------------------------------------------------
# Counted in AND gates with XOR free, which is the garbled-circuit cost model and the cost of
# the Flock-style families' witnesses: a full adder is one AND, since the carry is
# b ⊕ ((a ⊕ b) ∧ (b ⊕ c)), so an m-bit addition or subtraction is about m.
# A BLAKE3 compression is its seven rounds of eight G functions with four 32-bit additions, as
# BLAKE2B_ANDS counts BLAKE2b's. Flock lays a batch out as one block of 2^m0 committed bits per
# instance (its §4.1), and a compression's 6,944 carries and 896 input bits fit the block of
# 2^13, so BLAKE3_ANDS_PADDED is a compression's share of a Flock witness. It prices what is
# Flock's witness or hypercube: the per-bit rate measured on Flock's BLAKE3 batches, the base
# matrix's sum-check rounds, and the hashes of the Flock-style merges. An application's count
# is the unpadded AND gates, the step doing the padding.
BLAKE3_ANDS = 7 * 8 * 4 * 32
BLAKE3_ANDS_PADDED = 2**13


@functools.lru_cache(maxsize=None)
def mult_ands(n):
    """AND gates of an n-bit by n-bit integer multiplication, the cheapest at each width of:
    schoolbook, n² partial products and a reduction tree of about n² full adders; Karatsuba,
    three products of about half the width, with the two half-width sums, two subtractions
    and the recombination, about 4.5n; and Toom-Cook 3, five products of about a third of
    the width (the evaluations at 1, -1 and -2 are two to four bits wider), with the
    evaluations, the interpolation's eight additions on values of twice the part's width and
    its one exact division by three, done bit-serially at about four ANDs per bit, and the
    recombination, about 13.6n. Karatsuba pays from about 20 bits, as the free-XOR literature
    finds; Toom-Cook 3 gains a further few percent at 128 bits."""
    best = 2 * n * n - n
    if n >= 8:
        h = (n + 1) // 2
        best = min(best, mult_ands(h) + mult_ands(n - h) + mult_ands(h + 1) + round(4.5 * n) + 4)
    if n >= 12:
        k = (n + 2) // 3
        m = 2 * (k + 4)
        best = min(
            best,
            mult_ands(k)
            + mult_ands(n - 2 * k)
            + 2 * mult_ands(k + 2)
            + mult_ands(k + 4)
            + (10 * k + 12)
            + 12 * m
            + 5 * k,
        )
    return best


# ---- Pasta arithmetic in each arithmetization, for the transaction measure ----------------
# The transaction measure counts application gates as Pasta gates of a Pasta-arithmetic
# application, with the Ironwood recovery circuit as the reference (the recovery-circuit
# estimate of 2026-11-03, extended to the bit arithmetizations on 2026-11-12): seven BLAKE2b
# and one BLAKE3 compression, 160 Sinsemilla chunks, five fixed-base and one variable-base
# full-width scalar multiplication with complete additions, the nullifier's Poseidon,
# reductions and linking, and a Merkle path hashed under the page's policy; 570,000 gates
# over Pasta with a Poseidon path and 1,050,000 with a BLAKE3 one. Each arithmetization is
# costed component by component, in its own unit:
#   - The hashes, the generator selections and the reductions are bit operations. Over a
#     prime field they cost about the same gates in every field: one per bit for an XOR
#     (x + y - 2xy), one per bit and a carry for an addition, and 1,013 per Sinsemilla chunk,
#     the subset products of its ten bits, of which the generator's coordinates are free
#     linear forms. In a Boolean circuit with XOR free a 64-bit addition is 64 ANDs and an
#     XOR nothing, so a BLAKE2b compression is 24,576 ANDs against 51,600 Pasta gates, and a
#     selection is the same 1,013 products, each output bit then a free XOR of them. In a bit
#     arithmetization (BitZ's, or Kishu over Akita) each wire bit is one
#     committed bit: the XOR's output, the addition's 64 sum bits and its carry, the chunk's
#     1,013 products; a BLAKE2b compression is 50,560 bits.
#   - The curve arithmetic, about 14,500 multiplications in Pallas's base field, must be
#     emulated off Pasta: about 1,100 gates each over Goldilocks (nine 29-bit limbs, no
#     lookups) and about 700 at a 128-bit field (61-bit limbs). In a Boolean circuit a
#     multiplication is the 255-bit product by mult_ands and a Montgomery reduction by a
#     prime of no special form, whose two multiplications by constants are about three
#     quarters of a product each: about 120,000 ANDs. In BitZ's integer arithmetization it
#     is 510 committed bits: the value and the quotient of a b = q p + r, checked as one
#     integer relation. Kishu's claims are in the 64-bit field, so its Pasta arithmetic is
#     the same integer relation, and a multiplication is 510 digits there too.
#   - The Merkle path is 33 BLAKE3 compressions in the bit arithmetizations under either
#     policy, since Poseidon over Pallas's field would cost them 240 multiplications a node.
# So the recovery circuit is about 16.5 million Goldilocks gates, 10.7 million at a 128-bit
# field, 1.73 billion AND gates (the multiplications are all of it), 8.4 million committed
# bits in BitZ's arithmetization and as many digits in Kishu's, against the
# reference with a Poseidon path; per Pasta gate 29, 19, 3,100 and 15, or 16, 11, 1,700 and 8
# with a BLAKE3 path, which raises the reference to 1.05 million gates. The hashes
# are what makes the bit arithmetizations cheap: a field multiplication alone would put a
# Pasta gate at 510 bits. The page's transaction measure takes an application, the recovery
# circuit or a number of Merkle path checks (APPLICATIONS, in each arithmetization's unit
# under each policy), and divides it by the step's capacity in the same unit, `step_units`:
# 2^rank coefficients, which is 2^(rank-2) gates of four wires for the field families, 2^rank
# bits or digits for BitZ and Kishu, and BOOL_STEP_BITS AND gates for the
# Boolean families; rounded up, since a transaction smaller than a step pays a whole step.
BITZ_GATE_BITS = 510  # a Pasta gate as committed bits in BitZ's arithmetization: a 255-bit value and a 255-bit quotient
# Kishu's witness carries bits where the circuit needs bits as factors, in the hashes, and
# wider digits for integer-word data, which enters constraints only through linear forms:
# limbs, quotients, carries, claim-field values, amounts, hash inputs. A word of `bits` bits is
# floor(bits / 3) tribits, digits of three bits in Akita's own balanced base-8 alphabet
# (DIGIT_MAX 4), and a bit or a dibit, a digit of two bits, for the remainder if needed, so
# that its range is exact. The commitment and the fold cost the
# same per digit at any of these widths (the accumulation matrix stays rank 1 unmasked and
# rank 2 masked at the wider bound), and the range check with Akita's paired predicate costs
# b/2 products a digit for an alphabet of b values (b assumed even): one for a bit, which the per-digit
# Booleanity rate charges, two for a dibit, four for a tribit. The products beyond one a digit
# are charged to the application's PIOP (word_range_piop). Bitwise operations keep bits: a
# dibit XOR is degree two only with a committed quotient digit, which is pinned only by
# committing the reduced result, so dibits cannot leave every other XOR word uncommitted as
# bits do, and tribits have no degree-two XOR at all.
WORD_DIGIT_BITS = 3
RANGE_PRODUCTS = {1: 1, 2: 2, 3: 4}  # products a digit of the range check, by the digit's bits


def word_digits(bits):
    """Digits of a `bits`-bit word: tribits and one narrower digit for the remainder."""
    return math.ceil(bits / WORD_DIGIT_BITS)


def word_range_products(bits):
    """The range check's products over a word's digits beyond one a digit."""
    whole, rest = divmod(bits, WORD_DIGIT_BITS)
    return whole * (RANGE_PRODUCTS[3] - 1) + (RANGE_PRODUCTS[rest] - 1 if rest else 0)


def word_range_piop(bits):
    """The range check's surplus products as a PIOP part of their own."""
    return (0, 0, 0, word_range_products(bits))


BITS_PER_VALUE = 255  # a Pasta value's bits
VALUE_DIGITS = word_digits(BITS_PER_VALUE)  # a Pasta value in Kishu's digits
BLAKE2B_ANDS = 12 * 8 * 4 * 64  # twelve rounds of eight G functions with four 64-bit additions
# A compression's committed digits in a degree-two arithmetization over bits (BitZ's and
# Kishu's): per G function the four adders' sums and carries, and two of the four XOR words.
# Every word of G is used once as a factor, in an XOR, and once linearly, in an adder. A word
# needs committing only to be a factor, and an uncommitted XOR word enters its adder as the
# exact expressions x + y - 2xy of its bits. So of each chain of two XORs only the second's
# word is committed, certified against both XORs' inputs at once (XOR_RELATION_PIOP); a third
# XOR in the chain would need degree three. The finalisation's XORs are expressions too: a
# compression in a chain commits only the four output words that are the next compression's b
# inputs, its factors in the first round. Rotations are wiring.
BLAKE_G_COMMITTED_XORS = 2
BLAKE_CHAIN_WORDS = 4


def blake_bits(rounds, word_bits, add2, add3):
    """A BLAKE compression's committed digits: per G function two additions of two words at
    `add2` digits (the sum and a carry bit), two of three words at `add3` (the carry up to
    two, two bits), and the committed XOR words; then the chaining words."""
    g = rounds * 8
    return (
        g * (2 * add2 + 2 * add3 + BLAKE_G_COMMITTED_XORS * word_bits)
        + BLAKE_CHAIN_WORDS * word_bits
    )


BLAKE2B_BITS = blake_bits(12, 64, 65, 66)
BLAKE3_BITS = blake_bits(7, 32, 33, 34)
# As BLAKE2B_BITS, each 64-bit addition in two halves with a carry each, since a 64-bit sum
# can wrap modulo q.
BLAKE2B_BITS_KISHU = blake_bits(12, 64, 66, 68)
# Constraint counts for Kishu's PIOP, a sum-check over a constraint system on the committed
# table (Zinc+'s UCS, R1CS or CCS alike), beside the digit counts, as (product terms, nonzeros
# of small constants, nonzeros of field constants). A product term costs the prover the
# measured rate of the Booleanity sum-check, which is a degree-2 relation per entry under eq
# weights, and a linear-only constraint counts as one term; a nonzero of a linear form costs
# one multiplication of an extension element by the constant in the matrix-evaluation phase,
# two word multiplications for a power of two or a small constant and four for a field
# constant. Linear forms are over word entries: the table is laid out by bit position, so a
# word's evaluation is a batch of column claims, which Akita opens at the cost of one, and a
# bit is a one-bit word. An XOR bit committed on its own is z = x + y - 2xy, one product; a
# committed XOR word certified against the two XORs that produced it, z ⊕ a2 = d ⊕ a1 bit by
# bit, is two products a bit; a 32-bit addition a + b = s + 2^32 c over word entries with 33
# committed bits is one linear constraint, or 32 products and the constraint when an addend is
# an uncommitted XOR word; a 64-bit one two halves; a Sinsemilla chunk its committed subset
# products and its two coordinates' constraints (SINSEMILLA_CHUNK_PIOP below); the reductions
# and linking one term each.
CONSTRAINT_TERM_WORD_MULTS = 437.7 / 2**27 * WORD_MULTS_PER_MS  # BOOL_CHECK's rate, asserted there
NONZERO_SMALL_WORD_MULTS = WORD_MULTS["pasta_q64"]
NONZERO_FIELD_WORD_MULTS = 2 * WORD_MULTS["pasta_q64"]
XOR_BIT_PIOP = (1, 4, 0)
XOR_RELATION_PIOP = (
    2,
    8,
    0,
)  # a committed XOR word's bit against both XORs' inputs: two products, four factors and four linear entries
ADD32_PIOP = (1, 4, 0)
ADD32_XOR_PIOP = (
    32,
    68,
    0,
)  # an addition with an uncommitted XOR word as an addend: its 32 products' factors and the four word entries
ADD64_PIOP = (2, 8, 0)
ADD64_XOR_PIOP = (64, 136, 0)


PIOP_PARTS = (
    4  # product terms, small nonzeros, field nonzeros, range-check products beyond one a digit
)


def piop_sum(*parts):
    """The constraint counts of `count` copies of each (count, counts) part, summed; a part of
    three counts has no range-check products."""
    return tuple(
        sum(count * (part[i] if i < len(part) else 0) for count, part in parts)
        for i in range(PIOP_PARTS)
    )


def piop_word_mults(piop):
    """Word multiplications of the constraint PIOP and the range checks together; the range
    checks' products run at the Booleanity sum-check's rate, as the constraint terms do."""
    terms, small, field, *rest = piop
    return (
        (terms + sum(rest)) * CONSTRAINT_TERM_WORD_MULTS
        + small * NONZERO_SMALL_WORD_MULTS
        + field * NONZERO_FIELD_WORD_MULTS
    )


def piop_range_word_mults(piop):
    """The range checks' share of piop_word_mults."""
    return sum(piop[3:]) * CONSTRAINT_TERM_WORD_MULTS


def blake_piop(rounds, word_bits):
    """A BLAKE compression's constraint counts in Kishu's PIOP: per G function two plain
    additions, two additions taking an uncommitted XOR word, and two committed XOR words
    certified by XOR_RELATION_PIOP; then the chaining words, four committed by XOR_BIT_PIOP and
    four entering the next compression's first additions as expressions."""
    add, add_xor = (ADD32_PIOP, ADD32_XOR_PIOP) if word_bits == 32 else (ADD64_PIOP, ADD64_XOR_PIOP)
    g = rounds * 8
    return piop_sum(
        (2 * g, add),
        (2 * g, add_xor),
        (BLAKE_G_COMMITTED_XORS * g * word_bits, XOR_RELATION_PIOP),
        (BLAKE_CHAIN_WORDS * word_bits, XOR_BIT_PIOP),
        (BLAKE_CHAIN_WORDS, (word_bits, 2 * word_bits, 0)),
    )


BLAKE3_PIOP = blake_piop(7, 32)
BLAKE2B_PIOP = blake_piop(12, 64)
# A Sinsemilla chunk selects one of 1,024 generators by ten bits. Each coordinate of the
# selected point is a fixed linear form in the subset products of the bits, one coefficient per
# subset. Only a product that is a factor of another needs committing: the subsets within each
# half of the bits, 26 of two to five bits a half, are committed as bits, one product each, and
# every subset spanning both halves is the product of two committed monomials or bits, a term
# of the coordinate's constraint, 961 of them, its coefficient a field constant on one factor.
# The coordinates are materialized as committed bits, since the form would otherwise enter
# every limb product.
SINSEMILLA_HALF_MONOMIALS = 2**5 - 1 - 5
SINSEMILLA_COMMITTED_PRODUCTS = 2 * SINSEMILLA_HALF_MONOMIALS
SINSEMILLA_CROSS_PRODUCTS = (2**5 - 1) ** 2
SINSEMILLA_CHUNK_PIOP = piop_sum(
    (SINSEMILLA_COMMITTED_PRODUCTS, (1, 3, 0)),
    (
        2,
        (
            SINSEMILLA_CROSS_PRODUCTS,
            SINSEMILLA_CROSS_PRODUCTS + VALUE_DIGITS,
            SINSEMILLA_CROSS_PRODUCTS + SINSEMILLA_COMMITTED_PRODUCTS + 10 + 1,
        ),
    ),
    (2, word_range_piop(BITS_PER_VALUE)),
)
SINSEMILLA_CHUNK_DIGITS_KISHU = SINSEMILLA_COMMITTED_PRODUCTS + 2 * VALUE_DIGITS
REDUCTIONS_PIOP = (4000, 12000, 0)
# Two routes for Kishu's Pasta multiplication a b = k p + r over committed bits, since Akita's
# claims are in one fixed field and the relation cannot be checked modulo it alone: the prover
# could choose r. Limbs: the relation is checked coefficient by coefficient over 29-bit limbs,
# which are linear in the bits and cost nothing to commit; each of the 17 coefficients is one
# constraint of up to 9 product terms, bounded below q/2 so that it holds over the integers,
# with a committed carry of about 34 bits; the result, the quotient and the carries are
# committed. Fingerprint: as BitZ, the relation is one constraint in each of three PIOP
# instances over random 52-bit primes, each of which a nonzero 510-bit integer satisfies with
# probability about 2^-43; each instance's evaluation claim becomes about sqrt(2^rank) integer
# column sums by BitZ's tensor split, each exact as one claim in the 64-bit field, and the
# sums are committed as digits of 61 bits, the route's cost per step.
MULT_LIMBS = 9  # 29-bit limbs of a 255-bit value
MULT_CARRY_BITS = 34
MULT_COEFFICIENTS = 2 * MULT_LIMBS - 1
FINGERPRINT_INSTANCES = 3
FINGERPRINT_PRIME_BYTES = 8
COLUMN_SUM_BITS = 61
MULT_LIMBS_TERMS = MULT_LIMBS**2 + MULT_COEFFICIENTS  # the limb products and the carry relations
MULT_LIMBS_DIGITS = 2 * VALUE_DIGITS + MULT_COEFFICIENTS * word_digits(MULT_CARRY_BITS)
MULT_FINGERPRINT_DIGITS = 2 * VALUE_DIGITS  # the value and the quotient
# Digits, and constraint counts, per multiplication; the counts include the range checks'
# products beyond one a digit on the result, the quotient and the carries.
MULT_ROUTES = {
    "limbs": (
        MULT_LIMBS_DIGITS,
        piop_sum(
            (1, (MULT_LIMBS_TERMS, 2 * MULT_LIMBS**2 + MULT_COEFFICIENTS * (MULT_LIMBS + 3), 0)),
            (2, word_range_piop(BITS_PER_VALUE)),
            (MULT_COEFFICIENTS, word_range_piop(MULT_CARRY_BITS)),
        ),
    ),
    "fingerprint": (
        MULT_FINGERPRINT_DIGITS,
        piop_sum(
            (1, (FINGERPRINT_INSTANCES, 4 * FINGERPRINT_INSTANCES, 0)),
            (2, word_range_piop(BITS_PER_VALUE)),
        ),
    ),
}
KISHU_ARITHS = tuple(f"bits_pasta_{route}" for route in MULT_ROUTES)


def kishu_route(arith):
    return arith.removeprefix("bits_pasta_")


def fingerprint_step_sums(rank):
    """The fingerprint route's column sums a step: about sqrt(2^rank) for each instance."""
    return FINGERPRINT_INSTANCES * math.ceil(2 ** (rank / 2))


def fingerprint_step_digits(rank):
    return fingerprint_step_sums(rank) * word_digits(COLUMN_SUM_BITS)


def fingerprint_step_range_mults(rank):
    """The column sums' range checks beyond one product a digit, in word multiplications."""
    return piop_word_mults(
        (fingerprint_step_sums(rank) * word_range_products(COLUMN_SUM_BITS), 0, 0)
    )


def bits_unit(field):
    return "bits" if field == "bitz" or field.startswith("bits_pasta") else field


RECOVERY_MULTS = 14_500
RECOVERY_CURVE_PASTA = (
    16_100  # the multiplications as native gates, with the selectors and identity cases
)
RECOVERY_BITS = {  # the hashes, the selections, the reductions and linking, in the arithmetization's unit
    "pasta": 542_000,
    "goldilocks": 547_000,
    "fp128": 542_000,  # a 64-bit addition over Goldilocks is two halves
    "boolean": 7 * BLAKE2B_ANDS + BLAKE3_ANDS + 162_000 + 4_000,
    "bits": 7 * BLAKE2B_BITS + BLAKE3_BITS + 160 * SINSEMILLA_COMMITTED_PRODUCTS + 4_000,
    "bits_kishu": 7 * BLAKE2B_BITS_KISHU
    + BLAKE3_BITS
    + 160 * SINSEMILLA_CHUNK_DIGITS_KISHU
    + 4_000,
}
RECOVERY_MULT = {
    "goldilocks": 1_100,
    "fp128": 700,
    "bitz": BITZ_GATE_BITS,
    **{a: MULT_ROUTES[kishu_route(a)][0] for a in KISHU_ARITHS},
}
RECOVERY_PATH_POSEIDON = {"pasta": 9_500, "goldilocks": 15_600, "fp128": 15_600}
RECOVERY_PATH_BLAKE3 = {
    "pasta": 33 * BLAKE3_GATES,
    "goldilocks": 33 * BLAKE3_GATES,
    "fp128": 33 * BLAKE3_GATES,
    "boolean": 33 * BLAKE3_ANDS,
    "bits": 33 * BLAKE3_BITS,
}
BOOL_REDUCTION = 1.5  # the Montgomery reduction, as a multiple of the product
BOOL_STEP_BITS = 2**22


def recovery_cost(field, hp):
    """The reference circuit in the unit of `field`'s arithmetization, its Merkle path under
    policy `hp` where the field has a Poseidon; the bit arithmetizations hash it with BLAKE3
    under either."""
    unit = bits_unit(field)
    if field == "pasta":
        mult = RECOVERY_CURVE_PASTA / RECOVERY_MULTS
    elif field == "boolean":
        mult = (1 + BOOL_REDUCTION) * mult_ands(255)
    else:
        mult = RECOVERY_MULT[field]
    path = (
        RECOVERY_PATH_POSEIDON[field]
        if hp == "poseidon" and field in RECOVERY_PATH_POSEIDON
        else RECOVERY_PATH_BLAKE3[unit]
    )
    bits = RECOVERY_BITS["bits_kishu" if field.startswith("bits_pasta") else unit]
    return bits + RECOVERY_MULTS * mult + path


def path_cost(field, hp):
    """One Merkle path check, 32 levels and the leaf, in the unit of `field`'s
    arithmetization: hashed under policy `hp` where the field has a Poseidon, by BLAKE3 in
    the bit arithmetizations under either."""
    unit = bits_unit(field)
    if hp == "poseidon" and field in RECOVERY_PATH_POSEIDON:
        return RECOVERY_PATH_POSEIDON[field]
    return RECOVERY_PATH_BLAKE3[unit]


# ---- The hardware wallet's part of the Recovery Statement, as applications ----------------
# ZIP 2005's SoK^qsk is made on the device that holds qsk (its Option A), and the host's
# Recovery Statement proves the rest. Two shapes of that part are priced as applications on
# their own, under either hash policy, since their hash is the scheme's and not the page's:
#   - the device's own statement, one BLAKE3 compression for H^qk(qsk) = qk with the linking
#     commitment left out, for a device that proves it as a leaf of the same proof system;
#   - a leanSPHINCS verifier, for a device that signs SigHash with the stateless hash-based
#     signature of post-quantum Ethereum (EthLib's Cryptography/Sphincs module; EIP-8288 and
#     the draft EIP of ethereum/EIPs#12672), the host proving the verification with the
#     signature and the public key as witnesses. The counts are sphincs.art's pruned key of
#     lifetime 2^30 (TomWambsgans/sphincs.art at 8157875, scripts/scheme.py --json: one tree
#     of height 26 with a kept subtree of height 12, WOTS+C with 64 chains of 4 positions and
#     target sum 128, 8 forest coordinates), 262 Keccak-f[1600] permutations or 298 BLAKE2s
#     compressions, with the 4,276-byte signature as committed input bits; the signer grinds
#     2^(26 - 12) digests per signature, and the key's proved lifetime is 126,900 signatures,
#     one per recovery transaction. The layered forest key of the same lifetime verifies in
#     408 or 462 with a 6,332-byte signature, and Ethereum's provisional set, with FORS of 24
#     trees of height 10 in place of the forest, in 515 with 7,740 bytes.
# XOR is not free in a digit arithmetization or over a prime field. Keccak-f costs its 24
# rounds of committed lanes, each lane's bits certified against three inputs at two products a
# bit (XOR_RELATION_PIOP): in theta two parity lanes a column, the first over three of the
# column's lanes and the second over it and the other two, then the 25 lanes after theta, each
# against its lane and two parities; and chi's 25 output lanes, each bit certified by
# a'' ⊕ b0 = (1 - b1) b2 with no AND digit. Beside it a BLAKE2s compression is ten rounds of
# BLAKE3's G function. In a Boolean circuit with XOR free Keccak-f is chi's 38,400 ANDs and
# BLAKE2s its additions.
BLAKE2S_ROUNDS = 10
BLAKE2S_BITS = BLAKE2S_ROUNDS * 8 * (4 * 33 + BLAKE_G_COMMITTED_XORS * 32) + BLAKE_CHAIN_WORDS * 32
BLAKE2S_ANDS = BLAKE2S_ROUNDS * 8 * 4 * 32
BLAKE2S_PIOP = blake_piop(BLAKE2S_ROUNDS, 32)
KECCAK_ROUNDS = 24
# Theta's two parity lanes a column and its 25 lanes after it; chi's 25 lanes.
KECCAK_ROUND_LANES = 2 * 5 + 25 + 25
KECCAK_ROUND_BITS = KECCAK_ROUND_LANES * 64
KECCAK_BITS = KECCAK_ROUNDS * KECCAK_ROUND_BITS
KECCAK_ANDS = KECCAK_ROUNDS * 1600
KECCAK_PIOP = piop_sum((KECCAK_BITS, XOR_RELATION_PIOP))
# Hash calls of one verification of the pruned key, its signature bytes, its grinding digests
# per signature and its proved lifetime; the layered forest key's calls and bytes; Ethereum's
# provisional FORS set's; and the hash rates of a Ledger Nano S+ from sphincs.art's
# hardware-wallet benchmark, for the grinding's time there.
# In increasing order of cost in a digit arithmetization. BLAKE3's block and output sizes are
# BLAKE2s's, so its call count is the same.
LEANSPHINCS_VERIFY = {"blake3": 298, "blake2s": 298, "keccak": 262}
LEANSPHINCS_SIG_BYTES = 4276
# CAPSS (ePrint 2025/061), typed from its Tables 2, 3, and 6, over a 256-bit field at 128 bits
# unless said: signature bytes and the verifier's R1CS constraints of the instances the CAPSS
# page quotes, the permutation calls of verifying and signing (Anemoi-3 and Poseidon-3 at the
# default trade-off, the latter summed over its three widths), the Goldilocks instance's
# figures, the paper's estimate for a 64-bit field, and the factor it implies. The page's Kishu
# estimates take the Poseidon call counts at Q64_POSEIDON_MULTS a permutation and Q64_DIGITS a
# wire.
CAPSS_BYTES = {
    "anemoi3_short": 9504,
    "anemoi3_default": 12640,
    "poseidon3_default": 19616,
    "poseidon5_fast": 25824,
}
CAPSS_R1CS = {
    "griffin3_short": 20717,
    "anemoi3_default": 23484,
    "poseidon3_default": 46567,
    "poseidon5_fast": 71145,
}
CAPSS_ANEMOI_CALLS = {"verify": 173, "sign": 13902}
CAPSS_POSEIDON_CALLS = {"verify": 85 + 10 + 48, "sign": 1936 + 286 + 7790}
CAPSS_GOLDILOCKS = {"bytes": 9715, "sign_ms": 101, "verify_ms": 1.4}
CAPSS_GOLDILOCKS_R1CS = (80_000, 100_000)
CAPSS_BN254_SIGN_MS = 2460
CAPSS_FIELD_FACTOR = 4
LEANSPHINCS_GRIND = 2 ** (26 - 12)
LEANSPHINCS_LIFETIME = 126_900
LEANSPHINCS_LAYERED_VERIFY = {"keccak": 408, "blake2s": 462}
LEANSPHINCS_LAYERED_SIG_BYTES = 6332
LEANSPHINCS_ETHEREUM_PERMS = 515
LEANSPHINCS_ETHEREUM_BYTES = 7740
LEDGER_HASH_PER_S = {"keccak": 5800, "blake2s": 32600}
# One call of each hash as prime-field gates, AND gates, and bits or digits.
HASH_UNITS = {
    "blake3": {"gates": BLAKE3_GATES, "boolean": BLAKE3_ANDS, "bits": BLAKE3_BITS},
    "blake2s": {"gates": BLAKE2S_BITS, "boolean": BLAKE2S_ANDS, "bits": BLAKE2S_BITS},
    "keccak": {"gates": KECCAK_BITS, "boolean": KECCAK_ANDS, "bits": KECCAK_BITS},
}
HASH_PIOPS = {"blake3": BLAKE3_PIOP, "blake2s": BLAKE2S_PIOP, "keccak": KECCAK_PIOP}
# The wallet's own share of the device statement when the host proves the handoff. The
# handoff merge's witness is simulatable: the hiding commitment, the mask's commitment, the
# challenge, the claims and the obligation transcripts (the zero-knowledge note's §4.2). So the
# host can derive the challenge, prove the fold's merge and the obligations (the note's §5.8
# deferral), and verify the leaf's sum-checks in its own merge. The wallet keeps what touches
# the secret. It commits the leaf with a hiding padding at the masked rank. It proves its
# constraint and Booleanity sum-checks under Libra-style masking polynomials, ℓ (d + 1)
# committed elements each with ℓ the rounds, since the host sees their transcripts. It samples
# and commits the mask in idle time, and computes the response z = y + cs with the rejection
# test. The padding is computational. Aρ for ρ of HIDING_PADDING_BITS uniform bits is
# pseudorandom if knapsack-LWE is hard at the commitment's rows, which by the Micciancio–Mol
# duality is LWE of dimension bits − rows with rows samples and binary secret and error at the
# 64-bit modulus. HIDING_PADDING_ATTACK_BITS is the pinned lattice estimator's cheapest attack
# on that instance at 5,000 bits under the ADPS16 quantum model, by rows, and
# HIDING_PADDING_SWEEP the same at the device's 1,024 rows by the padding's bits
# (scripts/knapsack-lwe-check.py, REGENERATING.md): the dual hybrid attack on the binary
# secret, about a hundred bits below the primal attacks, so a primal estimate alone overstates
# the margin. The padding is sized per floor, the least on the sweep's grid, 50 bits where the
# floors are crossed, whose cheapest attack reaches the floor, so that the higher floor's hedge
# covers it too (the user, 2026-11-23). The device's matrix is the ℓ∞ route's for its own
# vector (accumulation_matrix, qk_device_matrix_rows); the zero-knowledge note's Euclidean
# masked matrix at q64 has 1,385 rows. The note's leftover-hash padding would be rows × 64 +
# 256 bits.
# Device rates are assumptions scaled from sphincs.art's hardware-wallet benchmark. A Ledger
# Nano S+ hashes BLAKE2s about 500 times below a laptop core and a Trezor Safe 3 about 200
# times, and 64-bit modular multiplication fares worse on a 32-bit core. The link rates are
# that benchmark's measured USB rate on the Nano S+ and its estimate for a pipelined transport.
HIDING_PADDING_SWEEP_ROWS = 1024  # the matrix rows the padding sweep below was run at
HIDING_PADDING_ATTACK_BITS = {1024: 159.3, 1385: 140.5, 2048: 107.1}
HIDING_PADDING_SWEEP = {
    3500: 83.8,
    3750: 95.7,
    4000: 108.1,
    4250: 120.8,
    4300: 123.3,
    4350: 125.6,
    4400: 128.3,
    4450: 130.9,
    4500: 133.3,
    4550: 136.0,
    4600: 138.6,
    4650: 141.2,
    4700: 143.7,
    4750: 146.3,
    4800: 148.9,
    4850: 151.5,
    4900: 154.2,
    4950: 156.8,
    5000: 159.3,
    5250: 172.6,
    5500: 186.0,
    5750: 199.6,
    6000: 213.4,
}
HIDING_PADDING_BITS = {
    floor: min(bits for bits, attack in HIDING_PADDING_SWEEP.items() if attack >= floor)
    for floor in (128, 147)
}
assert HIDING_PADDING_BITS == {128: 4400, 147: 4800}
SUMCHECK_MASK_DEGREE = 3
DEVICE_WORD_MULTS_PER_S = {"mcu": 1e7, "secure_element": 3e6}
DEVICE_LINK_BYTES_PER_S = {"measured": 21_000, "pipelined": 58_000}
# An animated QR channel (the hardware-wallets chapter): Keystone's firmware sends fountain-coded
# fragments of QR_FRAGMENT_BYTES at QR_FRAMES_PER_S, a kilobyte a second. A denser fragment
# that the format allows, and the ceiling of a version-40 symbol at error-correction level L,
# 4,296 alphanumeric characters or about 2,100 bytes of fragment after the UR encoding's
# overhead, are neither a demonstrated reliable operating point: reading dense codes depends on
# the screen, the light and the camera. The fountain code's redundancy after missed frames
# multiplies the lossless time, by about two at a quarter of the frames missed.
QR_FRAGMENT_BYTES = 200
QR_FRAMES_PER_S = 5
QR_DENSE_FRAGMENT_BYTES = 800
QR_MAX_FRAGMENT_BYTES = 2100


def hash_app_cost(field, hash_, calls, input_bytes=0):
    """`calls` of `hash_` and `input_bytes` of witness in the unit of `field`'s
    arithmetization: the inputs are tribits in Kishu, since a hash consumes its message words
    as addends, committed bits in BitZ, Boolean-checked wires in a field, and free wires in a
    Boolean circuit."""
    unit = bits_unit(field)
    kind = unit if unit in ("boolean", "bits") else "gates"
    if kind == "boolean":
        inputs = 0
    elif field in KISHU_ARITHS:
        inputs = word_digits(8 * input_bytes)
    else:
        inputs = 8 * input_bytes
    return calls * HASH_UNITS[hash_][kind] + inputs


def hash_app_piop(hash_, calls, input_bytes=0):
    """The constraint counts of `calls` of `hash_` in Kishu's PIOP, with the input words' range
    checks beyond one product a digit."""
    return piop_sum((calls, HASH_PIOPS[hash_]), (1, word_range_piop(8 * input_bytes)))


# Kishu's claim field and transcript: an F_q value as one-bit digits, a multiplication in E,
# the Poseidon variant's rate and cost, the range check before BLAKE3 hashes a prover-supplied
# word, and the digits and constraints of absorbing transcript bytes. Here, before the
# applications, since Zoodles prices its set openings with them.
Q64_BITS = 64
Q64_DIGITS = word_digits(Q64_BITS)  # an F_q value as digits: 21 tribits and a bit
E_MULT_DIGITS = 2 * Q64_DIGITS  # a multiplication in E: its output, two F_q values, as digits
STAGE_VALUE_COEFFICIENTS["kishu"] = (
    E_MULT_DIGITS  # a stage value, a claim-field element, as tribits
)
Q64_POSEIDON_RATE_BYTES = 8 * 8  # width 12, rate 8, 8-byte words
assert BLAKE3_BLOCK % Q64_POSEIDON_RATE_BYTES == 0  # circuit_slope spans whole blocks of either
Q64_POSEIDON_MULTS = 138 * 2  # 8 full and 42 partial rounds of x^3 (calc_round_numbers.py)
# A 64-bit value is a canonical F_q element only below q = 2^64 - 59, so a prover-supplied
# word whose bytes BLAKE3 hashes is first checked to be below q: the difference q - 1 - w is
# committed as a 64-bit word with one linear constraint, as many digits as the word. Poseidon
# absorbs the field elements themselves and needs none. In BitZ's bits the check is the
# conjunction of bits 63 to 6, the test on the low six bits, and one constraint forbidding
# both, about 63 committed bits.
RANGE_CHECK_DIGITS = word_digits(Q64_BITS)
RANGE_CHECK_BITS = 57 + 5 + 1


# Two constraints per S-box, their linear forms over about fifty state words after the partial
# rounds' layers; and the range checks of the multiplications' outputs beyond one product a digit.
POSEIDON_Q64_PIOP = piop_sum(
    (1, (Q64_POSEIDON_MULTS, 0, 138 * 100)), (Q64_POSEIDON_MULTS, word_range_piop(Q64_BITS))
)
RANGE_CHECK_PIOP = piop_sum((1, (1, 2, 0)), (1, word_range_piop(Q64_BITS)))
# Three field products by Karatsuba; the output's two values' range checks.
E_MULT_PIOP = piop_sum((1, (3, 12, 0)), (2, word_range_piop(Q64_BITS)))


def absorb_calls(bytes_, block, whole):
    """The hash calls that absorb `bytes_` at `block` bytes a call: whole calls for a whole
    transcript, the plain quotient for a share of a larger one."""
    return ceil_div(bytes_, block) if whole else bytes_ / block


def absorb_digits(bytes_, hp, checked_words=0, range_check=RANGE_CHECK_DIGITS, whole=False):
    """Digits to absorb `bytes_` of transcript under policy `hp`, with `checked_words`
    prover-supplied words range-checked before BLAKE3 hashes them, at `range_check` digits
    each: Kishu's by default, RANGE_CHECK_BITS for BitZ. `whole` says the bytes are a
    transcript of their own and not a share of the merge's."""
    if hp == "poseidon":
        calls = absorb_calls(bytes_, Q64_POSEIDON_RATE_BYTES, whole)
        return calls * Q64_POSEIDON_MULTS * Q64_DIGITS
    return absorb_calls(bytes_, BLAKE3_BLOCK, whole) * BLAKE3_BITS + checked_words * range_check


def absorb_piop(bytes_, hp, checked_words=0, whole=False):
    if hp == "poseidon":
        return piop_sum((absorb_calls(bytes_, Q64_POSEIDON_RATE_BYTES, whole), POSEIDON_Q64_PIOP))
    return piop_sum(
        (absorb_calls(bytes_, BLAKE3_BLOCK, whole), BLAKE3_PIOP), (checked_words, RANGE_CHECK_PIOP)
    )


# A Tachyon transaction keeps Tachyon's own proof tree (tachyon-zcash/tachyon 73031f7,
# `Stamp::prove`). A spend is a SpendBind and a SpendAction step, and an output an OutputBind
# seed and an OutputAction step. Each action after the first is an ActionMerge; then come the
# FeeFuse and Ragu's rerandomization, two fuses with the public bootstrap proof as the right
# child in Ragu at ef7668fb (one in the older Ragu that Tachyon pins). So a transaction of s
# spends and o outputs is 3s + 3o + 2 nodes. The page re-packs the tree for each rank's step
# size: a node larger than a step takes whole steps and its remainder joins the rest, which
# fill steps first-fit decreasing, and each rerandomization fuse, the list's last two nodes,
# is its own step. At rank 13 over
# Pasta no two action circuits share a step and the merge rides with the fee step; at rank 15
# every circuit of two tachyactions fits one step. The circuits were measured on 2026-11-14
# through Ragu's synthesis analysis on Tachyon's steps, at its header size of 9 over its
# stage of 5 values. They are Pasta gates with Poseidon, a gate being one multiplication with
# free linear constraints, and all are within the 2,048 of rank 13. In the other
# arithmetizations the transaction is Tachyon's circuits as they are: a pre-quantum protocol
# proven in a post-quantum proof system. That is not a useful deployment, which Zoodles is,
# but it compares the proof systems on the same application. The Poseidon permutations, two
# gates per S-box of degree 5 and 192 per permutation, are hashed under the page's policy. The
# fixed-base scalar multiplications' window selections, two gates per three-bit window in
# Ragu, cost the bits' four monomials in any unit, since the limbs' selections are then
# linear; each window's point addition, two gates, and each opening of a staged value at zeta,
# two gates by the action merge's 17 for six, are Pallas base-field multiplications. The
# remaining gates are the scalars' bit checks, the canonicity and range comparisons and the
# step's glue (the statements note), priced as bit operations, one gate, AND gate or committed
# bit each, which understates any among them that multiply field elements; `bits_as_mults`
# prices them as multiplications instead, for the prose's bound. The windows are 85 for a
# 255-bit scalar and 17 for a 51-bit amount (keep/tachyon-statements.md, the cost table). The
# rerandomization's circuit is the adapter's own handful of gates. Per-note steps (NoteSeed,
# NullifierDerive, the spendable and anchor-span steps) run in the background and are not
# counted, as in the benchmarks.
TACHYON_STEPS = {  # Pasta gates at header 9 and stage 5; Poseidon permutations; windows; openings
    "SpendBind": (1630, 2, 102, 0),
    "SpendAction": (1649, 3, 85, 2),
    "OutputBind": (1467, 2, 102, 0),
    "OutputAction": (1351, 2, 85, 2),
    "ActionMerge": (17, 0, 0, 6),
    "FeeFuse": (
        1934,
        3,
        102,
        4,
    ),  # the fee blind, the fee digest and the change commitment; the blind's 255-bit and the slack's 51-bit multiplications (stamp/proof/stamp.rs, gadgets/note.rs)
    "Rerandomize": (20, 0, 0, 0),
}
POSEIDON_RAGU_GATES = 192
WINDOW_SELECTION_GATES = 2  # Ragu's gates selecting a window's point among eight
WINDOW_SELECTION_OFF_PASTA = 4  # the three bits' four monomials, in any other unit
WINDOW_ADDITION_GATES = 2  # Ragu's gates adding a window's point, field multiplications
OPENING_GATES = 2  # Ragu's gates evaluating a staged value at zeta, field multiplications
BIT_GATE_OFF_PASTA = 1  # a bit check or a comparison's bit: one gate, AND gate or committed bit
BIT_CHECK_PIOP = (1, 2, 0)  # b² = b in Kishu's PIOP: one product term, two small nonzeros
# Tachyon's other gates stay priced as bits in Kishu too, since the measured counts do not
# separate its scalars' bit checks, which are bits, from its comparisons, which word digits
# would serve; Zoodles' range checks and sums, whose widths are known, take word digits.


def range_digits(field, bits):
    """A `bits`-bit range check or comparison in the unit of `field`'s arithmetization: the
    value's tribits in Kishu, a committed bit or a gate per bit elsewhere."""
    return word_digits(bits) if field in KISHU_ARITHS else bits * BIT_GATE_OFF_PASTA


def range_check_piop(bits):
    """A range check in Kishu's PIOP: one linear constraint over the value's digits, and the
    range check's products beyond one a digit."""
    return piop_sum((1, (1, word_digits(bits), 0)), (1, word_range_piop(bits)))


TACHYON_TRANSACTIONS = {
    2: (1, 1),
    4: (2, 2),
    8: (4, 4),
    16: (8, 8),
}  # tachyactions: spends, outputs


def tachyon_nodes(spends, outputs):
    return (
        ["SpendBind", "SpendAction"] * spends
        + ["OutputBind", "OutputAction"] * outputs
        + ["ActionMerge"] * (spends + outputs - 1)
        + ["FeeFuse", "Rerandomize", "Rerandomize"]
    )


def tachyon_node_cost(field, hp, node, bits_as_mults=False):
    """One proof-tree node's circuit in the unit of `field`'s arithmetization: its Poseidon
    permutations under policy `hp` where the field has a Poseidon, by BLAKE3 otherwise, its
    window selections as bit monomials, its window additions and openings as Pallas
    multiplications, and its other gates as bit operations, or as multiplications too under
    `bits_as_mults`."""
    gates, perms, windows, openings = TACHYON_STEPS[node]
    unit = bits_unit(field)
    if field == "pasta":
        mult = 1
    elif field == "boolean":
        mult = (1 + BOOL_REDUCTION) * mult_ands(255)
    else:
        mult = RECOVERY_MULT[field]
    if hp == "poseidon" and field == "pasta":
        permutation = POSEIDON_RAGU_GATES
    elif hp == "poseidon" and field in RECOVERY_PATH_POSEIDON:
        permutation = RECOVERY_PATH_POSEIDON[field] / 33
    else:
        permutation = RECOVERY_PATH_BLAKE3[unit] / 33
    selection = WINDOW_SELECTION_GATES if field == "pasta" else WINDOW_SELECTION_OFF_PASTA
    mults = windows * WINDOW_ADDITION_GATES + openings * OPENING_GATES
    other = gates - perms * POSEIDON_RAGU_GATES - windows * WINDOW_SELECTION_GATES - mults
    assert other >= 0, node
    bit = mult if bits_as_mults else BIT_GATE_OFF_PASTA
    return perms * permutation + windows * selection + mults * mult + other * bit


def recovery_piop(route):
    """The recovery circuit's constraint counts in Kishu's PIOP, by multiplication route."""
    return piop_sum(
        (7, BLAKE2B_PIOP),
        (1 + 33, BLAKE3_PIOP),
        (160, SINSEMILLA_CHUNK_PIOP),
        (1, REDUCTIONS_PIOP),
        (RECOVERY_MULTS, MULT_ROUTES[route][1]),
    )


def path_piop():
    return piop_sum((33, BLAKE3_PIOP))


def tachyon_node_piop(route, node):
    gates, perms, windows, openings = TACHYON_STEPS[node]
    mults = windows * WINDOW_ADDITION_GATES + openings * OPENING_GATES
    other = gates - perms * POSEIDON_RAGU_GATES - windows * WINDOW_SELECTION_GATES - mults
    return piop_sum(
        (perms, BLAKE3_PIOP),
        (windows, (4, 12, 0)),
        (mults, MULT_ROUTES[route][1]),
        (other, BIT_CHECK_PIOP),
    )


# AND gates per field multiplication in a Boolean circuit, a carry-less product of the field's
# width: Karatsuba at 128 and 256 bits, where its halving is exact; at 192 bits Toom-3 in
# characteristic 2 (Bodrato, WAIFI 2007), five products in place of a three-limb Karatsuba's
# six: three of 64 bits at the points 0, 1 and infinity, and two at x and x + 1, where a
# three-piece operand evaluates to 66 bits, a 64-bit product plus the cross terms of the two
# extra bits. Toom's other points are polynomials in x, which lengthen the pieces by their
# degree times k - 1, so larger k gains nothing at these widths and nothing at powers of two.
# Here, before the applications, since Zoodles prices its set bookkeeping with it.
CLMUL_ANDS = {
    128: 3**7,
    191: 3 * 3**6 + 2 * (3**6 + 2 * 2 * 64 + 4),
    192: 3 * 3**6 + 2 * (3**6 + 2 * 2 * 64 + 4),
    256: 3**8,
}


# ---- Zoodles, a spend protocol without Pasta arithmetic ------------------------------------
# A sketch (2026-11-21) of a shielded protocol with no curve arithmetic at all, named for the
# pasta-free noodle. It keeps Tachyon's architecture: the proof tree above without the
# rerandomization, and a note's membership and unspentness attested by a background lineage
# over the chain's anchors rather than by a Merkle path in the spend. The published tachygrams,
# a spend's two epoch nullifiers, an output's commitment and padding, and the fee step's change
# commitment, are roots of set polynomials that the merges multiply at the challenge. In Tachyon
# the set polynomials are Pedersen vector commitments and the bridge hash a Pedersen hash onto
# Pallas; here they are the proof system's own committed vectors with evaluation claims, and
# the bridge hash a BLAKE3 hash of the commitment, computed natively. A tachygram is an element
# of a 256-bit extension of the claim field (Pasta's own field; a quadratic extension of a
# 128-bit field or of Kishu's E; a quartic one of Goldilocks), so a root costs one
# multiplication there by Karatsuba, and an opening one more evaluation claim, absorbed by the
# merge above and folded by CLAIM_GATES multiplications. The curve goes. Amounts are
# range-checked and summed in the PCD headers in place of value commitments and the binding
# signature. Spend authorization is one of two methods per input. The first is a Sprout-like
# preimage check: the payment key is the BLAKE3 hash of the nullifier key and the quantum key,
# and the spend proves the quantum key's derivation from the quantum spending key too, two
# compressions where Tachyon's spend step derives the payment key alone. The second is a
# leanSPHINCS signature with one of LEANSPHINCS_VERIFY's hashes over a transaction digest
# (ZOODLES_SIGHASH_BYTES below), verified in the circuit with the public key as a witness,
# since the zero-knowledge fold hides it. The fee step fixes the fee last and hashes the change note,
# the maximum-fee note's value less the fee, as Tachyon's does. Every hash is BLAKE3 under
# either policy. The lineage's steps run in the background and are not in the transaction, as
# Tachyon's are not; `zoodles_epoch` below prices one epoch of them. The simpler variant
# `zoodles_merkle` proves a 32-level Merkle path under the page's policy in each spend
# instead, opening the note and deriving one nullifier there, with no set polynomials.
# Per node: BLAKE3 compressions, roots or products of set polynomials, openings at the
# challenge, and bits of range checks and header sums. A spend's bind step derives the two
# nullifiers and range-checks the epoch and the amount; its action step opens the payment key,
# under the preimage method derives the quantum key as well, and roots the nullifiers; an output's bind step hashes the commitment and the padding and
# range-checks the amount; its action step roots them; a merge multiplies the two sets and sums
# the amounts; the fee step hashes the change note, range-checks the slack, the fee and the
# change, and roots the change commitment.
ZOODLES_INPUTS = 2
ZOODLES_OUTPUTS = 2
ZOODLES_NOTE_COMPRESSIONS = 2
ZOODLES_AMOUNT_BITS = 51
# Tachyon's EPOCH_MAX + 1 is 2^32 block heights over epochs of 4,096 (constants.rs).
ZOODLES_EPOCH_BITS = 20
ZOODLES_SUM_BITS = 64
# A preimage check needs no transaction digest: it is proved inside the spend step, which the
# tree binds to the rest of the transaction, directly and through the PCD headers. A signature
# is made outside the proof, so its message must bind the transaction's effecting data: each
# spend's two epoch nullifiers, each output's commitment, the change commitment, the fee and
# the epoch (ZOODLES_SIGHASH_BYTES). An output's padding tachygram need not be in it, since
# the digest is never visible outside the step. The digest is a PCD header value: each spend
# verifies its signature over it, and the fee step recomputes it from the nullifiers and
# commitments that its children's headers carry, which a small transaction's headers hold
# (the user's design, 2026-11-21). The Merkle variant's digest is the same over its one
# nullifier a spend.
ZOODLES_TACHYGRAM_BITS = 256
ZOODLES_SIGHASH_BYTES = (
    (2 * ZOODLES_INPUTS + ZOODLES_OUTPUTS + 1) * ZOODLES_TACHYGRAM_BITS // 8
    + ZOODLES_SUM_BITS // 8
    + math.ceil(ZOODLES_EPOCH_BITS / 8)
)
ZOODLES_SIGHASH_COMPRESSIONS = math.ceil(ZOODLES_SIGHASH_BYTES / BLAKE3_BLOCK)
ZOODLES_MERKLE_SIGHASH_BYTES = (
    (ZOODLES_INPUTS + ZOODLES_OUTPUTS + 1) * ZOODLES_TACHYGRAM_BITS // 8
    + ZOODLES_SUM_BITS // 8
    + math.ceil(ZOODLES_EPOCH_BITS / 8)
)
ZOODLES_MERKLE_SIGHASH_COMPRESSIONS = math.ceil(ZOODLES_MERKLE_SIGHASH_BYTES / BLAKE3_BLOCK)
# The spend authorizations: the preimage check, and a leanSPHINCS signature with each hash.
ZOODLES_AUTHS = ("preimage", *(f"leansphincs_{h}" for h in LEANSPHINCS_VERIFY))


def leansphincs_hash(auth):
    """The hash of a `leansphincs_<hash>` authorization; None for the preimage check."""
    return auth.removeprefix("leansphincs_") if auth.startswith("leansphincs_") else None


ZOODLES_NODES = {  # compressions, roots, openings, and the widths of the range checks and sums
    "SpendBind": (2, 0, 0, (ZOODLES_EPOCH_BITS, ZOODLES_AMOUNT_BITS)),
    "SpendAction": (1, 2, 1, ()),
    "OutputBind": (2 * ZOODLES_NOTE_COMPRESSIONS, 0, 0, (ZOODLES_AMOUNT_BITS,)),
    "OutputAction": (0, 2, 1, ()),
    "ActionMerge": (0, 1, 3, (ZOODLES_SUM_BITS,)),
    "FeeFuse": (ZOODLES_NOTE_COMPRESSIONS, 1, 2, 3 * (ZOODLES_AMOUNT_BITS,) + (ZOODLES_SUM_BITS,)),
}
# Multiplications in the claim field for one in its 256-bit extension, where the field is not
# itself 256 bits wide; three elsewhere.
ZOODLES_ROOT_MULTS = {"pasta": 1, "fp128": 3, "goldilocks": 9}


def zoodles_nodes(spends, outputs):
    """Tachyon's tree without the two rerandomization fuses; the fee circuit is the root and is
    packed into a step with the rest, as the others are."""
    return tachyon_nodes(spends, outputs)[:-2]


BITZ_CLAIM_MULT_BITS = 128  # a product in BitZ's 128-bit field as committed bits


def claim_mult_cost(field):
    """One multiplication in a 128-bit claim field in the unit of `field`'s arithmetization: a
    native gate in a prime field, a carry-less Karatsuba product in a Boolean circuit, the
    product's two F_q values as tribits in Kishu, and its bits in BitZ."""
    if field == "boolean":
        return CLMUL_ANDS[128]
    if field in KISHU_ARITHS:
        return E_MULT_DIGITS
    if bits_unit(field) == "bits":
        return BITZ_CLAIM_MULT_BITS
    return 1


def zoodles_root_cost(field):
    return ZOODLES_ROOT_MULTS.get(field, 3) * claim_mult_cost(field)


def zoodles_opening_cost(field, hp):
    """One more evaluation claim: its bytes absorbed by the merge above, under the policy where
    the field has a Poseidon and by BLAKE3 otherwise, and CLAIM_GATES multiplications folding
    it."""
    fold = CLAIM_GATES * claim_mult_cost(field)
    if bits_unit(field) == "bits":
        kishu = field in KISHU_ARITHS
        hp = hp if kishu else "blake3"
        bytes_ = CLAIM_BYTES["kishu"]
        checked = bytes_ // 8 if hp == "blake3" else 0
        range_check = RANGE_CHECK_DIGITS if kishu else RANGE_CHECK_BITS
        return absorb_digits(bytes_, hp, checked, range_check) + fold
    if field == "boolean":
        return CLAIM_BYTES["fp128"] / BLAKE3_BLOCK * BLAKE3_ANDS + fold
    if hp == "poseidon":
        return RECOVERY_PATH_POSEIDON[field] / 33 + fold
    return CLAIM_BYTES[field] / BLAKE3_BLOCK * BLAKE3_GATES + fold


def zoodles_node_cost(field, hp, node, auth):
    """One Zoodles node in the unit of `field`'s arithmetization: its BLAKE3 compressions, its
    roots and openings, its bits, and under the signature authorization the leanSPHINCS
    verifier in a spend's action step and the transaction digest in the fee step."""
    blake3, roots, openings, widths = ZOODLES_NODES[node]
    verifier = 0
    if auth == "preimage" and node == "SpendAction":
        blake3 += 1  # qk = H^qk(qsk), beside the payment key's opening to (nk, qk)
    if h := leansphincs_hash(auth):
        if node == "SpendAction":
            verifier = hash_app_cost(field, h, LEANSPHINCS_VERIFY[h], LEANSPHINCS_SIG_BYTES)
        if node == "FeeFuse":
            blake3 += ZOODLES_SIGHASH_COMPRESSIONS
    return (
        hash_app_cost(field, "blake3", blake3)
        + roots * zoodles_root_cost(field)
        + openings * zoodles_opening_cost(field, hp)
        + sum(range_digits(field, bits) for bits in widths)
        + verifier
    )


def zoodles_node_piop(node, auth):
    blake3, roots, openings, widths = ZOODLES_NODES[node]
    parts = []
    if auth == "preimage" and node == "SpendAction":
        blake3 += 1
    if h := leansphincs_hash(auth):
        if node == "SpendAction":
            parts.append((1, hash_app_piop(h, LEANSPHINCS_VERIFY[h], LEANSPHINCS_SIG_BYTES)))
        if node == "FeeFuse":
            blake3 += ZOODLES_SIGHASH_COMPRESSIONS
    claim_bytes = CLAIM_BYTES["kishu"]
    return piop_sum(
        *parts,
        (blake3, BLAKE3_PIOP),
        (3 * roots + CLAIM_GATES * openings, E_MULT_PIOP),
        (openings, absorb_piop(claim_bytes, "blake3", claim_bytes // 8)),
        *((1, range_check_piop(bits)) for bits in widths),
    )


def zoodles_merkle_cost(field, hp, auth):
    """The Merkle-path variant's transaction: each spend opens its note, derives one nullifier
    and the payment key and proves its path under the policy, and under the signature
    authorization verifies its leanSPHINCS signature over the transaction digest; each output
    hashes its note; the fee step hashes the change note; the amounts are range-checked and
    summed."""
    amount = range_digits(field, ZOODLES_AMOUNT_BITS)
    total = range_digits(field, ZOODLES_SUM_BITS)
    spend = (
        path_cost(field, hp)
        + hash_app_cost(field, "blake3", ZOODLES_NOTE_COMPRESSIONS + 2 + (auth == "preimage"))
        + amount
    )
    sighash = 0
    if h := leansphincs_hash(auth):
        spend += hash_app_cost(field, h, LEANSPHINCS_VERIFY[h], LEANSPHINCS_SIG_BYTES)
        sighash = hash_app_cost(field, "blake3", ZOODLES_MERKLE_SIGHASH_COMPRESSIONS)
    output = hash_app_cost(field, "blake3", ZOODLES_NOTE_COMPRESSIONS) + amount
    fee = hash_app_cost(field, "blake3", ZOODLES_NOTE_COMPRESSIONS) + 3 * amount + total
    sums = (ZOODLES_INPUTS + ZOODLES_OUTPUTS - 1) * total
    return ZOODLES_INPUTS * spend + ZOODLES_OUTPUTS * output + fee + sighash + sums


def zoodles_merkle_piop(auth):
    blake3 = (
        ZOODLES_INPUTS * (ZOODLES_NOTE_COMPRESSIONS + 2 + (auth == "preimage"))
        + (ZOODLES_OUTPUTS + 1) * ZOODLES_NOTE_COMPRESSIONS
    )
    parts = [
        (ZOODLES_INPUTS, path_piop()),
        (blake3, BLAKE3_PIOP),
        (ZOODLES_INPUTS + ZOODLES_OUTPUTS + 3, range_check_piop(ZOODLES_AMOUNT_BITS)),
        (ZOODLES_INPUTS + ZOODLES_OUTPUTS, range_check_piop(ZOODLES_SUM_BITS)),
    ]
    if h := leansphincs_hash(auth):
        parts.append(
            (ZOODLES_INPUTS, hash_app_piop(h, LEANSPHINCS_VERIFY[h], LEANSPHINCS_SIG_BYTES))
        )
        parts.append((ZOODLES_MERKLE_SIGHASH_COMPRESSIONS, BLAKE3_PIOP))
    return piop_sum(*parts)


# ---- Zoodles' lineage: one note advanced one epoch ------------------------------------------
# The wallet's witness update, the shape of Tachyon's UnspentLift (stamp/proof/pool.rs): one
# step per epoch of ZOODLES_EPOCH_BLOCKS blocks, proving that the note's nullifier for the epoch
# is not among the epoch's published tachygrams. Tachyon attests that with a bucket, one
# residue profile's share of the epoch's tachygrams down to at most 2^ZOODLES_BUCKET_LOG members
# (its online polynomial slot), folded as a set polynomial that the step opens at the
# nullifier. Over Pedersen a commitment folds in one scalar multiplication; over digits the
# bucket's tachygrams would enter the wallet's accumulator element by element
# (ZOODLES_BUCKET_DIGITS, kept as the comparison), so Zoodles uses a sorted Merkle tree instead.
# The builder sorts the epoch's tachygrams once for everyone and hashes consecutive pairs into
# the leaves, so an exclusion proof is one leaf, the nullifier's two neighbours, with its path.
# The step derives the epoch's nullifier (one BLAKE3 compression), hashes the leaf and proves
# the path (ZOODLES_EPOCH_LOG + 1 hashes, under the page's policy as the Merkle variant's path
# is), compares the nullifier with both neighbours (two 256-bit comparisons as bits) and
# range-checks the epoch. The tree's size is the user's choice (2026-11-22): 2^ZOODLES_EPOCH_LOG
# tachygrams an epoch, 256 a block at Tachyon's epoch, between the bucket's 2^13 and a busy
# chain's 2^24; a doubling adds one hash to the step, and a shorter epoch adds steps a day. The
# bind, lift and fuse steps that close a segment run once per spend, not per epoch, and are
# left out.
ZOODLES_BUCKET_LOG = 13
ZOODLES_BUCKET_DIGITS = 2**ZOODLES_BUCKET_LOG * ZOODLES_TACHYGRAM_BITS
# Tachyon's EPOCH_SIZE, at the chain's 25-second target spacing since NU7.
ZOODLES_EPOCH_BLOCKS = 4096
ZOODLES_BLOCK_SECONDS = 25
ZOODLES_EPOCH_LOG = 20


def tree_path_cost(field, hp, levels):
    """A Merkle path of `levels` levels and its leaf in the unit of `field`'s arithmetization,
    hashed under policy `hp` where the field has a Poseidon and by BLAKE3 otherwise: the
    32-level path's cost per hash, each level being one hash of two children."""
    return path_cost(field, hp) * (levels + 1) / 33


# A bucketed table for an epoch's tachygram set, the non-membership accumulator of
# zcash/zcash#4062, priced beside the sorted tree on the epoch-set page: m tachygrams of
# ZOODLES_TACHYGRAM_BITS go to 2^B buckets by prefix, a bucket holding up to K suffixes, and an
# honest note is lost when its bucket overflows, so K is the least that bounds the overflow
# probability below 2^-lambda, by a union bound over the buckets of the Poisson tail of a
# bucket's load (its mean m / 2^B). The exclusion proof is the B path hashes and the bucket's
# contents at BLAKE3's block.
BUCKET_TABLE_ROWS = ((20, 16), (20, 18), (20, 20), (34, 32), (34, 34))  # (log2 m, B)
BUCKET_TABLE_LAMBDAS = (64, 128)


def log2_poisson_tail(mu, k):
    """log2 of P[Poisson(mu) >= k], the terms summed in log space."""
    first = (-mu + k * math.log(mu) - math.lgamma(k + 1)) / math.log(2)
    total, term, j = 0.0, 1.0, k
    while term > 1e-30:
        total += term
        j += 1
        term *= mu / j
    return first + math.log2(total)


def bucket_capacity(log_m, B, lam):
    """The least bucket capacity K with 2^B * P[load >= K + 1] <= 2^-lam."""
    mu = 2**log_m / 2**B
    K = max(1, int(mu))
    while B + log2_poisson_tail(mu, K + 1) > -lam:
        K += 1
    return K


def bucket_proof_hashes(B, K, tag_bits=None):
    """The exclusion proof's hashes: the path and the bucket's K entries, full suffixes or
    `tag_bits`-bit tags, at 512 bits a compression."""
    bits = K * (tag_bits if tag_bits else ZOODLES_TACHYGRAM_BITS - B)
    return B + math.ceil(bits / (8 * BLAKE3_BLOCK))


def bucket_tag_bits(log_m, B, lam):
    """Tags of T bits add a within-bucket collision term of about m * mu / 2^(T + 1)."""
    return log_m + (log_m - B) - 1 + lam


def zoodles_epoch_cost(field, hp):
    """The lineage step in the unit of `field`'s arithmetization."""
    return (
        hash_app_cost(field, "blake3", 1)
        + tree_path_cost(field, hp, ZOODLES_EPOCH_LOG)
        + 2 * range_digits(field, ZOODLES_TACHYGRAM_BITS)
        + range_digits(field, ZOODLES_EPOCH_BITS)
    )


def zoodles_epoch_piop():
    return piop_sum(
        (ZOODLES_EPOCH_LOG + 2, BLAKE3_PIOP),
        (2, range_check_piop(ZOODLES_TACHYGRAM_BITS)),
        (1, range_check_piop(ZOODLES_EPOCH_BITS)),
    )


# ---- Migration: recovery spends from an older pool with a Zoodles output ---------------------
# What a post-quantum proof system proves for the older pools is a migration: recovery spends
# of Tachyon or Ironwood notes and one Zoodles output, in Zoodles' proof tree with a recovery
# node in place of each spend's two steps. The transactions offered spend MIGRATION_INPUTS
# notes of one pool.
#   - An Ironwood input is the Ironwood recovery circuit (recovery_cost), ZIP 2005's Recovery
#     Statement.
#   - A Tachyon input is the recovery spend of the Recovery from Tachyon page, with the payment
#     key changed as that page suggests: H^qk(qsk) = qk, one BLAKE3 compression, and qk's
#     reduction modulo p, a 256-bit range check; four Poseidon permutations over Pallas
#     (TACHYON_RECOVERY_PERMUTATIONS: the payment key, the note's master key, the note
#     commitment, and the nullifier group's sponge, by Tachyon's key and nullifier definitions
#     in keep/tachyon-statements.md); the commitment's path in a hash-based tree over Tachyon's
#     published commitments and the nullifier's exclusion from a sorted tree over its published
#     nullifiers, each MIGRATION_TREE_LEVELS levels and a leaf under the page's policy, the
#     exclusion with its two 256-bit comparisons as the lineage step has them; and the amount's
#     and the epoch's range checks. One nullifier is derived and excluded here; a note's
#     nullifiers for the other epochs it has lived through are a lineage in the background, as
#     Zoodles' own is, and are not counted.
# Poseidon over Pallas is native over Pasta, POSEIDON_RAGU_GATES a permutation. In any other
# unit a permutation's POSEIDON_PALLAS_SBOXES S-boxes of degree five are three Pallas
# multiplications each, and one more reduces each S-box's input, a linear combination of
# earlier reduced values with constants of the field's size, whose relation is linear in the
# witness but needs its own quotient and result.
# Each recovery node joins the action tree as a spend's action step does, with that step's
# roots and openings. The output, the merges, and the fee step are Zoodles' own.
MIGRATION_INPUTS = (1, 4)
MIGRATION_POOLS = ("tachyon", "ironwood")
MIGRATION_TREE_LEVELS = 32
POSEIDON_PALLAS_SBOXES = POSEIDON_RAGU_GATES // 2
POSEIDON_PALLAS_MULTS = 4 * POSEIDON_PALLAS_SBOXES
TACHYON_RECOVERY_PERMUTATIONS = 4
TACHYON_RECOVERY_RANGES = 3 * (256,) + (ZOODLES_AMOUNT_BITS, ZOODLES_EPOCH_BITS)
MIGRATION_RECOVERY_NODES = {"tachyon": "TachyonRecovery", "ironwood": "IronwoodRecovery"}


def migration_nodes(pool, inputs):
    """Zoodles' tree for `inputs` recovery spends from `pool` and one output: a recovery node
    for each input, the output's two steps, a merge per action after the first, and the fee
    step."""
    return (
        [MIGRATION_RECOVERY_NODES[pool]] * inputs
        + ["OutputBind", "OutputAction"]
        + ["ActionMerge"] * inputs
        + ["FeeFuse"]
    )


def pallas_mult_cost(field):
    """One Pallas base-field multiplication in the unit of `field`'s arithmetization."""
    if field == "pasta":
        return 1
    if field == "boolean":
        return (1 + BOOL_REDUCTION) * mult_ands(255)
    return RECOVERY_MULT[field]


def poseidon_pallas_cost(field):
    """One Poseidon permutation over Pallas, which a recovery spend must open as Tachyon
    computed it, whatever the page's hash policy."""
    if field == "pasta":
        return POSEIDON_RAGU_GATES
    return POSEIDON_PALLAS_MULTS * pallas_mult_cost(field)


def tachyon_recovery_cost(field, hp):
    """One Tachyon recovery spend in the unit of `field`'s arithmetization."""
    return (
        hash_app_cost(field, "blake3", 1)
        + TACHYON_RECOVERY_PERMUTATIONS * poseidon_pallas_cost(field)
        + 2 * tree_path_cost(field, hp, MIGRATION_TREE_LEVELS)
        + sum(range_digits(field, bits) for bits in TACHYON_RECOVERY_RANGES)
    )


def migration_node_cost(field, hp, node):
    _, roots, openings, _ = ZOODLES_NODES["SpendAction"]
    join = roots * zoodles_root_cost(field) + openings * zoodles_opening_cost(field, hp)
    if node == "TachyonRecovery":
        return tachyon_recovery_cost(field, hp) + join
    if node == "IronwoodRecovery":
        return recovery_cost(field, hp) + join
    return zoodles_node_cost(field, hp, node, "preimage")


def migration_node_piop(route, node):
    if node not in MIGRATION_RECOVERY_NODES.values():
        return zoodles_node_piop(node, "preimage")
    _, roots, openings, _ = ZOODLES_NODES["SpendAction"]
    claim_bytes = CLAIM_BYTES["kishu"]
    join = (
        (3 * roots + CLAIM_GATES * openings, E_MULT_PIOP),
        (openings, absorb_piop(claim_bytes, "blake3", claim_bytes // 8)),
    )
    if node == "IronwoodRecovery":
        return piop_sum((1, recovery_piop(route)), *join)
    return piop_sum(
        (1 + 2 * (MIGRATION_TREE_LEVELS + 1), BLAKE3_PIOP),
        (TACHYON_RECOVERY_PERMUTATIONS * POSEIDON_PALLAS_MULTS, MULT_ROUTES[route][1]),
        *((1, range_check_piop(bits)) for bits in TACHYON_RECOVERY_RANGES),
        *join,
    )


MIGRATIONS = {f"{pool}_zoodles{n}": (pool, n) for pool in MIGRATION_POOLS for n in MIGRATION_INPUTS}


ARITHS = ("pasta", "goldilocks", "fp128", "boolean", "bitz", *KISHU_ARITHS)
APPLICATIONS = {  # the page's transaction applications, in each arithmetization's unit under each policy
    "recovery": {a: {hp: round(recovery_cost(a, hp)) for hp in HASH_POLICIES} for a in ARITHS},
    "path": {a: {hp: round(path_cost(a, hp)) for hp in HASH_POLICIES} for a in ARITHS},
    # The hardware wallet's part of the Recovery Statement: the device's statement, and a
    # leanSPHINCS verifier with each of the three hashes; their hash is the scheme's under
    # either policy.
    "qk": {a: {hp: round(hash_app_cost(a, "blake3", 1)) for hp in HASH_POLICIES} for a in ARITHS},
    **{
        f"leansphincs_{h}": {
            a: {hp: round(hash_app_cost(a, h, n, LEANSPHINCS_SIG_BYTES)) for hp in HASH_POLICIES}
            for a in ARITHS
        }
        for h, n in LEANSPHINCS_VERIFY.items()
    },
    # A Zoodles transaction is its proof tree's nodes, each in the unit, in order, by spend
    # authorization; the Merkle-path variant is one circuit.
    **{
        f"zoodles_{auth}": {
            a: {
                hp: [
                    round(zoodles_node_cost(a, hp, node, auth))
                    for node in zoodles_nodes(ZOODLES_INPUTS, ZOODLES_OUTPUTS)
                ]
                for hp in HASH_POLICIES
            }
            for a in ARITHS
        }
        for auth in ZOODLES_AUTHS
    },
    **{
        f"zoodles_merkle_{auth}": {
            a: {hp: round(zoodles_merkle_cost(a, hp, auth)) for hp in HASH_POLICIES} for a in ARITHS
        }
        for auth in ZOODLES_AUTHS
    },
    # One Zoodles note's lineage advanced one epoch.
    "zoodles_epoch": {
        a: {hp: round(zoodles_epoch_cost(a, hp)) for hp in HASH_POLICIES} for a in ARITHS
    },
    # A Tachyon transaction is its proof tree's nodes, each in the unit, in order.
    **{
        f"tachyon{n}": {
            a: {
                hp: [round(tachyon_node_cost(a, hp, node)) for node in tachyon_nodes(s, o)]
                for hp in HASH_POLICIES
            }
            for a in ARITHS
        }
        for n, (s, o) in TACHYON_TRANSACTIONS.items()
    },
    # A migration is Zoodles' tree with a recovery node for each input.
    **{
        app: {
            a: {
                hp: [round(migration_node_cost(a, hp, node)) for node in migration_nodes(pool, n)]
                for hp in HASH_POLICIES
            }
            for a in ARITHS
        }
        for app, (pool, n) in MIGRATIONS.items()
    },
}
# The work of Kishu's constraint PIOP per application, by multiplication route, which the
# transaction measure adds to its rows (DATA.piop); the other families' PIOPs are inside their
# measured or modelled provers.
PIOP_WORK = {
    "recovery": {a: round(piop_word_mults(recovery_piop(kishu_route(a)))) for a in KISHU_ARITHS},
    "path": {a: round(piop_word_mults(path_piop())) for a in KISHU_ARITHS},
    "qk": {a: round(piop_word_mults(hash_app_piop("blake3", 1))) for a in KISHU_ARITHS},
    **{
        f"leansphincs_{h}": {
            a: round(piop_word_mults(hash_app_piop(h, n, LEANSPHINCS_SIG_BYTES)))
            for a in KISHU_ARITHS
        }
        for h, n in LEANSPHINCS_VERIFY.items()
    },
    **{
        f"zoodles_{auth}": {
            a: round(
                sum(
                    piop_word_mults(zoodles_node_piop(node, auth))
                    for node in zoodles_nodes(ZOODLES_INPUTS, ZOODLES_OUTPUTS)
                )
            )
            for a in KISHU_ARITHS
        }
        for auth in ZOODLES_AUTHS
    },
    **{
        f"zoodles_merkle_{auth}": {
            a: round(piop_word_mults(zoodles_merkle_piop(auth))) for a in KISHU_ARITHS
        }
        for auth in ZOODLES_AUTHS
    },
    "zoodles_epoch": {a: round(piop_word_mults(zoodles_epoch_piop())) for a in KISHU_ARITHS},
    **{
        f"tachyon{n}": {
            a: round(
                sum(
                    piop_word_mults(tachyon_node_piop(kishu_route(a), node))
                    for node in tachyon_nodes(s, o)
                )
            )
            for a in KISHU_ARITHS
        }
        for n, (s, o) in TACHYON_TRANSACTIONS.items()
    },
    **{
        app: {
            a: round(
                sum(
                    piop_word_mults(migration_node_piop(kishu_route(a), node))
                    for node in migration_nodes(pool, n)
                )
            )
            for a in KISHU_ARITHS
        }
        for app, (pool, n) in MIGRATIONS.items()
    },
}

# Whether an application has Pasta multiplications, which is when Kishu's fingerprint route
# pays its per-step cost (DATA.has_mults).
APPLICATION_MULTS = (
    {"recovery": True, "path": False, "qk": False}
    | {f"leansphincs_{h}": False for h in LEANSPHINCS_VERIFY}
    | {f"zoodles_{auth}": False for auth in ZOODLES_AUTHS}
    | {f"zoodles_merkle_{auth}": False for auth in ZOODLES_AUTHS}
    | {"zoodles_epoch": False}
    | {f"tachyon{n}": True for n in TACHYON_TRANSACTIONS}
    | {app: True for app in MIGRATIONS}
)
# The proof trees whose last node, Ragu's rerandomization, is a step of its own when the tree
# is re-packed into steps (DATA.own_last_steps), and how many such nodes end the list: two for
# Ragu's two-pass rerandomization. Zoodles has no such node.
OWN_LAST_STEPS = {f"tachyon{n}": 2 for n in TACHYON_TRANSACTIONS}
# The applications whose user hands over a bare leaf without a fuse of their own, so that the
# masking fold covers the leaf's 2^rank digits rather than a chain's accumulator, and the merge
# that folds the leaf is the host's (DATA.leaf_handoff; the hardware-wallets chapter). Every
# other application's user chain has merges, and its last accumulator is what the fold masks.
LEAF_HANDOFF = {"qk"}

# The arithmetization of each family's application circuit, for `step_gates`; Kishu's rows
# set theirs by multiplication route.
FIELD = {
    "pedersen": "pasta",
    "fp128": "fp128",
    "goldilocks": "goldilocks",
    "pasta_q64": "pasta",
    "pasta_sis": "pasta",
    "pasta": "pasta",
    "whir": "pasta",
    "whir_gold": "goldilocks",
    "whir_hybrid": "pasta",
    "plonky3": "goldilocks",
    "flock": "boolean",
    "whir_rec": "pasta",
    "whir_gold_rec": "goldilocks",
    "whir_hybrid_rec": "pasta",
    "plonky3_rec": "goldilocks",
    "flock_rec": "boolean",
    "bitz": "bitz",
    "bitz_rec": "bitz",
    "bits_q64": "bits_pasta_limbs",
    "bits_q64_poseidon": "bits_pasta_limbs",
}

points = []

# Header sizes for the Pedersen-IPA rows: 2 and 4 as the study priced them, and 9, Tachyon's
# HEADER_SIZE (tachyon-zcash/tachyon, crates/tachyon/src/stamp/proof.rs). The post-quantum rows
# are priced at 2 and 4 and the page shows them at 2.
TACHYON_HEADER = 9
# One header element in the proof: a packed Pasta element in each of the left and right
# child's copies, for every scheme alike.
HEADER_ELEMENT_BYTES = 2 * 32
PCD_HEADERS = (
    2,
    4,
    TACHYON_HEADER,
)  # the header sizes the page offers; a Tachyon or recovery transaction forces 9

# Pedersen-IPA: the checked-in cycle design, over the configurations the circuit budget
# allows at each rank, with the fixed circuits as today or packed into the rank's budget.
for rank in RANKS:
    if _model["challenges_per_binder"](rank) < 1 or max_endoscalings(rank) < 1:
        continue  # a rank-12 circuit holds no binder challenge and no endoscaling point
    for packing in (False, True):
        Fn, Fm = fixed_counts(rank, packing)
        if packing and (Fn, Fm) == (19, 14):
            continue
        Emax = max_endoscalings(rank)
        for E in sorted({e for e in (4, 6, 8, 12, 16, 24, 32, Emax) if e <= Emax}):
            for binders in range(min_binders(rank), 5):
                r = size(Fn, Fm, binders, E, E, rank, 0)
                if r is None:
                    continue
                total, nat, nes = r
                commitments = nat + 2 + nes + 2
                # Rank and endoscalings per step are constants in the code; a
                # binder that binds more than two challenges, or merged fixed circuits,
                # are code changes within the protocol.
                change = "code" if (packing or binders < 4) else "none"
                # Shown at the 128-bit floor only: about 126 classical bits, no post-quantum
                # security (see the security-floor section below).
                points.append(
                    dict(
                        family="pedersen",
                        pq=False,
                        rank=rank,
                        E=E,
                        binders=binders,
                        floor=128,
                        groups=None,
                        packing=packing,
                        circuits=nat + nes,
                        change=change,
                        zk=None,
                        hashes="poseidon",
                        bytes=total,
                        prover=round(commitments * 2**rank * pedersen_per_coefficient(rank)),
                        step_prover=round(2**rank * pedersen_per_coefficient(rank)),
                        fold=0,
                        memory=commitments * 2**rank * 32,
                        accumulation=2 * (nat + nes + 5),  # base-field atoms absorbed per merge
                        gates=gates_per_merge(binders, E, E, nat, nes),
                        verify=pedersen_verify(rank, nat, nes),
                        folded=nat + nes + 5,
                        label=f"rank {rank}, {E} endoscalings/step, {binders} binder{'s' if binders != 1 else ''}"
                        + (", packed" if packing else ""),
                    )
                )

# The calibration's check: the checked-in row's step and merge are the measured fuse.
_checked_in = next(
    p
    for p in points
    if p["family"] == "pedersen"
    and p["rank"] == PEDERSEN_FUSE_RANK
    and p["E"] == 4
    and p["binders"] == 4
    and not p["packing"]
)
assert _checked_in["circuits"] + 5 == PEDERSEN_FUSE_COMMITMENTS, _checked_in["circuits"]
assert (
    abs(
        (_checked_in["step_prover"] + _checked_in["prover"]) / (1000 * WORD_MULTS_PER_MS)
        - PEDERSEN_FUSE_SECONDS
    )
    < 0.005
)

# ---- Security floor ----------------------------------------------------------------
# Akita's catalog and ARC's openings are sized at a 128-bit floor under the ADPS16 quantum
# core-SVP model. The higher floor is 147 bits, the most that Akita's rank-one compression
# maps allow at the catalog's geometry: the compression chain's first map, at ring dimension
# 16 and width 4,096, certifies at 147.3 bits, and a higher floor would need rank-two maps
# or two maps where there is one, which doubles the compressed images at every level (a
# 150-bit floor was tried first, 2026-10-15 to 2026-11-12, and stopped there). At 147 bits
# Akita's catalog is re-planned by its own planner in a checkout whose single policy, runtime
# width tables and compression cells are retargeted to that floor (2026-11-12), so the
# openings in AKITA[147] are planned. What the planner does not give, the prover's rows term
# and the verifier's inner-image share, takes the rank growth: for the weakest Module-SIS
# instance of each schedule in the shipped catalog's security report (115 schedules: 79 fp128,
# 17 fp64, 19 fp32), the smallest module rank whose maximum secure width covers the instance's
# width, at both floors, with the instance mapped through the modulus that the variant commits
# over; the ratio of the summed ranks is the factor (scripts/rank-scale.py, from the width tables
# regenerated at 147 bits: the catalog's own moduli and the Goldilocks table on 2026-11-12,
# the Pallas table on 2026-11-15). RANK_SUMS_147 holds, per mapping, the summed ranks at 128
# and 147 bits and the instances that move up a rank: the catalog's own mix of q128, q64 and
# q32 cells; the 64-bit modulus (the Goldilocks table, identical to q64's for these cells);
# and Pallas, where the instances sit at the width cap at both floors but one. WHIR's proofs measure 18%
# larger at 150 bits over both fields, taken as 16% at 147; ARC's openings scale with the
# floor. Pedersen-IPA over Pasta has about 126 classical bits (Pollard rho on a group of order
# near 2^254) and no post-quantum security, so it is shown at the 128-bit floor only, as the
# conventional pre-quantum baseline, and drops out at 147 bits.
RANK_INSTANCES = 115
RANK_SUMS_147 = {"own": (121, 150, 29), "q64": (185, 211, 26), "pallas": (117, 118, 1)}
RANK_MAPPING = {
    "fp128": "own",
    "goldilocks": "q64",
    "pasta_q64": "q64",
    "pasta_sis": "pallas",
    "pasta": "pallas",
}
RANK_SCALE_147 = {
    v: round(RANK_SUMS_147[m][1] / RANK_SUMS_147[m][0], 2) for v, m in RANK_MAPPING.items()
}
assert RANK_SCALE_147 == {
    "fp128": 1.24,
    "goldilocks": 1.14,
    "pasta_q64": 1.14,
    "pasta_sis": 1.01,
    "pasta": 1.01,
}
RANK_SCALE = {128: {v: 1.0 for v in RANK_SCALE_147}, 147: RANK_SCALE_147}
# WHIR at the higher floor: the reference implementation (WizardOfMenlo/whir at afec1fa) at
# 2^17 variables over both fields and rates 1/2 to 1/8, 20 bits of proof of work, the Johnson
# regime, at 128 and 147 bits (2026-11-15; scripts/whir-sweep-147.sh): proof KiB and verifier
# hashes in thousands at each floor. The proofs grow with the floor through the query count,
# independently of any lattice instance; the mean ratios are the page's factors.
WHIR_147 = {  # (field, rate): (KiB at 128, KiB at 147, khashes at 128, khashes at 147)
    ("Field256", "1/2"): (244.3, 284.3, 2.7, 3.1),
    ("Field256", "1/4"): (154.6, 178.7, 2.0, 2.2),
    ("Field256", "1/8"): (122.7, 142.4, 1.7, 1.9),
    ("Goldilocks3", "1/2"): (134.9, 155.7, 2.7, 3.0),
    ("Goldilocks3", "1/4"): (99.4, 114.4, 2.0, 2.2),
    ("Goldilocks3", "1/8"): (84.0, 96.8, 1.7, 1.9),
}
WHIR_SCALE = {128: 1.0, 147: round(statistics.mean(b / a for a, b, _, _ in WHIR_147.values()), 2)}
WHIR_HASHES_SCALE = {
    128: 1.0,
    147: round(statistics.mean(d / c for _, _, c, d in WHIR_147.values()), 2),
}
assert WHIR_SCALE[147] == 1.16 and WHIR_HASHES_SCALE[147] == 1.12
ARC_FLOOR_PCT = round(100 * (147 / 128 - 1))  # ARC's openings per input grow with the floor
# How far the maximum secure widths shrink from 128 to 147 bits, per modulus and ring
# dimension: the median of width_128 / width_147 over the cells the floor binds (neither width
# at the estimator's search cap, the 147-bit width strictly smaller), with the cell count, from
# the production table's policy audit at 128 bits and the regenerated audit at 147 for the
# shipped moduli, and the estimator's CSV tables for Pallas and Goldilocks (scripts/width-shrink.py,
# 2026-11-15). The 32-bit modulus shrinks least; the few cells at the largest dimensions, where
# the 147-bit width is still finite, shrink about 36-fold.
WIDTH_SHRINK_147 = {
    "q128": {
        8: (2.7, 18),
        16: (2.8, 9),
        32: (3.0, 5),
        64: (10.0, 465),
        128: (12.3, 209),
        256: (12.9, 150),
        512: (14.0, 78),
        1024: (36.2, 36),
    },
    "q64": {
        16: (2.8, 19),
        32: (2.9, 10),
        64: (4.9, 560),
        128: (11.6, 412),
        256: (13.3, 294),
        512: (15.3, 173),
        1024: (14.7, 91),
        2048: (36.1, 44),
    },
    "q32": {
        32: (2.8, 20),
        64: (4.4, 421),
        128: (4.5, 140),
        256: (5.3, 98),
        512: (6.1, 41),
        1024: (6.3, 33),
    },
    "pallas": {
        8: (2.8, 9),
        16: (3.0, 5),
        32: (3.0, 2),
        64: (9.7, 236),
        128: (12.5, 102),
        256: (13.1, 65),
        512: (35.8, 29),
    },
    "goldilocks": {
        8: (2.1, 20),
        16: (2.8, 19),
        32: (2.9, 10),
        64: (5.3, 605),
        128: (11.5, 414),
        256: (13.1, 306),
        512: (14.7, 177),
        1024: (14.7, 91),
        2048: (36.1, 44),
    },
}
FLOORS = (128, 147)
assert DEFAULT_FLOOR in FLOORS
# Core-SVP's exponents per BKZ block size under each cost model, and the block size at each
# floor: the catalog's own check reports 128.26 bits at block 484 (its instances land at 484 to
# 486), and its rank-one compression maps certify at 147.3 bits, block 556 (the margin section).
CORE_SVP_EXPONENTS = {"classical": 0.292, "quantum": 0.265, "paranoid": 0.2075}
BLOCK_SIZES = {128: 484, 147: 556}
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
IMAGE_SHARE = {v: IMAGE_COORDS * IMAGE_COORD_BYTES[v] / AKITA[128][v][0] for v in IMAGE_COORD_BYTES}


def rank_factor_share(variant, factor):
    """The multiplier on the opening, or on the verifier's work, when the rank grows by `factor`."""
    return 1 + IMAGE_SHARE[variant] * (factor - 1)


def floor_label(floor):
    return ", 147‑bit" if floor == 147 else ""


# The user's handoff merge under the note's §5.8 deferral: its circuit derives the challenge
# from the mask's K commitment images and the mask's evaluations at the claims' points, checks
# the commitment identity on the K images, and folds the claims. The decomposition of the
# response and the range and norm proofs are the aggregator's first fold's, which the
# zero-knowledge-layer merge that the accumulation prover prices already carries. The circuit
# takes whole step circuits of the rank at the masked rank's commitment rate.
def handoff_merge_gates(variant, K, circuits, hp):
    if hp == "poseidon":
        hashing = HASH_GATES_PER_ATOM * (K * ATOMS_PER_COMMITMENT[variant] + circuits)
    else:
        hashing = ceil_div(K * 128 + circuits * CLAIM_BYTES[variant], BLAKE3_BLOCK) * BLAKE3_GATES
    return hashing + K * FOLD_GATES_PER_IMAGE + circuits * CLAIM_GATES


def handoff_merge_cost(variant, K, circuits, rank, hp, floor, log_n):
    steps = math.ceil(handoff_merge_gates(variant, K, circuits, hp) / gate_budget(rank))
    return steps * 2**rank * ajtai_per_coefficient(variant, True, floor, log_n=log_n)


# Akita: no cycle, so endoscalings and binders do not exist. The committed groups are the
# stages plus one batch of every step circuit's witness; the number of step circuits follows
# from the merge circuit's gate estimate and the rank's budget.
for variant, hp in itertools.product(
    ("fp128", "goldilocks", "pasta_q64", "pasta_sis", "pasta"), HASH_POLICIES
):
    K = STAGES + 1
    for floor in FLOORS:
        for zk in (False, True):
            for rank in RANKS:
                circuits = akita_circuits(variant, K, rank, zk, hp)
                if circuits is None:
                    continue  # the per-circuit claim's hashing exceeds this rank's budget
                gates = akita_merge_gates(variant, K, circuits, zk, hp)
                atoms = akita_atoms(variant, K, circuits, zk)
                log_len = rank + math.log2(
                    circuits
                )  # the decider's accumulator is at the ordinary length, masked or not
                rank_scale = RANK_SCALE[floor][variant]
                # The opening is the floor's own plan; the floor's rank growth over the
                # catalog's own matrices enters the verifier through the inner images' share.
                # The accumulation matrix is the floor's ℓ∞ table's, masked or not
                # (ajtai_per_coefficient); the terminal's images are under the terminal's own
                # matrix.
                opening = akita_bytes(variant, K - 1, log_len, floor)
                instance = K * 128 + 2 * K * 32 + 4 + circuits * CLAIM_BYTES[variant]
                accumulator = accumulator_coefficients(variant, rank, circuits)
                # The bounds' N is this row's accumulator in digits, and the mask's
                # coordinates are stored at their own width.
                log_n = math.log2(accumulator * DIGITS[variant])
                mask_bits = mask_coordinate_bits(log_n=log_n)
                mask_sumcheck_atoms(mask_length(log_n=log_n))
                per_coefficient = ajtai_per_coefficient(variant, zk, floor, log_n=log_n)
                # The 128-bit and Goldilocks variants are Akita's published parameter sets;
                # the Pasta variants need a modulus profile Akita lacks, and the 64-bit
                # commitment variant a decoupled commitment modulus.
                change = "none" if variant in ("fp128", "goldilocks") else "design"
                points.append(
                    dict(
                        family=variant,
                        pq=True,
                        rank=rank,
                        E=None,
                        binders=None,
                        floor=floor,
                        hashes=hp,
                        groups=K,
                        packing=None,
                        circuits=circuits,
                        change=change,
                        zk=zk,
                        bytes=round(opening + instance),
                        prover=round(circuits * 2**rank * per_coefficient),
                        accumulation_prover=round(
                            circuits * 2**rank * per_coefficient
                            + accumulation_sumchecks(variant, accumulator)
                        ),
                        memory=accumulator_bytes(variant, accumulator),
                        peak_memory=round(
                            peak_fuse_bytes(
                                accumulator_bytes(variant, accumulator),
                                accumulator * DIGITS[variant],
                                CLAIM_BYTES[variant],
                                zk,
                                mask_bits,
                            )
                        ),
                        step_prover=round(2**rank * per_coefficient),
                        fold=round(
                            mask_fold(variant, accumulator, floor)
                            + handoff_merge_cost(variant, K, circuits, rank, hp, floor, log_n)
                        )
                        if zk
                        else 0,
                        fold_leaf=round(
                            mask_fold(variant, 2**rank, floor)
                            + handoff_merge_cost(variant, K, circuits, rank, hp, floor, log_n)
                        )
                        if zk
                        else 0,
                        accumulation=atoms,
                        gates=gates,
                        verify=akita_verify(
                            variant, log_len, zk, rank_factor_share(variant, rank_scale)
                        ),
                        folded=K,
                        label=f"rank {rank}, {circuits} circuit{'s' if circuits != 1 else ''}, {K} groups"
                        + HASH_LABEL[hp]
                        + (", ZK" if zk else "")
                        + floor_label(floor),
                    )
                )

# WHIR (ePrint 2024/1586), hash-based, over a 255-bit field such as Pasta's, which is FFT
# friendly. Measured with the reference implementation (WizardOfMenlo/whir at afec1fa; the
# rows are in estimates/whir-sweep.tsv): 128-bit security in the proven Johnson regime;
# 20 bits of grinding; folding factor 4. Per rate: proof bytes at 2^17, the growth per
# doubling of the witness, the verifier's hashes at 2^17, and the queries over all rounds,
# which is also the growth in hashes per doubling, one more Merkle level per query.
# The measurements are in estimates/whir-sweep-grind.tsv (2026-10-21, the same binary, --reps
# 3): both fields, rates 1/2 to 1/64, and a maximum proof-of-work of 0, 16, 20 or 24 bits in
# the query phase, at 2^17 and 2^18. The rate-1/8, 20-bit rows reproduce the earlier sweep
# (122.7 and 128.0 KiB over the 256-bit field). Over Goldilocks the claims are in its cubic
# extension, which 128-bit security needs under the correlated-agreement bound, where the
# quadratic extension is left at about 87 bits. Under BEEP the quadratic one serves (the next
# table).
# On the regime: the conjectures up to capacity were refuted over large fields in late 2025
# (Crites and Stewart, ePrint 2025/2046; ePrint 2026/1367 §5.4). Between the Johnson bound and
# capacity the question is open: proximity gaps beyond Johnson have been proved for
# Reed-Solomon codes in large characteristic and for adequate parameters (Dao, Kominers and
# Thaler, ePrint 2026/2056), and refuted over binary fields (ePrint 2026/2424). Every
# row's query counts are for a proximity parameter within the Johnson bound, the rows derived
# from BEEP included: BEEP needs only list decodability, which every code has up to that bound.
RATES = ("1/2", "1/4", "1/8", "1/16", "1/32", "1/64")
GRIND_DEFAULT = 16  # the default of the functions below; the page picks per row
WHIR_MEAS = {}
# estimates/whir-sweep-beep.tsv is the same grid over Goldilocks's quadratic extension, by
# scripts/whir-sweep-beep.sh, under the diagnostic switch of scripts/patches/whir/, which takes
# the fold's error as BEEP's with affine folding challenges, 2/|F| (ePrint 2026/2930, Theorem
# 5.3). The reference implementation's own proximity-gap term is about 87 bits in that field,
# and it would grind for the rest. Its other terms stay and cost 7 to 21 bits of proof of
# work. The query counts are those of the cubic extension.
WHIR_FIELDS = {"Field256": "pasta", "Goldilocks3": "gold", "Goldilocks2": "gold2"}
for table in ("whir-sweep-grind.tsv", "whir-sweep-beep.tsv"):
    rows = (HERE / "estimates" / table).read_text().rstrip("\n").split("\n")
    header = rows[0].split("\t")
    for line in rows[1:]:
        row = dict(zip(header, line.split("\t")))
        key = (WHIR_FIELDS[row["field"]], int(row["pow_max"]), row["rate"])
        WHIR_MEAS.setdefault(key, {})[int(row["log2_size"])] = dict(
            bytes=float(row["proof_KiB"]) * 1024,
            hashes=float(row["verifier_khashes"]) * 1000,
            queries=int(row["queries"]),
            first=int(row["first_samples"]),
        )

# The grinding settings are the ones measured for both fields at 2^17 and 2^20.
GRINDS = tuple(
    sorted(
        {
            g
            for (s, g, r), m in WHIR_MEAS.items()
            if 17 in m and 20 in m
            if all(
                (s2, g, r2) in WHIR_MEAS and 20 in WHIR_MEAS[(s2, g, r2)]
                for s2 in ("pasta", "gold")
                for r2 in RATES
            )
        }
    )
)


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
BEEP_SAMPLES = 5  # DEEP samples a fold without an MCA bound (BEEP's Table 1: 4 to 5)
BEEP_FLOOR = 128  # the floor of the rows derived from BEEP
HASH_VARIANTS = {
    "whir": dict(
        sizes="pasta",
        gates=288,
        native=35000,
        leaf_perms=4,
        leaf_bytes=512,
        elems=1,
        mult=32,
        size_factor=1,
    ),
    "whir_gold": dict(
        sizes="gold",
        gates=480,
        native=7200,
        leaf_perms=2,
        leaf_bytes=128,
        elems=1,
        mult=1.5,
        size_factor=1,
    ),
    "whir_hybrid": dict(
        sizes="gold",
        gates=288,
        native=35000,
        leaf_perms=2,
        leaf_bytes=128,
        elems=4,
        mult=1.5,
        size_factor=1,
    ),
    "plonky3": dict(
        sizes="gold",
        gates=480,
        native=7200,
        leaf_perms=2,
        leaf_bytes=128,
        elems=1,
        mult=1.5,
        size_factor=1.95,
    ),
}


# The Goldilocks variants under BEEP: the same variants with the claims in the quadratic
# extension, which BEEP's folding error allows at the 128-bit floor, where the
# correlated-agreement bound needs the cubic one. They are rows of the same families, derived
# (no implementation of BEEP exists), at that floor alone, and ranked with the strongest
# assumption, as BitZ's are.
for name in ("whir_gold", "whir_hybrid", "plonky3"):
    HASH_VARIANTS[name + "_beep"] = dict(
        HASH_VARIANTS[name], sizes="gold2", family=name, profile="beep", floors=(BEEP_FLOOR,)
    )


def variant_family(variant):
    return HASH_VARIANTS[variant].get("family", variant)


def variant_floors(variant):
    return HASH_VARIANTS[variant].get("floors", FLOORS)


def variant_label(variant):
    beep = HASH_VARIANTS[variant].get("profile") == "beep"
    return ", quadratic extension, Johnson bound with BEEP (derived)" if beep else ""


def hv(variant, hp):
    """The variant's hash figures under the policy: its Poseidon (`gates` and `native` per
    permutation, `leaf_perms` permutations per first-round leaf), or BLAKE3 at one
    compression per node, with the leaf's bytes (16 elements of the witness's field: 32-byte
    Pasta elements, or 8-byte Goldilocks words or limbs) in 64-byte blocks."""
    v = HASH_VARIANTS[variant]
    if hp == "poseidon":
        return v
    return dict(
        v, gates=BLAKE3_GATES, native=BLAKE3_NATIVE, leaf_perms=v["leaf_bytes"] / BLAKE3_BLOCK
    )


def whir_bytes(variant, rate, log_elems, grind=GRIND_DEFAULT):
    """The stand-alone proof's bytes at 2^log_elems elements. Under BEEP each fold, one a
    variable, also sends the two halves' evaluations at BEEP_SAMPLES points."""
    v = HASH_VARIANTS[variant]
    b17, slope, _, _ = whir_meas(v["sizes"], grind, rate)
    deep = (
        log_elems * 2 * BEEP_SAMPLES * ELEM_BYTES[v["sizes"]] if v.get("profile") == "beep" else 0
    )
    return (b17 + slope * (log_elems - 17) + deep) * v["size_factor"]


# A hash commitment is not homomorphic, so Ragu's split accumulation does not apply. ARC
# (ePrint 2024/1731) accumulates Reed-Solomon proximity claims instead: its verifier checks
# t = 2 lambda / log2(1/rate) Merkle openings per input in the proven, Johnson-bound regime
# (the factor 2 is that bound's; see the note on the regime at WHIR's measurements), each a
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


def arc_openings(rate, floor=DEFAULT_FLOOR, grind=GRIND_DEFAULT):
    return math.ceil(2 * (floor - grind) / math.log2(int(rate.split("/")[1])))


def arc_merge_gates(variant, rate, log_len, floor=DEFAULT_FLOOR, grind=GRIND_DEFAULT, hp="blake3"):
    v = hv(variant, hp)
    inv = int(rate.split("/")[1])
    depth = (
        log_len + math.log2(v["elems"]) + math.log2(inv)
    )  # path nodes plus the leaf's permutations
    t = arc_openings(rate, floor, grind)
    hashes = 2 * t * depth + (2 if grind else 0)  # plus the grinding check per input
    return hashes * v["gates"] + 2 * t * 16 + 2000


def arc_circuits(variant, rate, rank, floor=DEFAULT_FLOOR, grind=GRIND_DEFAULT, hp="blake3"):
    circuits = 1
    for _ in range(30):
        new = math.ceil(
            arc_merge_gates(variant, rate, rank + math.log2(circuits), floor, grind, hp)
            / gate_budget(rank)
        )
        if new == circuits:
            return circuits
        circuits = new
    return circuits


def grind_prover(native, grind):
    """The grinding's word multiplications per merge: 2^g evaluations of the grinding hash."""
    return 2**grind * native if grind else 0


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


def arc_accumulator_bytes(variant, rate, log_len):
    """The accumulator's codeword, the witness over the rate in the field's elements, and its
    Merkle tree of 16-element leaves at 32 bytes a node."""
    v = HASH_VARIANTS[variant]
    inv = int(rate.split("/")[1])
    elements = 2**log_len * v["elems"] * inv
    return elements * ELEM_BYTES[v["sizes"]] + elements / 16 * 2 * 32


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
    return (
        (hashes + queries * (log_elems - 17))
        * WHIR_HASHES_SCALE[floor]
        * (2.07 if variant_family(variant) == "plonky3" else 1)
    )


ARC_DECIDER_TREES = (
    3  # the decider's first round opens the two child accumulators and the root's witness
)
WHIR_FOLD = 16  # the reference implementation's folding factor: elements per first-round leaf
ELEM_BYTES = {
    "pasta": 32,
    "gold": 24,
    "gold2": 16,
}  # a committed element: the 255-bit field; Goldilocks's cubic extension; its quadratic one


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
    return (
        extra
        * (m["first"] * WHIR_FOLD * ELEM_BYTES[v["sizes"]] + path_hashes * 32)
        * v["size_factor"],
        extra * (path_hashes + m["first"] * v["leaf_perms"]),
    )


for variant, hp in itertools.product(HASH_VARIANTS, HASH_POLICIES):
    for grind in GRINDS:
        for floor in variant_floors(variant):
            for zk in (False, True):
                for rate in RATES:
                    for rank in HASH_RANKS:
                        circuits = arc_circuits(variant, rate, rank, floor, grind, hp)
                        log_len = rank + math.log2(circuits)
                        log_elems = log_len + math.log2(HASH_VARIANTS[variant]["elems"])
                        native = hv(variant, hp)["native"]
                        extra_bytes, extra_hashes = whir_extra_trees(
                            variant, rate, log_elems, grind, hp
                        )
                        points.append(
                            dict(
                                family=variant_family(variant),
                                profile=HASH_VARIANTS[variant].get("profile"),
                                pq=True,
                                rank=rank,
                                E=None,
                                binders=None,
                                floor=floor,
                                grind=grind,
                                hashes=hp,
                                groups=2,
                                packing=None,
                                circuits=circuits,
                                change="design",
                                zk=zk,
                                rate=rate,
                                # Zero knowledge is paid once per transaction, at the handoff to the public
                                # aggregator: the masks sit in the decider's proof and verification, and the
                                # masked prover's extra work goes to the fold, not to every merge.
                                bytes=round(
                                    (whir_bytes(variant, rate, log_elems, grind) + extra_bytes)
                                    * WHIR_SCALE[floor]
                                    + zk_bytes(floor, zk)
                                    + 2 * 32
                                    + 10 * 32
                                    + 4
                                ),
                                memory=round(arc_accumulator_bytes(variant, rate, log_len)),
                                prover=round(
                                    2**log_len * arc_per_coefficient(variant, rate, log_len, hp)
                                    + grind_prover(native, grind)
                                ),
                                step_prover=round(
                                    2**rank * arc_per_coefficient(variant, rate, log_len, hp)
                                ),
                                fold=round(
                                    (zk_prover(log_elems, zk) - 1)
                                    * 2**log_len
                                    * arc_per_coefficient(variant, rate, log_len, hp)
                                ),
                                accumulation=ARC_ATOMS,
                                gates=round(
                                    arc_merge_gates(variant, rate, log_len, floor, grind, hp)
                                ),
                                verify=round(
                                    (
                                        whir_verify_hashes(variant, rate, log_elems, floor, grind)
                                        + extra_hashes
                                        + zk_hashes(floor, zk)
                                    )
                                    * native
                                    + 1e6
                                ),
                                folded=2,
                                label=f"rank {rank}, rate {rate}, {arc_openings(rate, floor, grind)} openings/input, {circuits} circuits"
                                + variant_label(variant)
                                + HASH_LABEL[hp]
                                + (", ZK" if zk else "")
                                + floor_label(floor),
                            )
                        )

# Binary-field systems: Flock (arXiv 2607.27491) and Binius64 on the FRI-Binius and Ligerito
# commitments, Boolean R1CS over 𝔽₂ with claims in 𝔽₂^128 and a bit-oriented hash. They have
# no Pasta circuits, so the merge is priced in its own terms: ARC's openings as for the other
# hash-based variants, each path node a BLAKE3 compression in a block of 2^13 committed bits,
# Flock's layout for a batch, so the merge is a Boolean witness of that many bits, and there
# is no rank. Proof bytes come from
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
# design changes that the paper does not write down. Under the correlated-agreement bound a
# 128-bit field cannot reach 128 bits at these sizes; under BEEP it can, which is the fourth
# design (F2_DESIGNS). The first-round oracle has the same bytes under any packing,
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
    # FRI-Binius under BEEP with affine folding challenges (frib_optimizer's `beep_samples`):
    # the folding error is 2/|F| at any list size, so the paper's own 128-bit field serves at
    # the 128-bit floor, 127 bits, and the list can sit near the Johnson bound. No
    # implementation exists, so the rows are derived, at that floor alone, and ranked with the
    # strongest assumption, as BitZ's are. The list's batching error L/|F| is left to
    # F2_BEEP_LIST_BITS bits of grinding. The samples' evaluations, a multiplication an
    # element a sample, are under a percent of the prover and are not added.
    128: dict(
        pack=128,
        twiddle=2,
        label="128-bit field, Johnson bound with BEEP (derived)",
        beep=5,
        floors=(128,),
    ),
}
F2_BEEP_LIST_BITS = 8
F2_FIRST_BYTES = 32  # opened bytes per 256 witness bits in the first round, under any packing
CLMULS = {
    64: 1,
    128: 4,
    191: 7,
    192: 8,
    256: 11,
}  # 64-bit carry-less multiplications per field multiplication: Karatsuba over the limbs, plus the reductions
# Measured on 2026-11-21 on one core of an M4 Max on mains (scripts/clmul-bench.c): a GF(2^128)
# multiplication by six PMULL instructions, Karatsuba and a three-step reduction, takes
# GF128_MEASURED_NS with sixteen independent chains in flight, 2.8 word multiplications at the
# page's 3e9 a second, against the table's four carry-less multiplications taken as one word
# multiplication each. The factor scales every width's count to that measurement, so a
# carry-less multiplication costs 0.7 word multiplications wherever the table prices work.
GF128_MEASURED_NS = 0.94
CLMUL_WORD_MULTS = GF128_MEASURED_NS * WORD_MULTS_PER_MS / 1e6 / CLMULS[128]


def elem_bytes(bits):
    return (bits + 7) // 8


def limbs(bits):
    return (bits + 63) // 64


XOR_WEIGHT = (
    1 / 8
)  # a 64-bit word XOR against a word multiplication: the vector units do several per cycle
NTT_STAGES_SAVED = 4  # butterfly stages that the paper's interleaving saves in the commitment (§5)
FLOCK_PIOP_SHARE = (
    0.05,
    0.464,
)  # of Flock's prover: witness generation; zero-check and lincheck (Table 5, BLAKE3)
FRIB_MEASURED_MS = (
    144,
    160,
)  # FRI-Binius Table 2: single-threaded commit and open at 2^28 bits, rate 1/2, 𝔽₂^128
BLAKE3_PER_SECOND = 82100
WORD_MULTS_PER_SECOND = 3e9
ZK_LABEL = {None: "", "mask": ", ZK, batched mask", "zook": ", ZK, Zook-style, derived"}
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
    groups = [(r["ell"], ZOOK_MASK_COEFFS) for r in rounds] + [
        (1, pack)
    ]  # (masks per leaf, message length)
    bytes_, hashes, ops = terminal * elem, 0, 0
    for masks, length in groups:
        positions = (length + tzk) << ZOOK_MASK_RATE_BITS
        height = math.ceil(math.log2(positions))
        paths = frib.expected_multiproof_hashes(height, tzk)
        bytes_ += tzk * masks * elem + paths * 32 + masks * elem
        hashes += paths + tzk
        ops += (
            masks * positions * height / 2 * limbs(chal)
            + positions * masks * elem / 64 * BLAKE3_NATIVE
        )
    return bytes_, hashes, ops


def f2_ops(bits, rate_bits, chal, pack, rounds, twiddle):
    """Operation counts of the FRI-Binius prover on `bits` witness bits, in word
    multiplications: the additive NTT of the first oracle, at `twiddle` carry-less
    multiplications per butterfly; its tree; the ring switching (two passes of a
    challenge-field element by each bit, the tensor expansion and its sum-check over the
    packed coefficients); and the folds (the first step of the first round over the packing
    field), the folded trees, and the BaseFold sum-check."""
    first_bytes = bits * 2**rate_bits / 8
    n = first_bytes * 8 / pack
    ntt = n * (math.log2(n) - NTT_STAGES_SAVED) / 2 * twiddle
    tree = (first_bytes / 64 + first_bytes / (F2_FIRST_BYTES << rounds[0]["ell"])) * BLAKE3_NATIVE
    packed = bits / pack
    switch = 2 * bits * limbs(chal) * XOR_WEIGHT + 4 * packed * CLMULS[chal] * CLMUL_WORD_MULTS
    fold = 3 * packed * CLMULS[chal] * CLMUL_WORD_MULTS
    for i, r in enumerate(rounds):
        units = 2 ** (r["height"] + r["ell"])  # the round's oracle, in 256-bit units
        if i == 0:
            symbols = units * 256 / pack
            fold += symbols / 2 * (clmuls(pack, chal) + CLMULS[chal]) * CLMUL_WORD_MULTS
        else:
            fold += (
                units * CLMULS[chal] * CLMUL_WORD_MULTS
                + (units * elem_bytes(chal) / 64 + units / 2 ** r["ell"]) * BLAKE3_NATIVE
            )
    return dict(ntt=ntt, tree=tree, switch=switch, fold=fold)


FRIB_CALIB_ROUNDS = [
    dict(ell=2, height=m - 2 + 1) for m in range(20, 0, -2)
]  # the paper's folding factor 4
_calib = f2_ops(2**28, 1, 128, 128, FRIB_CALIB_ROUNDS, twiddle=2)
F2_SCALE = (
    FRIB_MEASURED_MS[0] * WORD_MULTS_PER_MS / (_calib["ntt"] + _calib["tree"]),
    FRIB_MEASURED_MS[1] * WORD_MULTS_PER_MS / (_calib["switch"] + _calib["fold"]),
)


def f2_piop(bits, chal):
    """Flock's measured prover less its commitment, per witness bit (one per AND gate), with
    the zero-check and lincheck scaled by half the challenge field's multiplication cost over
    𝔽₂^128's."""
    per_gate = WORD_MULTS_PER_SECOND / BLAKE3_PER_SECOND / BLAKE3_ANDS_PADDED
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
    # The list is the optimizer's own: the largest that the agreement bound admits, with the
    # codeword's length counted in field elements, as the original now does.
    out = frib.optimize(
        w,
        rate_bits,
        floor,
        grind,
        zk="true" if zk else "false",
        field_bits=chal,
        first_bytes=F2_FIRST_BYTES,
        first_trees=trees,
        beep_samples=F2_DESIGNS[chal].get("beep"),
        list_bits=F2_BEEP_LIST_BITS if F2_DESIGNS[chal].get("beep") else None,
    )
    rounds = out["rounds"]
    folds = [
        r for r in rounds if r["ell"] > 0
    ]  # a zk schedule with no reduction opens the mask and folds nothing
    packed_log = w - math.log2(pack)
    return dict(
        bytes=out["compressed"],
        queries=out["queries"],
        lb=out["list_bits"],
        # the verifier hashes the pruned paths, as the original now counts them
        auth=sum(r["compressed_auth_bytes"] for r in rounds) / frib.HASH_BYTES,
        opened=sum(r["opened_bytes"] for r in rounds),
        field_mults=2 * packed_log * pack
        + out["queries"] * (sum(2 ** r["ell"] for r in folds) + (1 if zk else 0))
        + 6 * packed_log,
        ops=f2_ops(2**w, rate_bits, chal, pack, folds, twiddle),
        # the mask is a polynomial of the witness's size, committed beside it in the
        # first round (Ulrich Haböck's correction of 2026-11-12)
        mask_share=1 if zk else 0,
        zook=zook_masks(folds, out["terminal_elements"], floor, chal, pack),
    )


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
    return dict(
        bytes=lin("bytes"),
        auth=lin("auth"),
        opened=lin("opened"),
        field_mults=lin("field_mults"),
        queries=b["queries"],
        lb=b["lb"],
        mask_share=a["mask_share"],
        ops={k: a["ops"][k] * (b["ops"][k] / a["ops"][k]) ** f for k in a["ops"]},
        zook=tuple(x + (y - x) * f for x, y in zip(a["zook"], b["zook"])),
    )


def f2_bytes(p, zk):
    """The proof's bytes, with the Zook-style masks when that variant is chosen."""
    return p["bytes"] + (p["zook"][0] if zk == "zook" else 0)


def f2_prover(bits, rate, floor, grind, chal, recursive, zk=None):
    """Word multiplications of the 𝔽₂ prover: Flock's PIOP, the scaled commitment (the NTT
    and two trees with the ring switching for an ARC step; a full proof for a recursive
    step), under zero knowledge the witness-size mask's commitment or the Zook-style masks'
    encoding, and the grinding."""
    p = frib_proof(
        bits, rate, floor, grind, chal, 1 if recursive else ARC_DECIDER_TREES, zk == "mask"
    )
    ops = p["ops"]
    mask = 1 + p["mask_share"] if zk == "mask" else 1
    if recursive:
        pcs = F2_SCALE[0] * mask * (ops["ntt"] + ops["tree"]) + F2_SCALE[1] * (
            ops["switch"] + ops["fold"]
        )
    else:
        pcs = (
            F2_SCALE[0] * (mask * (ops["ntt"] + ops["tree"]) + ops["tree"])
            + F2_SCALE[1] * ops["switch"]
        )
    if zk == "zook":
        pcs += F2_SCALE[0] * p["zook"][2]
    return f2_piop(bits, chal) + pcs + grind_prover(BLAKE3_NATIVE, grind)


def f2_verify(p, grind, chal, zk=None):
    """The decider's word multiplications: the proof's bytes absorbed into the transcript,
    its authentication and leaf hashes, the grinding check, the Zook-style masks' spot
    checks, and its field multiplications."""
    return (
        ceil_div(f2_bytes(p, zk), 64)
        + p["auth"]
        + p["opened"] / 64
        + (2 if grind else 0)
        + (p["zook"][1] if zk == "zook" else 0)
    ) * BLAKE3_NATIVE + p["field_mults"] * CLMULS[chal] * CLMUL_WORD_MULTS


# A hash-based family's merge also verifies its two inputs' PIOPs. Ragu's PIOP is evaluation
# based and its claims are in the merge already; Flock's and Zinc+'s are sum-checks, whose
# verifiers the merge runs. For Flock that is the zerocheck and the lincheck over the witness's
# variables, and a sum-check per base matrix (one BLAKE3 compression's R1CS, a nonzero a wire)
# that reduces the matrix's evaluation to a committed one for the accumulation to take, in
# place of the native verifier's own evaluation of the small matrices, which a circuit should
# not do. For BitZ it is Zinc+'s PIOP, the same shape, and the grand-product GKR, a layer per
# variable. A round costs four multiplications in the challenge field: a degree-three
# univariate at the challenge and the running eq factor. The Boolean merge multiplies by
# Karatsuba or Toom-3 (CLMUL_ANDS); BitZ's hybrid merge commits each product as a 128-bit element.
PIOP_ROUND_MULTS = 4
BITZ_FIELD_BITS = 128


def f2_piop_verifier_mults(log_bits):
    """Field multiplications of one input's Flock PIOP verifier at a witness of 2^log_bits."""
    matrix_rounds = math.log2(BLAKE3_ANDS_PADDED)
    return PIOP_ROUND_MULTS * (2 * log_bits + 3 * matrix_rounds)


def bitz_piop_verifier_mults(log_bits):
    """Field multiplications of one input's Zinc+ PIOP and GKR verifiers at 2^log_bits bits."""
    n = math.ceil(log_bits)
    return f2_piop_verifier_mults(log_bits) + PIOP_ROUND_MULTS * n * (n + 1) / 2


def f2_merge(rate, floor, grind=GRIND_DEFAULT, chal=128):
    """(hashes, AND gates) of a merge: two inputs, ARC's openings, paths through the tree of
    the 𝔽₂^128-packed witness divided by the rate, at its fixed point, plus the grinding
    check per input and the inputs' PIOP verifiers in the challenge field `chal`."""
    inv = int(rate.split("/")[1])
    t = arc_openings(rate, floor, grind)
    hashes = 2 * t * 30
    ands = hashes * BLAKE3_ANDS_PADDED
    for _ in range(40):
        verifier = 2 * f2_piop_verifier_mults(math.log2(ands)) * CLMUL_ANDS[chal]
        ands = hashes * BLAKE3_ANDS_PADDED + verifier
        depth = (
            math.log2(ands / 128 * inv / 16) + 4
        )  # path nodes, plus four compressions for a 256-byte leaf
        new = 2 * t * depth + (2 if grind else 0)
        if abs(new - hashes) < 1:
            break
        hashes = new
    return round(hashes), round(hashes * BLAKE3_ANDS_PADDED + verifier)


for grind in GRINDS:
    for floor in FLOORS:
        for rate in RATES:
            for chal, design in F2_DESIGNS.items():
                if floor not in design.get("floors", FLOORS):
                    continue
                hashes, ands = f2_merge(rate, floor, grind, chal)
                for zk in ZK_LABEL:
                    p = frib_proof(ands, rate, floor, grind, chal, ARC_DECIDER_TREES, zk == "mask")
                    points.append(
                        dict(
                            family="flock",
                            profile="beep" if design.get("beep") else None,
                            pq=True,
                            rank=None,
                            E=None,
                            binders=None,
                            floor=floor,
                            grind=grind,
                            groups=2,
                            packing=None,
                            circuits=None,
                            change="design",
                            zk=zk is not None,
                            zkv=zk,
                            rate=rate,
                            field=chal,
                            # The masks sit in the decider's proof and verification; the mask's prover work
                            # is paid once per transaction, at the handoff to the public aggregator, in the fold.
                            bytes=round(f2_bytes(p, zk) + 2 * 32 + 10 * 16 + 4),
                            memory=round(
                                ands * int(rate.split("/")[1]) * 5 / 32
                            ),  # the packed codeword and its tree of 256-byte leaves
                            prover=round(f2_prover(ands, rate, floor, grind, chal, False, None)),
                            # The family has no rank: its step is a Boolean circuit of BOOL_STEP_BITS AND gates
                            # at the merge's per-bit cost, which is its capacity for the transaction measure.
                            step_prover=round(
                                BOOL_STEP_BITS
                                * f2_prover(ands, rate, floor, grind, chal, False, None)
                                / ands
                            ),
                            fold=round(
                                f2_prover(ands, rate, floor, grind, chal, False, zk)
                                - f2_prover(ands, rate, floor, grind, chal, False, None)
                            ),
                            accumulation=ARC_ATOMS,
                            gates=ands,
                            verify=round(f2_verify(p, grind, chal, zk)),
                            folded=2,
                            label=f"rate {rate}, {design['label']}, list 2^{p['lb']}, {p['queries']} queries, {arc_openings(rate, floor, grind)} openings/input, {hashes:,} BLAKE3, {ands / 1e6:.1f}M AND gates"
                            + ZK_LABEL[zk]
                            + floor_label(floor),
                        )
                    )

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
    return (
        2 * rec_hashes(variant, rate, log_elems, floor, zk, grind) * v["gates"]
        + 2 * REC_ARITH_GATES
    )


def rec_circuits(variant, rate, rank, floor, zk=False, grind=GRIND_DEFAULT, hp="blake3"):
    circuits = 1
    for _ in range(30):
        new = math.ceil(
            rec_merge_gates(variant, rate, rank + math.log2(circuits), floor, zk, grind, hp)
            / gate_budget(rank)
        )
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
        for floor in variant_floors(variant):
            for zk in (False, True):
                for rate in RATES:
                    for rank in HASH_RANKS:
                        # Under recursion only the user's last proof, handed to the public aggregator,
                        # is masked; the public merges and the decider's proof are of public data, so
                        # the zero-knowledge rows equal the plain rows but for the fold, which carries
                        # the one masked proof's extra prover work.
                        circuits = rec_circuits(variant, rate, rank, floor, False, grind, hp)
                        log_len = rank + math.log2(circuits)
                        log_elems = log_len + math.log2(HASH_VARIANTS[variant]["elems"])
                        native = hv(variant, hp)["native"]
                        points.append(
                            dict(
                                family=variant_family(variant) + "_rec",
                                profile=HASH_VARIANTS[variant].get("profile"),
                                pq=True,
                                rank=rank,
                                E=None,
                                binders=None,
                                floor=floor,
                                grind=grind,
                                hashes=hp,
                                groups=2,
                                packing=None,
                                circuits=circuits,
                                change="design",
                                zk=zk,
                                rate=rate,
                                bytes=round(
                                    whir_bytes(variant, rate, log_elems, grind) * WHIR_SCALE[floor]
                                    + 2 * 32
                                    + 4
                                ),
                                prover=round(
                                    2**log_len * rec_per_coefficient(variant, rate, log_len, hp)
                                    + grind_prover(native, grind)
                                ),
                                step_prover=round(
                                    2**rank * rec_per_coefficient(variant, rate, log_len, hp)
                                ),
                                fold=round(
                                    (zk_prover(log_elems, zk) - 1)
                                    * 2**log_len
                                    * rec_per_coefficient(variant, rate, log_len, hp)
                                ),
                                accumulation=ARC_ATOMS,
                                gates=round(
                                    rec_merge_gates(variant, rate, log_len, floor, False, grind, hp)
                                ),
                                verify=round(
                                    rec_hashes(variant, rate, log_elems, floor, False, grind)
                                    * native
                                    + 1e6
                                ),
                                folded=2,
                                label=f"rank {rank}, rate {rate}, {round(rec_hashes(variant, rate, log_elems, floor, False, grind)):,} hashes/input, {circuits} circuits"
                                + variant_label(variant)
                                + HASH_LABEL[hp]
                                + (", ZK" if zk else "")
                                + floor_label(floor),
                            )
                        )


# Ligerito's verifier, for the recursion of BitZ: its levels, their rates and their query counts
# are the proof of concept's resolved configurations (bitz_levels, BITZ_QUERIES), by profile. A
# query opens a column of the level's interleaved elements through a path of the level's depth.
# The nodes are priced as BLAKE3 compressions in blocks of 2^13 committed bits, as the 𝔽₂ family's
# rows price them.
# Flock's implementation hashes with SHA-256 (§2), 31,400 witness bits per compression in its
# arithmetization (BitZ, Table 2) at 42,100 per second: 3.8 times the merge bits and half
# the throughput, for every row of these families alike. BitZ reports that proving many
# hashes with a binary-field SNARK beats its 7,144-bit CM arithmetization, so the hybrid
# merge takes the former. Ligerito's levels have their own rates, so a row's rate applies to
# its proof bytes and, in the ARC rows, to the accumulator's openings, not to the verifier.
# The 𝔽₂ family's recursive merge verifies the step's own FRI-Binius proof twice: its hashes
# as BLAKE3 compressions and its field multiplications by Karatsuba or Toom-3, at the fixed point.
def f2_rec_merge(rate, floor, grind, chal, zk=None):
    """(hashes, witness bits) of the recursive merge, plus the grinding check per input."""
    bits = 2**25
    hashes = 0
    for _ in range(40):
        p = frib_proof(bits, rate, floor, grind, chal, 1, zk == "mask")
        hashes = 2 * (p["auth"] + p["opened"] / 64 + (p["zook"][1] if zk == "zook" else 0)) + (
            2 if grind else 0
        )
        new = (
            hashes * BLAKE3_ANDS_PADDED
            + 2 * (p["field_mults"] + f2_piop_verifier_mults(math.log2(bits))) * CLMUL_ANDS[chal]
        )
        if abs(new - bits) < 1:
            break
        bits = new
    return round(hashes), round(bits)


for grind in GRINDS:
    for floor in FLOORS:
        for rate in RATES:
            for chal, design in F2_DESIGNS.items():
                if floor not in design.get("floors", FLOORS):
                    continue
                for zk in ZK_LABEL:
                    # Under recursion only the user's last proof is masked (see the WHIR recursion
                    # rows): the rows equal the plain rows but for the fold.
                    hashes, bits = f2_rec_merge(rate, floor, grind, chal, None)
                    p = frib_proof(bits, rate, floor, grind, chal, 1, False)
                    points.append(
                        dict(
                            family="flock_rec",
                            profile="beep" if design.get("beep") else None,
                            pq=True,
                            rank=None,
                            E=None,
                            binders=None,
                            floor=floor,
                            grind=grind,
                            groups=2,
                            packing=None,
                            circuits=None,
                            change="design",
                            zk=zk is not None,
                            zkv=zk,
                            rate=rate,
                            field=chal,
                            bytes=round(f2_bytes(p, None) + 2 * 32 + 4),
                            prover=round(f2_prover(bits, rate, floor, grind, chal, True, None)),
                            step_prover=round(
                                BOOL_STEP_BITS
                                * f2_prover(bits, rate, floor, grind, chal, True, None)
                                / bits
                            ),
                            fold=round(
                                f2_prover(bits, rate, floor, grind, chal, True, zk)
                                - f2_prover(bits, rate, floor, grind, chal, True, None)
                            ),
                            accumulation=ARC_ATOMS,
                            gates=bits,
                            verify=round(f2_verify(p, grind, chal, None)),
                            folded=2,
                            label=f"rate {rate}, {design['label']}, list 2^{p['lb']}, {p['queries']} queries, {hashes:,} hashes/merge, {bits / 1e6:.0f}M witness bits"
                            + ZK_LABEL[zk]
                            + floor_label(floor),
                        )
                    )

# BitZ (ePrint 2026/2141): a hash-based PCS over any finitely generated ring through binary
# fields. The witness is bit-decomposed and committed packed over 𝔽₂^128 with Flock's
# Ligerito; a claim over a ring R is lifted to the integers (a random prime where R is
# large) and proved in the exponent of 𝔽₂^128 by GKR grand products, so the cost is per bit
# and independent of R. With the Universal Constraint Systems of Zinc+ (ePrint 2026/855) the
# application is native over Pasta's field: integer witnesses with ideal membership modulo
# p, projected to a random prime field for the PIOP, so a Pasta gate is a 255-bit value and a
# 255-bit quotient, 510 committed bits. The merge is a hybrid circuit: the two Ligerito
# verifications as SHA-256 over 𝔽₂, and the GKR and PIOP verifiers native over 𝔽₂^128 and the
# projection field, their products committed as 128-bit elements (bitz_piop_verifier_mults in
# bitz_point). The PCS's sizes and times are measured (BITZ_MEASURED below). The prover is the
# commitment and the opening. The opening's grand-product GKR, which lifts the integer claims
# into the exponent of a generator of F_2^128, does not depend on the rate (Quang Dao: the
# prover with grand-product GKR is just really expensive). The commitment doubles with each
# halving of the rate. Beyond the measured floor the Ligerito bytes and the verifier scale
# with the floor, as queries do. The PIOP of Zinc+ adds, per its Table 4, 1.6 times the PCS
# prover's time on the application's share, 2 ms of verifier, and 36 kbytes of proof.
BITZ_PIOP = dict(prover=1.6, verify_ms=2.0, bytes=36000)
# The measurements behind BitZ's rows, by profile, rate exponent, and the logarithm of the
# committed bits. Each entry is (commit ms, prove ms, the grand-product GKR's part of the prove
# ms, verify ms, non-Ligerito bytes, Ligerito bytes). They are the proof of concept's
# (albert-garreta/BitZ-PoC at 8ced3b98) on one thread of this machine, by
# scripts/bitz-st-sweep.sh.
#
# One thread means RAYON_NUM_THREADS=1. The benchmark's own --threads 1 sizes only its main
# pool, and the library keeps a second pool of every core. Four phases hop onto that pool:
# the Merkle trees, from 8 Mbytes of data; the encoder's deep pass, from 64 Mbytes; the
# opening's combine step; and the lincheck's fold. A commit measured without the variable is
# about 1.6 times too fast at the sizes here, and more at the lower rates.
#
# "udr" is the unique-decoding regime with fold grinding at 128 bits, the proof of concept's
# profile udrg:<r>:4:128. It is what the proof of concept certifies at that level.
#
# "beep" is its Johnson profile at a 128-bit target (custom:<r>:4:128), under the diagnostic
# switch of scripts/patches/bitz/. The switch drops three checks that the profile cannot meet
# in a 128-bit field:
#   - the folding-phase target, a proximity-gap term of 86 to 97 bits here, which the code
#     otherwise makes up by grinding the fold challenges;
#   - the level-0 binding target, 118.7 bits at rate 1/2; and
#   - the outer round's grinding against an out-of-domain collision bound of 95 to 100 bits.
# BEEP (ePrint 2026/2930) is what would meet them. It takes several DEEP samples before each
# fold, in place of mutual correlated agreement. With affine folding challenges its folding
# error is 2/|F| (its Theorem 5.3), which is 127 bits. Its batching error is L/|F|, about 120
# bits, which a few bits of grinding cover. No implementation of BEEP exists. So these rows
# are the profile's measured sizes and times plus BEEP's samples (bitz_beep_overhead). They
# are at the 128-bit floor alone, since the 147-bit floor would require excessive grinding,
# and is mainly a hedge against attacks on lattices.
#
# A row whose committed bits fall outside the measured sizes is not priced.
BITZ_MEASURED = {
    "udr": {
        1: {
            22: (0.9, 37.3, 31.5, 2.94, 20981, 174292),
            23: (1.9, 50.8, 42.7, 2.92, 29865, 204068),
            24: (3.8, 74.9, 62.7, 3.25, 30921, 226796),
            25: (8.1, 113.8, 97.4, 3.16, 47961, 255860),
            26: (16.3, 188.0, 159.4, 4.49, 49173, 295228),
            27: (32.9, 355.4, 296.5, 6.77, 50349, 324956),
            28: (67.1, 647.6, 531.7, 7.11, 83853, 358436),
            29: (137.2, 1226.1, 1041.6, 12.28, 85185, 406716),
        },
        3: {
            22: (3.5, 48.4, 35.5, 2.37, 20981, 138516),
            23: (7.4, 69.1, 41.1, 2.42, 29865, 169100),
            24: (15.2, 89.9, 64.2, 2.98, 30921, 184596),
            25: (31.7, 123.8, 96.2, 2.96, 47961, 208700),
            26: (63.2, 215.5, 164.8, 4.25, 49173, 248460),
            27: (129.5, 454.7, 299.4, 6.58, 50349, 270764),
            28: (268.3, 772.1, 531.4, 6.96, 83853, 297100),
            29: (560.1, 1672.1, 1054.1, 11.97, 85185, 344116),
        },
    },
    "beep": {
        1: {
            22: (1.1, 42.8, 35.0, 2.51, 21118, 130708),
            23: (2.0, 52.8, 41.5, 2.28, 29770, 153356),
            24: (3.9, 84.3, 67.3, 2.60, 30914, 169260),
            25: (8.2, 115.1, 95.5, 2.81, 48170, 185420),
            26: (16.5, 195.2, 163.7, 3.77, 49150, 209092),
            27: (32.9, 349.3, 294.5, 6.17, 50414, 226308),
            28: (67.8, 621.1, 527.4, 6.71, 84134, 243300),
        },
        2: {
            22: (1.8, 41.3, 33.0, 2.21, 21118, 85844),
            23: (3.8, 48.0, 40.3, 2.08, 29770, 102444),
            24: (7.6, 86.0, 69.1, 2.45, 30914, 113836),
            25: (15.8, 121.8, 97.4, 2.56, 48170, 123276),
            26: (32.3, 194.0, 160.2, 3.58, 49150, 141388),
            27: (64.4, 358.5, 295.0, 5.83, 50414, 152876),
            28: (135.0, 654.8, 532.1, 6.49, 84134, 164620),
        },
        3: {
            22: (3.6, 46.2, 33.9, 2.15, 21118, 69788),
            23: (7.5, 53.6, 41.3, 1.99, 29770, 85244),
            24: (15.1, 87.2, 67.8, 2.47, 30914, 91740),
            25: (31.3, 116.1, 92.7, 2.47, 48170, 99516),
            26: (63.3, 202.7, 161.9, 3.64, 49150, 116524),
            27: (129.3, 371.8, 295.5, 5.77, 50414, 124908),
            28: (267.6, 668.4, 530.0, 6.53, 84134, 133356),
        },
        4: {
            22: (7.2, 38.3, 30.9, 2.18, 21118, 61676),
            23: (14.9, 54.3, 39.9, 1.93, 29770, 74844),
            24: (30.1, 78.7, 62.5, 2.54, 30914, 81308),
            25: (61.7, 130.0, 99.4, 2.51, 48170, 87164),
            26: (126.3, 213.5, 162.5, 3.44, 49150, 102324),
            27: (259.8, 395.2, 297.6, 5.78, 50414, 108340),
            28: (542.5, 716.3, 528.8, 6.38, 84134, 116596),
        },
        5: {
            22: (14.1, 48.6, 34.1, 2.15, 21118, 56260),
            23: (29.4, 58.0, 41.9, 2.02, 29770, 69724),
            24: (59.7, 90.5, 63.6, 2.24, 30914, 74556),
            25: (123.4, 145.4, 100.9, 2.41, 48170, 80316),
            26: (253.3, 233.9, 160.2, 3.47, 49150, 94684),
            27: (529.3, 447.1, 298.2, 5.74, 50414, 100316),
            28: (1095.7, 815.9, 533.9, 6.20, 84134, 107292),
        },
        6: {
            22: (28.5, 52.2, 35.8, 1.98, 21118, 53220),
            23: (58.2, 61.6, 39.4, 1.82, 29770, 65252),
            24: (120.7, 103.8, 65.2, 2.19, 30914, 69412),
            25: (247.5, 166.4, 100.4, 2.34, 48170, 75524),
            26: (510.2, 294.0, 167.7, 3.44, 49150, 89684),
            27: (1075.1, 540.7, 298.4, 5.65, 50414, 94708),
            28: (2217.2, 1019.3, 541.3, 6.22, 84134, 100180),
        },
    },
}
BITZ_MEASURED_FLOOR = 128
HASH_BITS = BLAKE3_ANDS_PADDED  # a hash in the merge's Boolean witness
# Queries a level by its rate exponent, from the profiles' resolved configurations at 128
# bits. Under unique decoding a query is worth under one bit. Under the Johnson bound it is
# worth half of log2(1/rate) bits, and each level also grinds 16 bits on its queries.
BITZ_QUERIES = {
    "udr": {1: 309, 2: 190, 3: 156, 4: 143, 5: 136, 6: 132, 7: 130, 8: 129},
    "beep": {1: 244, 2: 119, 3: 79, 4: 60, 5: 48, 6: 41, 7: 35, 8: 32, 9: 29, 10: 27},
}
BITZ_INITIAL_K = 4  # the first level folds 2^4 interleaved rows
BITZ_RECURSIVE_K = 3  # each later level 2^3
BITZ_FINAL_LOG = 5  # the final block's variables, at most
BITZ_ELEMENT_BYTES = BITZ_FIELD_BITS // 8
BITZ_PROFILE_LABEL = {"udr": "unique decoding", "beep": "Johnson bound with BEEP (derived)"}


def bitz_levels(profile, log_bits, r):
    """Ligerito's levels for a witness of 2^log_bits bits packed in 128-bit elements, from a
    first level at rate 2^-r: (log2 message columns, log2 interleaved rows, rate exponent), by
    the proof of concept's two ladders. The unique-decoding one stops at a final block of
    exactly BITZ_FINAL_LOG variables; the Johnson one folds BITZ_RECURSIVE_K at every level."""
    run = math.ceil(log_bits) - 7 - BITZ_INITIAL_K
    levels = [(run, BITZ_INITIAL_K, r)]
    while run > BITZ_FINAL_LOG:
        k = min(BITZ_RECURSIVE_K, run - BITZ_FINAL_LOG) if profile == "udr" else BITZ_RECURSIVE_K
        r += 1
        run -= k
        levels.append((run, k, r))
    return levels


def bitz_level_hashes(profile, log_bits, r, floor):
    """The verifier's hashes at each level: for each query, the opened column's elements at
    BLAKE3's block and its path, unpruned; the queries scale with the floor."""
    return [
        ceil_div(BITZ_QUERIES[profile][e] * floor, BITZ_MEASURED_FLOOR)
        * (2**k * BITZ_ELEMENT_BYTES / BLAKE3_BLOCK + cols + e)
        for cols, k, e in bitz_levels(profile, log_bits, r)
    ]


def bitz_queries(profile, log_bits, r, floor):
    return sum(
        ceil_div(BITZ_QUERIES[profile][e] * floor, BITZ_MEASURED_FLOOR)
        for _, _, e in bitz_levels(profile, log_bits, r)
    )


def bitz_beep_overhead(log_bits, r):
    """What BEEP adds to the measured Johnson profile: (proof bytes, prover ms). Each fold, one
    per halving, sends the two halves' evaluations at BEEP_SAMPLES points, and computing them
    costs a multiplication an element a sample, over folds whose sizes halve."""
    folds = sum(k for _, k, _ in bitz_levels("beep", log_bits, r))
    mults = 2 * BEEP_SAMPLES * 2 ** (log_bits - 7)
    return folds * 2 * BEEP_SAMPLES * BITZ_ELEMENT_BYTES, mults * GF128_MEASURED_NS / 1e6


def bitz_measured(profile, r, log_bits):
    """The profile's measurement at the rate, interpolated in the bits' logarithm between the
    two measured sizes around it; None outside the measured sizes."""
    table = BITZ_MEASURED[profile][r]
    lo, hi = math.floor(log_bits), math.ceil(log_bits)
    if lo not in table or hi not in table:
        return None
    t = log_bits - lo
    return [a + t * (b - a) for a, b in zip(table[lo], table[hi])]


# Zero knowledge for BitZ is derived, since its paper offers succinctness only: Ligero's random
# row per Ligerito level, whose symbol appears in every opened column, so that the columns
# reveal nothing; and a Libra-style mask polynomial per sum-check (Flock's zero-check and
# lincheck, Zinc+'s PIOP, and each layer of the GKR), a sum of univariates of degree three in
# each variable, committed as extra rows of the same Ligerito matrix under those random rows
# and opened with the witness, so that each sum-check runs over the masked polynomial. The
# masks are 4 × (3 log N + log N (log N + 1) / 2) field elements for a witness of N bits,
# 1,600 at 2^25, under a percent of the step, charged in the fold once per transaction; the
# random rows cost 16 bytes per opened column, in the decider's proof under ARC with its three
# first-round trees and nothing under recursion; the masks' claimed sums and evaluations are a
# few hundred bytes. Zook-style spot-checked mask oracles would cost about 100 KB here, one
# oracle per sum-check round over the GKR's 325 rounds, so they are not used. Whether ARC's
# accumulation preserves zero knowledge is not examined, as for the other hash-based rows.
BITZ_ZK_ELEM = (
    16  # a field element of 𝔽₂^128: a random row's symbol in an opened column, a mask's coefficient
)
BITZ_ZK_SUMCHECKS = 3  # the zero-check, the lincheck and Zinc+'s PIOP, each over log N variables; the GKR adds a layer per variable


def bitz_mask_elements(log_bits):
    n = math.ceil(log_bits)
    return ZOOK_MASK_COEFFS * (BITZ_ZK_SUMCHECKS * n + n * (n + 1) / 2)


def bitz_point(mode, rate, rank, floor, grind=None, zk=False, profile="udr"):
    app_bits = (
        2**rank
    )  # the step's application witness: 2^rank committed bits, as a step commits 2^rank coefficients elsewhere
    inv = int(rate.split("/")[1])
    r = inv.bit_length() - 1
    beep = profile == "beep"
    bits = app_bits + 2**25
    hashes = 0
    for _ in range(40):
        if mode == "rec":
            log_now = math.log2(bits)
            hashes = 2 * sum(bitz_level_hashes(profile, log_now, r, floor))
            if beep:
                hashes += 2 * bitz_beep_overhead(log_now, r)[0] / BLAKE3_BLOCK
        else:
            depth = math.log2(bits / 128 * inv) + 1
            hashes = 2 * arc_openings(rate, floor, grind or 0) * depth + (2 if grind else 0)
        verifier = 2 * bitz_piop_verifier_mults(math.log2(bits)) * BITZ_FIELD_BITS
        new = app_bits + hashes * HASH_BITS + verifier
        if abs(new - bits) < 1:
            break
        bits = new
    log_bits = math.log2(bits)
    measured = bitz_measured(profile, r, log_bits)
    if measured is None:
        return None  # the merge's bits are outside the measured sizes
    commit_ms, prove_ms, _, verify_ms, nonlig, lig = measured
    scale = floor / BITZ_MEASURED_FLOOR  # the Ligerito bytes and the verifier, as queries do
    deep_bytes, deep_ms = bitz_beep_overhead(log_bits, r) if beep else (0, 0)
    prover_ms = (commit_ms + prove_ms + deep_ms) * (1 + BITZ_PIOP["prover"] * app_bits / bits)
    # the decider's extra first-round trees, on the Ligerito part and, as a bound, on the whole verifier
    level_hashes = bitz_level_hashes(profile, log_bits, r, floor)
    extra = (ARC_DECIDER_TREES - 1) * level_hashes[0] / sum(level_hashes) if mode == "arc" else 0
    proof = nonlig + (lig * scale + deep_bytes) * (1 + extra) + BITZ_PIOP["bytes"]
    verify_ms = verify_ms * scale * (1 + extra)
    prover = prover_ms * WORD_MULTS_PER_MS + grind_prover(BLAKE3_NATIVE, grind or 0)
    # The zero-knowledge rows: the random rows' symbols and the masks' values in the decider's
    # proof under ARC; the masks' share of the witness in the fold, once per transaction.
    zk_bytes_ = (
        (
            bitz_queries(profile, log_bits, r, floor) * BITZ_ZK_ELEM * (1 + extra)
            + 3 * (BITZ_ZK_SUMCHECKS + 1) * BITZ_ZK_ELEM
        )
        if zk and mode == "arc"
        else 0
    )
    fold = round(prover * bitz_mask_elements(log_bits) * 128 / bits) if zk else 0
    return dict(
        family="bitz_rec" if mode == "rec" else "bitz",
        profile=profile,
        pq=True,
        rank=rank,
        E=None,
        binders=None,
        floor=floor,
        grind=grind,
        groups=2,
        packing=None,
        circuits=None,
        change="design",
        zk=zk,
        rate=rate,
        bytes=round(proof + zk_bytes_ + 2 * 32 + (10 * 32 if mode == "arc" else 0) + 4),
        # Under ARC the packed codeword and its tree of 256-byte leaves; under recursion the previous proof.
        memory=round(bits * inv * 5 / 32)
        if mode == "arc"
        else round(proof + zk_bytes_ + 2 * 32 + 4),
        prover=round(prover),
        step_prover=round(app_bits * prover_ms * WORD_MULTS_PER_MS / bits),
        fold=fold,
        accumulation=ARC_ATOMS,
        gates=round(hashes * HASH_BITS + verifier),
        verify=round((verify_ms + BITZ_PIOP["verify_ms"]) * WORD_MULTS_PER_MS),
        folded=2,
        label=f"rank {rank}, rate {rate}, {BITZ_PROFILE_LABEL[profile]}, {round(hashes):,} hashes/merge, 2^{log_bits:.1f} bits"
        + (", ZK, derived" if zk else "")
        + floor_label(floor),
    )


for mode in ("arc", "rec"):
    for grind in GRINDS if mode == "arc" else (None,):
        shapes = [("udr", floor, rate) for floor in FLOORS for rate in ("1/2", "1/8")] + [
            ("beep", BITZ_MEASURED_FLOOR, rate) for rate in RATES
        ]
        for profile, floor, rate in shapes:
            for zk in (False, True):
                for rank in BITZ_RANKS:
                    point = bitz_point(mode, rate, rank, floor, grind, zk, profile)
                    if point is not None:
                        points.append(point)

# Kishu, a bit-decomposed witness over Akita (an internal research draft of 2026-09-23 on
# Booleanity checking via structured modular projections, provisional): the application's
# values are committed one bit per digit over Akita's 64-bit modulus. The claims are in the
# 64-bit field itself, Akita's native profile, and each Pasta value is recomposed from 32-bit
# limbs proved as linear claims in the same sum-check. So there is no decoupled commitment, and
# the soundness obligations are Akita's own plus the Booleanity check's (the soundness note).
# BitZ's exponent-lift GKR is not needed: Booleanity of the committed table is certified over
# the prime field by the conventional weighted sum-check, or by one unweighted quadratic
# identity plus an integer norm bound, which a structured random projection supplies by
# revealing 160 coordinates. The
# draft's single-thread measurements at 2^27 bits over 2^64 - 59 on an M4 Max: the projection
# prover 113 ms, the optimized conventional Booleanity sumcheck 438 ms; verifiers 0.85 and
# 0.023 ms; reduction payloads 2,592 and 1,744 bytes; no commitment opening or hiding. Per
# bit that is 2.5 and 9.8 word multiplications, beside Akita's own 23.7 per digit at the 64-bit
# modulus. A step commits 2^rank digits, one bit each. The merge is Akita's, costed in digits
# as the recovery circuit is in recovery_cost. Its arithmetic is over the 64-bit field F_q and
# its quadratic extension E, the PIOP's own field. As in BitZ, the constraint PIOP runs over
# the ring itself, and only the final linear claim is proved on the bits. So a multiplication
# there is one constraint, with no bit decomposition and no quotient. But every wire of the
# constraint system is committed as its bits, 64 digits for an F_q value and 128 for an E
# value. So a bit
# gate is one digit, a BLAKE3 compression of the transcript is 15,072 digits and the images'
# reductions one per bit; the sum-check's arithmetic is 400 multiplications in E, each
# circuit's claim four and the Booleanity sum-check's verifier about 3,000, at 128 digits each.
# The transcript's elements and the claims are E values of 16 bytes (CLAIM_BYTES["kishu"]),
# the Booleanity sum-check's own transcript is absorbed with them, and under BLAKE3 every
# prover-supplied word is range-checked before hashing (RANGE_CHECK_DIGITS).
# Under the Poseidon option the transcript is hashed by Poseidon over F_q at width 12 and rate
# 8, eight 8-byte words a permutation, with the x^3 S-box, a permutation of F_q since 3 does
# not divide q - 1. Its round numbers are R_F = 8 and R_P = 42 at 128 bits with the security
# margin, from the official round-number script (calc_round_numbers.py, as for the study's
# Goldilocks and 65-bit rows): 138 S-boxes of two multiplications, 276 a permutation, each a
# 64-digit wire. On
# committed digits that is about a sixth more than BLAKE3 per absorbed byte. But a permutation
# is 276 constraints where a BLAKE3 compression is 7,904 (BLAKE3_PIOP), and the digit
# measure charges no constraints. Too close to call: both policies stay as variants of Kishu,
# the BLAKE3 rows under either option and the Poseidon rows under the arithmetic-hash option,
# and the frontier decides. The projection verifier scans 3.1 million sampled coefficients, a
# digit each, so
# under recursion the sum-check form is the usable one and the projection form is shown for its
# prover. Each coefficient the merge scans is a committed digit, about 26 word
# multiplications for the accumulation prover. The projection saves the prover 7.3 word
# multiplications per bit. It is therefore ahead only where a step commits about 3.6 bits per
# coefficient: 2^rank ≳ 3.6 V − 4.6 V_s − H, with V_s the sum-check verifier's digits and H
# the rest of the merge. That is rank 23 at the draft's geometry. Separately, ranks of 21 and
# up are too slow for a Zcash transaction, which puts the frontier's Kishu rows at 19 and 20,
# where the sum-check form wins. The geometry cannot move this much. The widths are set by
# the error target, and the first layer's coefficients times its retained prefix entries is
# the invariant (g c_1)^2 n, which makes a smaller description cost prover memory. One digit
# per coefficient is generous besides: the circuit must also regenerate each coefficient and
# apply it to an extension-field accumulator, of the order of a hundred digits. The
# frontier's Kishu rows thus take the sum-check form, whose soundness is the ordinary
# sum-check's; the projection's certificate is not on Kishu's path. Revealing the
# projection gives no zero knowledge, and the draft's certificates are conditional and not
# yet formalized.
BOOL_CHECK = {  # (word multiplications per bit, payload bytes, verifier ms, merge multiplications, merge bit gates)
    "projection": (113 / 2**27 * WORD_MULTS_PER_MS, 2592, 0.85, 0, 3_109_760),
    "sumcheck": (437.7 / 2**27 * WORD_MULTS_PER_MS, 1744, 0.023, 3000, 0),
}
assert abs(CONSTRAINT_TERM_WORD_MULTS - BOOL_CHECK["sumcheck"][0]) < 1e-9
BIT_GATE_PIOP = (1, 3, 0)
PIOP_ROUND_ELEMENTS = 4  # degree three with the eq weights
PIOP_ROUND_MULTS = 4


def piop_rounds(entries):
    return math.ceil(math.log2(entries)) + 1


def frontend_merge(K, circuits, rank, hp, bool_mults, bool_bits, bool_bytes, zk=False):
    """Kishu's merge: its digits (the transcript hashing, the images' reductions, the sum-check
    and claim arithmetic, the Booleanity check's verifier and transcript, the verifier of the
    child's constraint PIOP, and its own PIOP transcript, which the merge above absorbs) and
    the word multiplications of its own constraint PIOP; with zero knowledge the zk-layer
    merge's 18 more sum-check elements, as for the lattice rows."""
    rounds = piop_rounds(circuits * 2**rank)
    absorbed = (
        akita_absorbed_bytes("kishu", K, circuits, zk)
        + bool_bytes
        + rounds * PIOP_ROUND_ELEMENTS * CLAIM_BYTES["kishu"]
    )
    checked = 0 if hp == "poseidon" else ceil_div(absorbed - K * 128, 8)
    mults = SUMCHECK_GATES + CLAIM_GATES * circuits + bool_mults + rounds * PIOP_ROUND_MULTS
    digits = (
        absorb_digits(absorbed, hp, checked, whole=True)
        + 2 * K * FOLD_GATES_PER_IMAGE
        + mults * E_MULT_DIGITS
        + bool_bits
    )
    piop = piop_sum(
        (1, absorb_piop(absorbed, hp, checked, whole=True)),
        (2 * K * FOLD_GATES_PER_IMAGE, BIT_GATE_PIOP),
        (mults, E_MULT_PIOP),
        (bool_bits, BIT_GATE_PIOP),
    )
    return digits, piop_word_mults(piop)


def frontend_merge_digits(K, circuits, rank, hp, bool_mults, bool_bits, bool_bytes, zk=False):
    return frontend_merge(K, circuits, rank, hp, bool_mults, bool_bits, bool_bytes, zk)[0]


def kishu_step_overhead_digits(rank, hp):
    """Digits an application step adds to its 2^rank by either route: its PIOP transcript over
    the 64-bit field, absorbed and verified in the merge above."""
    rounds = piop_rounds(2**rank)
    transcript = rounds * PIOP_ROUND_ELEMENTS * CLAIM_BYTES["kishu"]
    checked = 0 if hp == "poseidon" else ceil_div(transcript, 8)
    return absorb_digits(transcript, hp, checked) + rounds * PIOP_ROUND_MULTS * E_MULT_DIGITS


def fingerprint_step_extra_digits(rank, hp):
    """The fingerprint route's digits on a step that has multiplications: the column sums of
    its three instances, and their transcripts absorbed and verified in the merge above. A
    step of hashes alone runs no instance and pays nothing, so the routes tie there."""
    rounds = piop_rounds(2**rank)
    transcripts = FINGERPRINT_INSTANCES * rounds * PIOP_ROUND_ELEMENTS * FINGERPRINT_PRIME_BYTES
    checked = 0 if hp == "poseidon" else ceil_div(transcripts, 8)
    return (
        fingerprint_step_digits(rank)
        + absorb_digits(transcripts, hp, checked)
        + FINGERPRINT_INSTANCES * rounds * PIOP_ROUND_MULTS * E_MULT_DIGITS
    )


# A Kishu step keeps at least this many circuits of 2^rank digits for the application beside
# its merge, so that the rank sets the step's capacity for the application as it does for the
# other families, and the merge's slack adds to it.
STEP_HEADROOM = 1.0


def merge_marginal_circuit(K, rank, hp, bool_mults, bool_bits, bool_bytes, zk=False):
    """The merge's digits for one more circuit in the step: its claim and the claim's
    absorption (circuit_slope)."""
    return circuit_slope(
        lambda c: frontend_merge_digits(K, c, rank, hp, bool_mults, bool_bits, bool_bytes, zk)
    )


def frontend_circuits(K, rank, hp, bool_mults, bool_bits, bool_bytes, zk=False):
    """The circuits of 2^rank digits a Kishu step is: the merge's digits, the step's own
    transcript digits in the merge above, and at least STEP_HEADROOM of a circuit for the
    application's nodes, which fill the rest (kishu_costs), at the fixed point, since the
    merge's digits grow with the circuits' claims; None where each circuit's claim costs more
    digits than the circuit holds, as for the lattice rows under BLAKE3."""
    per_circuit = merge_marginal_circuit(K, rank, hp, bool_mults, bool_bits, bool_bytes, zk)
    if per_circuit >= 2**rank:
        return None
    fixed = kishu_step_overhead_digits(rank, hp) + STEP_HEADROOM * 2**rank
    circuits = 1
    for _ in range(200):
        new = math.ceil(
            (
                frontend_merge_digits(K, circuits, rank, hp, bool_mults, bool_bits, bool_bytes, zk)
                + fixed
            )
            / 2**rank
        )
        if new == circuits:
            return circuits
        circuits = new
    return circuits


def handoff_merge_digits(K, circuits, hp):
    """Kishu's handoff merge under the note's §5.8 deferral (handoff_merge_gates for the lattice
    rows): its digits and its PIOP's word multiplications, for the mask's K images and claim
    evaluations absorbed, the images' reductions, and the claims' fold."""
    absorbed = K * 128 + circuits * CLAIM_BYTES["kishu"]
    checked = 0 if hp == "poseidon" else ceil_div(circuits * CLAIM_BYTES["kishu"], 8)
    mults = CLAIM_GATES * circuits
    digits = (
        absorb_digits(absorbed, hp, checked, whole=True)
        + K * FOLD_GATES_PER_IMAGE
        + mults * E_MULT_DIGITS
    )
    piop = piop_sum(
        (1, absorb_piop(absorbed, hp, checked, whole=True)),
        (K * FOLD_GATES_PER_IMAGE, BIT_GATE_PIOP),
        (mults, E_MULT_PIOP),
    )
    return digits, piop_word_mults(piop)


# A Kishu step is a slot of some circuits of 2^rank digits that the merge and the application
# share: the merge's digits and the step's own transcript digits take the first part, and the
# application's nodes fill the rest, as many as fit. The step has the circuits of
# frontend_circuits, the least that keep STEP_HEADROOM circuits for the application, so that
# the rank sets the capacity and the merge's slack adds to it; the transaction measure packs
# the application into that capacity, and the frontier chooses the rank per application. The
# padding is charged as it costs: the application's digits are committed and range-checked at
# their own number (unit_cost per digit), since a zero digit costs the Ajtai hash and the range
# sum-check nothing, while the fold's sum-checks and the mask run over the whole slot, the
# accumulator's length (accumulator_coefficients: circuits × 2^rank and the stages' values).
#
# Zero knowledge for Kishu is Akita's, as the lattice rows have it: the masked rank on
# every step's digits, the zk-layer merge's 18 more atoms, and the user's masking fold at the
# handoff, whose rejection sampling runs over the accumulator's digits. The projection form
# reveals coordinates and has no zero-knowledge rows.
def kishu_costs(
    K, circuits, rank, hp, check, floor, zk, route, alpha=MASK_ALPHA, sample=MASK_SAMPLE_WORD_MULTS
):
    """A Kishu row's work, and the parts of its masking fold. The merge's commitments, its own
    digits and the step's transcript digits, are the prover measure; with its constraint PIOP
    and the fold's sum-checks over the slot they are the accumulation prover. The application's
    digits are charged per digit (unit_cost), and the step's capacity for them is step_units,
    less the fingerprint route's digits on a step with multiplications (step_units_mults, None
    where those leave no room); the application's constraint PIOP itself is per application,
    DATA.piop. The fold is the
    expected rejection-sampling attempts, each a commitment of a mask of the accumulator's
    digits under the masked matrix and as many Gaussian samples, plus the handoff's merge;
    `fold_leaf` masks one circuit's 2^rank digits instead, for a bare leaf handed over without
    a fuse (LEAF_HANDOFF). `alpha` and `sample` stand in for the mask's Gaussian width and the
    sampler's cost, for the page's sweep of the two."""
    bool_per_bit, bool_bytes, _, bool_mults, bool_bits = BOOL_CHECK[check]
    digits, merge_piop = frontend_merge(
        K, circuits, rank, hp, bool_mults, bool_bits, bool_bytes, zk
    )
    accumulator = accumulator_coefficients("kishu", rank, circuits)
    log_n = math.log2(accumulator)  # the bounds' N: this row's accumulator in digits
    bits = DIGIT_MAX["kishu"]
    per_digit = (
        ajtai_per_coefficient("pasta_q64", zk, floor, alpha, log_n, bits) / DIGITS["pasta_q64"]
    )
    masked_digit = (
        ajtai_per_coefficient("pasta_q64", True, floor, alpha, log_n, bits) / DIGITS["pasta_q64"]
    )
    # A bare leaf's mask has the leaf's own σ and bound.
    leaf_masked_digit = (
        ajtai_per_coefficient("pasta_q64", True, floor, alpha, rank, bits) / DIGITS["pasta_q64"]
    )
    per_step_digit = per_digit + bool_per_bit
    overhead = kishu_step_overhead_digits(rank, hp)
    capacity = math.floor(circuits * 2**rank - digits - overhead)
    assert capacity >= STEP_HEADROOM * 2**rank, (rank, circuits, digits, overhead)
    route_extra = fingerprint_step_extra_digits(rank, hp) if route == "fingerprint" else 0
    commitments = (digits + overhead) * per_step_digit
    attempts = mask_attempts(alpha) if zk else 0
    handoff_digits, handoff_piop = handoff_merge_digits(K, circuits, hp)
    handoff = handoff_digits * per_step_digit + handoff_piop
    parts = dict(
        sampling=attempts * accumulator * sample,
        masks=attempts * accumulator * masked_digit,
        merge=handoff if zk else 0,
    )
    acc_rate = accumulation_sumchecks("pasta_q64", 1, digits=1, word_mults=WORD_MULTS["pasta_q64"])
    fields = dict(
        prover=round(commitments),
        accumulation_prover=round(commitments + merge_piop + acc_rate * accumulator),
        step_prover=round(capacity * per_step_digit),
        unit_cost=per_step_digit,
        step_units=capacity,
        step_units_mults=math.floor(capacity - route_extra) if capacity > route_extra else None,
        route_step=(
            round(route_extra * per_step_digit + fingerprint_step_range_mults(rank))
            if route == "fingerprint"
            else 0
        ),
        fold=round(sum(parts.values())),
        fold_leaf=round(attempts * 2**rank * (sample + leaf_masked_digit) + parts["merge"]),
        gates=round(digits),
    )
    return fields, parts


for (check, (_, bool_bytes, bool_verify_ms, bool_mults, bool_bits)), hp in itertools.product(
    BOOL_CHECK.items(), HASH_POLICIES
):
    K = STAGES + 1
    for floor in FLOORS:
        for zk in (False,) if check == "projection" else (False, True):
            for rank in FRONTEND_RANKS:
                circuits = frontend_circuits(K, rank, hp, bool_mults, bool_bits, bool_bytes, zk)
                if circuits is None:
                    continue  # the per-circuit claim's digits exceed this rank's circuit
                atoms = akita_atoms("kishu", K, circuits, zk)
                # Kishu's claims are at the 64-bit profile in a small extension, as the Goldilocks
                # variant's are, so its opening and decider follow that variant's plan and
                # measurement at Kishu's digit count; the Pasta-claims plan's extra bytes are
                # Pasta-width elements that Kishu does not have.
                log_len = rank + math.log2(circuits) - math.log2(DIGITS["goldilocks"])
                rank_scale = RANK_SCALE[floor]["goldilocks"]
                opening = akita_bytes("goldilocks", K - 1, log_len, floor)
                instance = K * 128 + 2 * K * 32 + 4 + circuits * CLAIM_BYTES["kishu"]
                accumulator = accumulator_coefficients("kishu", rank, circuits)
                for route in MULT_ROUTES:
                    fields, _ = kishu_costs(K, circuits, rank, hp, check, floor, zk, route)
                    points.append(
                        dict(
                            family="bits_q64" if hp == "blake3" else "bits_q64_poseidon",
                            pq=True,
                            rank=rank,
                            E=None,
                            binders=None,
                            floor=floor,
                            hashes=hp,
                            groups=K,
                            packing=None,
                            circuits=circuits,
                            change="design",
                            zk=zk,
                            check=check,
                            route=route,
                            arith=f"bits_pasta_{route}",
                            bytes=round(opening + instance + bool_bytes),
                            memory=accumulator_bytes("pasta_q64", accumulator, digits=1),
                            peak_memory=round(
                                peak_fuse_bytes(
                                    accumulator_bytes("pasta_q64", accumulator, digits=1),
                                    accumulator,
                                    CLAIM_BYTES["kishu"],
                                    zk,
                                    mask_coordinate_bits(
                                        log_n=math.log2(accumulator), digit_max=DIGIT_MAX["kishu"]
                                    ),
                                )
                            ),
                            accumulation=atoms,
                            verify=akita_verify(
                                "goldilocks",
                                log_len,
                                zk,
                                rank_factor_share("goldilocks", rank_scale),
                            )
                            + round(bool_verify_ms * WORD_MULTS_PER_MS),
                            folded=K,
                            label=f"rank {rank}, {circuits} circuit{'s' if circuits != 1 else ''} of 2^{rank} digits, {fields['gates'] / 1e6:.1f}M digits, {K} groups, Booleanity by {check}, multiplication by {route}"
                            + HASH_LABEL[hp]
                            + (", ZK" if zk else "")
                            + floor_label(floor),
                            **fields,
                        )
                    )

# ---- Flock-style Boolean circuits over Akita's binary groups (experimental) ----------------
# Akita's development branch commits a dense binary source as a group kind inside one
# ordinary grouped opening (LayerZero-Labs/akita#285, the `binary` feature; it replaces the
# LaBinius root reduction and nested commitment of its PR #229): the bits are packed into
# 128-bit carriers, the claim is a multilinear evaluation over a binary field, and the
# opening switches to the proof field inside. So the 𝔽₂ family's arithmetization, Boolean
# circuits with Flock's PIOP over 𝔽₂^128, can commit with Akita instead of FRI-Binius and
# accumulate with Akita's fold instead of ARC. The row prices that from the branch's
# measurements (specs/binary-p64-root.md there, scripts/binary-full-size.sh at 8046b4cd2,
# 2026-11): a binary-claim opening of 2^22 carriers, 2^29 bits, at the P128 root is 82,764 B,
# committed in 174 ms, opened in 648 ms and verified in 8.5 ms on an M4 Max under load with
# the `parallel` feature on; the P64 root is 1 to 4 percent smaller with times within noise.
#   - The merge is Akita's fold in a Boolean circuit, our estimate: the transcript absorbed by
#     BLAKE3 in blocks of 8,192 committed bits per compression, native in a Boolean circuit
#     under either hash policy; the fold of each child's 128-byte image by a ternary challenge of the page's
#     weight, one adder bit per image bit per unit of weight; and one proof-field
#     multiplication per sum-check element, counted in AND gates with XOR free by the cheapest
#     of schoolbook, Karatsuba and Toom-Cook 3 at each width (mult_ands), which dominates;
#     and the two inputs' Flock PIOP verifiers at the merge's own size, as the 𝔽₂ family's
#     merge counts them.
#   - Bytes: the measured opening extrapolated from 2^29 bits down to the merge's witness at
#     the planner's growth per doubling for the 128-bit field, with the stage groups at that
#     field's growth with K, plus the instance. The measured pair a doubling apart differ by
#     1.8 KB, which would make the proof about 8 KB smaller, but a one-doubling difference
#     between single runs is not a slope.
#   - Prover: the measured commit time per committed bit, at BINARY_THREADS times the measured
#     time for one thread, since BitZ's benchmark gave four to five times on ten threads of
#     this machine; plus Flock's PIOP. The accumulation prover adds the fold's sum-checks over
#     the accumulator (the merge's bits and the stages' values as bits), as the lattice rows
#     count them, at the binary field's multiplication cost (CLMULS[128] carry-less 64-bit
#     multiplications, one word multiplication each). The measured open time is the opening's,
#     which the accumulation prover does not count for the lattice rows either.
#   - Verify: the measured decider scaled to the merge's bits at Akita's single-thread slope.
#   - Atoms: Akita's at the 128-bit claim width; the transaction measure as the 𝔽₂ family's.
# Not modelled: zero knowledge (the groups are not hiding) and the higher floor (the q24
# Module-SIS certificate and the security ledger are open; the branch makes no security
# claim), so the row is at the 128-bit floor only; and the binary carrier field switch.
BINARY_MEASURED = dict(
    bytes=82764, commit_ms=174, prove_ms=648, verify_ms=8.5, log_bits=29, field=128
)
BINARY_THREADS = (
    10  # the measurements ran with the `parallel` feature; one thread is taken as ten times slower
)
BINARY_VERIFY_SLOPE = AKITA_VERIFY_MS["fp128"][1]


def reduce_ands(n):
    """AND gates of the reduction of a 2n-bit product modulo a prime 2^n - c with a small c
    of a few bits: the shifted additions of the high half by c's bits, a short second pass,
    and the final conditional subtraction, about 6n."""
    return 6 * n


def bits_akita_merge_parts(K, circuits, field):
    """AND gates of Akita's merge in a Boolean circuit, by part: the transcript hashed by
    BLAKE3, the fold of the children's images, the sum-check verifier's field multiplications,
    the claims, and the two inputs' Flock PIOP verifiers at the merge's own size, as the 𝔽₂
    family's merge counts them, at a fixed point."""
    parts = dict(
        hashing=ceil_div(akita_absorbed_bytes("fp128", K, circuits, False), BLAKE3_BLOCK)
        * BLAKE3_ANDS_PADDED,
        fold=2 * K * FOLD_GATES_PER_IMAGE * (MASK_CHALLENGE_L1 + 2),
        sumcheck=SUMCHECK_ATOMS * (mult_ands(field) + reduce_ands(field)),
        claims=CLAIM_GATES * circuits,
    )
    base = sum(parts.values())
    ands = base
    for _ in range(40):
        verifier = 2 * f2_piop_verifier_mults(math.log2(ands)) * CLMUL_ANDS[128]
        new = base + verifier
        if abs(new - ands) < 1:
            break
        ands = new
    parts["verifier"] = verifier
    return parts


def bits_akita_merge_ands(K, circuits, field):
    return sum(bits_akita_merge_parts(K, circuits, field).values())


def binary_open_bytes(log_bits, K):
    """The measured binary-source opening at the merge's bits, extrapolated at the 128-bit
    field's slope, with K - 1 further groups at that field's growth."""
    opening = BINARY_MEASURED["bytes"] - SLOPE[128]["fp128"] * (
        BINARY_MEASURED["log_bits"] - log_bits
    )
    return opening * akita_bytes("fp128", K - 1, 14) / AKITA[128]["fp128"][0]


K = STAGES + 1
bits_akita_ands = bits_akita_merge_ands(K, 1, BINARY_MEASURED["field"])
bits_akita_log = math.log2(bits_akita_ands)
bits_akita_accumulator = accumulator_coefficients("bits_akita", bits_akita_log, 1)
bits_akita_per_bit = (
    BINARY_MEASURED["commit_ms"]
    * BINARY_THREADS
    * WORD_MULTS_PER_MS
    / 2 ** BINARY_MEASURED["log_bits"]
)
bits_akita_prover = bits_akita_ands * bits_akita_per_bit + f2_piop(bits_akita_ands, 128)
bits_akita_accumulation = bits_akita_prover + accumulation_sumchecks(
    "fp128", bits_akita_accumulator, digits=1, word_mults=CLMULS[128] * CLMUL_WORD_MULTS
)
points.append(
    dict(
        family="bits_akita",
        pq=True,
        rank=None,
        E=None,
        binders=None,
        floor=128,
        hashes="any",
        groups=K,
        packing=None,
        circuits=None,
        change="design",
        zk=False,
        bytes=round(
            binary_open_bytes(bits_akita_log, K) + K * 128 + 2 * K * 32 + 4 + CLAIM_BYTES["fp128"]
        ),
        memory=round(bits_akita_accumulator / 8),  # the accumulator's bits, packed
        peak_memory=round(
            peak_fuse_bytes(
                bits_akita_accumulator / 8, bits_akita_accumulator, CLAIM_BYTES["fp128"], False, 0
            )
        ),
        prover=round(bits_akita_prover),
        accumulation_prover=round(bits_akita_accumulation),
        step_prover=round(BOOL_STEP_BITS * bits_akita_prover / bits_akita_ands),
        fold=0,
        accumulation=akita_atoms("fp128", K, 1, False),
        gates=round(bits_akita_ands),
        verify=round(
            (
                BINARY_MEASURED["verify_ms"]
                - BINARY_VERIFY_SLOPE * (BINARY_MEASURED["log_bits"] - bits_akita_log)
            )
            * WORD_MULTS_PER_MS
        ),
        folded=K,
        label=f"P128 root, 2^{bits_akita_log:.1f} committed bits, {bits_akita_ands / 1e6:.1f}M AND gates, {K} groups, experimental",
    )
)
FIELD["bits_akita"] = "boolean"

# Endoscaling capacity beyond the points to walk changes nothing; keep the smallest E of
# each set of identical Pedersen-IPA results.
for p in points:
    p.setdefault(
        "hashes", "any"
    )  # the 𝔽₂ family and BitZ hash with BLAKE3 natively, under either policy

seen, deduped = set(), []
for p in points:
    key = (
        p["family"],
        p["rank"],
        p["binders"],
        p["packing"],
        p["floor"],
        p["hashes"],
        p["zk"],
        p.get("zkv"),
        p.get("grind"),
        p.get("rate"),
        p.get("field"),
        p.get("route"),
        p["bytes"],
        p["prover"],
        p["accumulation"],
    )
    if key in seen:
        continue
    seen.add(key)
    deduped.append(p)

points = deduped

# How a family realises the Pasta arithmetic that the Ironwood recovery circuit needs: native,
# a gate over Pasta's field; relation, integer relations over committed bits with the result,
# the quotient and any carries committed and no committed intermediate wires (BitZ, Kishu);
# limbs, limb products as committed wires in another field; bits, a Boolean circuit. The first
# two enter the dominance test as a requirement: such a configuration is dominated only by
# another such, while a limbs or bits configuration can be dominated by any.
PASTA_ARITH = {
    "pedersen": "native",
    "fp128": "limbs",
    "goldilocks": "limbs",
    "pasta_q64": "native",
    "pasta_sis": "native",
    "pasta": "native",
    "whir": "native",
    "whir_gold": "limbs",
    "whir_hybrid": "native",
    "plonky3": "limbs",
    "flock": "bits",
    "whir_rec": "native",
    "whir_gold_rec": "limbs",
    "whir_hybrid_rec": "native",
    "plonky3_rec": "limbs",
    "flock_rec": "bits",
    "bitz": "relation, fingerprint",
    "bitz_rec": "relation, fingerprint",
    "bits_q64": "relation",
    "bits_q64_poseidon": "relation",
    "bits_akita": "bits",
}
PASTA_COUNTS = ("native", "relation")
# The security assumption is the dominance test's second requirement: a configuration is
# dominated only by one that assumes no more. The hash-based families rest on a random oracle
# alone; Akita's and Kishu's on Module-SIS as well; the Boolean-over-Akita row's security
# ledger is open, so it ranks above both and removes nothing (the user, 2026-11-21: a lattice
# scheme must not dominate a hash-based one, and a row that is not baked must not dominate the
# others). Pedersen-IPA is its own class, so its level never meets another.
LATTICE_FAMILIES = (
    "pedersen",
    "fp128",
    "goldilocks",
    "pasta_q64",
    "pasta_sis",
    "pasta",
    "bits_q64",
    "bits_q64_poseidon",
)
ASSUMPTION_LEVEL = {
    f: 2 if f == "bits_akita" else 1 if f in LATTICE_FAMILIES else 0 for f in PASTA_ARITH
}
# The changes a configuration needs are the third requirement, parameters only below code
# changes below design changes (the user, 2026-11-21): a configuration is dominated only by one
# that needs no more, which keeps the best parameter-only configurations on the frontier beside
# what the changes buy.
CHANGE_LEVEL = {"none": 0, "code": 1, "design": 2}

for p in points:
    p["pasta_arith"] = PASTA_ARITH[p["family"]] + (f", {p['route']}" if p.get("route") else "")
    p["pasta"] = p["pasta_arith"].split(",")[0] in PASTA_COUNTS
    # A row derived from an analysis that no implementation certifies (BitZ under BEEP) is ranked
    # with the strongest assumption, so that it removes no certified row from the frontier.
    p["assumption"] = 2 if p.get("profile") == "beep" else ASSUMPTION_LEVEL[p["family"]]

# Each point's arithmetization and its step's capacity in that arithmetization's unit, for
# the transaction measure (see APPLICATIONS); Kishu's rows set theirs in kishu_costs.
for p in points:
    p["arith"] = p.get("arith") or FIELD[p["family"]]
    if p.get("step_units") is not None:
        continue
    if p["rank"] is None:
        p["step_units"] = BOOL_STEP_BITS  # a Boolean step, in AND gates
    elif p["arith"] == "bitz" or p["arith"].startswith("bits_pasta"):
        p["step_units"] = 2 ** p["rank"]  # bits or digits, one per committed coefficient
    else:
        p["step_units"] = gate_budget(p["rank"])  # gates of four coefficients


# The frontier is taken to a tolerance (the user, 2026-11-25). A configuration that is ahead
# of another by a hair on one measure is not thereby a different choice, and the low ranks of
# a hash-based family, whose proofs differ in the fifth digit, crowded the frontier.
#
# This is epsilon-dominance (Laumanns, Thiele, Deb and Zitzler, 2002): q epsilon-dominates p
# when q is no more than a factor 1 + eps worse than p on every measure, and no worse on the
# three requirements. The paper keeps its set on a grid of boxes, which has an artifact: two
# configurations within the tolerance of each other on every measure both stay when a box
# boundary falls between them. So the set is built without a grid (the user's construction,
# 2026-11-26). The configurations are taken in increasing order of the product of their
# measures, and one is kept unless a configuration already kept epsilon-dominates it. Then:
#   - every configuration left out is epsilon-dominated by a kept one;
#   - every kept configuration is undominated in the exact sense, since one that dominated it
#     would have a smaller product, and either was kept before it or was left out for a kept
#     one that epsilon-dominates both; and
#   - of two kept configurations with the same requirements, the one taken later is better
#     than the other by more than the tolerance on some measure.
# The product orders the configurations whatever the measures' units, and ties in it go by
# family and then by label, so the order is fixed. Two configurations alike on every measure
# and requirement both stay if they are of different families, since neither is a reason to
# hide the other's scheme; of one family, the first stands for both. At eps = 0 this is exact
# dominance. The page's frontierAmong is the same rule on the measures selected there.
FRONTIER_TOLERANCES = (0, 0.02, 0.05)
FRONTIER_TOLERANCE = 0.02


def pareto(pts, eps=FRONTIER_TOLERANCE):
    measures = ("bytes", "prover", "accumulation")

    def requirements(p):
        return (-p["pasta"], p["assumption"], CHANGE_LEVEL[p["change"]])

    def product(p):
        return sum(math.log(p[m]) if p[m] > 0 else -math.inf for m in measures)

    def beats(q, p):
        """q epsilon-dominates p. Two configurations alike on every measure and requirement
        are a tie: of one family, the earlier in the order stands for both; of two families,
        both stay."""
        if not all(q[m] <= (1 + eps) * p[m] for m in measures):
            return False
        if not all(a <= b for a, b in zip(requirements(q), requirements(p))):
            return False
        tie = requirements(q) == requirements(p) and all(q[m] == p[m] for m in measures)
        return not tie or q["family"] == p["family"]

    order = sorted(
        range(len(pts)), key=lambda i: (product(pts[i]), pts[i]["family"], pts[i]["label"], i)
    )
    kept, keep = [], [False] * len(pts)
    for i in order:
        if not any(beats(q, pts[i]) for q in kept):
            kept.append(pts[i])
            keep[i] = True
    return keep


# ---- Grinding chosen per row ---------------------------------------------------------
# Each bit of grinding removes about one opening in a hundred, so about a percent of the
# circuits and of the prover, while the grinding's own cost doubles; the prover is least where
# the two cross, at 17 to 19 bits for the Poseidon families and 12 to 14 for the BLAKE3 ones,
# and the minimum is shallow. "best per row" takes, for every hash-based configuration, the
# measured setting with the smallest prover; the fixed settings stay selectable.
def grind_key(p):
    return (
        p["family"],
        p["floor"],
        p["zk"],
        p.get("rate"),
        p["rank"],
        p.get("packing"),
        p.get("field"),
        p.get("zkv"),
        p["hashes"],
        p.get("profile"),
    )


best = {}
for p in points:
    if p.get("grind") is None:
        continue
    k = grind_key(p)
    if k not in best or p["prover"] < best[k]["prover"]:
        best[k] = p

for p in list(best.values()):
    q = dict(
        p, grind="auto", grind_bits=p["grind"], label=p["label"] + f", {p['grind']}-bit grinding"
    )
    points.append(q)

# The page offers the settings the text discusses; the other measured settings serve only
# the best-per-row choice above.
GRIND_OPTIONS = (0, 16, 20, 24)
points = [p for p in points if p.get("grind") in (None, "auto") or p["grind"] in GRIND_OPTIONS]

for (cls, zk, floor), hp in itertools.product(
    (
        (True, False, 128),
        (True, True, 128),
        (True, False, 147),
        (True, True, 147),
        (False, None, 128),
    ),
    HASH_POLICIES,
):
    for grind in (None, "auto", *GRINDS):
        sub = [
            p
            for p in points
            if p["pq"] == cls
            and p["zk"] in (zk, None)
            and p["floor"] == floor
            and (p["hashes"] in ("blake3", "any") or hp == "poseidon")
            and p.get("grind") in (None, grind)
        ]
        for p, on in zip(sub, pareto(sub)):
            p["frontier"] = p.get("frontier", False) or on

# The rows that add no sum-check work have the merge's commitments as their accumulation
# prover (see accumulation_sumchecks), and the sum-check rate is the measured one.
for p in points:
    p.setdefault("accumulation_prover", p["prover"])
    p.setdefault(
        "memory", p["bytes"]
    )  # the rows under their own recursion hold only the previous proof
    p.setdefault("fold_leaf", p["fold"])  # only the lattice rows' masks scale with the accumulator
    p.setdefault("peak_memory", 2 * p["memory"])  # two accumulators, the output over one of them
assert (
    abs(BOOL_CHECK["sumcheck"][0] / WORD_MULTS["pasta_q64"] - SUMCHECK_FIELD_MULTS_PER_DIGIT) < 0.2
)

# ---- Pruning ---------------------------------------------------------------------------
# A point that another point of its family beats or equals on every measure the page can
# plot (bytes, prover, accumulation prover, atoms, gates, verifier, and the transaction
# measure at every transaction size, which is monotone in the per-step prover plus the
# accumulation prover and in the fold) is never on any frontier, provided the two are
# selectable only together: the
# same floor, zero-knowledge variant, hash policy, grinding, rank, packing, field design,
# endoscalings and binders. Within such a group the rows differ by rate. The header is not a
# row attribute: the page adds the application's header to every row's bytes alike, at
# HEADER_ELEMENT_BYTES an element. This keeps the page's size down without removing
# anything that a knob could isolate.
PRUNE_MEASURES = (
    "bytes",
    "prover",
    "accumulation_prover",
    "accumulation",
    "gates",
    "verify",
    "memory",
    "peak_memory",
)


def prune_key(p):
    return (
        p["family"],
        p["floor"],
        p["zk"],
        p.get("zkv"),
        p["hashes"],
        p.get("grind"),
        p["rank"],
        p.get("packing"),
        p.get("field"),
        p.get("route"),
        p.get("E"),
        p.get("binders"),
        p.get("profile"),  # a derived row does not prune a certified one
    )


def prune_measures(p):
    return tuple((p[m] or 0) for m in PRUNE_MEASURES) + (
        (p["step_prover"] or 0) + p["accumulation_prover"],
        p["fold"] or 0,
        p["fold_leaf"] or 0,
    )


def dominates(q, p):
    a, b = prune_measures(q), prune_measures(p)
    return all(x <= y for x, y in zip(a, b)) and a != b


prune_groups = {}
for p in points:
    prune_groups.setdefault(prune_key(p), []).append(p)
before = len(points)
points = [
    p
    for grp in prune_groups.values()
    for p in grp
    if not any(q is not p and dominates(q, p) for q in grp)
]
pruned = before - len(points)

budget = [
    dict(
        rank=r,
        gates=gate_budget(r),
        endoscalings=max_endoscalings(r),
        binders=min_binders(r) if _model["challenges_per_binder"](r) >= 1 else None,
        fixed=fixed_counts(r, True),
    )
    for r in RANKS
]

# ---- Prose figures and claims ----------------------------------------------------------
# The page's text and pasta-proof-size.md quote figures that the model computes. Each sits
# between markers in the tracked file, <!--fig:NAME-->value<!--/fig-->, invisible when the
# file is rendered. Writing pareto.html fills the markers from FIGURES; `--fill` writes the
# values back into the tracked files; the default run fails when a tracked value is stale, so
# the prose cannot drift from the model. Wording that a figure cannot carry, such as which row
# dominates which, is guarded by the claims below, which fail the run when the model no longer
# supports them.

RATE_PER_S = 1000 * WORD_MULTS_PER_MS  # word multiplications per second of one core


def app_units(p, app, policy):
    """The application's units in the row's arithmetization under the row's hash policy, or
    under the page's for a row priced under either: a number, or a proof tree's nodes."""
    return APPLICATIONS[app][p["arith"]][policy if p["hashes"] == "any" else p["hashes"]]


def pack_nodes(nodes, cap, own):
    """The page's packNodes: a proof tree's nodes into steps of capacity `cap`, a node larger
    than a step taking whole steps and its remainder joining the rest, which fill steps
    first-fit decreasing; the tree's last `own` nodes, a Tachyon tree's rerandomization
    fuses, are steps of their own."""
    steps, items = own, []
    for node in nodes[:-own] if own else nodes:
        steps += node // cap
        if node % cap:
            items.append(node % cap)
    bins = []
    for item in sorted(items, reverse=True):
        for i, b in enumerate(bins):
            if b + item <= cap:
                bins[i] += item
                break
        else:
            bins.append(item)
    return steps + len(bins)


def step_capacity(p, app):
    """A step's capacity for the application's units: step_units_mults where the application
    has Pasta multiplications and the row has one (Kishu's fingerprint route; None where the
    route's per-step digits leave the step no room), else step_units."""
    if APPLICATION_MULTS[app] and "step_units_mults" in p:
        return p["step_units_mults"]
    return p["step_units"]


def tx_steps(p, app, policy, count=1):
    """The page's txStepsFor (pareto-template.html): the application's units in as many steps
    as the row's step holds, rounded up, a proof tree packed by pack_nodes; infinite where the
    row's step has no capacity for the application."""
    units = app_units(p, app, policy)
    cap = step_capacity(p, app)
    if cap is None:
        return math.inf
    if not isinstance(units, list):
        return math.ceil(units * count / cap)
    return pack_nodes(units, cap, OWN_LAST_STEPS.get(app, 0))


def app_fold(p, app):
    """The application's masking fold: over the leaf alone for a bare leaf handed over without
    a fuse (LEAF_HANDOFF), over the chain's accumulator otherwise."""
    return p["fold_leaf"] if app in LEAF_HANDOFF else p["fold"]


def tx_work(p, app, policy, count=1):
    """The page's txWork: the steps' merges at the accumulation prover, and the application's
    units at the row's cost per unit where it has one (Kishu, whose steps the merge and the
    application share) or else at the per-step cost of as many steps; the fingerprint route's
    per-step cost on an application with multiplications; the masking fold; and Kishu's
    application PIOP."""
    steps = tx_steps(p, app, policy, count)
    if p.get("unit_cost") is not None:
        units = app_units(p, app, policy)
        total = sum(units) if isinstance(units, list) else units * count
        base = total * p["unit_cost"] + steps * p["accumulation_prover"]
    else:
        base = steps * (p["step_prover"] + p["accumulation_prover"])
    return (
        base
        + (steps * p.get("route_step", 0) if APPLICATION_MULTS[app] else 0)
        + app_fold(p, app)
        + PIOP_WORK.get(app, {}).get(p["arith"], 0) * count
    )


def shown(family, policy="blake3", zk=False, floor=DEFAULT_FLOOR, **where):
    """A family's rows as the page shows them under a hash policy (the arithmetic-hash option
    adds the Poseidon-priced rows to the BLAKE3 ones), a zero-knowledge setting and a floor,
    with the grinding chosen per row; `where` pins further fields."""
    allowed = ("any", "blake3") + (("poseidon",) if policy == "poseidon" else ())
    return [
        p
        for p in points
        if p["family"] == family
        and p["hashes"] in allowed
        and p["zk"] in (zk, None)
        and p["floor"] in (floor, None)
        and p.get("grind") in (None, "auto")
        and all(p.get(k) == v for k, v in where.items())
    ]


def pick(family, **where):
    """The one row that `where` picks out."""
    found = shown(family, policy="poseidon", **where)
    assert len(found) == 1, (family, where, [p["label"] for p in found])
    return found[0]


tx_checks = []  # the rows whose transaction figures the text quotes, for the page's self-check


def best_for(family, app, policy="blake3", count=1, **kw):
    """The row of a family with the least transaction work for an application, which is where
    the page's frontier puts the family, and its work."""
    p = min(
        (p for p in shown(family, policy, **kw) if p["step_prover"] is not None),
        key=lambda p: tx_work(p, app, policy, count),
    )
    work = tx_work(p, app, policy, count)
    tx_checks.append(
        dict(family=family, label=p["label"], app=app, policy=policy, count=count, transaction=work)
    )
    return p, work


KISHU = ("bits_q64", "bits_q64_poseidon")  # Kishu's two hash variants, a family each on the page


def kishu_best(app, **kw):
    """Kishu's least-transaction row over both variants under the arithmetic-hash option."""
    return min((best_for(f, app, "poseidon", **kw) for f in KISHU), key=lambda pw: pw[1])


def kishu_zk_costs(p, alpha=MASK_ALPHA, sample=MASK_SAMPLE_WORD_MULTS):
    """A Kishu zero-knowledge row's costs and fold parts at another Gaussian width or sampler
    cost: the row's circuits stay, since the zk-layer merge's extra atoms depend only on the
    rounded log of the mask's length, which is 3 for 6 to 11 slices a coordinate."""
    log_n = math.log2(accumulator_coefficients("kishu", p["rank"], p["circuits"]))
    mask_sumcheck_atoms(mask_length(alpha, log_n=log_n, digit_max=DIGIT_MAX["kishu"]))
    return kishu_costs(
        p["groups"],
        p["circuits"],
        p["rank"],
        p["hashes"],
        p["check"],
        p["floor"],
        True,
        p["route"],
        alpha,
        sample,
    )


def kishu_zk_best(app, alpha=MASK_ALPHA, sample=MASK_SAMPLE_WORD_MULTS, count=1):
    """Kishu's least zero-knowledge transaction over both variants and routes, the page's rows
    with their mask-dependent costs recomputed at `alpha` and `sample`; at the page's values it
    is kishu_best(app, zk=True, count=count) without the self-check's record."""
    best = None
    for f in KISHU:
        for p in shown(f, "poseidon", zk=True):
            q = dict(p, **kishu_zk_costs(p, alpha, sample)[0])
            w = tx_work(q, app, "poseidon", count)
            if best is None or w < best[1]:
                best = (q, w)
    return best


# The applications the page offers, with their counts (the application select).
PAGE_APPLICATIONS = (
    ("recovery", 1),
    ("recovery", 4),
    *((app, 1) for app in MIGRATIONS),
    ("qk", 1),
    *((f"leansphincs_{h}", 1) for h in LEANSPHINCS_VERIFY),
    *((f"zoodles_{auth}", 1) for auth in ZOODLES_AUTHS),
    *((f"zoodles_merkle_{auth}", 1) for auth in ZOODLES_AUTHS),
    ("zoodles_epoch", 1),
    *((f"tachyon{n}", 1) for n in sorted(TACHYON_TRANSACTIONS)),
    *(("path", n) for n in (1, 2, 4, 8, 16, 64)),
)
MASK_ALPHAS = (6, 12, 24, 48, 96)  # the page's sweep of the mask's Gaussian width
MASK_ALPHA_GRID = tuple(2 ** (k / 4) for k in range(8, 41))  # 4 to 1024 by quarter octaves
MASK_FAST_SAMPLE_WORD_MULTS = 300  # a sampler at 100 ns a coordinate, for the sweep
SAMPLER_RATES = {  # word multiplications a coordinate, for the sweeps of the mask's width
    "page": MASK_SAMPLE_WORD_MULTS,
    "karney": KARNEY_SAMPLE_WORD_MULTS,
    "fast": MASK_FAST_SAMPLE_WORD_MULTS,
    "free": 0,
}
KARNEY_MSAMPLES_PER_S = (2.109, 3.502)  # Karney's RandomLib sampler, million a second (Table 1)
# The least Pasta rows at the masked bound 2^42.2 from Akita's Euclidean estimator, 128 quantum
# bits at 2^22 columns: `pasta_rank 128 4194304 42.2` in the estimator checkout (the zero-knowledge
# note's §5.5); 356 at 2^42.6 and 366 at 2^43.2.
NOTE_MASKED_ROWS = 349
HLS18_CYCLES_PER_SAMPLE = (27672 / 1024, 47576 / 1024)  # without and with randomness, at 3.5 GHz
HLS18_GHZ = 3.5
DOUBLE_MANTISSA_BITS = 53


def rounded_gaussian_log_divergence(alpha=MASK_ALPHA, order=2):
    """log2 of (the Rényi divergence − 1) between the fold's mask as a rounded Gaussian with
    Sheppard's correction and the discrete Gaussian the proof assumes, over N coordinates
    (Jeudy, ePrint 2026/2583, Theorem 3.1)."""
    return math.log2(73 * order) + MASK_LOG_N - math.log2(33177600) - 8 * mask_log_sigma(alpha)


def double_undecided_log(alpha=MASK_ALPHA):
    """log2 of the fraction of coordinates that double-precision Box-Muller leaves within its
    error of a half-integer, 2 τσ 2^-53, the worst case over the tail."""
    return 1 + math.log2(MASK_TAIL) + mask_log_sigma(alpha) - DOUBLE_MANTISSA_BITS


KISHU_ZK_ALPHA = {}  # per application, the width that minimises Kishu's zk transaction (--figures)


def kishu_zk_optimum(app, count=1, sample=MASK_SAMPLE_WORD_MULTS):
    """The α on the grid at which Kishu's zero-knowledge transaction is least, with the row
    and its work there."""
    return min(
        ((a, *kishu_zk_best(app, a, sample, count)) for a in MASK_ALPHA_GRID),
        key=lambda t: t[2],
    )


def sig(x, n=2):
    """`x` to `n` significant figures, with thousands separators."""
    if x == 0:
        return "0"
    d = n - 1 - math.floor(math.log10(abs(x)))
    return f"{round(x, d):,.{max(d, 0)}f}"


def secs(work, n=3):
    return sig(work / RATE_PER_S, n)


def millis(work, n=3):
    return sig(work / WORD_MULTS_PER_MS, n)


def minutes(work):
    return sig(work / RATE_PER_S / 60, 3)


def sci(x):
    """`x` as the text writes word multiplications: 7.5e7."""
    e = math.floor(math.log10(x))
    m = round(x / 10**e, 1)
    if m >= 10:
        m, e = m / 10, e + 1
    return f"{m:g}e{e}"


def auto(v, n):
    """Three significant figures from 100 up, two below, unless `n` is given."""
    return n or (3 if v >= 100 else 2)


def kb(x, n=None):
    """Bytes in units of 1000, written kbytes, since KB is read as either 1000 or 1024 bytes."""
    return sig(x / 1000, auto(x / 1000, n)) + " kbytes"


def mb(x, n=2):
    return sig(x / 1e6, n) + " Mbytes"


def mil(x, n=None):
    """`x` in millions, the number alone."""
    return sig(x / 1e6, auto(x / 1e6, n))


def millions(x, n=None):
    return f"{mil(x, n)} million" if x >= 1e5 else f"{sig(x / 1e3, auto(x / 1e3, n))} thousand"


def fmt(x):
    return f"{x:,}"


FIGURES = {}


def fig(name, value):
    assert name not in FIGURES, name
    FIGURES[name] = str(value)


def tex_pow2(exponent):
    """A power of two as a LaTeX math span, for a figure that stands in the prose as a formula;
    a marker never sits inside a math span, so the figure carries the whole span."""
    return f"$2^{{{exponent}}}$"


CLAIMS = {}  # name -> (text, holds): wording the figures cannot carry, checked against the model


def claim(name, text, holds):
    """A qualitative statement that the model checks. The sentence it guards sits in a prose
    file between `<!--claim:name:hash-->` and `<!--/claim-->`, the hash a digest of this text,
    so that rewording the claim stales the marker until the sentence has been looked at."""
    assert name not in CLAIMS, f"two claims named {name}"
    CLAIMS[name] = (text, bool(holds))


def define_figures():
    """The figures and claims, paragraph by paragraph; the locals stay out of the module."""
    # The application costs, in each arithmetization's unit (the Transaction prover paragraph).
    APP = APPLICATIONS
    fig("app_recovery_pasta_poseidon", sig(APP["recovery"]["pasta"]["poseidon"]))
    fig("app_recovery_pasta_blake3", millions(APP["recovery"]["pasta"]["blake3"], 3))
    fig("app_recovery_goldilocks_poseidon", mil(APP["recovery"]["goldilocks"]["poseidon"], 3))
    fig("app_recovery_goldilocks_blake3", mil(APP["recovery"]["goldilocks"]["blake3"], 3))
    fig("app_recovery_fp128_poseidon", mil(APP["recovery"]["fp128"]["poseidon"], 3))
    fig("app_recovery_fp128_blake3", mil(APP["recovery"]["fp128"]["blake3"], 3))
    fig("recovery_mult_goldilocks", fmt(RECOVERY_MULT["goldilocks"]))
    fig("recovery_mult_fp128", fmt(RECOVERY_MULT["fp128"]))
    fig("bitz_gate_bits", BITZ_GATE_BITS)
    fig("bits_per_value", BITS_PER_VALUE)
    fig("digits_q64", DIGITS["pasta_q64"])
    fig("poseidon_ragu_gates", POSEIDON_RAGU_GATES)
    fig("mask_attempts", sig(MASK_ATTEMPTS))
    fig("mask_sample_word_mults", MASK_SAMPLE_WORD_MULTS)
    fig("app_recovery_boolean", f"{sig(APP['recovery']['boolean']['blake3'] / 1e9, 3)} billion")
    fig("app_recovery_bitz", millions(APP["recovery"]["bitz"]["blake3"]))
    for a in KISHU_ARITHS:
        fig(f"app_recovery_kishu_{kishu_route(a)}", millions(APP["recovery"][a]["blake3"]))
        recovery_piop_ = recovery_piop(kishu_route(a))
        fig(
            f"piop_recovery_kishu_{kishu_route(a)}_s",
            secs(piop_word_mults(recovery_piop_) - piop_range_word_mults(recovery_piop_)),
        )
        fig(f"range_recovery_kishu_{kishu_route(a)}_s", secs(piop_range_word_mults(recovery_piop_)))
    fig("mult_limbs_digits", fmt(MULT_ROUTES["limbs"][0]))
    fig("mult_limbs_terms", MULT_LIMBS_TERMS)
    fig("mult_fingerprint_digits", MULT_FINGERPRINT_DIGITS)
    fig("value_digits", VALUE_DIGITS)
    fig("mult_carry_digits", word_digits(MULT_CARRY_BITS))
    fig("column_sum_digits", word_digits(COLUMN_SUM_BITS))
    fig("sinsemilla_chunk_digits", fmt(SINSEMILLA_CHUNK_DIGITS_KISHU))
    fig("sinsemilla_committed_products", SINSEMILLA_COMMITTED_PRODUCTS)
    fig("sinsemilla_cross_products", SINSEMILLA_CROSS_PRODUCTS)
    fig("mult_coefficients", MULT_COEFFICIENTS)
    fig("mult_carry_bits", MULT_CARRY_BITS)
    fig("fingerprint_instances", FINGERPRINT_INSTANCES)
    fig("column_sum_bits", COLUMN_SUM_BITS)
    fig("fingerprint_step_digits_21", sig(fingerprint_step_digits(21), 3))
    fig("blake2b_bits_kishu", fmt(BLAKE2B_BITS_KISHU))
    fig("blake2b_piop_terms", fmt(BLAKE2B_PIOP[0]))
    fig("constraint_term_mults", sig(CONSTRAINT_TERM_WORD_MULTS))
    fig("nonzero_small_mults", NONZERO_SMALL_WORD_MULTS)
    fig("nonzero_field_mults", NONZERO_FIELD_WORD_MULTS)
    per_digit_default = (
        ajtai_per_coefficient(
            "pasta_q64",
            log_n=math.log2(accumulator_coefficients("kishu", 21, 1)),
            digit_max=DIGIT_MAX["kishu"],
        )
        / DIGITS["pasta_q64"]
        + BOOL_CHECK["sumcheck"][0]
    )
    blake3_64b = (BLAKE3_BITS + 8 * RANGE_CHECK_DIGITS) * per_digit_default + piop_word_mults(
        piop_sum((1, BLAKE3_PIOP), (8, RANGE_CHECK_PIOP))
    )
    poseidon_64b = Q64_POSEIDON_MULTS * Q64_DIGITS * per_digit_default + piop_word_mults(
        POSEIDON_Q64_PIOP
    )
    fig("blake3_64b_mults", sig(blake3_64b))
    fig("poseidon_64b_mults", sig(poseidon_64b))
    fig("hash_64b_within_pct", round(100 * abs(blake3_64b / poseidon_64b - 1)))
    claim(
        "hash_within_quarter",
        "with commitments and constraints charged, BLAKE3 and Poseidon over the 64-bit field are within a quarter of each other per 64 bytes absorbed in Kishu's merge",
        abs(blake3_64b / poseidon_64b - 1) < 0.25,
    )
    fig("blake3_piop_terms", fmt(BLAKE3_PIOP[0]))
    fig("blake3_piop_nonzeros", fmt(BLAKE3_PIOP[1]))
    fig("poseidon_q64_piop_nonzeros", fmt(POSEIDON_Q64_PIOP[2]))
    fig("app_path_pasta_poseidon", sig(APP["path"]["pasta"]["poseidon"]))
    fig("app_path_goldilocks_poseidon", sig(APP["path"]["goldilocks"]["poseidon"], 3))
    fig("app_path_pasta_blake3", sig(APP["path"]["pasta"]["blake3"], 3))
    fig("app_path_boolean", sig(APP["path"]["boolean"]["blake3"]))
    fig("app_path_bitz", sig(APP["path"]["bitz"]["blake3"], 3))
    claim(
        "path_blake3_any_field",
        "a Merkle path costs the same gates in any prime field with BLAKE3",
        APP["path"]["pasta"]["blake3"]
        == APP["path"]["goldilocks"]["blake3"]
        == APP["path"]["fp128"]["blake3"],
    )
    claim(
        "path_bits_digits_equal",
        "a Merkle path costs the same in bits for BitZ and in digits for Kishu",
        all(APP["path"]["bitz"]["blake3"] == APP["path"][a]["blake3"] for a in KISHU_ARITHS),
    )
    claim(
        "path_gold_fp128_equal",
        "the recovery circuit's Goldilocks and 128-bit Poseidon paths cost the same gates",
        APP["path"]["goldilocks"]["poseidon"] == APP["path"]["fp128"]["poseidon"],
    )
    fig(
        "ands_per_pasta_gate",
        sig(APP["recovery"]["boolean"]["blake3"] / APP["recovery"]["pasta"]["blake3"], 3),
    )
    fig("bool_mult_ands", sig((1 + BOOL_REDUCTION) * mult_ands(255)))

    # The hardware wallet's part of the Recovery Statement as applications: the device's own
    # statement, and a leanSPHINCS verifier with each of three hashes (the Transaction prover
    # section).
    fig("bits_akita_per_bit", sig(bits_akita_per_bit))
    fig("app_qk_gates", sig(APP["qk"]["pasta"]["blake3"], 3))
    fig("app_qk_boolean", sig(APP["qk"]["boolean"]["blake3"], 3))
    fig("app_qk_bits", sig(APP["qk"][KISHU_ARITHS[0]]["blake3"], 3))
    fig("leansphincs_keccak_calls", LEANSPHINCS_VERIFY["keccak"])
    fig("leansphincs_blake2s_calls", LEANSPHINCS_VERIFY["blake2s"])
    fig("leansphincs_blake3_calls", LEANSPHINCS_VERIFY["blake3"])
    fig("leansphincs_sig_bytes", fmt(LEANSPHINCS_SIG_BYTES))
    fig("leansphincs_ethereum_perms", LEANSPHINCS_ETHEREUM_PERMS)
    # The CAPSS page: the paper's figures, and the Kishu estimates at the model's rates.
    fig("capss_short_bytes_min", fmt(min(CAPSS_BYTES.values())))
    fig("capss_fast_bytes_max", fmt(max(CAPSS_BYTES.values())))
    fig("capss_r1cs_min", fmt(min(CAPSS_R1CS.values())))
    fig("capss_r1cs_max", fmt(max(CAPSS_R1CS.values())))
    fig("capss_anemoi_default_bytes", fmt(CAPSS_BYTES["anemoi3_default"]))
    fig("capss_anemoi_default_r1cs", fmt(CAPSS_R1CS["anemoi3_default"]))
    fig("capss_poseidon_default_bytes", fmt(CAPSS_BYTES["poseidon3_default"]))
    fig("capss_poseidon_default_r1cs", fmt(CAPSS_R1CS["poseidon3_default"]))
    fig("capss_verify_calls", CAPSS_ANEMOI_CALLS["verify"])
    fig("capss_sign_calls", sig(CAPSS_ANEMOI_CALLS["sign"], 3))
    fig("capss_poseidon_verify_calls", CAPSS_POSEIDON_CALLS["verify"])
    fig("capss_poseidon_sign_calls", sig(CAPSS_POSEIDON_CALLS["sign"], 2))
    fig("capss_goldilocks_bytes", fmt(CAPSS_GOLDILOCKS["bytes"]))
    fig("capss_goldilocks_sign_ms", CAPSS_GOLDILOCKS["sign_ms"])
    fig("capss_goldilocks_verify_ms", CAPSS_GOLDILOCKS["verify_ms"])
    fig("capss_goldilocks_r1cs_min", fmt(CAPSS_GOLDILOCKS_R1CS[0]))
    fig("capss_goldilocks_r1cs_max", fmt(CAPSS_GOLDILOCKS_R1CS[1]))
    fig("capss_bn254_sign_ms", fmt(CAPSS_BN254_SIGN_MS))
    fig("capss_field_factor", CAPSS_FIELD_FACTOR)
    fig("capss_kishu_digits_est", millions(CAPSS_GOLDILOCKS_R1CS[1] * Q64_DIGITS, 2))
    capss_verify_64 = CAPSS_POSEIDON_CALLS["verify"] * CAPSS_FIELD_FACTOR
    fig(
        "capss_kishu_poseidon_digits_est",
        millions(capss_verify_64 * Q64_POSEIDON_MULTS * Q64_DIGITS, 3),
    )
    capss_sign_64 = CAPSS_POSEIDON_CALLS["sign"] * CAPSS_FIELD_FACTOR
    fig("capss_kishu_poseidon_sign_calls", sig(capss_sign_64, 2))
    fig(
        "capss_device_sign_s_est",
        sig(capss_sign_64 * Q64_POSEIDON_MULTS / DEVICE_WORD_MULTS_PER_S["mcu"], 2),
    )
    fig("keccak_bits", sig(KECCAK_BITS, 3))
    fig("blake2s_bits", sig(BLAKE2S_BITS, 3))
    keccak_kishu = APP["leansphincs_keccak"][KISHU_ARITHS[0]]["blake3"]
    blake2s_kishu = APP["leansphincs_blake2s"][KISHU_ARITHS[0]]["blake3"]
    blake3_kishu = APP["leansphincs_blake3"][KISHU_ARITHS[0]]["blake3"]
    fig("app_leansphincs_keccak_kishu", millions(keccak_kishu, 3))
    fig("app_leansphincs_blake2s_kishu", millions(blake2s_kishu, 3))
    fig("app_leansphincs_blake3_kishu", millions(blake3_kishu, 3))
    fig("leansphincs_keccak_over_blake2s", sig(keccak_kishu / blake2s_kishu))
    fig("leansphincs_blake3_of_blake2s_pct", round(100 * blake3_kishu / blake2s_kishu))
    claim(
        "leansphincs_blake3_cheaper",
        "the leanSPHINCS verifier with BLAKE3 costs about seven tenths of the one with BLAKE2s in Kishu's digits",
        0.65 <= blake3_kishu / blake2s_kishu <= 0.75,
    )
    fig(
        "leansphincs_keccak_over_blake2s_boolean",
        sig(
            APP["leansphincs_keccak"]["boolean"]["blake3"]
            / APP["leansphincs_blake2s"]["boolean"]["blake3"]
        ),
    )
    claim(
        "leansphincs_keccak_dearer",
        "the leanSPHINCS verifier with Keccak-256 costs between five and eight times the one with BLAKE2s in Kishu's digits",
        5 <= keccak_kishu / blake2s_kishu <= 8,
    )
    for app in ("qk", "leansphincs_blake2s", "leansphincs_keccak", "leansphincs_blake3"):
        p, w = kishu_best(app, zk=True)
        fig(f"tx_{app}_kishu_zk_s", secs(w))
        fig(f"tx_{app}_kishu_zk_rank", p["rank"])
        if app == "qk":
            merges = tx_steps(p, app, "poseidon") * p["accumulation_prover"]
            fig("tx_qk_kishu_zk_merges_pct", round(100 * merges / w))
            fig("tx_qk_kishu_zk_fold_pct", round(100 * app_fold(p, app) / w))
            claim(
                "qk_merge_and_fold",
                "the merge and the masking fold are over nine tenths of Kishu's zero-knowledge transaction for the device's statement alone",
                (merges + app_fold(p, app)) / w > 0.9,
            )
            qk_fold = app_fold(p, app)

    # The wallet's own share of the device statement with the host proving the handoff (the
    # constants' comment): its digits, its online and idle work, the response's size, and the
    # times on the assumed devices and link.
    leaf = APP["qk"][KISHU_ARITHS[0]]["blake3"]
    # The chapter's figures are at the page's default floor; the other floor's padding is quoted.
    padding = HIDING_PADDING_BITS[DEFAULT_FLOOR]
    sumcheck_rounds = math.ceil(math.log2(leaf + padding))
    mask_elements = 2 * sumcheck_rounds * (SUMCHECK_MASK_DEGREE + 1)
    # The device's vector is the leaf's bits, the padding bits, and the sum-check mask
    # elements, F_q values in the widest digits that keep its masked matrix at the padding
    # sweep's rows, judged by the vector's exact ℓ2 norm rather than DIGIT_MAX √N: tribits at
    # the 128-bit floor and balanced dibits at 147, where 33 digits in {-2, ..., 1} hold a
    # signed residue of q (32 fall short of 2^63). The range check's products beyond one a
    # digit join the device's online work.
    element_widths = (  # digits a value, the digit's bits
        (Q64_DIGITS, 3),
        (Q64_BITS // 2 + 1, 2),
        (Q64_BITS, 1),
    )

    def device_vector(floor):
        """The device vector's digits, the log of its ℓ2 norm, its mask elements' digits and
        their bits, and its matrix's cost a digit and rows at `floor`."""
        pad = HIDING_PADDING_BITS[floor]
        for element_digits, digit_bits in element_widths:
            bound = 1 if digit_bits == 1 else 2 ** (digit_bits - 1)
            digits = leaf + pad + mask_elements * element_digits
            log_l2 = math.log2(leaf + pad + mask_elements * element_digits * bound**2) / 2
            cost, rank_, degree_, _ = accumulation_matrix(
                "pasta_q64", floor, masked_log_beta_inf_l2(log_l2), math.log2(digits)
            )
            if rank_ * degree_ == HIDING_PADDING_SWEEP_ROWS:
                return digits, log_l2, element_digits, digit_bits, cost, rank_ * degree_
        raise ValueError(
            f"no mask-element width keeps the device's matrix at the sweep's rows at {floor}"
        )

    device_digits, device_log_l2, element_digits, element_bits, matrix_cost, _ = device_vector(
        DEFAULT_FLOOR
    )
    device_rows = {floor: device_vector(floor)[5] for floor in FLOORS}
    element_bits_by_floor = {floor: device_vector(floor)[3] for floor in FLOORS}
    # The leaf is committed under the masked matrix for the device's own vector.
    masked_digit = matrix_cost * WORD_MULTS["pasta_q64"]
    element_range = mask_elements * element_digits * (RANGE_PRODUCTS[element_bits] - 1)
    device_online = (
        device_digits * (masked_digit + BOOL_CHECK["sumcheck"][0])
        + piop_word_mults(BLAKE3_PIOP)
        + piop_word_mults((0, 0, 0, element_range))
        + device_digits
    )
    device_idle = MASK_ATTEMPTS * device_digits * (MASK_SAMPLE_WORD_MULTS + masked_digit)
    device_log_sigma = math.log2(MASK_ALPHA) + math.log2(MASK_CHALLENGE_L1) + device_log_l2
    z_bits = math.ceil(math.log2(MASK_TAIL) + device_log_sigma)
    z_bytes = device_digits * z_bits / 8
    fig("qk_sumcheck_mask_elements", mask_elements)
    fig("qk_device_element_digits", element_digits)
    fig("qk_device_element_digits_128", device_vector(128)[2])
    claim(
        "device_element_widths",
        "the device's sum-check mask elements are balanced dibits at the 147-bit floor and tribits at the 128-bit floor",
        element_bits_by_floor == {128: 3, 147: 2},
    )
    fig("hiding_padding_bits", fmt(padding))
    fig("hiding_padding_bits_128", fmt(HIDING_PADDING_BITS[128]))
    # The device's masked matrix at each floor's padding, and the note's leftover-hash padding
    # at its rows.
    statistical_padding = device_rows[DEFAULT_FLOOR] * 64 + 256
    fig("qk_device_matrix_rows", fmt(device_rows[DEFAULT_FLOOR]))
    fig("hiding_padding_attack_bits", round(HIDING_PADDING_SWEEP[padding]))
    fig("hiding_padding_attack_bits_128", round(HIDING_PADDING_SWEEP[HIDING_PADDING_BITS[128]]))
    fig("hiding_padding_attack_bits_1385", round(HIDING_PADDING_ATTACK_BITS[1385]))
    claim(
        "hiding_padding_secure",
        "the device's matrix has the sweep's 1,024 rows at both floors, where each floor's padding is the least on the grid whose cheapest attack reaches the floor, the grid's previous point falling short; at the note's 1,385 rows 5,000 bits reach the 128-bit floor alone, and at 2,048 rows not even that",
        all(rows == HIDING_PADDING_SWEEP_ROWS for rows in device_rows.values())
        and all(
            HIDING_PADDING_SWEEP[HIDING_PADDING_BITS[f]] >= f
            and HIDING_PADDING_SWEEP[HIDING_PADDING_BITS[f] - 50] < f
            for f in FLOORS
        )
        and 128 <= HIDING_PADDING_ATTACK_BITS[1385] < max(FLOORS)
        and HIDING_PADDING_ATTACK_BITS[2048] < 128,
    )
    fig("hiding_padding_statistical_kbits", round(statistical_padding / 1000))
    fig("hiding_padding_statistical_over_statement", sig(statistical_padding / leaf))
    fig("qk_device_digits", sig(device_digits, 3))
    fig("qk_device_online_ms", millis(device_online))
    fig("qk_device_idle_ms", millis(device_idle))
    fig("qk_device_z_bits", z_bits)
    fig("qk_device_z_kbytes", kb(z_bytes))
    # The witness packed at its digits' widths: the leaf's and the padding's bits, and the mask
    # elements' digits at their bits each.
    fig(
        "qk_device_witness_kbytes",
        kb((leaf + padding + mask_elements * element_digits * element_bits) / 8),
    )
    fig("device_mcu_rate", f"{sig(DEVICE_WORD_MULTS_PER_S['mcu'] / 1e6, 1)} million")
    fig("device_se_rate", f"{sig(DEVICE_WORD_MULTS_PER_S['secure_element'] / 1e6, 1)} million")
    fig("qk_device_mcu_s", sig(device_online / DEVICE_WORD_MULTS_PER_S["mcu"]))
    fig(
        "qk_device_secure_element_s", sig(device_online / DEVICE_WORD_MULTS_PER_S["secure_element"])
    )
    fig("device_link_kbytes_s", round(DEVICE_LINK_BYTES_PER_S["measured"] / 1000))
    fig("qk_device_link_s", sig(z_bytes / DEVICE_LINK_BYTES_PER_S["measured"]))
    fig("qk_device_link_pipelined_s", sig(z_bytes / DEVICE_LINK_BYTES_PER_S["pipelined"]))
    claim(
        "qk_device_share_small",
        "with the host proving the handoff, the wallet's online work for the device statement is under a tenth of the handoff fold the measure charges the user",
        device_online < qk_fold / 10,
    )

    # For the hardware wallets page: the response's information-content floor (the leaf alone,
    # no padding and no masking elements), a succinct Kishu proof of the leaf at the least rank
    # that holds it (one circuit, the opening at the planner's floor), the signature sizes, and
    # the loss of the collision-resistance reduction for the signature of knowledge.
    floor_log_sigma = math.log2(MASK_ALPHA) + math.log2(MASK_CHALLENGE_L1) + math.log2(leaf) / 2
    z_floor_bytes = leaf * math.ceil(math.log2(MASK_TAIL) + floor_log_sigma) / 8
    min_rank = math.ceil(math.log2(leaf))
    groups = STAGES + 1
    succinct = (
        akita_bytes("goldilocks", groups - 1, min_rank - math.log2(DIGITS["goldilocks"]))
        + groups * 128
        + 2 * groups * 32
        + 4
        + CLAIM_BYTES["kishu"]
        + BOOL_CHECK["sumcheck"][1]
    )
    fig("qk_z_floor_kbytes", kb(z_floor_bytes))
    fig("qk_min_rank", min_rank)
    fig("qk_succinct_proof_kbytes", kb(succinct))
    fig("qr_fragment_bytes", QR_FRAGMENT_BYTES)
    fig("qr_frames_per_s", QR_FRAMES_PER_S)
    fig("qr_kbytes_per_s", sig(QR_FRAGMENT_BYTES * QR_FRAMES_PER_S / 1000, 1))
    fig("qk_qr_current_s", sig(z_bytes / (QR_FRAGMENT_BYTES * QR_FRAMES_PER_S)))
    fig("qr_dense_fragment_bytes", QR_DENSE_FRAGMENT_BYTES)
    fig("qk_qr_dense_s", sig(z_bytes / (QR_DENSE_FRAGMENT_BYTES * QR_FRAMES_PER_S)))
    fig("qr_max_fragment_bytes", fmt(QR_MAX_FRAGMENT_BYTES))
    fig("qk_qr_max_s", sig(z_bytes / (QR_MAX_FRAGMENT_BYTES * QR_FRAMES_PER_S)))
    claim(
        "qk_qr_channel_too_big",
        "the leaf's masked response with no padding and no masking elements, and a succinct proof of the leaf, are each at least three times the largest leanSPHINCS signature",
        min(z_floor_bytes, succinct) >= 3 * LEANSPHINCS_ETHEREUM_BYTES,
    )
    fig("leansphincs_layered_sig_bytes", fmt(LEANSPHINCS_LAYERED_SIG_BYTES))
    fig("leansphincs_layered_keccak_calls", LEANSPHINCS_LAYERED_VERIFY["keccak"])
    fig("leansphincs_layered_blake2s_calls", LEANSPHINCS_LAYERED_VERIFY["blake2s"])
    fig("leansphincs_ethereum_bytes", fmt(LEANSPHINCS_ETHEREUM_BYTES))
    fig("leansphincs_grind", fmt(LEANSPHINCS_GRIND))
    fig("leansphincs_lifetime", fmt(LEANSPHINCS_LIFETIME))
    fig("leansphincs_grind_keccak_s", sig(LEANSPHINCS_GRIND / LEDGER_HASH_PER_S["keccak"]))
    fig("leansphincs_grind_blake2s_s", sig(LEANSPHINCS_GRIND / LEDGER_HASH_PER_S["blake2s"]))

    # Zoodles: its tree's nodes, hashes, roots and openings; its transaction in Kishu's digits
    # and the families' transaction provers, by spend authorization and for the Merkle-path
    # variant; and Tachyon's four tachyactions beside them.
    nodes = zoodles_nodes(ZOODLES_INPUTS, ZOODLES_OUTPUTS)
    fig("zoodles_nodes", len(nodes))
    fig("zoodles_blake3", sum(ZOODLES_NODES[n][0] for n in nodes))
    fig("zoodles_roots", sum(ZOODLES_NODES[n][1] for n in nodes))
    fig("zoodles_openings", sum(ZOODLES_NODES[n][2] for n in nodes))
    fig("zoodles_sighash_blake3", ZOODLES_SIGHASH_COMPRESSIONS)
    fig("zoodles_sighash_bytes", fmt(ZOODLES_SIGHASH_BYTES))
    # The digest's hashing against one step at the rank the signature transaction favours.
    p_sig, _ = kishu_best("zoodles_leansphincs_blake3", zk=True)
    claim(
        "zoodles_sighash_small",
        "the transaction digest's hashing is under a tenth of one step at the rank Kishu's signature transaction favours",
        hash_app_cost(p_sig["arith"], "blake3", ZOODLES_SIGHASH_COMPRESSIONS)
        < 0.1 * 2 ** p_sig["rank"],
    )
    fig(
        "zoodles_opening_kishu_digits",
        sig(zoodles_opening_cost("bits_pasta_fingerprint", "blake3"), 3),
    )
    # The Merkle-path variants carry only the figures the text quotes.
    zoodles_zk, zoodles_plain, zoodles_bitz_zk, zoodles_flock = {}, {}, {}, {}
    for app in (
        *(f"zoodles_{auth}" for auth in ZOODLES_AUTHS),
        *(f"zoodles_merkle_{auth}" for auth in ZOODLES_AUTHS),
    ):
        full = not app.startswith("zoodles_merkle")
        units = APP[app][KISHU_ARITHS[0]]["blake3"]
        digits = sum(units) if isinstance(units, list) else units
        if full or app == "zoodles_merkle_preimage":
            fig(f"app_{app}_kishu", millions(digits, 3) if digits >= 1e6 else sig(digits, 3))
        p, w = kishu_best(app)
        zoodles_plain[app] = w
        p, w_zk = kishu_best(app, zk=True)
        zoodles_zk[app] = w_zk
        fig(f"tx_{app}_kishu_zk_s", secs(w_zk))
        zoodles_bitz_zk[app] = best_for("bitz", app, zk=True)[1]
        zoodles_flock[app] = best_for("flock", app)[1]
        if not full:
            continue
        fig(f"tx_{app}_kishu_s", secs(w))
        fig(f"tx_{app}_kishu_zk_rank", p["rank"])
        fig(f"tx_{app}_kishu_zk_steps", tx_steps(p, app, "blake3"))
        fig(f"tx_{app}_bitz_zk_s", secs(zoodles_bitz_zk[app]))
        p, w = best_for("bits_akita", app, floor=128)
        fig(f"tx_{app}_bits_akita_s", secs(w))
        fig(f"tx_{app}_flock_s", secs(zoodles_flock[app]))
        p, w = best_for("goldilocks", app, "poseidon")
        fig(f"tx_{app}_goldilocks_s", secs(w))
    claim(
        "zoodles_preimage_quarter",
        "in Kishu with zero knowledge the Zoodles transaction by preimage costs under a quarter of the one by leanSPHINCS signature with BLAKE3",
        zoodles_zk["zoodles_preimage"] < zoodles_zk["zoodles_leansphincs_blake3"] / 4,
    )
    claim(
        "zoodles_merkle_paths_most",
        "the Merkle-path variant's two paths are more than half of its Kishu digits",
        2 * APP["path"]["bitz"]["blake3"]
        > APP["zoodles_merkle_preimage"][KISHU_ARITHS[0]]["blake3"] / 2,
    )
    p, tachyon4 = kishu_best("tachyon4")
    fig("tx_tachyon4_kishu_s", secs(tachyon4))
    p, tachyon4_zk = kishu_best("tachyon4", zk=True)
    fig("tx_tachyon4_kishu_zk_s", secs(tachyon4_zk))
    # The migrations (the Recovery from Tachyon page).
    kishu_limbs = "bits_pasta_limbs"
    fig("app_tachyon_recovery_kishu", millions(APP["tachyon_zoodles1"][kishu_limbs]["blake3"][0]))
    fig("app_tachyon_zoodles1_kishu", millions(sum(APP["tachyon_zoodles1"][kishu_limbs]["blake3"])))
    for app in MIGRATIONS:
        fig(f"tx_{app}_kishu_zk_s", secs(kishu_best(app, zk=True)[1]))
    p, tachyon4_bitz_zk = best_for("bitz", "tachyon4", zk=True)
    fig("tx_tachyon4_bitz_zk_s", secs(tachyon4_bitz_zk))
    p, tachyon4_flock = best_for("flock", "tachyon4")
    fig("tx_tachyon4_flock_s", secs(tachyon4_flock))
    fig("tachyon4_over_zoodles_flock", sig(tachyon4_flock / zoodles_flock["zoodles_preimage"], 2))
    p, w = best_for("pedersen", "tachyon4", "poseidon", floor=128)
    fig("tx_tachyon4_pedersen_s", secs(w))
    p, w = best_for("pedersen", "zoodles_merkle_preimage", "poseidon", floor=128)
    fig("tx_zoodles_merkle_pedersen_s", secs(w))
    fig(
        "zoodles_preimage_of_tachyon_pct",
        round(100 * zoodles_zk["zoodles_preimage"] / tachyon4_zk),
    )
    fig(
        "zoodles_merkle_of_tachyon_pct",
        round(100 * zoodles_zk["zoodles_merkle_preimage"] / tachyon4_zk),
    )
    for app, name_, name in (
        ("zoodles_preimage", "zoodles_preimage", "Zoodles by preimage"),
        ("zoodles_merkle_preimage", "zoodles_merkle", "the Merkle-path variant of Zoodles"),
    ):
        claim(
            f"{name_}_beats_tachyon",
            f"{name} costs less than Tachyon's four tachyactions on the transaction prover in Kishu, with and without zero knowledge, and in BitZ",
            zoodles_zk[app] < tachyon4_zk
            and zoodles_plain[app] < tachyon4
            and zoodles_bitz_zk[app] < tachyon4_bitz_zk,
        )
    # Zoodles' lineage step: the tree's size and the step, the bucket it replaces, the
    # families' figures, and the spend at the lineage's rank.
    fig("zoodles_bucket_coeffs", fmt(2**ZOODLES_BUCKET_LOG))
    fig("zoodles_bucket_digits", millions(ZOODLES_BUCKET_DIGITS, 3))
    fig("zoodles_epoch_blocks", fmt(ZOODLES_EPOCH_BLOCKS))
    fig("zoodles_epoch_days", sig(ZOODLES_EPOCH_BLOCKS * ZOODLES_BLOCK_SECONDS / 86400, 2))
    fig("zoodles_epoch_tachygrams", fmt(2**ZOODLES_EPOCH_LOG))
    fig("zoodles_epoch_per_block", fmt(2**ZOODLES_EPOCH_LOG // ZOODLES_EPOCH_BLOCKS))
    fig("zoodles_epoch_hashes", ZOODLES_EPOCH_LOG + 2)
    # The Zoodles page's packing in numbers: the nodes' digits by kind, and how many actions a
    # step holds beside the fee, each action a spend or an output with its merge.
    node_names = tachyon_nodes(2, 2)[:-2]
    node_digits = dict(zip(node_names, APP["zoodles_preimage"][KISHU_ARITHS[0]]["blake3"]))
    spend_digits = node_digits["SpendBind"] + node_digits["SpendAction"]
    output_digits = node_digits["OutputBind"] + node_digits["OutputAction"]
    fig("zoodles_spend_digits", fmt(spend_digits))
    fig("zoodles_output_digits", fmt(output_digits))
    fig("zoodles_merge_digits", fmt(node_digits["ActionMerge"]))
    fig("zoodles_fee_digits", fmt(node_digits["FeeFuse"]))
    sphincs_nodes = dict(
        zip(node_names, APP["zoodles_leansphincs_blake3"][KISHU_ARITHS[0]]["blake3"])
    )
    fig(
        "zoodles_leansphincs_blake3_spend_digits",
        millions(sphincs_nodes["SpendBind"] + sphincs_nodes["SpendAction"], 3),
    )
    action = (spend_digits + output_digits) / 2 + node_digits["ActionMerge"]
    # Actions in a step beside its merge and the fee node, at the zero-knowledge limb row's
    # capacity for the application at each rank.
    for rank in (17, 19, 21):
        row = pick("bits_q64", rank=rank, zk=True, route="limbs", floor=DEFAULT_FLOOR)
        fig(
            f"zoodles_actions_per_step_{rank}",
            int((row["step_units"] - node_digits["FeeFuse"]) // action),
        )
    # The epoch-set page's comparison of the bucketed table with the sorted tree, whose
    # exclusion proof is the path and the leaf, log2 m + 1 hashes.
    gaps = []
    for log_m in sorted({row[0] for row in BUCKET_TABLE_ROWS}):
        fig(f"tree_hashes_{log_m}", log_m + 1)
    for log_m, B in BUCKET_TABLE_ROWS:
        for lam in BUCKET_TABLE_LAMBDAS:
            fig(f"bucket_k{lam}_{log_m}_{B}", bucket_capacity(log_m, B, lam))
        hashes = bucket_proof_hashes(B, bucket_capacity(log_m, B, 64))
        fig(f"bucket_hashes_{log_m}_{B}", hashes)
        gaps.append(hashes - (log_m + 1))
    fig("bucket_tag_bits_20_16", bucket_tag_bits(20, 16, 64))
    fig(
        "bucket_tag_hashes_20_16",
        bucket_proof_hashes(16, bucket_capacity(20, 16, 64), bucket_tag_bits(20, 16, 64)),
    )
    fig("bucket_mu_20_16", 2**20 // 2**16)
    claim(
        "bucket_table_dearer",
        "in every row of the epoch-set page's table the bucketed table's exclusion proof takes at least ten more hashes than the sorted tree's",
        min(gaps) >= 10,
    )
    fig("app_zoodles_epoch_kishu", sig(APP["zoodles_epoch"][KISHU_ARITHS[0]]["blake3"], 3))
    claim(
        "zoodles_tree_under_bucket",
        "the sorted tree's lineage step is under a sixth of the bucket's digits in Kishu",
        6 * APP["zoodles_epoch"][KISHU_ARITHS[0]]["blake3"] < ZOODLES_BUCKET_DIGITS,
    )
    p, w = kishu_best("zoodles_epoch")
    fig("tx_zoodles_epoch_kishu_s", secs(w))
    fig("tx_zoodles_epoch_kishu_rank", p["rank"])
    lineage_rank = p["rank"]
    p, w = best_for("bitz", "zoodles_epoch")
    fig("tx_zoodles_epoch_bitz_s", secs(w))
    p, w = best_for("flock", "zoodles_epoch")
    fig("tx_zoodles_epoch_flock_s", secs(w))
    p, w = best_for("goldilocks", "zoodles_epoch", "poseidon")
    fig("tx_zoodles_epoch_goldilocks_s", secs(w))
    p, w = best_for("pedersen", "zoodles_epoch", "poseidon", floor=128)
    fig("tx_zoodles_epoch_pedersen_s", secs(w))
    spend, spend_w = kishu_best("zoodles_preimage", zk=True)
    p, w = kishu_best("zoodles_preimage", zk=True, rank=lineage_rank)
    fig("tx_zoodles_preimage_kishu_zk_lineage_rank_s", secs(w))
    claim(
        "zoodles_lineage_rank_is_spends",
        "the lineage step's best Kishu rank is the zero-knowledge spend's own, so the spend at the lineage's rank costs its least",
        lineage_rank == spend["rank"] and w == spend_w,
    )
    second_preimage = 1 - math.exp(-1)
    fig("sok_second_preimage_pct", round(100 * second_preimage))
    fig("sok_loss_factor", sig(2 / second_preimage))
    claim(
        "sok_loss_small",
        "the collision-resistance reduction for the signature of knowledge loses less than a factor of four",
        2 / second_preimage < 4,
    )

    # The recovery circuit per note on one core, at the default floor: each family's best row, as
    # the page's frontier shows it (the Transaction prover paragraph).
    checked_in = pick("pedersen", floor=128, rank=PEDERSEN_FUSE_RANK, E=4, binders=4, packing=False)
    p, w = kishu_best("recovery")
    fig("tx_recovery_kishu_route", p["route"])
    fig("tx_recovery_kishu_s", secs(w))
    fig("tx_recovery_kishu_rank", p["rank"])
    fig("tx_recovery_kishu_steps", tx_steps(p, "recovery", "poseidon"))
    p, w = best_for("bitz", "recovery")
    fig("tx_recovery_bitz_s", secs(w))
    fig("tx_recovery_bitz_rank", p["rank"])
    bitz_recovery_work = w
    claim(
        "bitz_recovery_one_step",
        "BitZ's best recovery row holds the circuit in one step",
        tx_steps(p, "recovery", "blake3") == 1,
    )
    bitz_recovery_bytes = p["bytes"]
    p, w = best_for("pasta_q64", "recovery", "poseidon", hashes="poseidon")
    fig("tx_recovery_q64_s", secs(w))
    fig("tx_recovery_q64_rank", p["rank"])
    p_blake3, w_blake3 = best_for("pasta_q64", "recovery", "blake3", hashes="blake3")
    fig("tx_recovery_q64_blake3_s", secs(w_blake3))
    fig("tx_recovery_q64_blake3_rank", p_blake3["rank"])
    claim(
        "q64_recovery_sumchecks",
        "the Pasta-claims row's recovery prover is nearly all the fold's sum-checks",
        tx_steps(p, "recovery", "poseidon") * (p["accumulation_prover"] - p["prover"]) > 0.8 * w,
    )
    p, w = best_for("goldilocks", "recovery", "poseidon", hashes="poseidon")
    fig("tx_recovery_goldilocks_s", secs(w))
    w = tx_work(checked_in, "recovery", "poseidon")
    fig("tx_recovery_pedersen_minutes", minutes(w))
    fig("tx_recovery_pedersen_steps", tx_steps(checked_in, "recovery", "poseidon"))
    tx_checks.append(
        dict(
            family="pedersen",
            label=checked_in["label"],
            app="recovery",
            policy="poseidon",
            count=1,
            transaction=w,
        )
    )
    p, w = best_for("pedersen", "recovery", "poseidon", floor=128)
    fig("tx_recovery_pedersen_best_minutes", minutes(w))
    fig("tx_recovery_pedersen_best_rank", p["rank"])
    fig("tx_recovery_pedersen_best_E", p["E"])
    p, w = kishu_best("recovery", zk=True)
    fig("tx_recovery_kishu_zk_route", p["route"])
    fig("tx_recovery_kishu_zk_s", secs(w))
    fig("tx_recovery_kishu_zk_rank", p["rank"])
    _, parts = kishu_zk_costs(p)
    # The masked bound's N at this row, for the per-digit rates the text quotes.
    recovery_log_n = math.log2(accumulator_coefficients("kishu", p["rank"], p["circuits"]))
    fig("tx_recovery_kishu_zk_sampling_s", secs(parts["sampling"]))
    fig("mask_sample_ns", sig(MASK_SAMPLE_NS, 2))
    fig("mask_sample_rng_ns", sig(MASK_SAMPLE_RNG_NS, 2))
    fig("mask_sample_chacha_ns", sig(MASK_SAMPLE_CHACHA_NS, 2))
    fig("mask_sample_chacha_rng_ns", sig(MASK_SAMPLE_CHACHA_RNG_NS, 2))

    # Where Kishu's zero-knowledge cost goes, and what moves it (the zero-knowledge section's
    # Kishu paragraphs): the fold's parts, the steps' part against the plain row's, the
    # per-digit commitment rate masked and plain; the sampler, the page's rounded Gaussian
    # against Karney's exact method and a 100 ns one; the sweep of the mask's width at the
    # page's sampler; the fold's amortisation over four recovery inputs; and the width that
    # minimises each application's zero-knowledge transaction at each sampler rate, against the
    # page's width.
    assert kishu_zk_best("recovery")[1] == w
    zk_steps = tx_steps(p, "recovery", "poseidon")
    zk_per_step = p["step_prover"] + p["accumulation_prover"] + p["route_step"]
    fig("tx_recovery_kishu_zk_fold_s", secs(p["fold"]))
    fig("tx_recovery_kishu_zk_masks_s", secs(parts["masks"]))
    fig("tx_recovery_kishu_zk_fold_merge_s", secs(parts["merge"]))
    fig("tx_recovery_kishu_zk_steps", zk_steps)
    fig("tx_recovery_kishu_zk_step_ms", millis(zk_per_step))
    fig("tx_recovery_kishu_zk_steps_s", secs(zk_steps * zk_per_step))
    fig("tx_recovery_kishu_zk_piop_ms", millis(PIOP_WORK["recovery"][p["arith"]]))
    plain, plain_w = kishu_best("recovery")
    plain_steps = tx_steps(plain, "recovery", "poseidon")
    plain_per_step = plain["step_prover"] + plain["accumulation_prover"] + plain["route_step"]
    fig("tx_recovery_kishu_steps_s", secs(plain_steps * plain_per_step))
    kishu_bits = DIGIT_MAX["kishu"]
    digit_mults = (
        ajtai_per_coefficient(
            "pasta_q64", False, DEFAULT_FLOOR, log_n=recovery_log_n, digit_max=kishu_bits
        )
        / DIGITS["pasta_q64"]
    )
    fig("kishu_digit_mults", sig(digit_mults, 3))
    fig("kishu_value_commit_mults", sig(VALUE_DIGITS * digit_mults, 3))
    fig(
        "kishu_digit_mults_masked",
        sig(
            ajtai_per_coefficient(
                "pasta_q64", True, DEFAULT_FLOOR, log_n=recovery_log_n, digit_max=kishu_bits
            )
            / DIGITS["pasta_q64"],
            3,
        ),
    )
    claim(
        "kishu_zk_steps_over_fold",
        "Kishu's zero-knowledge recovery spends more in its steps and merges than in the fold",
        zk_steps * zk_per_step > p["fold"],
    )
    claim(
        "kishu_zk_rank_below_plain",
        "Kishu's zero-knowledge optimum for the recovery circuit is at a lower rank than the plain row's, which is a single step",
        p["rank"] < plain["rank"] and plain_steps == 1,
    )
    fig("mask_alpha", MASK_ALPHA)
    fig("hls18_sample_ns_min", sig(HLS18_CYCLES_PER_SAMPLE[0] / HLS18_GHZ))
    fig("hls18_sample_ns_max", sig(HLS18_CYCLES_PER_SAMPLE[1] / HLS18_GHZ))
    fig("mask_rounded_divergence", tex_pow2(round(rounded_gaussian_log_divergence())))
    fig("mask_double_undecided", tex_pow2(round(double_undecided_log())))
    fig("mask_double_undecided_folds", tex_pow2(round(-(double_undecided_log() + MASK_LOG_N))))
    claim(
        "rounded_gaussian_negligible",
        "the rounded Gaussian's divergence from the discrete one is below 2^-128 over the fold's coordinates, and double precision leaves a fold's undecided coordinates at a fraction above 2^-16",
        rounded_gaussian_log_divergence() < -128 and double_undecided_log() + MASK_LOG_N > -16,
    )
    fig("mask_karney_sample_ns", round(KARNEY_SAMPLE_WORD_MULTS / RATE_PER_S * 1e9))
    fig("karney_ns_min", sig(1000 / KARNEY_MSAMPLES_PER_S[1]))
    fig("karney_ns_max", sig(1000 / KARNEY_MSAMPLES_PER_S[0]))
    q, wk = kishu_zk_best("recovery", MASK_ALPHA, KARNEY_SAMPLE_WORD_MULTS)
    fig("tx_recovery_kishu_zk_karney_s", secs(wk))
    fig("tx_recovery_kishu_zk_karney_rank", q["rank"])
    fig("mask_fast_sample_ns", round(MASK_FAST_SAMPLE_WORD_MULTS / RATE_PER_S * 1e9))
    q, wf = kishu_zk_best("recovery", MASK_ALPHA, MASK_FAST_SAMPLE_WORD_MULTS)
    fig("tx_recovery_kishu_zk_fast_s", secs(wf))
    fig("tx_recovery_kishu_zk_fast_rank", q["rank"])
    sweep = {}
    for a in MASK_ALPHAS:
        q, wa = kishu_zk_best("recovery", a)
        sweep[a] = wa
        q_log_n = math.log2(accumulator_coefficients("kishu", q["rank"], q["circuits"]))
        fig(f"mask_attempts_alpha{a}", sig(mask_attempts(a)))
        log_beta = masked_log_beta_inf(a, log_n=q_log_n, digit_max=kishu_bits)
        fig(f"mask_log_beta_alpha{a}", sig(log_beta, 3))
        _, m_rank, m_degree, _ = accumulation_matrix("pasta_q64", DEFAULT_FLOOR, log_beta, q_log_n)
        fig(f"mask_matrix_alpha{a}", f"{m_rank} × {fmt(m_degree)}")
        fig(f"mask_bits_alpha{a}", mask_coordinate_bits(a, log_n=q_log_n, digit_max=kishu_bits))
        fig(f"mask_length_alpha{a}", mask_length(a, log_n=q_log_n, digit_max=kishu_bits))
        fig(
            f"kishu_digit_mults_alpha{a}",
            sig(
                ajtai_per_coefficient("pasta_q64", True, DEFAULT_FLOOR, a, q_log_n, kishu_bits)
                / DIGITS["pasta_q64"],
                3,
            ),
        )
        fig(f"tx_recovery_kishu_zk_alpha{a}_s", secs(wa))
        fig(f"tx_recovery_kishu_zk_alpha{a}_rank", q["rank"])
    assert sweep[MASK_ALPHA] == w
    fig("kishu_zk_alpha_48_to_96_pct", sig(100 * (1 - sweep[96] / sweep[48])))
    claim(
        "kishu_zk_falls_with_alpha",
        "Kishu's zero-knowledge recovery falls at each doubling of α from 6 to 96",
        all(sweep[a] > sweep[2 * a] for a in (6, 12, 24, 48)),
    )
    # The widest and the narrowest masks the table's rows take, and the slices' thresholds on
    # the sweep's grid at the recovery row (the width paragraph).
    recovery_log_n = math.log2(accumulator_coefficients("kishu", p["rank"], p["circuits"]))
    fig(
        "mask_bits_alpha1024",
        mask_coordinate_bits(max(MASK_ALPHA_GRID), log_n=recovery_log_n, digit_max=kishu_bits),
    )
    nine = [
        a
        for a in MASK_ALPHA_GRID
        if mask_length(a, log_n=recovery_log_n, digit_max=kishu_bits) == 9
    ]
    fig("mask_nine_slices_alpha", sig(max(nine)))
    fig("mask_attempts_nine_slices", sig(mask_attempts(max(nine)), 3))
    fig(
        "mask_tenth_slice_alpha",
        sig(
            min(
                a
                for a in MASK_ALPHA_GRID
                if mask_length(a, log_n=recovery_log_n, digit_max=kishu_bits) >= 10
            )
        ),
    )
    q, w4 = kishu_best("recovery", zk=True, count=4)
    fig("tx_recovery4_kishu_zk_note_s", secs(w4 / 4))
    fig("tx_recovery4_kishu_zk_rank", q["rank"])

    # The minimum over the width is shallow: the widths on the grid within two percent of it.
    def band(app, n, sample):
        least = kishu_zk_optimum(app, n, sample)[2]
        close = [a for a in MASK_ALPHA_GRID if kishu_zk_best(app, a, sample, n)[1] < 1.02 * least]
        return min(close), max(close)

    excess, optima = {}, {}
    for name, sample in SAMPLER_RATES.items():
        worst = 0
        for app, n in PAGE_APPLICATIONS:
            a, q, wo = kishu_zk_optimum(app, n, sample)
            w_page = kishu_zk_best(app, MASK_ALPHA, sample, n)[1]
            if (
                app != "qk"
            ):  # the device's statement alone is one compression: its transaction is its merges, and its optimum is no transaction's
                optima[(name, app, n)] = a
                worst = max(worst, w_page / wo - 1)
            KISHU_ZK_ALPHA.setdefault(f"{app}:{n}", {})[name] = dict(
                alpha=round(a, 1), rank=q["rank"], zk_s=secs(wo), page_alpha_s=secs(w_page)
            )
        excess[name] = worst
    lo, hi = band("recovery", 1, MASK_SAMPLE_WORD_MULTS)
    fig("kishu_zk_alpha_recovery_band_min", sig(lo))
    fig("kishu_zk_alpha_grid_top", fmt(round(max(MASK_ALPHA_GRID))))
    fig("kishu_zk_alpha_page_excess_pct", sig(100 * excess["page"]))
    claim(
        "alpha_optimum_at_grid_top",
        "the transaction measure's least zero-knowledge work is at the top of the width grid for every transaction-sized application at every sampler rate, since the masked matrix does not move across the grid",
        all(a == max(MASK_ALPHA_GRID) for a in optima.values())
        and hi == max(MASK_ALPHA_GRID)
        and len({FIGURES[f"mask_matrix_alpha{a}"] for a in MASK_ALPHAS}) == 1,
    )
    claim(
        "alpha_page_excess",
        "the page's width keeps nine slices a coordinate and is within ten percent of the measure's least for every transaction-sized application at the page's sampler",
        mask_length(log_n=recovery_log_n, digit_max=kishu_bits) == 9 and excess["page"] < 0.10,
    )
    p, w = best_for("pasta_q64", "recovery", "poseidon", zk=True, hashes="poseidon")
    fig("tx_recovery_q64_zk_s", secs(w))
    fig("tx_recovery_q64_zk_rank", p["rank"])
    p, w = best_for("bitz", "recovery", zk=True)
    fig("tx_recovery_bitz_zk_s", secs(w))
    fig("tx_recovery_bitz_zk_more_kb", kb(p["bytes"] - bitz_recovery_bytes))
    claim(
        "bitz_recovery_zk_unchanged",
        "BitZ's recovery prover is unchanged with zero knowledge",
        abs(w / bitz_recovery_work - 1) < 0.01,
    )

    # Tachyon transactions (the Tachyon transactions paragraph). Over Pasta the nodes are the
    # measured circuits; over Goldilocks and in a Boolean circuit a node is many steps.
    for node, (gates, *_) in TACHYON_STEPS.items():
        if node != "Rerandomize":
            fig(f"tachyon_{node}_gates", fmt(gates))
    fig("tachyon_rank13_gates", fmt(gate_budget(13)))
    claim(
        "tachyon_nodes_fit_rank13",
        "every Tachyon node fits rank 13's circuit",
        all(g <= gate_budget(13) for g, *_ in TACHYON_STEPS.values()),
    )
    action_nodes = ("SpendBind", "SpendAction", "OutputBind", "OutputAction", "FeeFuse")
    gold_upper = [
        math.ceil(
            tachyon_node_cost("goldilocks", "poseidon", n, bits_as_mults=True) / gate_budget(17)
        )
        for n in action_nodes
    ]
    fig("tachyon_node_gold17_upper_min", min(gold_upper))
    fig("tachyon_node_gold17_upper_max", max(gold_upper))
    gold_steps = [
        math.ceil(tachyon_node_cost("goldilocks", "poseidon", n) / gate_budget(17))
        for n in action_nodes
    ]
    bool_steps = [
        math.ceil(tachyon_node_cost("boolean", "blake3", n) / BOOL_STEP_BITS) for n in action_nodes
    ]
    fig("tachyon_node_gold17_min", min(gold_steps))
    fig("tachyon_node_gold17_max", max(gold_steps))
    fig("tachyon_node_bool_min", min(bool_steps))
    fig("tachyon_node_bool_max", max(bool_steps))
    claim(
        "tachyon_bits_as_mults_more_steps",
        "pricing a Tachyon node's remaining gates as multiplications gives more Goldilocks steps than pricing them as bits, for every action node",
        all(u > s for u, s in zip(gold_upper, gold_steps)),
    )
    fig("tachyon2_nodes", len(tachyon_nodes(*TACHYON_TRANSACTIONS[2])))
    fig("tachyon2_pedersen13_steps", tx_steps(checked_in, "tachyon2", "poseidon"))
    claim(
        "tachyon2_rank13_packing",
        "at rank 13 no two action circuits of two tachyactions share a step and the merge rides with the fee step",
        tx_steps(checked_in, "tachyon2", "poseidon")
        == len(tachyon_nodes(*TACHYON_TRANSACTIONS[2])) - 1,
    )
    rank15 = best_for("pedersen", "tachyon2", "poseidon", rank=15, floor=128)[0]
    claim(
        "tachyon2_rank15_one_step",
        "at rank 15 every circuit of two tachyactions fits one step beside the two rerandomization fuses",
        tx_steps(rank15, "tachyon2", "poseidon") == 3,
    )
    w = tx_work(checked_in, "tachyon2", "poseidon")
    tx_checks.append(
        dict(
            family="pedersen",
            label=checked_in["label"],
            app="tachyon2",
            policy="poseidon",
            count=1,
            transaction=w,
        )
    )
    fig("tx_tachyon2_pedersen_s", secs(w))
    fig(
        "tx_tachyon2_tachyon_tree_s",
        secs(
            len(tachyon_nodes(*TACHYON_TRANSACTIONS[2]))
            * (checked_in["step_prover"] + checked_in["accumulation_prover"]),
            3,
        ),
    )
    p, w = best_for("pedersen", "tachyon2", "poseidon", rank=15, floor=128)
    fig("tx_tachyon2_pedersen15_s", secs(w))
    fig("tx_tachyon2_pedersen15_E", p["E"])
    fig("tx_tachyon2_pedersen15_steps", tx_steps(p, "tachyon2", "poseidon"))
    p, w = best_for("pasta_q64", "tachyon2", "poseidon", hashes="poseidon")
    fig("tx_tachyon2_q64_s", secs(w))
    fig("tx_tachyon2_q64_rank", p["rank"])
    p, w = best_for("bitz", "tachyon2")
    fig("tx_tachyon2_bitz_s", secs(w))
    fig("tx_tachyon2_bitz_rank", p["rank"])
    bitz_tachyon2_work = w
    p, w = kishu_best("tachyon2")
    fig("tx_tachyon2_kishu_route", p["route"])
    fig("tx_tachyon2_kishu_s", secs(w))
    fig("tx_tachyon2_kishu_rank", p["rank"])
    fig("tx_tachyon2_kishu_hash", HASH_LABEL[p["hashes"]][2:])
    p, w = best_for("goldilocks", "tachyon2", "poseidon", hashes="poseidon")
    fig("tx_tachyon2_goldilocks_s", secs(w))
    fig("tx_tachyon2_goldilocks_steps", tx_steps(p, "tachyon2", "poseidon"))
    p, w = best_for("flock", "tachyon2")
    fig("tx_tachyon2_f2_s", secs(w))
    fig("tx_tachyon2_f2_steps", tx_steps(p, "tachyon2", "blake3"))
    p, w = best_for("pasta_q64", "tachyon2", "poseidon", zk=True, hashes="poseidon")
    fig("tx_tachyon2_q64_zk_s", secs(w))
    p, w = kishu_best("tachyon2", zk=True)
    fig("tx_tachyon2_kishu_zk_s", secs(w))
    p, w = best_for("bitz", "tachyon2", zk=True)
    claim(
        "bitz_tachyon2_zk_unchanged",
        "BitZ's two-tachyaction prover is unchanged with zero knowledge",
        abs(w / bitz_tachyon2_work - 1) < 0.01,
    )
    w = tx_work(checked_in, "tachyon16", "poseidon")
    tx_checks.append(
        dict(
            family="pedersen",
            label=checked_in["label"],
            app="tachyon16",
            policy="poseidon",
            count=1,
            transaction=w,
        )
    )
    fig("tx_tachyon16_pedersen_s", secs(w))
    fig("tx_tachyon16_pedersen_steps", tx_steps(checked_in, "tachyon16", "poseidon"))
    p, w = best_for("pedersen", "tachyon16", "poseidon", rank=15, floor=128)
    fig("tx_tachyon16_pedersen15_s", secs(w))
    fig("tx_tachyon16_pedersen15_steps", tx_steps(p, "tachyon16", "poseidon"))
    fig(
        "tx_tachyon16_q64_s",
        secs(best_for("pasta_q64", "tachyon16", "poseidon", hashes="poseidon")[1]),
    )
    fig("tx_tachyon16_bitz_s", secs(best_for("bitz", "tachyon16")[1]))
    fig("tx_tachyon16_kishu_s", secs(kishu_best("tachyon16")[1]))
    fig(
        "tx_tachyon16_goldilocks_s",
        secs(best_for("goldilocks", "tachyon16", "poseidon", hashes="poseidon")[1]),
    )
    # Orchard's Halo 2 prover on the same machine with assembly, one thread (2026-11-14): two
    # actions and sixteen.
    HALO2_SECONDS = {2: 1.88, 16: 14.0}
    fig("halo2_2_s", HALO2_SECONDS[2])
    fig("halo2_16_s", sig(HALO2_SECONDS[16]))
    ratios = sorted(
        tx_work(checked_in, f"tachyon{n}", "poseidon") / RATE_PER_S / HALO2_SECONDS[n]
        for n in HALO2_SECONDS
    )
    fig("tachyon_over_halo2_min", sig(ratios[0]))
    fig("tachyon_over_halo2_max", sig(ratios[-1]))

    # The decider's ranges by family group (the axes list), in milliseconds over the rows shown
    # under either hash policy at the default floor.
    def decider_ms(families, hashes=None):
        """Pedersen-IPA and the binary groups are shown at the 128-bit floor alone."""
        return sorted(
            p["verify"] / WORD_MULTS_PER_MS
            for f in families
            for p in shown(
                f, "poseidon", floor=128 if f in ("pedersen", "bits_akita") else DEFAULT_FLOOR
            )
            if hashes is None or p["hashes"] == hashes
        )

    fast = decider_ms(("fp128", "goldilocks", "flock", "flock_rec", "bits_akita")) + decider_ms(
        (
            "whir",
            "whir_gold",
            "whir_hybrid",
            "whir_rec",
            "whir_gold_rec",
            "whir_hybrid_rec",
            "plonky3",
            "plonky3_rec",
        ),
        "blake3",
    )
    claim(
        "fast_deciders_under_10ms",
        "the 64-bit and 128-bit lattice rows, the binary-field families and the BLAKE3 hash-based deciders take under ten milliseconds",
        max(fast) < 10,
    )

    for name, families, hashes in (
        ("pasta", ("pasta", "pasta_q64", "pasta_sis", *KISHU, "bitz", "bitz_rec"), None),
        ("pedersen", ("pedersen",), None),
        ("whir_gold", ("whir_gold", "whir_gold_rec"), "poseidon"),
        ("whir_pasta", ("whir", "whir_rec"), "poseidon"),
    ):
        ms = decider_ms(families, hashes)
        fig(f"decider_{name}_ms_min", sig(ms[0], 3))
        fig(f"decider_{name}_ms_max", sig(ms[-1], 3))

    # The stage groups' support (the accumulation prover paragraph): Ragu's native stages'
    # values, and the bits they are in Kishu.
    fig("stage_values", fmt(STAGE_VALUES_TOTAL))
    fig("kishu_stage_digits", sig(STAGE_VALUES_TOTAL * STAGE_VALUE_COEFFICIENTS["kishu"], 2))
    # The least rank at which one circuit holds Kishu's merge, below which the batch is about
    # the merge's size whatever the rank.
    # The merge within one circuit, beside the application's.
    one_circuit = min(p["rank"] for p in shown("bits_q64", "blake3", zk=True) if p["circuits"] <= 2)
    fig("kishu_one_circuit_rank", one_circuit)
    zk_rows = {p["rank"]: p for p in shown("bits_q64", "blake3", zk=True, route="limbs")}
    flat = [zk_rows[r]["accumulation_prover"] for r in range(15, 20)]
    claim(
        "kishu_accumulation_flat_then_doubles",
        "Kishu's accumulation prover is within a tenth of flat from rank 15 to 19, and its accumulator doubles with each rank from the rank where one circuit holds the merge",
        max(flat) < 1.1 * min(flat)
        and all(
            abs(
                accumulator_coefficients("kishu", r + 1, zk_rows[r + 1]["circuits"])
                / accumulator_coefficients("kishu", r, zk_rows[r]["circuits"])
                - 2
            )
            < 0.05
            for r in range(one_circuit, max(zk_rows))
        ),
    )

    # Accumulator memory (the axes list).
    fig("memory_q64_rank17", mb(pick("pasta_q64", rank=17, hashes="poseidon")["memory"], 3))
    fig(
        "memory_kishu_rank21",
        mb(pick("bits_q64", rank=21, hashes="blake3", check="sumcheck", route="limbs")["memory"]),
    )
    fig(
        "memory_pedersen_rank13",
        mb(pick("pedersen", floor=128, rank=13, E=4, binders=4, packing=False)["memory"]),
    )
    fig(
        "memory_pedersen_rank13_3",
        mb(pick("pedersen", floor=128, rank=13, E=4, binders=4, packing=False)["memory"], 3),
    )

    # Peak fuse memory (the axes list): Kishu at rank 21 with and without zero knowledge, Akita
    # with Pasta claims at rank 17, and Pedersen-IPA at rank 13.
    kishu21 = dict(rank=21, hashes="blake3", check="sumcheck", route="limbs")
    fig("peak_kishu_rank21_zk", mb(pick("bits_q64", zk=True, **kishu21)["peak_memory"]))
    fig("peak_kishu_rank21", mb(pick("bits_q64", **kishu21)["peak_memory"]))
    fig("peak_q64_rank17", mb(pick("pasta_q64", rank=17, hashes="poseidon")["peak_memory"], 3))
    fig(
        "peak_pedersen_rank13",
        mb(pick("pedersen", floor=128, rank=13, E=4, binders=4, packing=False)["peak_memory"]),
    )
    fig("packed_digit_bits", PACKED_DIGIT_BITS - 1)

    # The circuit budget table: the rows of its body.
    def budget_row(b):
        fixed = (
            _model["packed"](_model["NATIVE_FIXED"], b["rank"]),
            _model["packed"](_model["NESTED_FIXED"], b["rank"]),
        )
        today = (len(_model["NATIVE_FIXED"]), len(_model["NESTED_FIXED"]))
        packed = "as today" if fixed == today else f"{fixed[0]}, {fixed[1]}"
        binders = "none fits" if b["binders"] is None else b["binders"]
        return (
            f'    <tr><td>{b["rank"]}</td><td class="num">{fmt(b["gates"])}</td><td class="num">{b["endoscalings"]}</td>'
            f'<td class="num">{binders}</td><td class="num">{packed}</td></tr>'
        )

    fig("budget_rows", "\n" + "\n".join(budget_row(b) for b in budget) + "\n  ")
    fig("fixed_native_count", len(_model["NATIVE_FIXED"]))
    fig("fixed_nested_count", len(_model["NESTED_FIXED"]))
    for side, fixed in (("native", "NATIVE_FIXED"), ("nested", "NESTED_FIXED")):
        for name, gates in _model[fixed].items():
            fig(f"fixed_{side}_{name}", fmt(gates))
    fig("step_gates_per_point", _model["STEP_GATES_PER_POINT"])
    fig("step_gates_overhead", _model["STEP_GATES_OVERHEAD"])
    fig(
        "endoscaling_step_gates",
        fmt(4 * _model["STEP_GATES_PER_POINT"] + _model["STEP_GATES_OVERHEAD"]),
    )
    fig("binder_gates_per_challenge", _model["BINDER_GATES_PER_CHALLENGE"])
    fig("binder_gates_overhead", _model["BINDER_GATES_OVERHEAD"])
    fig("challenges_bound", _model["CHALLENGES_BOUND"])
    fig("budget_gates_13", fmt(gate_budget(13)))
    fig("budget_constraints_13", fmt(4 * gate_budget(13)))
    for r in (14, 15):
        fig(f"packed_native_{r}", _model["packed"](_model["NATIVE_FIXED"], r))
        fig(f"packed_nested_{r}", _model["packed"](_model["NESTED_FIXED"], r))

    # Pedersen-IPA's checked-in configuration and the smallest proofs that fit (the Proof bytes
    # item, the Rank paragraph, and pasta-proof-size.md's budget paragraphs).
    ch = pick("pedersen", floor=128, rank=13, E=4, binders=4, packing=False)
    fig("pedersen_checked_in_bytes", fmt(ch["bytes"] + 4 * HEADER_ELEMENT_BYTES))
    fig("pedersen_checked_in_wire_bytes", fmt(ch["bytes"] + 4 * HEADER_ELEMENT_BYTES + 28))
    fig("pedersen_checked_in_h2_bytes", fmt(ch["bytes"] + 2 * HEADER_ELEMENT_BYTES))
    fig("pedersen_checked_in_h0_bytes", fmt(ch["bytes"]))
    claim(
        "rank14_adds_128_bytes",
        "rank 14 adds 128 bytes to the checked-in proof",
        pick("pedersen", floor=128, rank=14, E=4, binders=4, packing=False)["bytes"] - ch["bytes"]
        == 128,
    )
    least = {
        r: min(
            shown("pedersen", "poseidon", rank=r, floor=128),
            key=lambda p: (p["bytes"], p["prover"]),
        )
        for r in (14, 15, 16)
    }
    # The note compares these with the checked-in proof at a two-element header.
    fig("pedersen_least14_bytes", fmt(least[14]["bytes"] + 2 * HEADER_ELEMENT_BYTES))
    fig("pedersen_least15_bytes", fmt(least[15]["bytes"] + 2 * HEADER_ELEMENT_BYTES))
    fig("pedersen_least15_E", least[15]["E"])
    claim(
        "smallest_pedersen_proofs",
        "the smallest rank-14 proof has the fixed circuits packed, and the smallest rank-15 proof one binder and the fixed circuits packed",
        least[14]["packing"] and least[15]["packing"] and least[15]["binders"] == 1,
    )
    claim(
        "rank16_no_bytes_gain",
        "rank 16 gains no bytes over rank 15",
        least[16]["bytes"] >= least[15]["bytes"],
    )
    claim(
        "rank14_packed_beats_13",
        "rank 14 with the fixed circuits packed beats rank 13 on bytes, prover commitment work and atoms",
        any(
            p["bytes"] < ch["bytes"]
            and p["prover"] < ch["prover"]
            and p["accumulation"] < ch["accumulation"]
            for p in shown("pedersen", "poseidon", rank=14, packing=True, floor=128)
        ),
    )
    claim(
        "ranks_15_16_trade_prover",
        "ranks 15 and 16 buy bytes and atoms with prover commitment work",
        all(
            least[r]["bytes"] < least[14]["bytes"]
            and least[r]["accumulation"] < least[14]["accumulation"]
            and least[r]["prover"] > least[14]["prover"]
            for r in (15, 16)
        ),
    )
    fig("pedersen_rank14_E16_b1_bytes", fmt(size(19, 14, 1, 16, 16, 14, 2)[0]))
    fig("pedersen13_decider_ms", sig(ch["verify"] / WORD_MULTS_PER_MS, 3))
    fig("pedersen_per_coeff_13", sig(pedersen_per_coefficient(13)))
    fig("pedersen_per_coeff_14", sig(pedersen_per_coefficient(14)))
    for v in ("pasta", "pasta_q64", "fp128", "goldilocks"):
        fig(f"ajtai_per_coeff_{v}", sig(ajtai_per_coefficient(v)))
    fig("min_binders_14", min_binders(14))
    claim(
        "rank12_rows",
        "rank 12 has no Pedersen-IPA rows and no Akita rows under BLAKE3",
        not shown("pedersen", "poseidon", rank=12, floor=128)
        and not any(shown(v, rank=12, hashes="blake3") for v in DIGITS),
    )
    fig("bitz_max_rank", BITZ_RANKS[-1])
    fig("kishu_max_rank", FRONTEND_RANKS[-1])

    # Akita at rank 16 under the two hash policies (the Hashes paragraph), and rank 17 under
    # BLAKE3 (the Rank paragraph).
    VARIANTS = tuple(DIGITS)
    PASTA_VARIANTS = ("pasta_q64", "pasta_sis", "pasta")
    a16 = {(v, hp): pick(v, rank=16, hashes=hp) for v in VARIANTS for hp in HASH_POLICIES}
    Kg = STAGES + 1
    absorbed = [
        akita_absorbed_bytes(v, Kg, a16[(v, "blake3")]["circuits"], False) for v in VARIANTS
    ]
    fig("akita16_absorbed_kb_min", sig(min(absorbed) / 1000, 1))
    fig("akita16_absorbed_kb_max", sig(max(absorbed) / 1000, 1))
    fig("akita16_compressions_min", round(min(absorbed) / BLAKE3_BLOCK))
    fig("akita16_compressions_max", round(max(absorbed) / BLAKE3_BLOCK))
    atoms = [a16[(v, "poseidon")]["accumulation"] for v in VARIANTS]
    fig("akita16_atoms_min", min(atoms))
    fig("akita16_atoms_max", max(atoms))
    fig("fp128_16_poseidon_gates", millions(a16[("fp128", "poseidon")]["gates"]))
    fig("fp128_16_blake3_gates", millions(a16[("fp128", "blake3")]["gates"]))
    fig("q64_16_blake3_gates", millions(a16[("pasta_q64", "blake3")]["gates"]))
    claim(
        "blake3_rank16_small_fields_same",
        "Goldilocks and the 128-bit field have the same merge gates and circuits under BLAKE3 at rank 16",
        a16[("goldilocks", "blake3")]["gates"] == a16[("fp128", "blake3")]["gates"]
        and a16[("goldilocks", "blake3")]["circuits"] == a16[("fp128", "blake3")]["circuits"],
    )
    claim(
        "blake3_rank16_pasta_same",
        "the three Pasta variants have the same merge gates and circuits under BLAKE3 at rank 16 to within 5%",
        max(a16[(v, "blake3")]["gates"] for v in PASTA_VARIANTS)
        < 1.05 * min(a16[(v, "blake3")]["gates"] for v in PASTA_VARIANTS)
        and len({a16[(v, "blake3")]["circuits"] for v in PASTA_VARIANTS}) == 1,
    )
    fig("fp128_16_blake3_circuits", a16[("fp128", "blake3")]["circuits"])
    fig("q64_16_blake3_circuits", a16[("pasta_q64", "blake3")]["circuits"])
    fig("fp128_16_poseidon_circuits", a16[("fp128", "poseidon")]["circuits"])
    claim(
        "poseidon_rank16_two_circuits",
        "Akita's merge takes two circuits with Poseidon at rank 16",
        all(a16[(v, "poseidon")]["circuits"] == 2 for v in VARIANTS),
    )
    for v in ("fp128", "goldilocks"):
        fig(f"{v}_16_blake3_prover", sci(a16[(v, "blake3")]["prover"]))
        fig(f"{v}_16_poseidon_prover", sci(a16[(v, "poseidon")]["prover"]))
    ratio = {v: a16[(v, "blake3")]["prover"] / a16[(v, "poseidon")]["prover"] for v in VARIANTS}
    for v in ("fp128", "goldilocks", "pasta", "pasta_q64"):
        fig(f"{v}_16_prover_ratio", sig(ratio[v]))
    claim(
        "blake3_prover_ratios",
        "the two Pasta-modulus variants have the same BLAKE3-to-Poseidon merge prover ratio; Goldilocks's is above the 128-bit field's and the 64-bit-commitment variant's above the Pasta-modulus ones', since at the 64-bit modulus the wider BLAKE3 accumulator takes the matrix to degree 1,024",
        ratio["goldilocks"] > 1.05 * ratio["fp128"]
        and sig(ratio["pasta_sis"]) == sig(ratio["pasta"])
        and ratio["pasta_q64"] > 1.05 * ratio["pasta"],
    )
    more_bytes = {v: a16[(v, "blake3")]["bytes"] - a16[(v, "poseidon")]["bytes"] for v in VARIANTS}
    fig(
        "akita16_more_kb_small_min",
        round(min(more_bytes[v] for v in ("fp128", "goldilocks")) / 1000),
    )
    fig(
        "akita16_more_kb_small_max",
        round(max(more_bytes[v] for v in ("fp128", "goldilocks")) / 1000),
    )
    fig("akita16_more_kb_pasta_min", round(min(more_bytes[v] for v in PASTA_VARIANTS) / 1000))
    fig("akita16_more_kb_pasta_max", round(max(more_bytes[v] for v in PASTA_VARIANTS) / 1000))
    more_atoms = [
        a16[(v, "blake3")]["accumulation"] - a16[(v, "poseidon")]["accumulation"] for v in VARIANTS
    ]
    fig("akita16_more_atoms_min", sig(min(more_atoms)))
    fig("akita16_more_atoms_max", sig(max(more_atoms)))
    cuts = [
        1 - pick(v, rank=17, hashes="blake3")["prover"] / a16[(v, "blake3")]["prover"]
        for v in VARIANTS
    ]
    fig("akita17_blake3_cut_pct_min", round(100 * min(cuts)))
    fig("akita17_blake3_cut_pct_max", round(100 * max(cuts)))
    less = {
        v: a16[(v, "blake3")]["bytes"] - pick(v, rank=17, hashes="blake3")["bytes"]
        for v in VARIANTS
    }
    fig("akita17_blake3_less_kb_small", kb(max(less[v] for v in ("fp128", "goldilocks")), 1))
    fig("akita17_blake3_less_kb_pasta", kb(max(less[v] for v in PASTA_VARIANTS), 1))
    akita_ms = sorted(
        p["verify"] / WORD_MULTS_PER_MS
        for v in ("fp128", "goldilocks")
        for p in shown(v, "poseidon", hashes="poseidon")
    )
    fig("akita_decider_ms_min", sig(akita_ms[0], 3))
    fig("akita_decider_ms_max", sig(akita_ms[-1], 3))
    pasta_ms = sorted(
        p["verify"] / WORD_MULTS_PER_MS
        for v in PASTA_VARIANTS
        for p in shown(v, "poseidon", hashes="poseidon")
    )
    fig("akita_pasta_decider_ms_max", sig(pasta_ms[-1], 3))
    for v in VARIANTS:
        fig(f"image_share_pct_{v}", round(100 * IMAGE_SHARE[v]))
    fig("whir_scale_147_pct", round(100 * (WHIR_SCALE[147] - 1)))
    fig("whir_hashes_147_pct", round(100 * (WHIR_HASHES_SCALE[147] - 1)))
    fig("arc_floor_pct", ARC_FLOOR_PCT)
    # The width shrink by ring-dimension group, across the moduli; the medians of 30 and more are
    # the few cells at the largest dimensions, reported apart.
    GROUPS = {"small": (8, 16, 32), "64": (64,), "mid": (128, 256), "large": (512, 1024, 2048)}
    outliers = []
    for group, ds in GROUPS.items():
        meds = [
            m for shrink in WIDTH_SHRINK_147.values() for d, (m, _) in shrink.items() if d in ds
        ]
        typical = [m for m in meds if m < 30]
        outliers += [m for m in meds if m >= 30]
        fig(f"shrink_{group}_min", round(min(typical)))
        fig(f"shrink_{group}_max", round(max(typical)))
    fig("shrink_outlier", round(statistics.mean(outliers)))
    claim(
        "shrink_q32_least",
        "the 32-bit modulus shrinks least at every ring dimension from 64 up",
        all(
            WIDTH_SHRINK_147["q32"][d][0]
            <= min(s[d][0] for s in WIDTH_SHRINK_147.values() if d in s)
            for d in (64, 128, 256, 512, 1024)
        ),
    )
    claim(
        "shrink_36fold_large_dims",
        "the 36-fold cells are at ring dimension 512 and above only",
        all(d >= 512 for s in WIDTH_SHRINK_147.values() for d, (m, _) in s.items() if m >= 30),
    )
    fig("rank_instances", RANK_INSTANCES)
    # The cost models' bits at each floor's block size (the cost-model table).
    for floor in FLOORS:
        fig(f"block_{floor}", BLOCK_SIZES[floor])
        for model, exponent in CORE_SVP_EXPONENTS.items():
            fig(f"bits_{model}_{floor}", round(exponent * BLOCK_SIZES[floor]))
    claim(
        "floors_block_sizes",
        "each floor's block size gives the floor's bits under quantum sieving",
        all(round(CORE_SVP_EXPONENTS["quantum"] * BLOCK_SIZES[f]) == f for f in FLOORS),
    )
    for m, (low, high, moves) in RANK_SUMS_147.items():
        fig(f"rank_sum_{m}_128", low)
        fig(f"rank_sum_{m}_147", high)
        fig(f"rank_moves_{m}", moves)
        fig(f"rank_scale_{m}", f"{high / low:.2f}")

    # The WHIR-type rows at rate 1/8 and rank 13 (the hash-based families, ARC against
    # recursion, Hashes and Decider work paragraphs).
    WHIR_TYPES = ("whir", "whir_gold", "whir_hybrid", "plonky3")
    w13 = {
        (f, hp): pick(f, rate="1/8", rank=13, hashes=hp) for f in WHIR_TYPES for hp in HASH_POLICIES
    }
    whir8 = w13[("whir", "poseidon")]
    arc_pos = [p for f in WHIR_TYPES for p in shown(f, "poseidon", hashes="poseidon")]
    fig("whir_poseidon_kb_min", kb(min(p["bytes"] for p in arc_pos)))
    fig("whir_poseidon_kb_max", kb(max(p["bytes"] for p in arc_pos)))
    over_ped = sorted(p["prover"] / ch["prover"] for p in arc_pos)
    fig("whir_poseidon_over_pedersen_min", sig(over_ped[0]))
    fig("whir_poseidon_over_pedersen_max", sig(over_ped[-1]))
    fig("whir_poseidon_gates_min", mil(min(p["gates"] for p in arc_pos)))
    fig("whir_poseidon_gates_max", mil(max(p["gates"] for p in arc_pos)))
    over_akita = sorted(p["gates"] / a16[("fp128", "poseidon")]["gates"] for p in arc_pos)
    fig("whir_poseidon_over_akita_min", sig(over_akita[0]))
    fig("whir_poseidon_over_akita_max", sig(over_akita[-1]))
    log_elems = 13 + math.log2(whir8["circuits"]) + math.log2(HASH_VARIANTS["whir"]["elems"])
    fig("whir13_standalone_kb", kb(whir_bytes("whir", "1/8", log_elems, whir8["grind_bits"])))
    fig("whir13_kb", kb(whir8["bytes"]))
    whir32 = pick("whir", rate="1/32", rank=13, hashes="poseidon")
    fig("whir13_1_32_kb", kb(whir32["bytes"]))
    fig("whir32_over_8_prover", sig(whir32["prover"] / whir8["prover"]))
    claim(
        "whir_rate32_third_off",
        "rate 1/32 takes about a third off WHIR's proof and merge against rate 1/8",
        0.6 <= whir32["bytes"] / whir8["bytes"] <= 0.75
        and 0.6 <= whir32["gates"] / whir8["gates"] <= 0.75,
    )
    gold8 = w13[("whir_gold", "poseidon")]
    fig("whir_gold_prover_cut", sig(whir8["prover"] / gold8["prover"], 1))
    claim(
        "whir_gold_sixth_off",
        "Goldilocks cuts WHIR's proof by about a sixth and grows its merge",
        0.78 <= gold8["bytes"] / whir8["bytes"] <= 0.9 and gold8["gates"] > whir8["gates"],
    )
    rec8 = pick("whir_rec", rate="1/8", rank=13, hashes="poseidon")
    fig("whir_rec13_kb", kb(rec8["bytes"]))
    claim(
        "rec_proofs_half_arc",
        "the recursive rows' proofs are a little over half the ARC rows'",
        0.5 < rec8["bytes"] / whir8["bytes"] < 0.62,
    )
    fig("arc_openings_1_8", round(arc_openings("1/8", 128, 0)))
    # The frontier page's own ARC comparisons run at its default floor.
    fig("arc_openings_1_8_default", round(arc_openings("1/8", DEFAULT_FLOOR, 0)))
    for rate in ("1/2", "1/4"):
        fig(f"arc_openings_{rate.replace('/', '_')}", round(arc_openings(rate, 128, 0)))
    claim(
        "whir_rec_wash_rate8",
        "WHIR's recursion is about a wash on the prover at rate 1/8, and its merge about two fifths larger",
        0.9 <= rec8["prover"] / whir8["prover"] <= 1.15
        and 1.3 <= rec8["gates"] / whir8["gates"] <= 1.5,
    )
    rec2, arc2 = (
        pick("whir_rec", rate="1/2", rank=13, hashes="poseidon"),
        pick("whir", rate="1/2", rank=13, hashes="poseidon"),
    )
    claim(
        "whir_rec_rate2_saves",
        "at rate 1/2 recursion saves about a third of WHIR's prover and a twentieth of its merge",
        0.6 <= rec2["prover"] / arc2["prover"] <= 0.72
        and 0.9 <= rec2["gates"] / arc2["gates"] <= 0.98,
    )
    ALL_MEASURES = (
        "bytes",
        "prover",
        "accumulation_prover",
        "accumulation",
        "gates",
        "verify",
        "memory",
    )

    def dominated(p, qs):
        return any(
            all(q[m] <= p[m] for m in ALL_MEASURES) and any(q[m] < p[m] for m in ALL_MEASURES)
            for q in qs
        )

    claim(
        "poseidon_rate2_rec_dominates",
        "with Poseidon trees every rate-1/2 ARC row of WHIR over Pasta, WHIR over Goldilocks and the limb hybrid is dominated on every measure by a recursive row of its family",
        all(
            dominated(a, shown(f + "_rec", "poseidon", hashes="poseidon"))
            for f in ("whir", "whir_gold", "whir_hybrid")
            for a in shown(f, "poseidon", rate="1/2", hashes="poseidon")
        ),
    )
    claim(
        "blake3_no_rec_dominance",
        "under BLAKE3 trees no ARC row is dominated by its family's recursive row, nor the 𝔽₂ family's or BitZ's under either hash",
        not any(
            dominated(a, shown(f + "_rec", "poseidon", hashes="blake3"))
            for f in WHIR_TYPES
            for a in shown(f, "poseidon", hashes="blake3")
        )
        and not any(
            dominated(a, shown(f + "_rec", "poseidon"))
            for f in ("flock", "bitz")
            for a in shown(f, "poseidon")
        ),
    )
    fri_rec8 = pick("plonky3_rec", rate="1/8", rank=13, hashes="poseidon")
    claim(
        "fri_rec_twice_arc",
        "FRI's recursion costs about twice ARC",
        1.7 <= fri_rec8["prover"] / w13[("plonky3", "poseidon")]["prover"] <= 2.4,
    )
    for hp in HASH_POLICIES:
        fig(f"whir13_{hp}_gates", mil(w13[("whir", hp)]["gates"]))
        fig(f"whir13_{hp}_circuits", fmt(w13[("whir", hp)]["circuits"]))
    g_ratio = sorted(
        w13[(f, "blake3")]["gates"] / w13[(f, "poseidon")]["gates"] for f in WHIR_TYPES
    )
    fig("whir13_blake3_gates_ratio_min", sig(g_ratio[0]))
    fig("whir13_blake3_gates_ratio_max", sig(g_ratio[-1]))
    p_ratio = sorted(
        w13[(f, "blake3")]["prover"] / w13[(f, "poseidon")]["prover"]
        for f in ("whir", "whir_gold", "plonky3")
    )
    fig("whir13_blake3_prover_ratio_min", sig(p_ratio[0]))
    fig("whir13_blake3_prover_ratio_max", sig(p_ratio[-1]))
    fig(
        "hybrid13_blake3_prover_cut",
        sig(w13[("whir_hybrid", "poseidon")]["prover"] / w13[("whir_hybrid", "blake3")]["prover"]),
    )
    v_ratio = sorted(
        w13[(f, "poseidon")]["verify"] / w13[(f, "blake3")]["verify"] for f in WHIR_TYPES
    )
    fig("whir13_blake3_verify_cut_min", sig(v_ratio[0]))
    fig("whir13_blake3_verify_cut_max", sig(v_ratio[-1]))
    claim(
        "blake3_whir_proofs_deciders",
        "with BLAKE3 trees the WHIR-type proofs grow by about a sixth, and the deciders take a few milliseconds",
        all(
            1.1 <= w13[(f, "blake3")]["bytes"] / w13[(f, "poseidon")]["bytes"] <= 1.25
            and w13[(f, "blake3")]["verify"] / WORD_MULTS_PER_MS < 3
            for f in WHIR_TYPES
        ),
    )
    claim(
        "blake3_whir_grind_24",
        "with BLAKE3 trees the WHIR-type rows take 24 bits of grinding at rate 1/8 and rank 13",
        all(w13[(f, "blake3")]["grind_bits"] == 24 for f in WHIR_TYPES),
    )
    for f in ("whir", "whir_gold", "whir_rec", "whir_gold_rec"):
        fig(
            f"{f}13_poseidon_decider_ms",
            sig(
                pick(f, rate="1/8", rank=13, hashes="poseidon")["verify"] / WORD_MULTS_PER_MS,
                3,
            ),
        )
    claim(
        "blake3_whir_deciders_ms",
        "the WHIR-type deciders take about a millisecond with BLAKE3 trees",
        all(
            0.5 <= pick(f, rate="1/8", rank=13, hashes="blake3")["verify"] / WORD_MULTS_PER_MS <= 2
            for f in WHIR_TYPES + ("whir_rec", "whir_gold_rec")
        ),
    )
    log_len = 13 + math.log2(whir8["circuits"])
    fig("whir_per_coeff_poseidon", sig(arc_per_coefficient("whir", "1/8", log_len, "poseidon")))
    claim(
        "whir_blake3_prover_per_coeff",
        "WHIR's prover with BLAKE3 trees is a few thousand word multiplications per coefficient",
        1000
        < arc_per_coefficient(
            "whir", "1/8", 13 + math.log2(w13[("whir", "blake3")]["circuits"]), "blake3"
        )
        < 10000,
    )
    for g in (0, 16, 20, 24):
        fig(f"whir_meas_1_8_g{g}_kb", kb(WHIR_MEAS[("pasta", g, "1/8")][17]["bytes"]))
        fig(f"whir_meas_1_32_g{g}_kb", kb(WHIR_MEAS[("pasta", g, "1/32")][17]["bytes"]))
    for rate in ("1/2", "1/4", "1/8"):
        m = WHIR_MEAS[("pasta", 20, rate)][17]
        fig(f"whir_sweep_{rate.replace('/', '_')}_kb", kb(m["bytes"]))
        fig(f"whir_sweep_{rate.replace('/', '_')}_khashes", sig(m["hashes"] / 1000) + "k")
    for g in (17, 20):
        fig(
            f"grind_{g}_pct",
            sig(100 * grind_prover(hv("whir", "poseidon")["native"], g) / whir8["prover"], 1),
        )
    whir_rates = [pick("whir", rate=r, rank=13, hashes="poseidon") for r in ("1/2", "1/4", "1/8")]
    fig("whir13_rates_gates_min", mil(min(p["gates"] for p in whir_rates)))
    fig("whir13_rates_gates_max", mil(max(p["gates"] for p in whir_rates)))
    fig(
        "whir13_over_akita_poseidon",
        sig(min(p["gates"] for p in whir_rates) / a16[("fp128", "poseidon")]["gates"], 1),
    )
    fig("whir13_over_today_min", sig(min(p["gates"] for p in whir_rates) / ch["gates"], 1))
    fig("whir13_over_today_max", sig(max(p["gates"] for p in whir_rates) / ch["gates"], 1))
    gold_rates = [
        pick("whir_gold", rate=r, rank=13, hashes="poseidon") for r in ("1/2", "1/4", "1/8")
    ]
    fig("whir_gold13_kb_min", kb(min(p["bytes"] for p in gold_rates)))
    fig("whir_gold13_kb_max", kb(max(p["bytes"] for p in gold_rates)))

    # The 𝔽₂ family (the binary-field paragraph and the Hashes paragraph).
    f192 = {p["rate"]: p for p in shown("flock", field=192, zkv=None)}
    f8 = f192["1/8"]
    fig("f2_gates_min", mil(min(p["gates"] for p in f192.values())))
    fig("f2_gates_max", mil(max(p["gates"] for p in f192.values())))
    hashes_8, ands_8 = f2_merge("1/8", DEFAULT_FLOOR, GRIND_DEFAULT, 128)
    f2_piop_mults = f2_piop_verifier_mults(math.log2(ands_8))
    f2_piop_ands = 2 * f2_piop_mults * CLMUL_ANDS[128]
    fig("f2_piop_mults", fmt(round(f2_piop_mults, -1)))
    fig("f2_piop_mands", sig(f2_piop_ands / 1e6, 2))
    fig("f2_piop_pct", sig(100 * f2_piop_ands / ands_8, 2))
    claim(
        "f2_piop_verifier_small",
        "the F2 family's PIOP verifiers are under a fifth of its merge at every rate",
        all(
            2 * f2_piop_verifier_mults(math.log2(a)) * CLMUL_ANDS[128] < a / 5
            for a in (f2_merge(r, DEFAULT_FLOOR, GRIND_DEFAULT, 128)[1] for r in RATES)
        ),
    )
    bitz17 = bitz_point("arc", "1/8", 17, DEFAULT_FLOOR)
    bitz_bits = 2**17 + bitz17["gates"]
    bitz_piop_mults = bitz_piop_verifier_mults(math.log2(bitz_bits))
    bitz_piop_bits = 2 * bitz_piop_mults * BITZ_FIELD_BITS
    fig("bitz_piop_mults", fmt(round(bitz_piop_mults, -2)))
    fig("bitz_piop_kbits", fmt(round(bitz_piop_bits / 1000)))
    fig("bitz_piop_pct", sig(100 * bitz_piop_bits / bitz17["gates"], 2))
    claim(
        "bitz_piop_verifier_small",
        "BitZ's PIOP and GKR verifiers are under two percent of its merge",
        bitz_piop_bits < bitz17["gates"] / 50,
    )
    fig("f2_rate_highest", min(f192, key=lambda r: int(r.split("/")[1])))
    fig("f2_rate_lowest", max(f192, key=lambda r: int(r.split("/")[1])))
    for fld in (192, 191, 256):
        fig(f"f2_1_8_{fld}_kb", kb(pick("flock", rate="1/8", field=fld, zkv=None)["bytes"]))
    less = [
        1
        - pick("flock", rate="1/8", field=fld, zkv=None)["bytes"]
        / pick("flock", rate="1/8", field=256, zkv=None)["bytes"]
        for fld in (192, 191)
    ]
    fig("f2_192_191_less_pct", sig(100 * sum(less) / 2, 1))
    claim(
        "f2_191_192_proofs_equal",
        "the 192- and 191-bit designs' proofs are within a percent of each other at rate 1/8",
        abs(less[0] - less[1]) < 0.01,
    )
    fig("f2_192_1_64_prover", f"{sig(f192['1/64']['prover'] / 1e9)} billion")
    # WHIR over Goldilocks under BEEP: the quadratic extension against the cubic one, at the
    # 128-bit floor and rank 13.
    wg = {(q["rate"], q.get("profile")): q for q in shown("whir_gold", floor=BEEP_FLOOR, rank=13)}
    wg_less = [100 * (1 - wg[(r, "beep")]["bytes"] / wg[(r, None)]["bytes"]) for r in RATES]
    wg_memory = [100 * (1 - wg[(r, "beep")]["memory"] / wg[(r, None)]["memory"]) for r in RATES]
    fig("whir_beep_less_pct_min", sig(min(wg_less), 2))
    fig("whir_beep_less_pct_max", sig(max(wg_less), 2))
    fig("whir_beep_memory_less_pct", sig(min(wg_memory), 2))
    fig("whir_beep_1_8_kb", kb(wg[("1/8", "beep")]["bytes"]))
    fig("whir_cubic_low_1_8_kb", kb(wg[("1/8", None)]["bytes"]))
    claim(
        "whir_beep_smaller_same_prover",
        "at the 128-bit floor WHIR over Goldilocks's quadratic extension under BEEP has a smaller proof and accumulator than over the cubic extension at every rate, with the same merge and merge prover",
        min(wg_less) > 0
        and min(wg_memory) > 0
        and all(wg[(r, "beep")][k] == wg[(r, None)][k] for r in RATES for k in ("prover", "gates")),
    )
    # The design under BEEP, against the 192-bit design, both at the 128-bit floor.
    beep_floor = F2_DESIGNS[128]["floors"][0]
    f128 = {p["rate"]: p for p in shown("flock", floor=beep_floor, field=128, zkv=None)}
    f192_low = {p["rate"]: p for p in shown("flock", floor=beep_floor, field=192, zkv=None)}
    for rate in ("1/8", "1/64"):
        tag = rate.replace("/", "_")
        fig(f"f2_beep_{tag}_kb", kb(f128[rate]["bytes"]))
        fig(f"f2_192_low_{tag}_kb", kb(f192_low[rate]["bytes"]))
    bytes_less = [100 * (1 - f128[r]["bytes"] / f192_low[r]["bytes"]) for r in RATES]
    prover_less = [100 * (1 - f128[r]["prover"] / f192_low[r]["prover"]) for r in RATES]
    fig("f2_beep_less_pct_min", sig(min(bytes_less), 1))
    fig("f2_beep_less_pct_max", sig(max(bytes_less), 1))
    fig("f2_beep_prover_less_pct_min", sig(min(prover_less), 2))
    fig("f2_beep_prover_less_pct_max", sig(max(prover_less), 2))
    fig("f2_beep_list_bits", tex_pow2(F2_BEEP_LIST_BITS))
    fig("f2_beep_samples", F2_DESIGNS[128]["beep"])
    claim(
        "f2_beep_smaller_cheaper",
        "at the 128-bit floor the binary-field design under BEEP has a smaller proof and a cheaper merge prover than the 192-bit design at every rate",
        min(bytes_less) > 0 and min(prover_less) > 0,
    )
    f256 = {p["rate"]: p for p in shown("flock", field=256, zkv=None)}
    f191 = {p["rate"]: p for p in shown("flock", field=191, zkv=None)}
    r256 = [f256[r]["prover"] / f192[r]["prover"] for r in f192 if r in f256]
    fig("f2_256_more_pct_max", sig(100 * (max(r256) - 1), 1))
    claim(
        "f2_256_prover_not_less",
        "the 256-bit design's prover is never less than the 192-bit one's by more than a percent",
        min(r256) >= 0.99,
    )
    pct191 = sorted(100 * (f191[r]["prover"] / f192[r]["prover"] - 1) for r in f192 if r in f191)
    fig("f2_191_less_pct", sig(-pct191[0], 1))
    fig("f2_191_more_pct", sig(pct191[-1], 1))
    claim(
        "f2_191_prover_rates",
        "the 191-bit design's prover is less than the 192-bit one's at the highest rate and more at the lowest",
        f191["1/2"]["prover"] < f192["1/2"]["prover"]
        and f191["1/64"]["prover"] > f192["1/64"]["prover"],
    )
    fig("f2_decider_ms_min", sig(min(p["verify"] for p in f192.values()) / WORD_MULTS_PER_MS, 3))
    fig("f2_decider_ms_max", sig(max(p["verify"] for p in f192.values()) / WORD_MULTS_PER_MS, 3))
    fig("f2_192_kb_min", kb(min(p["bytes"] for p in f192.values())))
    fig("f2_192_kb_max", kb(max(p["bytes"] for p in f192.values())))
    frec = {p["rate"]: p for p in shown("flock_rec", field=192, zkv=None)}
    fig("f2_rec_192_kb_min", kb(min(p["bytes"] for p in frec.values())))
    fig("f2_rec_192_kb_max", kb(max(p["bytes"] for p in frec.values())))
    f_least = min(f192.values(), key=lambda p: p["prover"])
    fig("f2_192_prover_least", mil(f_least["prover"]))
    claim(
        "f2_prover_least_rate_4",
        "the 𝔽₂ family's prover is least at rate 1/4, with rate 1/8 within a tenth of it",
        f_least["rate"] == "1/4" and f192["1/8"]["prover"] <= 1.1 * f_least["prover"],
    )
    fig(
        "f2_over_gold_poseidon",
        sig(f_least["prover"] / a16[("goldilocks", "poseidon")]["prover"], 1),
    )
    fig(
        "f2_over_gold_blake3",
        sig(f_least["prover"] / a16[("goldilocks", "blake3")]["prover"]),
    )
    claim(
        "f2_prover_fraction_of_gold_blake3",
        "the 𝔽₂ family's least prover is between two thirds and nine tenths of Akita over Goldilocks's with BLAKE3",
        2 / 3 <= f_least["prover"] / a16[("goldilocks", "blake3")]["prover"] <= 0.9,
    )
    fig("f2_1_8_prover", sci(f8["prover"]))
    fig("f2_1_8_kb", kb(f8["bytes"]))
    fig("f2_1_8_gates", mil(f8["gates"]))
    fig("goldilocks_16_blake3_kb", kb(a16[("goldilocks", "blake3")]["bytes"]))
    fig("goldilocks_16_poseidon_kb", kb(a16[("goldilocks", "poseidon")]["bytes"]))
    claim(
        "gold_poseidon_dominates_f2_rate8",
        "Akita over Goldilocks with Poseidon dominates the 𝔽₂ family's rate-1/8 row on bytes and prover",
        a16[("goldilocks", "poseidon")]["bytes"] < f8["bytes"]
        and a16[("goldilocks", "poseidon")]["prover"] < f8["prover"],
    )
    frec8 = {fld: pick("flock_rec", rate="1/8", field=fld, zkv=None) for fld in (192, 191, 256)}
    for fld, p in frec8.items():
        fig(f"f2_rec_1_8_{fld}_bits", mil(p["gates"]))
    rr = sorted(p["prover"] / f8["prover"] for p in frec8.values())
    fig("f2_rec_over_arc_prover_min", sig(rr[0]))
    fig("f2_rec_over_arc_prover_max", sig(rr[-1]))
    fig("f2_rec_1_8_192_kb", kb(frec8[192]["bytes"]))
    claim(
        "f2_rec_proof_quarter_smaller",
        "the 𝔽₂ family's recursive proof is about a quarter smaller than its ARC one at rate 1/8",
        0.68 <= frec8[192]["bytes"] / f8["bytes"] <= 0.8,
    )
    fm = pick("flock", rate="1/8", field=192, zkv="mask", zk=True)
    fz = pick("flock", rate="1/8", field=192, zkv="zook", zk=True)
    fig("f2_mask_more_kb", kb(fm["bytes"] - f8["bytes"]))
    fig("f2_mask_kb", kb(fm["bytes"]))
    fig("f2_zook_more_kb", kb(fz["bytes"] - f8["bytes"]))
    claim(
        "f2_mask_fold_shares",
        "the batched mask costs two thirds of the row's prover in the fold, and the Zook-style masks about a hundredth",
        0.55 <= fm["fold"] / f8["prover"] <= 0.8 and fz["fold"] / f8["prover"] < 0.03,
    )

    # BitZ (the BitZ paragraph, ARC against recursion, zero knowledge) and Kishu (its paragraph).
    b13 = pick("bitz", rank=13, rate="1/8")
    fig("bitz13_kb", kb(b13["bytes"]))
    fig("bitz13_prover", sci(b13["prover"]))
    fig("bitz13_merge_bits", millions(b13["gates"]))
    fig("bitz13_merge_bits_m", mil(b13["gates"]))
    fig("bitz13_decider_ms", sig(b13["verify"] / WORD_MULTS_PER_MS, 3))
    HASH_FAMILIES = (
        "whir",
        "whir_gold",
        "whir_hybrid",
        "plonky3",
        "flock",
        "bitz",
        "whir_rec",
        "whir_gold_rec",
        "whir_hybrid_rec",
        "plonky3_rec",
        "flock_rec",
        "bitz_rec",
    )
    claim(
        "bitz_unbeaten_among_hash_pasta",
        "no other hash-based family's row with Pasta claims has both a smaller proof and a cheaper prover than BitZ at rank 13, rate 1/8",
        not any(
            q["pasta"] and q["bytes"] <= b13["bytes"] and q["prover"] <= b13["prover"]
            for f in HASH_FAMILIES
            if f != "bitz"
            for q in shown(f, "poseidon")
        ),
    )
    fig("frontier_tolerance_pct", round(100 * FRONTIER_TOLERANCE))
    fig("bitz_piop_prover_factor", BITZ_PIOP["prover"])
    fig("bitz_piop_verify_ms", sig(BITZ_PIOP["verify_ms"], 3))
    fig("bitz_piop_kb", kb(BITZ_PIOP["bytes"]))
    # BitZ's measurements at 2^25 bits and 128 bits of security (BITZ_MEASURED).
    udr25 = {r: BITZ_MEASURED["udr"][r][25] for r in BITZ_MEASURED["udr"]}
    beep25 = {r: BITZ_MEASURED["beep"][r][25] for r in BITZ_MEASURED["beep"]}
    fig("bitz_rate_1_8_lig", sig(udr25[3][5] / udr25[1][5], 2))
    fig("bitz_25_rate_penalty", sig((udr25[3][0] + udr25[3][1]) / (udr25[1][0] + udr25[1][1]), 3))
    fig("bitz_prover_25_ms", sig(udr25[1][0] + udr25[1][1], 3))
    fig("bitz_gkr_25_ms", sig(udr25[1][2]))
    fig("bitz_25_verify_ms", sig(udr25[1][3], 3))
    fig("bitz_gkr_share_pct", round(100 * udr25[1][2] / (udr25[1][0] + udr25[1][1])))
    for r in udr25:
        fig(f"bitz_commit_25_r{r}_ms", sig(udr25[r][0], 3))
    fig("bitz_commit_25_r6_ms", sig(beep25[6][0], 3))
    shares = {r: [v[2] / (v[0] + v[1]) for v in BITZ_MEASURED["udr"][r].values()] for r in udr25}
    claim(
        "bitz_gkr_four_fifths",
        "the grand-product GKR is about four fifths of BitZ's prover at rate 1/2, and a smaller share at rate 1/8",
        all(0.72 <= s <= 0.84 for s in shares[1]) and max(shares[3]) < min(shares[1]),
    )
    # The stand-alone proofs at 2^25 bits, by regime and rate, and BEEP's samples.
    for r in udr25:
        fig(f"bitz_udr_25_r{r}_kb", kb(udr25[r][4] + udr25[r][5]))
    deep_bytes = bitz_beep_overhead(25, 1)[0]
    for r in beep25:
        fig(f"bitz_beep_25_r{r}_kb", kb(beep25[r][4] + beep25[r][5] + deep_bytes))
    fig("bitz_beep_folds", sum(k for _, k, _ in bitz_levels("beep", 25, 1)))
    fig("bitz_beep_samples", BEEP_SAMPLES)
    fig("bitz_beep_deep_kb", kb(deep_bytes))
    fig("bitz_udr_queries_25", bitz_queries("udr", 25, 3, BITZ_MEASURED_FLOOR))
    fig("bitz_beep_queries_25", bitz_queries("beep", 25, 3, BITZ_MEASURED_FLOOR))
    fig("bitz_beep_queries_25_r6", bitz_queries("beep", 25, 6, BITZ_MEASURED_FLOOR))
    # The rows at the 128-bit floor: the smallest proof under each regime.
    rows128 = shown("bitz", floor=BITZ_MEASURED_FLOOR)
    least = {
        profile: min((q for q in rows128 if q["profile"] == profile), key=lambda q: q["bytes"])
        for profile in BITZ_MEASURED
    }
    fig("bitz_udr128_min_kb", kb(least["udr"]["bytes"]))
    fig("bitz_beep128_min_kb", kb(least["beep"]["bytes"]))
    fig("bitz_beep128_min_rate", least["beep"]["rate"])
    fig("bitz_beep128_min_prover_over_udr", sig(least["beep"]["prover"] / least["udr"]["prover"]))
    claim(
        "bitz_beep_halves_proof",
        "at the 128-bit floor BitZ's smallest row under the Johnson bound with BEEP is under half of its smallest unique-decoding row's bytes, at the lowest rate and within a tenth of its merge prover",
        least["beep"]["bytes"] < 0.5 * least["udr"]["bytes"]
        and least["beep"]["rate"] == RATES[-1]
        and abs(least["beep"]["prover"] / least["udr"]["prover"] - 1) < 0.1,
    )
    b12 = pick("bitz", rank=12, rate="1/8")
    claim(
        "bitz_rank12_slightly_smaller",
        "rank 12 gives BitZ a slightly smaller proof and merge prover",
        b12["bytes"] < b13["bytes"] and b12["prover"] < b13["prover"],
    )
    bz_rec13 = pick("bitz_rec", rank=13, rate="1/8")
    fig("bitz_rec13_merge_bits", mil(bz_rec13["gates"]))
    fig("bitz_rec_over_arc_hashing", sig(bz_rec13["gates"] / b13["gates"], 1))
    fig("bitz_rec_over_arc_prover", sig(bz_rec13["prover"] / b13["prover"]))
    fig("bitz_rec_less_pct", round(100 * (1 - bz_rec13["bytes"] / b13["bytes"])))
    claim(
        "bitz_rec_smaller_proof_dearer",
        "BitZ's recursion row has a smaller proof than its ARC row at a greater prover and merge",
        bz_rec13["bytes"] < b13["bytes"]
        and bz_rec13["prover"] > b13["prover"]
        and bz_rec13["gates"] > b13["gates"],
    )
    fig("ligerito_columns", bitz_queries("udr", math.log2(b13["gates"]), 3, DEFAULT_FLOOR))
    fig("ligerito_levels", len(bitz_levels("udr", math.log2(b13["gates"]), 3)))
    b13z = pick("bitz", rank=13, rate="1/8", zk=True)
    fig("bitz13_zk_more_kb", kb(b13z["bytes"] - b13["bytes"]))
    fig("bitz_mask_elements_25", fmt(round(bitz_mask_elements(25))))
    ba = pick("bits_akita", floor=128)
    fig("bits_akita_decider_ms", sig(ba["verify"] / WORD_MULTS_PER_MS, 3))
    fig("bits_akita_gates", millions(ba["gates"]))
    fig("bits_akita_kb", kb(ba["bytes"]))
    fig("bits_akita_prover", sci(ba["prover"]))
    # The Boolean-over-Akita merge's parts (the family's merge paragraph).
    parts = bits_akita_merge_parts(K, 1, BINARY_MEASURED["field"])
    fig("bits_akita_transcript_kb", sig(akita_absorbed_bytes("fp128", K, 1, False) / 1000, 2))
    for part in ("hashing", "fold", "sumcheck", "verifier"):
        fig(f"bits_akita_{part}_mands", sig(parts[part] / 1e6, 2))
    fig("bits_akita_merge_mands", sig(bits_akita_ands / 1e6, 2))
    claim(
        "bits_akita_sumcheck_dominates",
        "the sum-check verifier's field multiplications are the largest part of the Boolean-over-Akita merge",
        parts["sumcheck"] > max(v for k, v in parts.items() if k != "sumcheck"),
    )
    fig("bits_akita_f2_merge_ratio", sig(f8["gates"] / ba["gates"], 2))
    claim(
        "bits_akita_merge_below_f2",
        "the binary-groups merge is smaller than the 𝔽₂ family's ARC merge at rate 1/8",
        ba["gates"] < f8["gates"],
    )
    fig(
        "bits_akita_mults_per_pasta_gate",
        sig(
            ba["step_prover"]
            / BOOL_STEP_BITS
            * APP["recovery"]["boolean"]["blake3"]
            / APP["recovery"]["pasta"]["blake3"]
        ),
    )
    fig("q64_mults_per_pasta_gate", sig(4 * ajtai_per_coefficient("pasta_q64")))
    k_b = pick("bits_q64", rank=17, hashes="blake3", check="sumcheck", route="limbs")
    k_p = pick("bits_q64_poseidon", rank=17, check="sumcheck", route="limbs")
    q_b = pick("pasta_q64", rank=17, hashes="blake3")
    q_p = pick("pasta_q64", rank=17, hashes="poseidon")
    fig("kishu17_blake3_digits", millions(k_b["gates"]))
    fig("kishu17_blake3_circuits", k_b["circuits"])
    fig("kishu17_blake3_kb", kb(k_b["bytes"]))
    fig("kishu17_blake3_prover", sci(k_b["prover"]))
    fig("kishu17_blake3_decider_ms", sig(k_b["verify"] / WORD_MULTS_PER_MS, 3))
    fig("kishu17_poseidon_digits", millions(k_p["gates"]))
    fig("kishu17_poseidon_kb", kb(k_p["bytes"]))
    fig("kishu17_poseidon_prover", sci(k_p["prover"]))
    sum_bytes, sum_mults, sum_bits = (BOOL_CHECK["sumcheck"][i] for i in (1, 3, 4))
    for hp in HASH_POLICIES:
        fig(
            f"kishu_claim_digits_{hp}",
            sig(merge_marginal_circuit(Kg, 17, hp, sum_mults, sum_bits, sum_bytes)),
        )
    fig(
        "kishu13_blake3_circuits",
        fmt(
            pick("bits_q64", rank=13, hashes="blake3", check="sumcheck", route="limbs")["circuits"]
        ),
    )
    claim(
        "kishu_rows_from_rank13",
        "Kishu has rows from rank 13 under both hashes, where the lattice rows under BLAKE3 start at 14",
        shown("bits_q64", rank=13)
        and shown("bits_q64_poseidon", "poseidon", rank=13)
        and not any(shown(v, rank=13, hashes="blake3") for v in VARIANTS),
    )
    fig("q64_17_blake3_prover", sci(q_b["prover"]))
    fig("kishu_vs_q64_blake3_prover", sig(q_b["prover"] / k_b["prover"]))
    fig("kishu_vs_q64_poseidon_prover", sig(q_p["prover"] / k_p["prover"]))
    claim(
        "kishu_poseidon_merge_prover_smaller",
        "under Poseidon too Kishu's merge prover at rank 17 is smaller than the 64-bit variant's",
        k_p["prover"] < q_p["prover"],
    )
    fig("q64_17_blake3_kb", kb(q_b["bytes"]))
    claim(
        "kishu_blake3_dominates_q64",
        "under BLAKE3 Kishu at rank 17 dominates the 64-bit variant on bytes, prover, accumulation prover, atoms, decider and memory",
        all(
            k_b[m] <= q_b[m]
            for m in ("bytes", "prover", "accumulation_prover", "accumulation", "verify", "memory")
        ),
    )
    fig("kishu_vs_q64_poseidon_kb", kb(abs(k_p["bytes"] - q_p["bytes"]), 1))
    claim(
        "kishu_poseidon_proof_smaller",
        "under Poseidon Kishu's proof at rank 17 is smaller than the 64-bit variant's",
        k_p["bytes"] < q_p["bytes"],
    )
    bz17 = pick("bitz", rank=17, rate="1/8")
    fig("kishu_vs_bitz_bytes", sig(bz17["bytes"] / k_b["bytes"]))
    rk = sorted(bz17["prover"] / k["prover"] for k in (k_b, k_p))
    fig("kishu_vs_bitz_prover_min", sig(rk[0]))
    fig("kishu_vs_bitz_prover_max", sig(rk[-1]))
    proj, sumc = BOOL_CHECK["projection"], BOOL_CHECK["sumcheck"]
    fig("bool_projection_prover_ms", round(proj[0] * 2**27 / WORD_MULTS_PER_MS))
    fig("bool_sumcheck_prover_ms", round(sumc[0] * 2**27 / WORD_MULTS_PER_MS))
    fig("bool_projection_verify_ms", proj[2])
    fig("bool_sumcheck_verify_ms", sumc[2])
    fig("bool_projection_kb", kb(proj[1]))
    fig("bool_sumcheck_kb", kb(sumc[1]))
    fig("bool_projection_per_bit", sig(proj[0]))
    fig("bool_sumcheck_per_bit", sig(sumc[0]))
    fig("bool_projection_scan", millions(proj[4]))
    fig("bool_sumcheck_merge_mults", fmt(sumc[3]))
    fig("blake3_bits", sig(BLAKE3_BITS))
    fig("q64_digits", Q64_DIGITS)
    fig("e_mult_digits", E_MULT_DIGITS)
    fig("q64_poseidon_mults", Q64_POSEIDON_MULTS)
    fig("kishu_claim_bytes", CLAIM_BYTES["kishu"])
    fig("range_check_digits", RANGE_CHECK_DIGITS)
    poseidon_of_blake3 = (
        Q64_POSEIDON_MULTS * Q64_DIGITS / Q64_POSEIDON_RATE_BYTES / (BLAKE3_BITS / BLAKE3_BLOCK)
    )
    fig("poseidon_of_blake3_digits_pct", round(100 * poseidon_of_blake3))
    claim(
        "poseidon_fewer_digits_than_blake3",
        "Poseidon over the 64-bit field commits fewer digits per absorbed byte than BLAKE3 in Kishu's merge, since its wires are tribits where BLAKE3's are bits",
        poseidon_of_blake3 < 1,
    )
    fig("sumcheck_gates", SUMCHECK_GATES)
    fig("claim_gates", CLAIM_GATES)
    claim(
        "kishu_beats_bitz13",
        "Kishu at rank 17 under BLAKE3 beats BitZ at rank 13 on bytes and prover",
        k_b["bytes"] < b13["bytes"] and k_b["prover"] < b13["prover"],
    )

    # The page's negative statements: rows that do not exist, and measures that do not move.
    claim(
        "blake3_akita_first_ranks",
        "under BLAKE3 there are no Akita rows at rank 13, and none at rank 14 for the Pasta variants",
        not any(shown(v, rank=13, hashes="blake3") for v in VARIANTS)
        and not any(shown(v, rank=14, hashes="blake3") for v in PASTA_VARIANTS)
        and all(shown(v, rank=14, hashes="blake3") for v in ("fp128", "goldilocks"))
        and all(shown(v, rank=15, hashes="blake3") for v in PASTA_VARIANTS),
    )
    fig("akita14_blake3_circuits", fmt(pick("fp128", rank=14, hashes="blake3")["circuits"]))
    fig("pasta15_blake3_circuits", fmt(pick("pasta_q64", rank=15, hashes="blake3")["circuits"]))
    claim(
        "blake3_first_rank_circuits_shared",
        "Goldilocks has the 128-bit field's circuit count at rank 14 under BLAKE3, and the three Pasta variants share theirs at rank 15",
        pick("goldilocks", rank=14, hashes="blake3")["circuits"]
        == pick("fp128", rank=14, hashes="blake3")["circuits"]
        and len({pick(v, rank=15, hashes="blake3")["circuits"] for v in PASTA_VARIANTS}) == 1,
    )
    for v, width in (("fp128", 16), ("pasta_q64", 32)):
        fig(
            f"claim_gates_blake3_{width}",
            sig(circuit_slope(lambda c: akita_merge_gates(v, Kg, c, False, "blake3"))),
        )
    claim(
        "pedersen_only_under_poseidon",
        "the Pedersen-IPA rows exist only under the arithmetic-hash option",
        all(p["hashes"] == "poseidon" for p in points if p["family"] == "pedersen"),
    )
    claim(
        "blake3_native_rows_unchanged",
        "the 𝔽₂ family, BitZ and the binary-groups family are the same rows under either hash policy",
        all(
            p["hashes"] == "any"
            for p in points
            if p["family"] in ("flock", "flock_rec", "bitz", "bitz_rec", "bits_akita")
        ),
    )
    claim(
        "kishu_projection_no_zk",
        "Kishu's projection form has no zero-knowledge rows",
        not any(shown(f, "poseidon", zk=True, check="projection") for f in KISHU),
    )
    claim(
        "drop_out_at_147",
        "Pedersen-IPA and the binary-groups row drop out at the 147-bit floor",
        not shown("pedersen", "poseidon", floor=147) and not shown("bits_akita", floor=147),
    )
    claim(
        "pedersen_zk_unchanged",
        "Pedersen-IPA's points do not change with zero knowledge",
        all(p["zk"] is None for p in points if p["family"] == "pedersen"),
    )
    claim(
        "akita_zk_decider_small",
        "zero knowledge moves Akita's decider by under a tenth, one more circuit's claim at most",
        all(
            abs(z["verify"] / a["verify"] - 1) < 0.1
            for v in VARIANTS
            for hp in HASH_POLICIES
            for a in shown(v, "poseidon", hashes=hp)
            for z in shown(v, "poseidon", zk=True, hashes=hp)
            if z["rank"] == a["rank"]
        ),
    )
    claim(
        "pasta_native_list",
        "the 𝔽₂ family and the binary-groups row realise Pasta arithmetic in bits, the 128-bit, Goldilocks and Plonky3 rows in limbs, BitZ and Kishu as relations, and the dominance rule counts native and relation",
        all(PASTA_ARITH[f] == "bits" for f in ("flock", "flock_rec", "bits_akita"))
        and all(
            PASTA_ARITH[f] == "limbs"
            for f in ("fp128", "goldilocks", "whir_gold", "whir_gold_rec", "plonky3", "plonky3_rec")
        )
        and all(PASTA_ARITH[f].startswith("relation") for f in ("bitz", "bitz_rec", *KISHU))
        and PASTA_COUNTS == ("native", "relation"),
    )

    # The zero-knowledge mask's parameters (the zero-knowledge paragraph): the note's slices
    # and its Euclidean factor; and over every lattice row shown at either floor, under both
    # policies with zero knowledge on and off, the ℓ∞ route's accumulation matrices: the
    # masked over the unmasked rate, the bits above the unmasked bound, the bits a coordinate
    # and the slices, and how the matrices move with the floor (the margin section).
    fig("mask_rank", sig(MASK_RANK))
    fig("mask_sumcheck_atoms", MASK_SUMCHECK_ATOMS)

    def lattice_rows(floor):
        """(key, variant, log_n, digit size, zk) of every lattice row shown at `floor`: the
        Akita variants under both policies, Kishu under the arithmetic-hash option."""
        rows = []
        for v in DIGITS:
            for hp in HASH_POLICIES:
                for zk in (False, True):
                    for p in shown(v, hp, zk=zk, floor=floor, hashes=hp):
                        n = accumulator_coefficients(v, p["rank"], p["circuits"]) * DIGITS[v]
                        rows.append(((v, hp, zk, p["rank"]), v, math.log2(n), DIGIT_MAX[v], zk))
        for f in KISHU:
            for zk in (False, True):
                for p in shown(f, "poseidon", zk=zk, floor=floor):
                    n = accumulator_coefficients("kishu", p["rank"], p["circuits"])
                    key = (f, p["check"], p["route"], zk, p["rank"])
                    rows.append((key, "pasta_q64", math.log2(n), DIGIT_MAX["kishu"], zk))
        return rows

    def matrices(variant, table_floor, log_n, digit_max):
        """The unmasked and the masked matrix a row gets from a floor's table, as (rank, degree),
        with their rates."""
        unmasked = accumulation_matrix(
            variant, table_floor, unmasked_log_beta_inf(digit_max=digit_max), log_n
        )
        masked = accumulation_matrix(
            variant, table_floor, masked_log_beta_inf(log_n=log_n, digit_max=digit_max), log_n
        )
        return unmasked, masked

    shapes = {}  # (floor, key) -> the row's two matrices at its floor's table
    for floor in FLOORS:
        for key, v, log_n, dm, zk in lattice_rows(floor):
            shapes[(floor, key)] = (*matrices(v, floor, log_n, dm), log_n, dm)
    zk_shapes = [s for (fl, key), s in shapes.items() if key[-2]]
    factors = [m[0] / u[0] for u, m, _, _ in zk_shapes]
    kishu_factor = FIGURES["kishu_digit_mults_masked"], FIGURES["kishu_digit_mults"]
    fig("mask_cost_factor_min", sig(min(factors)))
    fig("mask_cost_factor_max", sig(max(factors), 3))
    fig("kishu_mask_cost_factor", sig(float(kishu_factor[0]) / float(kishu_factor[1]), 3))
    fig(
        "mask_bits_min",
        min(mask_coordinate_bits(log_n=lg, digit_max=dm) for _, _, lg, dm in zk_shapes),
    )
    fig(
        "mask_bits_max",
        max(mask_coordinate_bits(log_n=lg, digit_max=dm) for _, _, lg, dm in zk_shapes),
    )
    fig("mask_slices_min", min(mask_length(log_n=lg, digit_max=dm) for _, _, lg, dm in zk_shapes))
    fig("mask_slices_max", max(mask_length(log_n=lg, digit_max=dm) for _, _, lg, dm in zk_shapes))
    extra = [
        masked_log_beta_inf(log_n=lg, digit_max=dm) - unmasked_log_beta_inf(digit_max=dm)
        for _, _, lg, dm in zk_shapes
    ]
    fig("mask_extra_bits_min", round(min(extra)))
    fig("mask_extra_bits_max", round(max(extra)))
    plain_rates = sorted({u[0] for u, _, _, _ in shapes.values()})
    fig("ajtai_plain_mults", sig(plain_rates[0]))
    fig("ajtai_plain_mults_1024", sig(plain_rates[-1]))
    claim(
        "accumulation_unmasked_rank1",
        "every lattice row's unmasked accumulation matrix is rank 1, at degree 512 or 1,024",
        all(u[1] == 1 and u[2] in ACCUMULATION_DEGREES for u, _, _, _ in shapes.values())
        and plain_rates == [1 + math.log2(d) / 2 for d in ACCUMULATION_DEGREES],
    )
    claim(
        "mask_cost_factor",
        "the masked accumulation matrix's rate is 1.0 to 1.4 times the unmasked one's across the lattice rows, with a rank and a degree more at most, and 14/11 on Kishu's rows",
        min(factors) >= 1.0
        and max(factors) < 1.4
        and all(m[1] <= u[1] + 2 and m[2] >= u[2] for u, m, _, _ in zk_shapes)
        and abs(float(kishu_factor[0]) / float(kishu_factor[1]) - 14 / 11) < 0.01,
    )
    # How the matrices move with the floor: the rows shown at both floors, those whose rank
    # or degree differs between the 128-bit and 147-bit tables, and those that would move at
    # a 150-bit table.
    shape = lambda m: m[1:3]

    def in_force(key, pair):
        """The (rank, degree) of the matrix a row commits under: the masked one for a
        zero-knowledge row (the flag is the key's second-last field), the unmasked otherwise."""
        return shape(pair[1] if key[-2] else pair[0])

    common = [key for (fl, key) in shapes if fl == 128 and (147, key) in shapes]
    moves147 = [
        key
        for key in common
        if in_force(key, shapes[(128, key)]) != in_force(key, shapes[(147, key)])
    ]
    at150 = {key: matrices(v, 150, lg, dm) for key, v, lg, dm, _ in lattice_rows(147)}
    moves150 = [
        key for key in at150 if in_force(key, at150[key]) != in_force(key, shapes[(147, key)])
    ]
    fig("matrix_rows_both_floors", len(common))
    fig("matrix_moves_147", len(moves147))
    fig("matrix_moves_150", len(moves150))
    # A Kishu row's key is (family, check, route, zk, rank); an Akita row's (variant, hash,
    # zk, rank).
    kishu_moves147 = [key for key in moves147 if key[0] in KISHU]
    fig("matrix_moves_147_kishu", len(kishu_moves147))
    claim(
        "matrix_moves_147_blake3_wide",
        "the rows whose accumulation matrix grows from the 128-bit floor to the 147-bit one are BLAKE3 rows of the Akita variants and Kishu's rows at rank 23 without zero knowledge, the widest accumulators",
        bool(kishu_moves147)
        and all(
            (len(key) == 4 and key[1] == "blake3")
            or (key[0] in KISHU and key[3] is False and key[4] == 23)
            for key in moves147
        ),
    )
    claim(
        "kishu_matrix_same_at_150",
        "Kishu's accumulation matrices are the same at 147 and 150 bits",
        all(
            shape(shapes[(147, key)][0]) == shape(at150[key][0])
            and shape(shapes[(147, key)][1]) == shape(at150[key][1])
            for key in common
            if key[0] in KISHU
        ),
    )
    claim(
        "matrix_moves_150_q64_plain",
        "at a 150-bit floor the only accumulation matrices to move are the unmasked ones of the Pasta-claims rows with 64-bit commitments, from degree 512 to 1,024",
        bool(moves150)
        and all(
            len(key) == 4
            and key[0] == "pasta_q64"
            and not key[2]
            and shape(shapes[(147, key)][0]) == (1, 512)
            and shape(at150[key][0]) == (1, 1024)
            for key in moves150
        ),
    )
    # The ℓ∞ route at the note's own example, N = 2^22 base-8 digits (its §5.5).
    note_beta_inf = masked_log_beta_inf()
    fig("note_linf_masked_beta", tex_pow2(sig(note_beta_inf, 3)))
    fig("note_linf_unmasked_beta", tex_pow2(sig(unmasked_log_beta_inf(), 3)))
    u, m = matrices("pasta_sis", 128, MASK_LOG_N, 4)
    fig("note_linf_pasta_masked", f"rank {m[1]} at degree {fmt(m[2])}")
    claim(
        "note_linf_pasta_unchanged",
        "on the ℓ∞ route the note's example over the Pasta modulus has the same accumulation matrix masked and unmasked",
        shape(u) == shape(m),
    )
    u, m = matrices("pasta_q64", 128, MASK_LOG_N, 4)
    fig("note_linf_q64_plain", f"rank {u[1]} at degree {fmt(u[2])}")
    fig("note_linf_q64_masked", f"rank {m[1]} at degree {fmt(m[2])}")
    fig("note_linf_q64_factor", sig(m[0] / u[0], 3))
    # The accumulator's digit vector, N base-8 digits, and the masked one's MASK_LENGTH slices.
    unmasked_bytes = 2**MASK_LOG_N * 3 / 8
    fig("accumulator_mb", mb(unmasked_bytes))
    fig("masked_accumulator_mb", mb(MASK_LENGTH * unmasked_bytes))
    fig("masked_accumulator_mb_alpha6", mb(mask_length(6) * unmasked_bytes, 3))

    # The zero-knowledge note's worked example over Pasta (its §5.3 and §5.4), at the page's
    # parameters: weight-20 challenges in dimension 512, α = 48, N = 2^22 digits, the page's
    # sampler, and 32 word multiplications per Pasta multiplication. The masked rank is Akita's
    # estimator's at the masked bound (NOTE_MASKED_ROWS); the alternatives' rows follow the
    # (log β)² rule, which the estimator confirms at the §5.5 bounds. An attempt commits the
    # mask, N/d NTTs of size d and rows · N/d pointwise products, and draws N samples; the
    # alternatives are α = 12 and 6 at the same challenges, and Karney's sampler.
    note_c_l1, note_d = MASK_CHALLENGE_L1, 512
    assert abs(NOTE_MASKED_ROWS / (ROWS["pasta_sis"] * MASK_RANK) - 1) < 0.01
    fig("note_cs_bound", tex_pow2(sig(math.log2(note_c_l1) + MASK_LOG_S, 3)))
    fig("note_sigma", tex_pow2(sig(mask_log_sigma(), 3)))
    fig("note_z2", tex_pow2(sig(1 + mask_log_sigma() + MASK_LOG_N / 2, 3)))
    fig("note_zinf", tex_pow2(sig(math.log2(MASK_TAIL) + mask_log_sigma(), 3)))
    fig("note_beta", tex_pow2(sig(masked_log_beta(), 3)))
    note_rows = NOTE_MASKED_ROWS
    fig("note_masked_rows", note_rows)
    fig("note_masked_kb", sig(note_rows * 32 / 1000, 3))
    fig("note_unmasked_kb", sig(ROWS["pasta_sis"] * 32 / 1000, 2))
    fig("note_padding_kdigits", sig((note_rows * 255 + 256) / 3 / 1000, 2))
    fig("note_rank_factor", sig(MASK_RANK, 3))
    fig("note_zinf_bits", math.ceil(math.log2(MASK_TAIL) + mask_log_sigma()))
    fig("note_z_mb", mb(2**MASK_LOG_N * math.ceil(math.log2(MASK_TAIL) + mask_log_sigma()) / 8))

    def note_attempt(alpha, c_l1=note_c_l1, d=note_d, sample=MASK_SAMPLE_WORD_MULTS):
        rows = note_rows if alpha == MASK_ALPHA else ROWS["pasta_sis"] * mask_rank(alpha, c_l1)
        commit = 2**MASK_LOG_N * (rows / d + math.log2(d) / 2) * WORD_MULTS["pasta_sis"]
        return commit, 2**MASK_LOG_N * sample

    fig("note_ntts", tex_pow2(sig(MASK_LOG_N + math.log2(math.log2(note_d) / 2), 3)))
    fig("note_pointwise", tex_pow2(sig(MASK_LOG_N + math.log2(note_rows / note_d), 3)))
    fig(
        "note_mults",
        tex_pow2(sig(MASK_LOG_N + math.log2(note_rows / note_d + math.log2(note_d) / 2), 3)),
    )
    commit, sampling = note_attempt(MASK_ALPHA)
    fig("note_word_mults", tex_pow2(sig(math.log2(commit), 3)))
    fold = (commit + sampling) * MASK_ATTEMPTS
    fig("zk_note_commit_s", secs(commit))
    fig("zk_note_sampling_s", secs(sampling))
    fig("zk_note_sampling_over_commit", sig(sampling / commit))
    fig("zk_note_attempt_s", secs(commit + sampling))
    fig("zk_note_fold_s", secs(fold))
    fig("zk_note_fold_alpha12_s", secs(sum(note_attempt(12)) * mask_attempts(12)))
    fig("zk_note_fold_alpha6_s", secs(sum(note_attempt(6)) * mask_attempts(6)))
    fig("zk_note_attempt_alpha6_s", secs(sum(note_attempt(6)), 2))
    fig(
        "zk_note_fold_karney_s",
        secs(sum(note_attempt(MASK_ALPHA, sample=KARNEY_SAMPLE_WORD_MULTS)) * MASK_ATTEMPTS),
    )
    fig("note_batch_alpha48", math.ceil(math.log(0.01) / math.log(1 - 1 / MASK_ATTEMPTS)))
    fig("note_batch_alpha12", math.ceil(math.log(0.01) / math.log(1 - 1 / mask_attempts(12))))
    fig("note_batch_alpha6", math.ceil(math.log(0.01) / math.log(1 - 1 / mask_attempts(6))))
    fig("note_blocks_k", math.ceil(math.log(2**-10 / 256) / math.log(1 - 1 / MASK_ATTEMPTS)))
    claim(
        "mask_fold_phone_seconds",
        "the masking fold is a fraction of a second on a fast core and a few seconds on a phone (the note's §5.8)",
        0.1 <= fold / RATE_PER_S < 1,
    )
    # The note's example is at Pasta's modulus. The transactions a post-quantum Zcash would prove
    # are the migrations, and the page prices them with Kishu, without zero knowledge and with
    # it, on each one's best row.
    plain = [kishu_best(app)[1] for app in MIGRATIONS]
    masked = [kishu_best(app, zk=True)[1] for app in MIGRATIONS]
    fig("zk_note_migration_min_s", secs(min(plain)))
    fig("zk_note_migration_max_s", secs(max(plain)))
    fig("zk_note_migration_zk_min_s", secs(min(masked)))
    fig("zk_note_migration_zk_max_s", secs(max(masked)))
    over = [100 * (m / q - 1) for m, q in zip(masked, plain)]
    fig("zk_note_zk_over_plain_pct_min", sig(min(over), 2))
    fig("zk_note_zk_over_plain_pct_max", sig(max(over), 2))
    claim(
        "kishu_migration_zk_overhead",
        "zero knowledge adds more than a third and less than the whole of a Kishu migration's prover without it",
        all(100 / 3 < x < 100 for x in over),
    )

    for r in (13, 14, 15, 16):
        fig(f"endoscalings_{r}", max_endoscalings(r))
        if r < 16:
            fig(
                f"challenges_per_binder_{r}",
                min(_model["challenges_per_binder"](r), _model["CHALLENGES_BOUND"]),
            )
    fig("pedersen_checked_in_h2_wire_bytes", fmt(ch["bytes"] + 2 * HEADER_ELEMENT_BYTES + 28))


define_figures()

# ---- Filling the markers --------------------------------------------------------------
PROSE_FILES = (
    "pareto-template.html",
    "pasta-proof-size.md",
    "zk-fiat-shamir-with-aborts.md",
    "kishu-arithmetization.md",
    "hardware-wallets.md",
    "zoodles.md",
    "zoodles-epoch-set.md",
    "spend-authorization.md",
    "auth-preimage.md",
    "auth-leansphincs.md",
    "auth-capss.md",
    "recovery-ironwood.md",
    "recovery-tachyon.md",
)
MARKER = re.compile(r"<!--fig:([\w.]+)-->(.*?)<!--/fig-->", re.S)
# A claim's sentence sits between `<!--claim:names:hash-->` and `<!--/claim-->`, the names
# comma-separated where one sentence carries several claims, the hash the first six hex digits
# of SHA-256 over the claims' texts, so that rewording a claim stales its sentence's marker.
CLAIM_MARKER = re.compile(r"<!--claim:([\w,]+):([0-9a-f]*)-->(.*?)<!--/claim-->", re.S)
# The generated pages say which commit of this file their figures come from: the template
# carries `<!--model-commit-->` in its lede, which the outputs replace and the template keeps.
MODEL_COMMIT_MARKER = "<!--model-commit-->"
MODEL_COMMIT_URL = "https://github.com/zcash/pqzcash/commit/"


def model_commit_sentence():
    """The last commit that changed this file, linked, and whether the working copy differs."""
    this = pathlib.Path(__file__).name
    try:
        full, short = subprocess.run(
            ["git", "log", "-1", "--format=%H %h", "--", this],
            cwd=HERE,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split()
        modified = bool(
            subprocess.run(
                ["git", "status", "--porcelain", "--", this],
                cwd=HERE,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
        )
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        return ""
    state = " with uncommitted changes" if modified else ""
    return f' This is commit <a href="{MODEL_COMMIT_URL}{full}"><code>{short}</code></a> of the model{state}.'


def filled(text, used):
    def sub(m):
        name = m.group(1)
        if name not in FIGURES:
            raise SystemExit(f"no figure named {name}")
        used.add(name)
        return f"<!--fig:{name}-->{FIGURES[name]}<!--/fig-->"

    return MARKER.sub(sub, text)


def claim_hash(names):
    return hashlib.sha256("\n".join(CLAIMS[n][0] for n in names).encode()).hexdigest()[:6]


def filled_claims(text, marked):
    def sub(m):
        names = m.group(1).split(",")
        for n in names:
            if n not in CLAIMS:
                raise SystemExit(f"no claim named {n}")
            marked.add(n)
        return f"<!--claim:{m.group(1)}:{claim_hash(names)}-->{m.group(3)}<!--/claim-->"

    return CLAIM_MARKER.sub(sub, text)


# `frontier` serves the printout below; the page computes its own frontiers over the selection.
data = dict(
    points=[{k: v for k, v in p.items() if k != "frontier"} for p in points],
    labels=LABEL,
    applications=APPLICATIONS,
    piop=PIOP_WORK,
    has_mults=APPLICATION_MULTS,
    own_last_steps=OWN_LAST_STEPS,
    leaf_handoff=sorted(LEAF_HANDOFF),
    change_level=CHANGE_LEVEL,
    frontier_tolerance=FRONTIER_TOLERANCE,
    tachyon_header=TACHYON_HEADER,
    header_element_bytes=HEADER_ELEMENT_BYTES,
    pcd_headers=PCD_HEADERS,
    akita_table={f: dict(K=AKITA_K, **t) for f, t in AKITA.items()},
    budget=budget,
    proxies=dict(
        prover="native 64-bit word multiplications for one step's commitments, dense polynomials assumed; see the page",
        per_coefficient={v: round(ajtai_per_coefficient(v)) for v in DIGITS}
        | {"pedersen_rank14": round(pedersen_per_coefficient(14))},
        accumulation="base-field atoms the merge circuit absorbs per fold: 2 per Pedersen commitment; for Akita 120 sum-check elements plus the compressed images at the variant's atom width",
        gates="gates synthesized across every circuit of one merge: measured for Pedersen-IPA, estimated for Akita",
        verify="the decider's verification in word-multiplication equivalents at 3e9 per second: modelled for Pedersen-IPA, measured for Akita and the hash-based verifiers, see the page",
        peak_memory="bytes a fuse holds at its peak: two accumulators, the fold's second-round sum-check table, and the mask under zero knowledge for the lattice rows; two accumulators otherwise",
    ),
)
data["tx_checks"] = tx_checks
assert all(
    sum(p["family"] == c["family"] and p["label"] == c["label"] for p in points) == 1
    for c in tx_checks
)


# The page as the book's chapter embeds it. The standalone page above is one file, with its own
# fonts and light and dark themes, for the published artifact. The book gets the same page in
# four files beside the chapter (scripts/build-book.sh copies them): the HTML with the text, a
# stylesheet scoped to the page's wrapper and coloured from mdbook's theme variables, the script,
# and the data as a script that sets a global, so that mdbook's search index sees the text and
# not the data, and the built book works from a file: URL, where a fetch would be refused. The
# chapter includes the HTML with `{{#include}}`; it has no blank lines, so Markdown sees one
# HTML block.
BOOK_THEME_VARIABLES = (
    "--surface: var(--bg); --ink: var(--fg); --muted: var(--icons); --rule: var(--quote-border); "
    "--accent: var(--links); --accent-ink: var(--links); --mono: var(--mono-font);"
)
BOOK_DARK_THEMES = ".coal #pareto, .navy #pareto, .ayu #pareto"
BOOK_DROPPED_RULES = ("body", "h1", "h2", "h3", "h4", "h5", "p")  # the book's typography applies
BOOK_DROPPED_DECLARATIONS = (
    "font-family: var(--serif);",
    "font-family: var(--sans);",
    "font-size: 16px; line-height: 1.55;",  # .prose
)
# The tables take the book's header fill, and every row is filled: odd rows in the book's
# alternate-row colour, even rows in that colour deepened by a little of the text colour. So
# the table reads as a surface of its own rather than as stripes on the page. The page's own
# rule under each row replaces mdbook's grid of cell borders.
BOOK_EXTRA_CSS = """\
#pareto.wrap { padding: 0; }
#pareto a.header { color: inherit; }
#pareto th { color: var(--fg); }
#pareto table tbody tr { background: var(--table-alternate-bg); }
#pareto table tbody tr:nth-child(2n) { background: color-mix(in srgb, var(--table-alternate-bg), var(--fg) 6%); }
#pareto table th, #pareto table td { border: 0; border-bottom: 1px solid var(--rule); }
"""


def css_rules(text):
    """The stylesheet's top-level items: (prelude, body) for each block, or (comment, None)."""
    items, i = [], 0
    while i < len(text):
        while i < len(text) and text[i].isspace():
            i += 1
        if i == len(text):
            break
        if text.startswith("/*", i):
            j = text.index("*/", i) + 2
            items.append((text[i:j].strip(), None))
            i = j
            continue
        j = text.find("{", i)
        if j < 0:
            break
        depth, k = 1, j + 1
        while depth:
            if text[k] == "{":
                depth += 1
            elif text[k] == "}":
                depth -= 1
            k += 1
        items.append((text[i:j].strip(), text[j + 1 : k - 1]))
        i = k
    return items


def scope_css(text):
    """Every rule under the page's wrapper; the theme blocks and the dropped rules left out."""
    out = []
    for prelude, body in css_rules(text):
        if body is None:
            out.append(prelude)
            continue
        if prelude.startswith(":root") or prelude in BOOK_DROPPED_RULES:
            continue
        if prelude.startswith(("@media", "@container")):
            if "prefers-color-scheme" in prelude:
                continue
            out.append(f"{prelude} {{\n{scope_css(body)}\n}}")
            continue
        for d in BOOK_DROPPED_DECLARATIONS:
            body = body.replace(d, "")
        selectors = [s.strip() for s in prelude.split(",")]
        scoped = ", ".join(
            "#pareto" + s if s.startswith(".wrap") else f"#pareto {s}" for s in selectors
        )
        out.append(f"{scoped} {{{body}}}")
    return "\n".join(out)


def mdbook_id(heading):
    """The id mdbook gives a heading: lowercased, with letters, digits, '_' and '-' kept,
    whitespace turned into hyphens and everything else dropped."""
    return "".join(
        "-" if ch.isspace() else ch.lower() if ch.isalnum() or ch in "_-" else "" for ch in heading
    )


def write_book_files(page, data_json):
    style = page[page.index("<style>") + 7 : page.index("</style>")]
    body = page[page.index("</style>") + 8 : page.index('<script src="https://cdnjs')]
    plotly = page[page.index('<script src="https://cdnjs') : page.index("<script>\n")]
    script = page[page.index("<script>\n") + 9 : page.rindex("</script>")]
    palettes = re.findall(r"--c-[a-z0-9]+: #[0-9a-fA-F]+;", style)
    half = len(palettes) // 3  # the light palette, then the same dark one twice
    assert palettes[half : 2 * half] == palettes[2 * half :], "the two dark palettes differ"
    light, dark = " ".join(palettes[:half]), " ".join(palettes[half : 2 * half])
    # The plot and the controls keep the standalone page's dark theme, for contrast, whatever
    # the book's theme; the text around them follows the book.
    panel = next(
        body for prelude, body in css_rules(style) if prelude == ':root[data-theme="dark"]'
    )
    panel = " ".join(
        d.strip() + ";" for d in panel.split(";") if d.strip() and not d.strip().startswith("--bg:")
    )
    css = (
        f"#pareto {{ {BOOK_THEME_VARIABLES} {light} }}\n{BOOK_DARK_THEMES} {{ {dark} }}\n"
        f"#pareto .top {{ {panel} color: var(--ink); }}\n"
        + scope_css(style)
        + "\n"
        + BOOK_EXTRA_CSS
    )
    # mdbook wraps a Markdown heading's text in a link to its own anchor, which carries the
    # hover cue and the click-to-link; the page's headings are HTML, so they get the same.
    body = re.sub(
        r'<h([2-5]) id="([^"]+)">(.*?)</h\1>',
        r'<h\1 id="\2"><a class="header" href="#\2">\3</a></h\1>',
        body,
    )
    # References to a note's sections link to its chapter in the book; the standalone page shows
    # them as text. The ids are the ones mdbook gives the note's headings. The zero-knowledge
    # note is the default; `data-note` names another, by its key in NOTE_CHAPTERS, whose values
    # are the source file beside this one and the chapter's path from the page's directory.
    # `data-section` is a numbered section of the note, or a heading's id written with its `#`.
    NOTE_CHAPTERS = {
        "zk": ("zk-fiat-shamir-with-aborts.md", "kishu/zk-fiat-shamir-with-aborts.html"),
        "kishu-arithmetization": ("kishu-arithmetization.md", "kishu/arithmetization.html"),
        "hardware-wallets": (
            "hardware-wallets.md",
            "../zoodles/spend-authorization/hardware-wallets.html",
        ),
        "spend-authorization": ("spend-authorization.md", "../zoodles/spend-authorization.html"),
    }
    note_ids = {
        name: {
            m.group(1): mdbook_id(f"{m.group(1)} {m.group(2)}")
            for m in re.finditer(
                r"^#{2,4} (\d+(?:\.\d+){0,2})\.? (.+)$",
                pathlib.Path(__file__).with_name(source).read_text(),
                flags=re.M,
            )
        }
        for name, (source, _) in NOTE_CHAPTERS.items()
    }

    def note_link(m):
        name = m.group(1) or "zk"
        target = NOTE_CHAPTERS[name][1]
        if sec := m.group(2):
            target += sec if sec.startswith("#") else "#" + note_ids[name][sec]
        return f'<a href="{target}">{m.group(3)}</a>'

    body = re.sub(
        r'<span class="noteref"(?: data-note="([a-z-]+)")? data-section="([\w.#-]*)">(.*?)</span>',
        note_link,
        body,
    )
    lines = [ln for ln in body.split("\n") if ln.strip() and not ln.strip().startswith("<h1>")]
    html = (
        '<link rel="stylesheet" href="pareto.css">\n'
        + "\n".join(lines)
        + "\n"
        + plotly.strip()
        + '\n<script src="pareto-data.js"></script>\n<script src="pareto.js"></script>\n'
    )
    assert "<h1" not in html and "\n\n" not in html
    assert script.count("const DATA = /*DATA*/;") == 1
    js = (
        "(function (DATA) {\n"
        "if (!DATA) { document.getElementById('selfcheck').textContent = 'The page\\'s data, pareto-data.js, did not load.'; return; }\n"
        + script.replace("const DATA = /*DATA*/;\n", "")
        + "})(window.PARETO_DATA);\n"
    )
    (HERE / "pareto-book.html").write_text(html)
    (HERE / "pareto.css").write_text(css)
    (HERE / "pareto.js").write_text(js)
    (HERE / "pareto-data.js").write_text("window.PARETO_DATA = " + data_json + ";\n")


# Fill the markers: pareto.html always from the model; the tracked files only with `--fill`,
# and otherwise the run fails on a stale value, as it does on a failed claim. `--figures`
# lists every figure.
fill = "--fill" in sys.argv
if "--figures" in sys.argv:
    for name, value in FIGURES.items():
        print(f"{name} = {value}")
    for name, (text, _) in CLAIMS.items():
        print(f"claim {name}: {text}")
    for app, row in KISHU_ZK_ALPHA.items():
        print(f"kishu zk optimum {app}: {row}")
used, marked, stale, stale_claims, dangling, marker_led = set(), set(), [], [], [], []
for name in PROSE_FILES:
    path = HERE / name
    text = path.read_text()
    if name.endswith(".md"):
        # CommonMark starts an HTML block at a line beginning with `<!--`, even inside a
        # paragraph, which would render the rest of the paragraph literally.
        marker_led += [
            f"{name}:{n}"
            for n, line in enumerate(text.split("\n"), 1)
            if line.lstrip().startswith("<!--")
        ]
    new = filled_claims(filled(text, used), marked)
    stale += [
        (name, m.group(1), m.group(2), n.group(2))
        for m, n in zip(MARKER.finditer(text), MARKER.finditer(new))
        if m.group(2) != n.group(2)
    ]
    stale_claims += [
        (name, m.group(1), m.group(2), n.group(2))
        for m, n in zip(CLAIM_MARKER.finditer(text), CLAIM_MARKER.finditer(new))
        if m.group(2) != n.group(2)
    ]
    if text.count("<!--claim:") != text.count("<!--/claim-->"):
        dangling.append(name)
    if name == "pareto-template.html":
        data_json = json.dumps(data, separators=(",", ":"))
        stamped = new.replace(MODEL_COMMIT_MARKER, model_commit_sentence())
        (HERE / "pareto.html").write_text(stamped.replace("/*DATA*/", data_json))
        write_book_files(stamped, data_json)
    if fill and new != text:
        path.write_text(new)
for name, figure, old, new in stale:
    print(f"{name}: fig:{figure}: {old!r} -> {new!r}", file=sys.stderr)
for name, names, old, new in stale_claims:
    print(f"{name}: claim:{names}: {old!r} -> {new!r}; the claim now reads:", file=sys.stderr)
    for n in names.split(","):
        print(f"    {n}: {CLAIMS[n][0]}", file=sys.stderr)
failed = [f"{name}: {text}" for name, (text, holds) in CLAIMS.items() if not holds]
for text in failed:
    print(f"claim no longer holds: {text}", file=sys.stderr)
if unused := set(FIGURES) - used:
    print(f"figures not used in any file: {', '.join(sorted(unused))}", file=sys.stderr)
unmarked = sorted(set(CLAIMS) - marked)
if unmarked:
    print(f"claims with no marked sentence in any file: {', '.join(unmarked)}", file=sys.stderr)
for name in dangling:
    print(f"{name}: unbalanced claim markers", file=sys.stderr)
for where in marker_led:
    print(
        f"{where}: a marker starts the line, which Markdown renders as an HTML block",
        file=sys.stderr,
    )
if (stale or stale_claims) and not fill:
    print(
        f"{len(stale)} stale figures and {len(stale_claims)} stale claim markers in the tracked files; run `python pareto-model.py --fill` to update them",
        file=sys.stderr,
    )
if failed or unmarked or dangling or marker_led or ((stale or stale_claims) and not fill):
    sys.exit(1)
pre = [p for p in points if not p["pq"]]
post = [p for p in points if p["pq"] and p["zk"] is not True and p["floor"] == 128]
post_zk = [p for p in points if p["pq"] and p["zk"] is not False and p["floor"] == 128]
print(
    f"{len(points)} points after pruning {pruned} dominated within their family: {len(pre)} Pedersen-IPA with {sum(p['frontier'] for p in pre)} on its frontier, "
    f"{len(post)} post-quantum with {sum(p['frontier'] for p in post)} on its frontier, "
    f"{len(post_zk)} post-quantum zero-knowledge with {sum(p['frontier'] for p in post_zk)}; wrote pareto.html"
)

for p in sorted(
    [p for p in points if p["frontier"] and p["floor"] != 147],
    key=lambda p: (p["pq"], p["hashes"], p["bytes"]),
):
    print(
        f"  {p['family']:10} {p['label']}: {p['bytes']:,} B, prover {p['prover']:.3g}, atoms {p['accumulation']}, gates {p['gates']:,}"
    )
