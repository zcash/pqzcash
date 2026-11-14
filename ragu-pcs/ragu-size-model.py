"""Compressed Ragu proof size model, counted from the structs (pasta-proof-size.md §8).

Instance: circuit_id (4 B), two headers (H field elements each), the six online openings
(a point and a value for each of the two online polynomial slots of the left, right and
output proofs), native commitments (native_NUM + 2 for AbA/AbB, + registry_xy + p, + the
two online polynomial commitments), nested commitments (nested_NUM + 2, + registry_xy + p
+ challenges_partial), 19 scalars. This is the payload of Ragu's wire format
(`CompressedProof::encoded_len`, tachyon-zcash/ragu 8109a41c), which adds a 28-byte
versioned envelope: 7,908 + 28 = 7,936 bytes at rank 13 with four-element headers.
Per curve: fold (2 points, 2 scalars), p, q, 5 openings, p(1/r), q(r); batch f + 11
evaluations; IPA s_commitment + RANK rounds of 2 points + c.
Component counts: native_NUM = Fn + binders + native_steps, nested_NUM = Fm + nested_steps,
steps = max(1, ceil((points - 1)/E)), and each side's batched points are
1 + 2*(other_NUM + per_child) + extra, with per_child = 4 and extra = 6 as checked in.

Usage: python ragu-size-model.py            # checked-in configuration and knob sensitivity
       python ragu-size-model.py search      # broad grid search, summary near a target
       python ragu-size-model.py search 5900 # other target
       python ragu-size-model.py budget      # circuit budget per rank and the smallest feasible proof
"""
import itertools, math, sys
P = S = 32
# Online polynomial slots per proof (ragu_pcd's NUM_ONLINE_POLYNOMIALS); a step opens its two
# children's and its own, so the instance carries 3 * ONLINE_POLYS openings.
ONLINE_POLYS = 2

def steps(points, E):
    return max(1, math.ceil((points - 1) / E))

def counts(Fn, Fm, binders, En, Em, per_child=4, extra=6):
    if En * Em <= 4:
        return None  # each component feeds 2/E components to the other side: divergent
    nat, nes = Fn + binders + 1, Fm + 1
    for _ in range(100):
        nes_new = Fm + steps(1 + 2 * (nat + per_child) + extra, Em)
        nat_new = Fn + binders + steps(1 + 2 * (nes_new + per_child) + extra, En)
        if (nat_new, nes_new) == (nat, nes):
            return nat, nes
        nat, nes = nat_new, nes_new
    return None

def size(Fn, Fm, binders, En, Em, rank, H, per_child=4, extra=6):
    c = counts(Fn, Fm, binders, En, Em, per_child, extra)
    if c is None:
        return None
    nat, nes = c
    online = 2 * 3 * ONLINE_POLYS * S + ONLINE_POLYS * P
    instance = 4 + 2 * H * S + online + (nat + 2 + 2) * P + (nes + 2 + 3) * P + 19 * S
    per_curve = (2 * P + 2 * S) + 2 * P + 5 * S + 2 * S + (P + 11 * S) + (P + 2 * rank * P + S)
    return instance + 2 * per_curve, nat, nes

# ---- Circuit budget ----------------------------------------------------------------
# A step circuit at rank r has 2^(r-2) gates and four times as many constraints (2,048 and
# 8,192 at rank 13). The figures below are the internal circuits' synthesis counts pinned
# in ragu_pcd's internal tests at rank 13, and the capacity chapter of the book.

def gate_budget(rank):
    return 1 << (rank - 2)

def constraint_budget(rank):
    return 4 * gate_budget(rank)

# The fixed circuits of each side (gates). The remaining components of each side are stage
# polynomials, which the rank does not change.
NATIVE_FIXED = dict(hashes_1=1992, hashes_2=2044, inner_collapse=1921, outer_collapse=1592,
                    compute_v=1834, bind_beta=2029, bind_endoscalar=780)
NESTED_FIXED = dict(export=1384, collapse=1624, compute_v=1661, loading=776)
NATIVE_OTHER = 19 - len(NATIVE_FIXED)
NESTED_OTHER = 14 - len(NESTED_FIXED)
# A native endoscaling step: 2,026 gates and 3,678 constraints for four points, 1,108 and
# 1,842 for two. The nested step is 2,043 gates for four points.
STEP_GATES_PER_POINT, STEP_GATES_OVERHEAD = 459, 190
STEP_CONSTRAINTS_PER_POINT, STEP_CONSTRAINTS_OVERHEAD = 918, 6
NESTED_STEP_GATES_OVERHEAD = 207
# A binder: about 1,985 gates for two of the ten challenges. Per challenge, a 128-bit
# decomposition (128 boolean gates), a fixed-base endoscaling (455, the chained endoscalar
# operation of the capacity chapter) and the running sum come to about 590; the remaining
# 805 is taken as the circuit's overhead. This split is derived, not measured.
BINDER_GATES_PER_CHALLENGE, BINDER_GATES_OVERHEAD = 590, 805
CHALLENGES_BOUND = 10

def max_endoscalings(rank, nested=False):
    """The most endoscalings one step circuit holds at this rank."""
    overhead = NESTED_STEP_GATES_OVERHEAD if nested else STEP_GATES_OVERHEAD
    by_gates = (gate_budget(rank) - overhead) // STEP_GATES_PER_POINT
    by_constraints = (constraint_budget(rank) - STEP_CONSTRAINTS_OVERHEAD) // STEP_CONSTRAINTS_PER_POINT
    return min(by_gates, by_constraints)

def challenges_per_binder(rank):
    return (gate_budget(rank) - BINDER_GATES_OVERHEAD) // BINDER_GATES_PER_CHALLENGE

def min_binders(rank):
    """The fewest binder circuits that bind the ten challenges at this rank."""
    return math.ceil(CHALLENGES_BOUND / challenges_per_binder(rank))

def packed(fixed, rank):
    """How many circuits of this rank hold the fixed circuits, by first-fit decreasing
    packing of their gate counts. Merging circuits is a design change, not a parameter."""
    bins = []
    for g in sorted(fixed.values(), reverse=True):
        for i, b in enumerate(bins):
            if b + g <= gate_budget(rank):
                bins[i] = b + g
                break
        else:
            bins.append(g)
    return len(bins)

def fixed_counts(rank, packing):
    """(Fn, Fm): the fixed component counts, as today or with the fixed circuits packed."""
    if not packing:
        return 19, 14
    return NATIVE_OTHER + packed(NATIVE_FIXED, rank), NESTED_OTHER + packed(NESTED_FIXED, rank)

def feasible(rank, En, Em, binders):
    return (En <= max_endoscalings(rank) and Em <= max_endoscalings(rank, nested=True)
            and binders >= min_binders(rank))

def gates_per_merge(binders, En, Em, nat, nes, per_child=4, extra=6):
    """Gates synthesized across every circuit of one merge, both sides."""
    native_points = 1 + 2 * (nes + per_child) + extra
    nested_points = 1 + 2 * (nat + per_child) + extra
    native_steps = steps(native_points, En)
    nested_steps = steps(nested_points, Em)
    return (sum(NATIVE_FIXED.values()) + sum(NESTED_FIXED.values())
            + (native_points - 1) * STEP_GATES_PER_POINT + native_steps * STEP_GATES_OVERHEAD
            + (nested_points - 1) * STEP_GATES_PER_POINT + nested_steps * NESTED_STEP_GATES_OVERHEAD
            + CHALLENGES_BOUND * BINDER_GATES_PER_CHALLENGE + binders * BINDER_GATES_OVERHEAD)

def budget_report():
    print("rank  gates  endoscalings/step (native, nested)  binders  fixed circuits packed (native, nested)")
    for rank in (13, 14, 15, 16):
        print(f"{rank:4} {gate_budget(rank):6}  {max_endoscalings(rank):2}, {max_endoscalings(rank, True):2}"
              f"{'':24}{min_binders(rank):2}       {packed(NATIVE_FIXED, rank)} of {len(NATIVE_FIXED)}, "
              f"{packed(NESTED_FIXED, rank)} of {len(NESTED_FIXED)}")
    print("\nsmallest feasible proof at each rank (header 2 / header 4), with gates per merge:")
    for rank in (13, 14, 15, 16):
        for packing in (False, True):
            if packing and fixed_counts(rank, True) == (19, 14):
                continue
            Fn, Fm = fixed_counts(rank, packing)
            En, Em, b = max_endoscalings(rank), max_endoscalings(rank, True), min_binders(rank)
            r2, r4 = size(Fn, Fm, b, En, Em, rank, 2), size(Fn, Fm, b, En, Em, rank, 4)
            assert r2 is not None and r4 is not None
            g = gates_per_merge(b, En, Em, r2[1], r2[2])
            print(f"  rank {rank}, E {En}/{Em}, {b} binders, fixed {'packed' if packing else 'as today'}"
                  f" ({Fn}, {Fm}): {r2[0]} / {r4[0]} B; components {r2[1]} + {r2[2]}; {g:,} gates per merge")

CHECKED_IN = dict(Fn=19, Fm=14, binders=5, En=4, Em=4, rank=13, H=4)

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "budget":
        budget_report()
        return
    if len(sys.argv) > 1 and sys.argv[1] == "search":
        target = int(sys.argv[2]) if len(sys.argv) > 2 else 5900
        Es = (1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 24, 32)
        grid = dict(Fn=range(15, 20), Fm=range(11, 15), binders=range(0, 9), En=Es, Em=Es,
                    rank=(13, 14, 15), H=range(0, 9), per_child=(3, 4, 5), extra=(4, 5, 6, 7, 8))
        keys = list(grid)
        rows = []
        for combo in itertools.product(*grid.values()):
            kw = dict(zip(keys, combo))
            r = size(**kw)
            if r is None:
                continue
            t, nat, nes = r
            rows.append((t, nat, nes, combo))
        print(f"grid size {len(rows)}; total range {min(r[0] for r in rows)} .. {max(r[0] for r in rows)}")
        near = [r for r in rows if abs(r[0] - target) <= 50]
        print(f"within 50 B of {target}: {len(near)} combinations")
        # Which single-knob changes from the checked-in config at rank 14 reach the target region?
        print("\nnearest to target with at most two knobs changed from the checked-in configuration (rank forced to 14):")
        base = dict(CHECKED_IN); base["rank"] = 14; base.update(per_child=4, extra=6)
        found = []
        for r in rows:
            kw = dict(zip(keys, r[3]))
            changed = [k for k in keys if k != "rank" and kw[k] != base[k]]
            if len(changed) <= 2 and kw["rank"] == 14 and abs(r[0] - target) <= 100:
                found.append((abs(r[0] - target), r[0], {k: kw[k] for k in changed}))
        if not found:
            print("  none within 100 B of the target")
        for d, t, ch in sorted(found)[:15]:
            print(f"  {t} B  changes: {ch}")
        # The parts of the proof that no parameter in the grid touches.
        fixed = 19 * S + 2 * ((2 * P + 2 * S) + 2 * P + 5 * S + 2 * S + (P + 11 * S)) + 2 * (P + 2 * 14 * P + S) + 4
        print(f"\nparameter-independent part at rank 14 (19 instance scalars, both curves' reductions and batches, both IPAs, id): {fixed} B")
        print("minimum instance commitments (one step per side, no binders, smallest fixed component counts in the grid):",
              (15 + 0 + 1 + 4 + 11 + 1 + 5) * P, "B")
        print("\nplausible region (E <= 8 on both sides, H >= 2, rank 14, binders >= 1, checked-in batching constants):")
        pl = [r for r in rows if dict(zip(keys, r[3]))["En"] <= 8 and dict(zip(keys, r[3]))["Em"] <= 8
              and dict(zip(keys, r[3]))["H"] >= 2 and dict(zip(keys, r[3]))["rank"] == 14
              and dict(zip(keys, r[3]))["binders"] >= 1 and dict(zip(keys, r[3]))["per_child"] == 4
              and dict(zip(keys, r[3]))["extra"] == 6]
        best = min(pl)
        print("  minimum:", best[0], "B at", dict(zip(keys, best[3])))
        pn = sorted(r for r in pl if abs(r[0] - target) <= 50)
        print(f"  within 50 B of {target}: {len(pn)}")
        for r in pn[:10]:
            print("   ", r[0], dict(zip(keys, r[3])))
        return
    t, nat, nes = size(**CHECKED_IN)
    print("checked-in configuration:", CHECKED_IN, "->", t, "bytes; native/nested components", nat, nes)
    print("knob sensitivity from the checked-in configuration at rank 14, H=4:")
    for En in (4, 6, 8, 12, 16, 32):
        kw = dict(CHECKED_IN, rank=14, En=En, Em=En)
        print(f"  E={En:2d} both sides:", size(**kw)[0], counts(19, 14, 5, En, En))
    for b in (5, 3, 1, 0):
        print(f"  binders={b}, E=8 both:", size(**dict(CHECKED_IN, rank=14, En=8, Em=8, binders=b))[0])
    for H in (0, 2, 4, 8):
        print(f"  H={H}, E=8 both:", size(**dict(CHECKED_IN, rank=14, En=8, Em=8, H=H))[0])

if __name__ == "__main__":
    main()
