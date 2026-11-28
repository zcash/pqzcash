# The hiding padding's knapsack-LWE hardness (the hardware-wallets chapter, HIDING_PADDING_*
# in the model): Aρ for ρ of 5,000 uniform bits under the device's masked accumulation matrix
# is pseudorandom if knapsack-LWE is hard at the matrix's rows, which by the Micciancio–Mol
# duality is LWE of dimension bits − rows with rows samples and binary secret and error at the
# 64-bit modulus. Every attack of the pinned lattice estimator is costed under the ADPS16
# quantum model, as the page's SIS instances are, at the ℓ∞ route's 1,024 rows, the
# zero-knowledge note's Euclidean 1,385, and 2,048; then the padding is swept at the device's
# rows so that the page can take the least that reaches each floor. Run from ragu-pcs, with
# the estimator in the Akita clone's third_party submodule (scripts/akita-checkout.sh), under
# work/ or $RAGU_PCS_WORK: `sage scripts/knapsack-lwe-check.py`.
#
# With arguments it runs one sweep only, at other rows: `sage scripts/knapsack-lwe-check.py ROWS
# START STOP STEP`, the padding from START to STOP bits inclusive. The 165-bit level's wallet
# matrix has 2,048 rows, where the padding that reaches a floor is longer.
import os
import sys

WORK = os.environ.get("RAGU_PCS_WORK", os.path.join(os.getcwd(), "work"))
sys.path.insert(0, os.path.join(WORK, "akita-src", "third_party", "lattice-estimator"))
from estimator import LWE, ND
from estimator.reduction import ADPS16
from sage.all import log

q = 2**64 - 59
attacks = (
    ("primal_usvp", LWE.primal_usvp),
    ("primal_bdd", LWE.primal_bdd),
    ("primal_hybrid", LWE.primal_hybrid),
    ("dual_hybrid", LWE.dual_hybrid),
)


def instance(rows, bits):
    return LWE.Parameters(
        n=bits - rows,
        q=q,
        Xs=ND.Uniform(0, 1),
        Xe=ND.Uniform(0, 1),
        m=rows,
        tag=f"rows{rows}bits{bits}",
    )


def cost(attack, params):
    c = attack(params, red_cost_model=ADPS16(mode="quantum"))
    return float(log(c["rop"], 2)), c.get("beta"), c.get("d")


def sweep(rows, grid):
    print("sweep: rows,bits,primal_usvp,dual_hybrid", flush=True)
    for bits in grid:
        params = instance(rows, bits)
        primal = cost(LWE.primal_usvp, params)[0]
        dual = cost(LWE.dual_hybrid, params)[0]
        print(f"sweep: {rows},{bits},{primal:.1f},{dual:.1f}", flush=True)


if len(sys.argv) > 1:
    rows, start, stop, step = (int(a) for a in sys.argv[1:5])
    sweep(rows, range(start, stop + 1, step))
    sys.exit(0)

for rows in (1024, 1385, 2048):
    params = instance(rows, 5000)
    print(params, flush=True)
    for name, attack in attacks:
        bits_, beta, d = cost(attack, params)
        print(f"  {name}: rop 2^{bits_:.1f} beta {beta} d {d}", flush=True)

# The sweep at the device's rows, the two attacks that are ever the cheapest above: steps of
# 250 bits, and of 50 where the two floors are crossed.
grid = sorted({*range(3500, 6001, 250), *range(4250, 5001, 50)})
sweep(1024, grid)
