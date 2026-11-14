# Spike: Kishu (BitZ over Akita), the Booleanity-by-projection frontend

`booleanity_spike.py` is a toy of Kishu, the study's BitZ-over-Akita frontend: the internal draft
"Efficient Booleanity Checking via Structured Modular Projections" (2026-09-23) together with
the decoupled-modulus bridge of `pasta-proof-size.md` §6.3. It is pure Python 3 with no
dependencies and runs in under a second at n = 2^12. `python booleanity_spike.py [seed]` runs an
honest prover and three cheats and asserts the outcomes. It exists to make the protocol
concrete, not to be fast or secure.

## What it does

1. **Source.** n = 2^12 bits in F_q, q = 2^64 − 59; the first 255 are a Pasta field element's
   bits, the rest random. A mocked commitment (`Oracle`) answers one evaluation ŝ(ρ) over
   E = F_q[u]/(u² − 2), standing in for Akita's opening of a binary source.
2. **Projection** (draft §5.1). g = 4 independent tensor chains of balanced-ternary cores
   A_i ∈ {−1, 0, 1}^(c_i × c_{i−1} × d_i), entries with probabilities 1/4, 1/2, 1/4, over the
   address factorization n = 256 · 4 · 4 with channel widths c = (8, 8, 6). The prover reveals
   y = T s, 24 field elements; the verifier checks each chain's **centered integer energy**
   Σ ctr_q(y_i)² against an integer bound C.
3. **The lift** (Theorem 1). With E_x = Σ ctr_q(s_i)² < Q0 and Q0 + √(n Q0) < q, the field
   identity Σ s_i(s_i − 1) = 0 holds over the integers, so every entry is a bit. At q ≈ 2^64 and
   n = 2^12 the theorem admits Q0 up to 2^64.0; an honest source has E_x ≤ n = 2^12. The
   projection only has to separate energies 2^52 apart, which is why a cheap sketch suffices.
4. **One quadratic sum-check** (draft equation 6). λ ∈ E^24 batches the 24 projection claims
   ⟨T_row, s⟩ = y_row with the defect: Σ_a ŝ(a)(ŝ(a) − 1) + ŝ(a) ŵ(a) = ⟨λ, y⟩ with
   w = T^T λ. Twelve rounds, three E elements each, final check c = v(v − 1 + ŵ(ρ)) with
   v = ŝ(ρ) from the oracle. The verifier evaluates ŵ(ρ) by the backward contraction through
   the cores (draft §4.1): about 10,000 coefficient operations instead of n, and the spike
   asserts it equals the materialized table's evaluation.
5. **Pasta claims** (§6.3). The 255 bits are read as eight 32-bit limbs ⟨c_j, s⟩; each is an
   integer below 2^32 < q, so its F_q inner product is its integer inner product (no wrap, given
   Booleanity and n ≤ 2^31). The limb claims join the same sum-check through weights μ_j, and the
   verifier recomposes V = Σ 2^(32 j) v_j over the integers and reduces modulo p.
6. **The comparison law** (draft equation 13, with CertifiedJL's constants K = 681/1250 and
   t = 25123/10000). `lower_tail` convolves the log-densities of Z_c = (b_c − X)^+ and gives the
   single-chain error for a source of energy at least Q0: 0.045 for these toy cores, and
   4 × 10^-6 over four chains, about 2^-18. The draft's 4 × (43, 43, 43, 43, 40) chains at
   n = 2^27 reach 2^-136 with 160 revealed coordinates.

## The four scenarios

| scenario | energy check | sum-check | Pasta claim |
|---|---|---|---|
| honest | ok | ok | recomposes to the committed value |
| two large entries whose defects cancel modulo q | **fails** (chain energies ≈ 2^127) | ok | ok |
| prover alters one revealed y | ok | **fails** | ok |
| prover alters one limb value | ok | **fails** | wrong value |

The second row is the point of the construction: the field identity alone accepts a
non-Boolean source, and the projection is what rejects it.

## What the real system adds

- Akita's opening of ŝ(ρ) for a binary source committed in its binary groups (the `dev`
  branch's `binary` feature, tracked by LayerZero-Labs/akita#285, measured in its PRs #312 and
  #428), and the extension-field evaluation claim it must authenticate; the openings here cost
  nothing.
- Fiat–Shamir, including the AES counter-mode derivation of the cores; and hiding, which
  revealing y forgoes (the study's zero-knowledge rows use Akita's mask on the rows term).
- The certified parameters: the honest-rejection bound (draft equation 14, here Markov at p = 1
  giving C = 2^59.6), the comparison-law certificate at 2^-136, and the exact-arithmetic checks.
- The prover's packed-bit first layer and implicit-bit startup (draft §4.2), which are what make
  it 113 ms at 2^27 bits; the toy materializes everything.
- The merge circuit: `frontend_merge_digits` in `pareto-model.py` prices absorbing the
  sum-check transcript, the revealed coordinates and the claims, and the projection verifier's
  coefficient scan in the sum-check form.

## Mapping to the page's `bits_q64` row

The row charges 255 one-bit digits per Pasta value (the limbs' coefficient vectors cost
nothing to commit), 2.5 word multiplications per bit for the projection check or 9.8 for the
conventional sum-check, the revealed coordinates and sum-check messages as payload bytes, and
the merge as above. The spike's shapes agree with the row's assumptions: one evaluation claim
per sum-check, three E elements per round, and r = g · c_L revealed coordinates.
