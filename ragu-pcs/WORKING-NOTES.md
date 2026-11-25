# Working notes: Ragu + Akita proof-size work (as of 2026-10-14)

State of everything, for picking up after a context reset. Paths are relative to this
directory (`ragu-pcs`). The two substantive notes are
`zk-fiat-shamir-with-aborts.md` (zero knowledge for a lattice accumulation step) and
`pasta-proof-size.md` (proof sizes at a Pasta modulus; §6 decoupled commitment modulus;
§8 conclusions as a PCD scheme; §8.1 measured Pedersen-IPA size, group dependence, prover
word multiplications). The Akita paper is ePrint 2026/1983; `work/akita.txt` is its text.

## Code

- Akita scratch clone: `work/akita-src` at commit 60b82bc30f4f8f1130ccd71fe10b0b9bed909ab9,
  patched; the full diff is `akita-pasta-widths.patch` here (regenerate with `git diff` after
  `git add --intent-to-add` of the two new examples; regenerated 2026-10-15 with the 150-bit
  estimator changes, 22 files). Additions: `pallas`/`goldilocks` moduli
  in the estimator; `pasta_rank` example; `with_field_widths` re-pricing; `FieldWidthOverride`
  with `commitment_field_bits`; `expanded_schedule_proof_breakdown`; process-wide pricing
  override read from `AKITA_PRICING_WIDTHS=base:challenge:ext[:commitment]` by
  `gen_schedule_artifacts`; `catalog_reprice` example (`--artifacts DIR`); terminal pricing
  split (`terminal_response_planner_bytes_split`) routed into the planner's suffix search and
  the catalog estimate. Build: `RUSTUP_TOOLCHAIN=1.96.0 cargo build --release -p akita-planner
  --features catalog-security --bin gen_schedule_artifacts --examples`.
- Ragu (a local checkout of `tachyon-zcash/ragu`, branch main at 8109a41c, 2026-11-13, clean):
  upstream's wire format (`crates/ragu_pcd/src/wire/`, PR #875) gives
  `CompressedProof::<Pasta>::encoded_len::<R, HEADER_SIZE>()`, the exact encoded length with its
  28-byte envelope. Our earlier uncommitted `encoded_len` (which pinned 7,460 at the fork's
  526b0e3e) was superseded by it and dropped on 2026-11-14 (commits 1cdfcb90 and 9a2388fa, in the
  reflog only). Measure by appending a scratch test to `tests/compress.rs` (compiled into the lib's
  tests) that prints the values with `std::println!`, run with
  `cargo test -p ragu_pcd --lib <name> -- --nocapture`, and revert; only ranks 7, 13 and 14 have
  `Rank` instances.

## Data and scripts here

- `work/`: the Akita clone, the build and run logs, and earlier drafts of the scripts.
- `estimates/`: a copy of the outputs of `work/akita-pasta-estimates.sh`, whose originals with
  their logs are in `work/akita-pasta-out/` (summary.txt; L2 and Linf width
  tables for pallas and goldilocks; re-plans at all-32-byte, SIS-aware, and 64-bit-commitment
  pricing; catalog security report). Caveat: `replan-q64-catalog.tsv`'s proof_bytes column
  priced the terminal's inner images at the base width (fixed after the run); use the
  `reprice-replan-q64.tsv` figures instead.
- `work/akita-pasta-out/groups/q64-k{0,1,2,4,8,12}/`: openings with K precommitted groups
  (k0 output is unreliable; it reports two groups).
- `ragu-size-model.py`: compressed Pedersen-IPA proof size model (`search <target>` for the grid;
  `budget` for the circuit budget per rank: max endoscalings per step, min binders, fixed-circuit
  packing, gates per merge).
- `pareto-model.py` + `pareto-template.html` -> `pareto.html`: the Pareto page (Plotly from cdnjs).
- `sage-sis-check.py`, `pasta_rank.rs`, `akita-pasta-rank.csv`: estimator cross-checks.
- `hash-based/`: the user's copies of WHIR (2024/1586), Haböck's Basefold in the list-decoding
  regime (2024/1571), ARC (2024/1731), WARP (2025/753), Zook (2026/391), the 2026 SoK on
  hash-based PCS (2026/1367), Titan (2026/908), Blaze (2024/1609), FRI-Binius (2024/504), the
  small-field SoK (2026/1371) and Flock (arXiv 2607.27491); `work/2026-2103.pdf` is LaBinius
  (lattice, decoupled commitment modulus, binary evaluation field). Text extractions in
  `work/hash-based/`. Binary-field systems and LaBinius are discussed on the page and in
  pasta-proof-size.md but not plotted: Boolean arithmetizations have no Pasta circuits.
- `work/whir-src`: WizardOfMenlo/whir at afec1fac27c1c8cc7331aa5668bc9800f104d92c (MIT or
  Apache-2.0), built in release; `estimates/whir-sweep.tsv` has its proof sizes and verifier
  hashes at 2^17 and 2^18 over Goldilocks ext2/ext3 and a 256-bit field, rates 1/2 to 1/8,
  100 and 128 bits, Johnson regime (`work/whir-sweep2.log` is the raw run). The 128-bit
  security runs over the 128-bit Goldilocks extension hang: unattainable parameters.

## Key numbers

- Pedersen-IPA compressed proof: 7,908 B of payload (rank 13, 4 endoscalings/step, 5 binders,
  header 4; 7,936 with the wire format's 28-byte envelope, measured at ragu 8109a41c on
  2026-11-14; 7,460 before Ragu's online polynomials added six (point, value) openings and two
  commitments, 448 B, to every compressed proof). The figures below are from before that change.
  5,892 B, the figure from the other agent's search, is exactly rank 14, 16 endoscalings/step,
  one binder, header 2, but the circuit budget (`python ragu-size-model.py budget`, from the
  gate counts pinned in ragu_pcd's internal tests) allows only 8 endoscalings and needs 2
  binders at rank 14. Feasible minima (header 2): rank 14 packed 5,988 B; rank 15 packed
  5,700 B (17 endoscalings, 1 binder); rank 16 no better. One more rank costs 128 B;
  endoscalings 4->8 remove 35 components, 1,120 B. Floor ~5.3 KB. The binder split
  (590/challenge + 805 overhead) is derived, not measured; the Akita merge gates are estimated.
- Akita opening at 2^14 dense: fp128 65,074; Goldilocks ~61,050; Pasta plain 101,441
  (re-planned) / 83,234 SIS-aware; Pasta with 64-bit commitments 70,725 (re-planned).
- Per-coefficient prover word multiplications: Pedersen 6,400; Ajtai at Pasta 14,200; 128-bit
  2,600; Pasta/64-bit 2,000; Goldilocks 400.
- Zero knowledge on the Pareto page (toggle): Akita with the masked witness costs about twice
  the prover work (the 2.2x rows term of the accumulation matrix, system-wide; weight-20
  challenges in dimension 512 since the evening of 2026-11-04, 2.37 with the note's weight-32 example) and 18 more atoms
  in the zero-knowledge layer's merge, which is the merge priced; the opening bytes and the
  verifier are unchanged, since the decider's accumulator is at the ordinary length and Akita's
  internal levels and terminal keep their own bounds (since 2026-11-04; before, the length was
  charged to the opening, +1.5 to 7 KB, and to the verifier, x1.15; the same day's modelling of
  the masked rank through the terminal images' share, +36 to 59% bytes, was withdrawn, since
  that share is the floor's mechanism, not the mask's).
  Pedersen-IPA's blinding is free, so its points do not change.
- Hash-based (WHIR with ARC accumulation over Pasta, on the Pareto page): WHIR at 2^17 over a
  256-bit field, 128 bits, Johnson regime: 244/155/123 KiB at rates 1/2, 1/4, 1/8 with 2.7k,
  2.0k, 1.7k verifier hashes. ARC's verifier: 2*128/log2(1/rate) openings per input (256, 128,
  85), paths through a tree over W/rate; merge gates 3.7M/1.8M/1.3M at 288 per Poseidon node,
  so 600 to 1,800 step circuits at rank 13 and a prover of 6.5e11 to 9e11 word mults (Poseidon
  Merkle trees at 35K word mults per permutation). Goldilocks variant (Goldilocks3 rows:
  135/99/84 KiB at 2^17; width-12 rate-8 Poseidon at 480 gates and 7,200 word mults): 115 to
  228 KB, prover 1.4e11 to 1.9e11, merge 2.2M to 6.3M gates. Pasta/64-bit-limb hybrid
  (Pasta merge circuit, so Pasta Poseidon over packed limbs, 4 limbs per coefficient): 121 to
  244 KB, prover 1.7e12 to 2.3e12, worse than plain Pasta. Plonky3 variant: FRI over
  Goldilocks under ARC, same merge and prover as the Goldilocks WHIR variant, decider proof
  1.95x WHIR's (the WHIR paper's measured FRI/WHIR ratio at matched parameters); priced with
  Poseidon, not its default Poseidon2, and at 128 proven bits. All dominated by Akita on every
  measure; the advantage of the Pasta variant is a native Pasta field. Dominance treats native
  Pasta support as a requirement: a Pasta-native point is dominated only by a Pasta-native one.
  Binary-field family (Flock/Binius-style over 𝔽₂ with ARC, no rank): bytes from Ulrich
  Haböck's FRI-Binius optimizer (frib_optimizer.py, since 2026-10-22; before that FRI-Binius
  Table 1 at 100-bit unique decoding x1.3, 1.7x larger) at the merge's witness size, in two
  designs (pack 256 = challenge field 256; pack 64 with challenges in 𝔽₂^192), list decoding up
  to the Johnson bound, the row's grinding, and for ARC rows the decider's three first-round
  trees; prover = Flock's measured PIOP (scaled by the challenge field) + FRI-Binius's
  commitment counted operation by operation and calibrated to its Table 2 (see 2026-10-28/29);
  merge = 2 x openings x depth BLAKE3 compressions of ~2^13 AND gates (not comparable with Pasta
  gates). ARC, 192-bit, best grinding: 446/241/174/140/121/106 KB at rates 1/2..1/64, prover
  6.0e8/4.2e8/4.4e8/5.7e8/8.5e8/1.4e9, 74M..14M AND gates; recursive 340..81 KB at 2.5e9..5.1e9
  and 332M..76M witness bits. The prover is least at rates 1/4..1/8 (8x Akita Goldilocks's 5.1e7,
  whose proof is 68 KB); no 𝔽₂ row beats Akita on bytes and prover together. Zero knowledge (full
  mask, Diamond 2025/1015 = the optimizer's zk option, since 2026-10-30): ARC +63..265 KiB and
  x1.2..1.5 prover; recursive +30..115 KiB and x1.5..2.1; the upper bound. Zook-style (derived,
  since 2026-11-02): ARC +27..54 KiB at x1.00..1.03; recursive +32..61 KiB at x1.03..1.15; the
  lower estimate. The capacity conjectures were refuted in late 2025
  (SoK 2026/1367 §5.4), so conjectured WHIR sizes (36-187 KiB) do not apply. Basefold is
  subsumed by WHIR over RS codes; Zook makes hash-based zk free at the IOP level; Titan
  (DL-based, Pasta, 25 KB) is not post-quantum and larger than Ragu's IPA.
- Security floor knob on the page (128 / 150 quantum bits, ADPS16): since 2026-10-15 the
  Akita figures at 150 bits use per-variant rank factors from the 150-bit width tables in
  `work/akita-150-out/` (`RANK_SCALE_150` in pareto-model.py): 1.27 for the 128-bit field
  (the catalog's own q128/q64/q32 mix: summed ranks 121 -> 154 over the 115 weakest
  instances; 32 go 1 -> 2, one 2 -> 3), 1.16 for the 64-bit moduli (q64 and Goldilocks give
  identical tables for these cells: 185 -> 215; 12 go 1 -> 2, 17 go 2 -> 3, one 4 -> 5), 1.01
  for Pallas (117 -> 118, one instance moves). The factor scales the images' share of the
  opening, the prover's rows term, and the verifier; still not re-planned, and the rank-one
  compression maps (147 bits) are assumed to hold. The Euclidean ladder alone gave 12% more
  rows (`work/akita-pasta-rank-150.log`), the figure used before. Pedersen-IPA (about 126
  classical bits, Pollard rho on a ~2^254 group; nothing post-quantum) is shown at the 128-bit
  floor only and drops out at 150 (the user, 2026-10-15). WHIR proofs +18% at 150 bits
  (`work/whir-sweep-150.log`); ARC openings scale with the floor. pasta-proof-size.md §9
  discusses the Module-SIS cost models with references; `work/2015-046.pdf` is
  Albrecht–Player–Scott.
- Verifier work on the page (third measure "verifier work"; unit toggle word mults /
  microseconds at 3e9 per second): Pedersen-IPA modelled (two 2^rank MSMs plus a scalar mult
  per folded commitment, ~49 ms at rank 13); Akita measured (paper Table 16, one thread: 4.2 ms
  fp128, 3.9 ms Goldilocks at 2^27 bits, +0.4 ms per doubling; Pasta variants x4, an
  assumption); hash-based deciders = WHIR verifier hashes x native Poseidon cost (+1e6 for
  arithmetic; the ARC rows add the decider's two extra first-round trees, so WHIR over Pasta is
  62 ms at rate 1/8 under ARC and 31 under recursion), Blake3-measured 0.7-1.4 ms; 𝔽₂ = the
  FRI-Binius verifier: auth + leaf hashes x BLAKE3 native + field mults x clmuls, 0.2-1.4 ms;
  BitZ's Ligerito 1.3 ms-class verifier scaled by the extra trees in its ARC rows. Akita's small-field
  (p32) verifier is slower than p64/p128 at equal bits because of 4x the coefficients and
  degree-4 extension-field arithmetic in the sum-checks.
- Rank under Akita follows the application: the merge is cut into step circuits and opened as
  one batch, so its cost is nearly flat in rank (about 160 B and a dozen atoms from rank 13 to
  16 via per-circuit claims, against a few percent of prover padding). Under Pedersen-IPA the
  merge itself wants rank 14 or 15, so the application and the merge compete for the rank.

## Open

- 150-BIT WIDTH TABLES DONE (overnight 2026-10-15, 02:23 to 03:53, plus q32 at 08:11): the
  SIS width tables at a 150-bit ADPS16-quantum floor, the first half of the planner-backed
  150-bit policy agreed on 2026-10-14. Script `work/akita-150-tables.sh`; outputs and one log
  per step in `work/akita-150-out/`; `summary.txt` there has the step timings (q128 17 min,
  q64 7 min, pallas 58 min, goldilocks 8 min, q32 minutes). CSV only:
  `l2-width-table-150.csv` (four moduli) plus `l2-width-table-150-q32.csv`, and
  `linf-width-table-150-{q128,q64,pallas,goldilocks,q32}.csv`. Checked: every rejected width
  has a finite cost below 150 and every accepted width is certified at or above it. Where the
  floor binds, widths shrink 12 to 20 times at d >= 64; q64 and goldilocks have 83 small cells
  with no secure width. Over the catalog's 115 weakest instances, the summed rank grows 1.27
  (own moduli), 1.16 (q64 or goldilocks), 1.01 (pallas); the page uses these (Key numbers
  above). Estimator changes made for it, in the patch: a `Quantum150BitADPS16` variant of the
  estimator's `SisSecurityPolicy` (label, 150-bit constraint, CSV label parse); a `--policy`
  flag on `infinity_width_table`; `EstimateConfig::akita_infinity_table_for(policy)`, so that
  the proven-pruned certificate targets the policy's own floor (the production function
  proved "above 128.26" and stopped, which read as a width-7 boundary); and, for a
  non-production policy, a certificate that is non-finite or short of the target counts as
  insecure instead of stopping the table. Smoke check: q64, d=64, bound 1, ranks 1 and 2
  certify "above-target 150.26" at beta 567 up to the 4096 cap.
  RE-PLAN AT 150 BITS, STAGED (2026-10-15 morning; the user asked for it, to run on mains
  power). Instead of a second policy in the crate, the worktree `work/akita-src-150` (branch
  `pasta-widths-150` of the clone, with the patch applied) makes the single policy the 150-bit
  one: `Quantum128BitADPS16` renamed to `Quantum150BitADPS16` throughout (tag 1 kept, so the
  shipped artifacts still parse), the estimator's constraint set to 150, the Euclidean target
  to 150, and the six rank-one compression cells re-sized from the overnight tables at bound 1
  (q128: 508 -> 277 at d=8, 7077 -> 3806 at d=16; q64: 254 -> 138, 3538 -> 1903; q32: 127 ->
  69, 1769 -> 951; all still feasible at rank one, certified "above-target 150.26"). The
  runtime tables are regenerated there with the production emitters (`euclidean_width_table
  --format rust-split`, `infinity_width_table --format rust-split`; log
  `work/akita-150-out/replan/tables-rust-split.log`; done 08:53 to 10:02 on 2026-10-15), then
  the planner is rebuilt. The emitters' header comments hard-coded "128 bits"; in the worktree
  the infinity emitter now prints the policy's floor, the Euclidean emitter's constant says 150,
  and the two generated `mod.rs` headers were corrected by hand (they are outside the table
  digest, which covers the `q*.rs` files and `policy_audit.csv`; its domain string still says
  `128bit`, a namespace tag, left alone). The
  planner runs are in `work/akita-150-replan.sh`: the fp128 (and fp64) families at Akita's
  own, Pasta, and 64-bit-commitment pricings with the planner's `--catalog-report`; the
  per-K group sweeps (`fp128_dense`, final 14:1 plus K x `--precommitted-group
  fp128_dense:14:1`, 64-bit pricing, as the page's 128-bit K sweep was made) and the same in
  fp64; `catalog_reprice` over every output. Then: read the 150-bit openings per variant and
  K from the reprice TSVs (page recipe: fp128 = original_total of `fp128_dense final=14:1`
  in replan-base; pasta = pallas_total in replan-pallas; pasta_q64 = pallas_q64_total in
  replan-q64; pasta_sis = pallas_sis_total in replan-base; goldilocks = `fp64_dense` row;
  K>0 from the group runs), the rank growth from the reports, and replace `RANK_SCALE_150`
  on the page with planner-backed figures; update the page text, pasta-proof-size.md §9, and
  this file. Page bug fixed and published meanwhile (v50): with the view held, a change of
  work unit now carries the held ranges across the unit factor instead of rescaling.

- ADD BITZ (the user, 2026-10-15, after the Cambridge talk): BitZ, ePrint 2026/2141 (Bloemen,
  Garreta, Kostrzewa, Londhe, Soukhanov, Wu; code github.com/worldfnd/BitZ, MIT), a hash-based
  multilinear PCS over any finitely generated ring S with evaluation claims over another ring R
  through a homomorphism: the witness is bit-decomposed and committed packed over a binary
  field with recursive Ligerito openings through Flock, the claim over R is moved to Z by a
  random prime (prime fingerprinting), then to inner products over Z proved by the exponent
  lift (`prod ((x^gamma_i - 1) b_i + 1) = x^<gamma, b>`) and GKR grand products over the binary
  field; cost depends on the coefficient bit-length only, with range checks free. With S = Z and
  R = a Pasta field it is a Pasta-native hash-based point, the gap the page notes for the
  binary-field family. Numbers so far (search snippet only): about 50 ms prover, 3.3 ms
  verifier, 76 kB proof, MacBook Air M5 single-threaded, 21 ms on 10 threads, instance size
  not yet known. DONE 2026-10-15 evening: the user's PDF is `work/2026-2141.pdf` (ePrint's PDF
  is behind a browser challenge for this shell), text in `work/hash-based/2026-2141.txt`; also
  `work/2026-855.pdf` (Zinc+, Universal Constraint Systems, which BitZ supports and which are
  native over Pasta's F_p: integer witnesses with ideal membership modulo p, projected to a
  random ~192-bit prime field for the PIOP) and `work/2025-316.pdf` (Zinc), texts beside it.
  Model (`pareto-model.py`, families `bitz` with ARC and `bitz_rec`): a Pasta gate is 510
  committed bits (255-bit value and quotient); the merge is a hybrid circuit, Boolean hashing
  plus native GKR/PIOP verifiers (not counted); costs from BitZ Table 10 (rate 1/2, 100 bits,
  one thread, 2^20..2^31 bits; prover, verifier, non-Ligerito and Ligerito proof parts)
  interpolated in log2(bits), rate 1/8 by Table 9's ratios (Ligerito part 0.56, prover 1.30),
  Ligerito part x1.3 to 128 bits and the WHIR factor to 150, verifier with the floor, Zinc+'s
  PIOP from its Table 4 (1.6x the PCS prover on the application's share, 2 ms, 36 KB). Result
  at rank 13, rate 1/8, ARC, 128 bits: 188 KB, 3.9e8 word mults, 31M merge bits, 5 ms decider,
  on the frontier (Pasta-native). Revised the same evening with the measured scalings (BITZ
  MEASURED below): 302 KB, 3.6e8, 31M bits, 5 ms, still on the frontier; 3.8e8 after the
  overnight run's rate factor (2026-10-16). The page and
  pasta-proof-size.md §8.1 record it.
- NATIVE RECURSION FOR THE HASH-BASED FAMILIES (Quang Dao, with the user, 2026-10-15): price
  each hash-based scheme with its own recursion or accumulation scheme, not with ARC. For
  WHIR, Plonky3-style FRI, Flock/Binius64 and BitZ that is full recursive verification unless
  a scheme ships an accumulation scheme of its own: the merge circuit verifies the two input
  proofs (the measured verifier hash counts, e.g. WHIR's 2,700/2,000/1,700 at 2^17 per input,
  against ARC's 2 x openings x depth: 11,800 at rate 1/2), each step emits a full proof, and
  the decider verifies one proof. BitZ's measured verifier (Table 10) is the per-input cost in
  a hybrid Boolean circuit. Clarified by the user: keep the ARC rows and add native-recursion
  rows beside them, so that each scheme is compared with its ARC version; for BitZ price the
  recursion verifier over its binary extension natively (one constraint per F_{2^128}
  operation), since handling relations over several fields and rings efficiently is the point
  of the scheme, so its merge is the Ligerito hashing plus a small native part. DONE
  2026-10-15 evening: `pareto-model.py` has `*_rec` families beside every hash-based family.
  WHIR/FRI: the merge is two verifications at the measured hash counts (hashes at 2^17 plus
  queries per doubling), the prover 4/3 of encode-and-commit (folding factor 4), the decider
  unchanged. Ligerito (Flock, BitZ): Flock's instantiation, five levels at rates 1/2..1/32
  with 218/106/71/53/43 queries at 100 bits (linear in the floor), two variables folded per
  level (an assumption), a column of four elements per query; nodes priced as BLAKE3 for
  parity with the 𝔽₂ ARC row (Flock's implementation uses SHA-256: 3.8x the bits, half the
  throughput, for every row of these families alike). Findings: WHIR recursion is a wash at
  rate 1/8 and saves a fifth of the merge and half the prover at rate 1/2; FRI recursion costs
  about twice ARC; Ligerito recursion opens 491 columns per proof against ARC's 86 openings at
  rate 1/8, so it costs two to seven times ARC's hashing, and ARC stays the better row for
  Flock and BitZ.
- BITZ MEASURED (the user, 2026-10-15: "do BitZ first"): the paper's PoC,
  github.com/albert-garreta/BitZ-PoC (MIT, run only), cloned to `work/bitz-poc` at 8ced3b98
  (2026-10-04); rustup auto-installed its pinned toolchain 1.98.1; built with
  `RUSTFLAGS="-C target-cpu=native" cargo build --release --features unchecked,span-metrics
  --bin bitz` (`parallel` is a default feature of the crate, so `--threads 1` sets a
  one-thread rayon pool: the runs are genuinely single-threaded, as their RESULT lines say).
  Script
  `work/bitz-pcs-sweep.sh`; outputs `work/bitz-out/` (RESULT lines in `bitz-pcs-results.txt`,
  one log and one LaTeX table per profile). The raw sweep samples the claim prime after the
  commitment (q of 110 to 112 bits; no Round 1), Ligerito hashes with BLAKE3. On battery,
  2^25..2^27 bits, 3 reps: `custom:1:4` (100 bits, Johnson, rate 1/2) reproduces Table 10's
  bytes exactly (190,158 / 208,970 / 223,658 B) with prover 150 / 290 / 564 ms (commit 8 / 17 /
  34 more; the paper's M5: 80 / 151 / 298), verifier 4.3 / 6.2 / 10.5 ms; the GKR grand product
  is 119 / 234 / 478 ms of it, Ligerito 17 / 30 / 39. `custom:1:4:128` and `udr:*:128` are
  rejected by the validator (OOD or proximity-gap bits short of 128); `udrg:1:4:128` (unique
  decoding, fold grinding): 304 / 344 / 375 KB (Ligerito 256 / 295 / 325 KB), prover 145 / 315
  / 563 ms, verifier 5.4 / 8.6 / 12.3 ms; `udrg:3:4:128` (rate 1/8): 257 / 298 / 321 KB,
  prover 166 / 310 / 721 ms (the 2^27 Ligerito step 194 ms looks like an outlier), verifier
  5.1 / 7.5 / 11.9 ms; `secure` fails. Ratios applied to Table 10 on the page: 128 bits = 1.8x
  Ligerito bytes, 1.05x non-Ligerito, 1.27x verifier, 1.0x prover; rate 1/8 = 0.83x Ligerito
  bytes, 1.2x prover. Quang: the prover with grand-product GKR is just really expensive. Lower
  rates (the user: "they might be cheaper in proof size when committing to small values"):
  `udrg:4:4:128` (rate 1/16) gives 264 / 308 / 332 KB and prover 211 / 372 / 670 ms, so 3%
  more proof and 27% more prover than rate 1/8; rates 1/32 and 1/64 are rejected ("Ligerito
  requires inverse-rate exponent 1..4"). Rate 1/8 is the proof-size minimum. JOHNSON AT 128
  (the user: "try at the Johnson bound; there is analysis work in progress that can bring it to
  128 bits, potentially"): the validator caps the Johnson profile at the out-of-domain binding
  term, 118.7 bits at rate 1/2 and 117.7 at 1/8 with one OOD sample, and `ood_samples` is not
  a knob. `custom:1:4:118` on mains: proof 216,686 B at 2^25 and 239,634 B at 2^26 (Ligerito
  170,700 / 192,860, against 144,324 / 162,396 at 100 bits: x1.18, linear in the bits), verifier
  3.3 / 4.4 ms; but 18 to 20 grinding bits at the OOD round make the opening 46 s at 2^26, 99.6%
  of the prover, so the times are grinding; the user stopped the run at 2^27 ("a completely
  impractical grinding factor"). Projection to 128 bits at the Johnson bound, Ligerito bytes
  x1.28 over 100 bits: about 231 KB at 2^25 and 255 KB at 2^26, 24 to 26% below the
  unique-decoding figures (304 / 344 KB). The rows keep the certified unique-decoding numbers;
  the projection is in the text. Grinding plans (decoded from the RESULT lines' Ligerito
  JSON, per level: fold grinding, query grinding, queries): `custom:1:4` at 100 bits 12/16/183,
  9/16/90, 6/16/60, 3/16/45 (378 queries); `udrg:1:4:128` 16/0/309, 14/0/190, 12/0/156,
  10/0/143 (798 queries: the unique-decoding regime's doubling, the loose analysis);
  `udrg:3:4:128` 19/0/155, 16/0/141, 14/0/135, 12/0/132; `custom:1:4:118` 30/16/222,
  27/16/109, 24/16/72, 21/16/54. The user: grinding at 2^27 or above is not a configuration
  we would deploy and only shows as needed because the security analysis is loose, so the
  118-bit Johnson profile is out of scope; the overnight run keeps the profiles at 16 to 19
  bits. OVERNIGHT RUN launched 2026-10-15 late evening on mains (USB-C, not the Apple
  adapter): `work/bitz-overnight.sh` (the rebuild was a no-op, `parallel` being default-on;
  `custom:1:4`, `udrg:1:4:128`,
  `udrg:3:4:128` at 2^25..2^28, threads 1 and 10, 5 reps, cooldowns), outputs in
  `work/bitz-out/overnight/` (results.txt, summary.txt). DONE in 8 minutes (23:03 to 23:11
  BST, mains throughout). Single thread, 100 bits: prove 103 / 197 / 380 / 696 ms at 2^25..28
  (commit 6 / 11 / 23 / 49 more; the paper's M5: 80 / 151 / 298 / 537), so this M4 Max is 1.3x
  the paper on one thread; ten threads: 25.5 / 39.8 / 71.4 / 118.6 ms (the paper: 28.3 / 48.6 /
  87.2 / 153), a 4 to 5x speedup. Ratios: 128 bits (udrg:1:4) costs the prover 0.94 to 1.02x,
  the Ligerito bytes 1.77 to 1.88x, the verifier 1.12 to 1.25x (set 1.17; was 1.27); rate 1/8 at
  128 bits: Ligerito bytes 0.82 to 0.84x, prover (prove + commit) 1.19 to 1.31x (set 1.25; was
  1.2), verifier the same. The 2^27 rate-1/8 Ligerito step is 133 ms on mains (191 at 2^28,
  36 at 2^26): a real rise at that size, not an outlier. At 2^28 the non-Ligerito proof part
  jumps from 50 to 84 KB (more mu_j values), as in Table 10. Model and page updated. TO DO
  on mains: rerun with `RUSTFLAGS="-C target-cpu=native"` single- and multi-thread (build with
  `--features unchecked,span-metrics,parallel`, run `--sweep-threads 1,10`), repeat the 2^27
  rate-1/8 cell.
- ZERO KNOWLEDGE FOR WHIR (the user, 2026-10-15: "zk is not free for WHIR/Zook at the PCS
  level"; "Plonky3 does have zk for WHIR so it should be possible to quantify the difference"):
  Plonky3 cloned to `work/plonky3-src` (commit f98331687, 2026-10-13, MIT or Apache-2.0, run
  only, no dependency taken); its `whir/src/pcs/zk/` composes 2026/391 into `HidingWhirPcs`
  and `whir/benches/zk_overhead.rs` measures it. Run on battery (57%), single core, filter
  `whir_zk_overhead`, log `work/plonky3-zk-overhead.log`: KoalaBear with a quintic extension,
  folding 4, rate 1/4, 100 bits per phase under the capacity bound, 16 bits of grinding, masks
  `ell_zk` 16 at rate 1/32. Proof 30,914 B plain against 103,583 B zk at 2^16 (3.35x), 37,490
  against 110,139 at 2^18 (2.94x): an additive 73 KB. Prover 45.8 against 78.6 ms at 2^16,
  182.3 against 205.1 ms at 2^18: an additive 23 to 33 ms, 12% at 2^18. The hiding security
  report lists the mask groups (sumcheck masks per round, message length 16, 21 spot checks
  each). The octic 128-bit group of the benchmark panics at its config (RandomnessExceedsSlack),
  unrelated. Modelled on the page: ZK rows for the WHIR and FRI families (ARC and recursive)
  add 73 KB x floor/100, a prover factor 1 + 0.125 x 2^(18 - log elems), and 1,300 x floor/100
  hash checks per proof to the decider and the recursive merge; the ARC merge unchanged. Flock
  and BitZ are succinct-only by their papers and drop out of the ZK view. Published as v53; the
  user: "that now looks how Quang expected". RERUN DONE on mains with the native CPU flag
  (`cd work/plonky3-src && RUSTFLAGS="-Ctarget-cpu=native" ~/.cargo/bin/cargo bench --bench
  zk_overhead -p p3-whir -- whir_zk_overhead`, log `work/plonky3-zk-overhead-mains-native.log`;
  the first run, on battery and without the flag, lacked it, as the user asked about: the WHIR
  sweep lacked it too, BitZ's build had it; only timings are affected): bytes identical; prover
  30.7 against 53.0 ms at 2^16 and 121.1 against 139.5 ms at 2^18, an additive 19 to 22 ms,
  15% at 2^18 (12% on battery); `ZK_PROVER` set to (0.15, 18).
- AKITA'S BINARY-SOURCE COMMITMENT (the user, 2026-10-15: "see the open PRs"): LayerZero-Labs/akita
  PR #229 `feat(labinius): polynomial commitment for binary and prime evaluation claims`
  (Quang; crate `akita-labinius-pcs`, feature `labinius`, off by default; spec saved as
  `work/akita-labinius-pcs-spec.md`, PR bodies in `work/akita-prs-labinius.txt`), with #230
  (faster root opening kernels, opening 23 to 34% faster) and #240 (commit and open dense
  polynomials from signed integer blocks, i8/i16 sources without a field lift). The PCS commits
  a binary source (2^22 cells of 128-bit words at the sample geometry, fold width 2^8) by the
  LaBinius root reduction of #228 and opens, with one nested Akita grouped proof, a binary claim
  (multilinear evaluation over a binary host field F128 or F192), a prime claim (a linear
  functional of the committed bits over the proof field: `Family64` = Prime64Offset59 with Ext2
  challenges, `Family128` = Prime128Offset275), or both. Non-hiding. Sample at 2^22 cells (2^29
  bits), 16-core M4 Max, parallel: proof 91 to 104 KB (reduction 20 to 30 KB, nested Akita
  proof 70 to 73 KB), commit 0.06 s, open 0.53 to 0.67 s (0.37 to 0.48 s after #230), verify 14
  to 25 ms; commitment 343 bytes. Catalogs cover cell logs 16, 18, 20, 22 (2^23 to 2^29 bits);
  2^24 cells is not supported. Open obligations per the PR: knowledge extraction across fold
  challenges, the SIS reduction at the admitted rank, Fiat-Shamir of the composition, frontend
  soundness. Relevance: the lattice backend for bit-decomposed witnesses (Flock-style Boolean
  circuits, or BitZ's arithmetization); the prime claim is over a fixed proof prime, while
  BitZ's and Zinc+'s lift from Z needs a random prime, so a Pasta-native combination is the
  future-work item below, not a drop-in. Not on the page yet: placement to be agreed.
- BITS OVER AKITA, THE DRAFT FRONTEND (the user, 2026-10-15 evening): `work/main3.pdf`,
  "Efficient Booleanity Checking via Structured Modular Projections", internal research
  draft of 2026-09-23 (treat as provisional, may have errors; text in
  `work/hash-based/main3.txt`). The user: "the point is that you can do the boolean check
  over a large field, and then you don't need GKR for exponentiation as in BitZ." Idea: a
  committed bit table over F_q (q = 2^64 - 59) is certified Boolean by sum s(s-1) = 0 in F_q
  plus an integer norm bound Ex < Q0 with Q0 + sqrt(n Q0) < q (Theorem 1), the bound supplied by
  a structured random projection (four independent tensor chains, 160 revealed coordinates,
  balanced-ternary coefficients from AES counter mode) with certified error 2^-136 conditional
  on CertifiedJL's modular estimates. §6 (M4 Max, one thread, 2^27 bits): projection prover
  113 ms (packing 5.9, sampling 0.2, forward projection 60.8, sumcheck 45.9), the optimized
  conventional Booleanity sumcheck (histogram startup) 438 ms; verifiers 0.85 vs 0.023 ms (the
  projection verifier scans 3.1M sampled coefficients); payloads 2,592 vs 1,744 B uncompressed;
  no PCS opening, no hiding; not production Akita/Aerie times. Modelled as family `bits_q64`:
  255 one-bit digits per Pasta value over the page's `pasta_q64` accounting (same decoupled
  commitment, same open soundness), plus the check at 2.5 (projection) or 9.8 (sumcheck) word
  mults per bit, payload bytes, verifier ms, and merge gates 3,000 (sumcheck) or 3.1M
  (projection, the coefficient scan in-circuit); zk=False. Result at rank 15, 128 bits: 88 KB,
  prover 6.6e8 / 8.4e8, merge 27K / 3.1M gates, decider 11 ms; against pasta_q64 (83 KB,
  2.0e8, 24K) dominated, since three times the digits are committed and then checked; against
  BitZ (302 KB, 3.6e8, 31M-bit merge) 3.4x smaller proof and 1000x smaller merge for 2x the
  prover. Its case is a Boolean or hash-heavy application with free range checks, not the
  Pasta-arithmetic recovery circuit. The user renamed the family "BitZ over Akita". Quang: we
  are likely overestimating this prover, possibly because the (loose) security analysis
  assumes too much grinding; the page and the write-up now call the prover an upper bound. To
  revisit when the analysis tightens: the rows term (567 at the 64-bit modulus, the
  estimator's unmasked collision bound) and whether a binary source needs that rank. The user
  corrected "which the Ironwood recovery circuit is not": it is hash-heavy. ZIP 2005's cost
  section (`~/olddaira/zips.pristine/zips/zip-2005.md`, "Cost"): 7 BLAKE2b-512 compressions
  (3 multiplexed between H^rivk_ext and H^ask + H^nk + H^rivk_legacy, 1 H^rivk_int, 1 H^psi,
  2 H^rcm), 1 Commit^ivk and 1 NoteCommit (Sinsemilla), 1 fixed-base and 1 variable-base
  full-width Pallas scalar multiplication, 1 Merkle path check plus 1 MerkleCRH, and 1 BLAKE3
  compression in SoK^qsk; "the expensive parts are the 7 BLAKE2b compressions". With UCS the
  integer arithmetic simulates F_p efficiently. The user: the plot primarily considers the
  cost of recursion, since that is easier to estimate and every designer cares about it,
  whereas which other circuit to benchmark is hard to agree on, being application-dependent;
  the page text now says so. TO DO: cost the recovery circuit per component
  in the bit arithmetization (hash bits per BLAKE2b compression in a Flock/BitZ-style
  arithmetization, integer-simulated Pallas arithmetic with quotients) and compare with its
  Pasta-gate cost, instead of the page's "2^rank gates at 255 bits each".
- Quang (2026-10-15): as future work it might be possible to combine BitZ's arithmetization
  features (bit-decomposed witnesses, claims over any ring through a homomorphism, free range
  checks, the UCS constraints of Zinc+) with a lattice backend such as Akita, in place of the
  binary-field hash-based commitment. Not modelled; a note for pasta-proof-size.md's
  conclusions.
- Page bug fixed 2026-10-16 (v58): with "hold the view" off, the 2D axes autoranged to the
  plotted points with no margin, so a lone frontier point at the data's edge (BitZ with ARC
  under "verifier work", collapse on, per-family off) sat on the right border and was easy to
  lose or clip; the user read it as a Pareto collapse. The 2D view now takes the same padded
  ranges over the plotted points as the 3D view. Diagnosed by driving the page in headless
  Chrome with puppeteer-core (`work/pup/probe.mjs` reports ranges and the BitZ point per
  state, `work/pup/shot.mjs` screenshots; `work/pup/` holds the scratch npm install).
- The Pareto page is published as a private artifact at
  <https://claude.ai/artifact/CrW3rrJ8D7gUAk27y92LLm>; after changes, run `python pareto-model.py`
  and republish to that URL.
- Decoupled-modulus design needs the relation rows with quotients and a soundness write-up.
- ZK note open points 1-9 (randomizer claim, trace blinding, child data, one-fold theorem, ...).

## 2026-10-21: rate and grinding sweep for Ulrich (Shielded Labs)

Questions relayed by the user: (1) "86 openings per input is more than needed in the list
decoding regime" (true up to capacity, 43 at rate 1/8, but those conjectures are refuted; the page
is at the Johnson bound); (2) "you need a larger field than 128 bits to go up to the Johnson
bound, but then significantly fewer samples" (true: unique decoding needs 154 at rate 1/8 against
86 at Johnson; the page's ARC rows over Pasta and Goldilocks-cubic are already at Johnson, the
𝔽₂/BitZ rows are in the unique-decoding regime because F_{2^128} cannot reach Johnson at 128 bits);
(3) grinding in the query phase: t = 2(λ − g)/log2(1/ρ); the page's ARC count is ungrinded while
the WHIR measurements carry 20 bits, an inconsistency to fix; the user: choose g so that the
prover cost does not appreciably rise; (4) "rate 1/32, 16 bits of grinding, 256-bit field: how
much smaller are the proofs?" MEASURED with the reference implementation (`work/whir-src`,
`work/whir-rate-pow-sweep.tsv`, Field256, 128 bits, Johnson, folding 4, --reps 5): at 2^17,
rate 1/8 with 20 bits reproduces the page's 122.7 KiB (76 first-round samples); rate 1/32 with
16 bits is 97.7 KiB (47 samples), −20%; with 20 bits 93.4 KiB, −24%; rate 1/64 with 16 bits
89.4 KiB, −27%. Verifier hashes 1.7k → 1.5k. The reference prover (Blake3 trees) goes 58 → 151
ms (3×) at rate 1/32 and 292 ms at 1/64. Grinding cost in that prover: 20 bits adds about 10
ms at 2^17 (58.5 against 47.8 at rate 1/8), 16 bits about 1 ms. At 2^18: rate 1/32, 16 bits,
101.5 KiB (slope 3.8 KiB per doubling). ARC openings per input at rate 1/32 with 16 bits:
2·112/5 = 45 against 86, merge hashing per input 45 × 28 levels = 1,260 against 86 × 26 = 2,236,
−44%, at four times the accumulation prover's encoding and hashing. Not yet on the page: rates
1/16 to 1/64 and a grinding knob for ARC (`arc_openings`), offered to the user.

## 2026-10-21, later: the page updated for rates and grinding

`pareto-model.py` now loads `estimates/whir-sweep-grind.tsv` (both fields, rates 1/2 to 1/64,
maximum proof of work 0/16/20/24 bits, 2^17 and 2^18, 128 bits, Johnson, --reps 3; the prover_ms
column is noisy at 24 bits and two cells are blank, unused). `RATES` has six rates for the WHIR,
FRI, Goldilocks and hybrid families (ARC and recursive rows); 𝔽₂ and BitZ keep their rates.
`GRINDS = (0, 16, 20, 24)`, default 16 (the user: a grinding amount that does not appreciably
raise the prover; for the BLAKE3 families 20 bits is about half a merge's prover). Hash-based
points carry `grind`; `arc_openings(rate, floor, grind) = ceil(2 (floor − grind) / log2(1/ρ))`;
the prover adds 2^g evaluations of the family's Merkle hash per merge (`grind_prover`,
BLAKE3 at 200 word mults), the merge gates one check per input; WHIR's sizes and verifier
hashes come from the sweep at the selected grinding (`whir_meas`). Template: a Grinding radio
group, the filter and listener, the openings paragraph (224, 112, 75, 56, 45, 38 at 16 bits),
the knobs bullet, a new Grinding paragraph after Security floor, the proof-bytes bullet, and the
hash-based families paragraph's ranges (108 to 332 KB, 16 to 700 times Pedersen-IPA's prover,
0.6 to 3.2 M merge gates, 20 to 140 times Akita's). Loop nests re-indented to four spaces. At
rank 13, grinding 16: rate 1/8 157 KB, 1.09 M gates, 7.8e11; rate 1/32 118 KB, 0.69 M gates,
2.0e12. Republished to the same artifact URL.

Addendum, same evening: the user saw a prover minimum between 16 and 20 bits. Evaluated at every
integer g with the model (prover = circuits × per-coefficient + 2^g × native): the minimum is
at 17 (rate 1/8) or 18 (rate 1/32) for both Pasta and Goldilocks WHIR, shallow (within a
percent from 16 to 20); mechanism: a bit of grinding removes about one opening in a hundred,
the grinding doubles, crossing where 2^g permutations are about one percent of the prover.
Measured sizes at 8, 12, 17, 18, 19, 22 bits too, and every setting at 2^20 (the TSV has 10
settings × 6 rates × 2 fields × {17, 18, 20}; 17 and 19 bits have no prover_ms). `GRINDS` is
derived from the TSV; `whir_meas` takes the slope over the three doublings to 2^20, which
removed the non-monotone sizes (a one-doubling slope carried noise five doublings out) and
RAISED every hash-based row's bytes, since a folding round is added every two doublings: rate
1/8 pow 20 measures 122.7 / 128.0 / 149.5 KiB at 2^17 / 2^18 / 2^20, about 9 KiB per doubling
against 5 over the first. The page's default is now "best per row" (`grind="auto"` points: the
measured setting with the smallest prover, labelled "{g}-bit grinding"; the frontier pass runs
per setting), a `<select id="grind">` with the fixed settings beside it. Choices at 128 bits,
no ZK: Poseidon families 17 to 20 (mostly 18), BLAKE3 families 12 to 16. Rank 13 at best per
row: rate 1/8 177 KB, 1.07 M gates, 7.7e11; rate 1/32 133 KB, 0.67 M, 1.9e12. Text ranges:
118 to 365 KB, 16 to 650 times Pedersen-IPA's prover, 0.6 to 3.2 M gates, 20 to 140 times
Akita's. pareto.html is 8.2 MB (17,914 points). Republished to the same URL.

## 2026-10-21, night, finished 2026-10-22: Ulrich's FRI-Binius optimizer in the model

State at the end of the night session (the integration itself is the last bullets):
- `frib_optimizer.sage` is Ulrich Haböck's script (given to the user). `frib_optimizer.py` is my
  port: `^` → `**`, Sage's log/ceil/sqrt → math, plus ONE extension, `field_bits` (default 256) in
  `CAT_bits` and `optimize` (sets FIELD_BYTES = field_bits/8 and the agreement bound). Run with
  the Sage env's python: `~/miniforge3/envs/sage/bin/python frib_optimizer.py --w 25 --rate 3
  --grind 16`. Log of the first runs: `work/frib-optimizer.log`. Ulrich: ignore the zk option
  (Ligerito can take the Zook randomisation at negligible size).
- What his model is: witness of 2^w bits packed into GF(2^256) (2^(w−8) felts); 128 bits of
  security; queries t = ceil((grind − λ)/log2 α) with α = (1 + 1/(2m))·√ρ in the list regime
  (Guruswami–Sudan multiplicity m from the list size, default 2^15) or (1+ρ)/2 for unique
  decoding (list 0); the correlated-agreement term CAT = 5·list_bits − log2 3 + n − F (BCHKS25
  simplified; BCIKS20 n − F for unique decoding) with n = w + rate_bits must be ≤ −λ; folding
  schedule optimised for the compressed proof (expected multiproof hashes ≈ Merkle caps).
- COMPARABILITY CHECK (the user asked): same witness (2^17 elements of 256 bits = 2^25 bits),
  128 bits, Johnson/list regime, 256-bit field, same grinding: his queries are within 1–5 of the
  WHIR reference implementation's first-round samples at every rate and grinding (e.g. 75 vs 79
  at rate 1/8, 16 bits), his compressed sizes 10–13% below WHIR's measured (113 vs 127 KiB at
  rate 1/8; 82 vs 98 at 1/32), his CAT margin 152–165 bits. Unique decoding at rate 1/8, 16
  bits: 135 queries, 181 KiB — matches the page's OLD 𝔽₂ basis (FRI-Binius Table 1 at 100 bits
  unique decoding ×1.3 = 194 KB). So his model is at the WHIR rows' level, 1.7× below the old 𝔽₂
  rows.
- FIELD SIZE (the user asked about 128–256): with n = w + rate_bits as his check counts it, at
  2^25 bits, 16-bit grinding: 128 bits not reachable at 128-bit security in any regime (CAT
  alone ≈ 100 bits; hence FRI-Binius at 100, BitZ at 118); 160: list regime only at rate 1/8
  (list 2^1, 88 queries, 101 KiB), unique decoding elsewhere (115–123 queries, 137–144 KiB); 176:
  lists 2^3–2^4, 81/62/50/41 queries, 99/85/75/67 KiB at rates 1/8..1/64; 192: lists 2^6–2^7,
  76/57/46/39 queries, 98/82/73/68 KiB — the SMALLEST (opened values 24 B, queries within one of
  256's), and three 64-bit words (the user: still efficient on 64-bit processors); 224: 105/89/
  77/71; 256: 113/95/82/75. At 2^27 bits rate 1/32: 192 → 92 KiB vs 256 → 106. Caveat: at 192
  the CAT margin is 129–133 bits (at the target), at 256 it is ~152 (25 bits of slack).
- PAGE INTEGRATION, DONE 2026-10-22 (the first attempt, a replace script, failed on its anchor
  and wrote nothing; the edits were then made directly). `pareto-model.py` imports
  `frib_optimizer` (Nix python finds it beside the script; Pyright's "could not be resolved" is
  noise). `frib_at(w, rate_bits, floor, grind, field)` (cached) takes the largest list ≤ 2^15 with
  `frib.CAT_bits(w + rate_bits, lb, field) ≤ −floor` (his check, n = w + rate_bits) and runs
  `frib.optimize` at it; it returns (compressed bytes, queries, authentication hashes = the
  uncompressed auth bytes / 32, lb). `frib_proof(bits, rate, floor, grind, field)` interpolates
  in log2 between the whole sizes around w = log2(bits) − log2(field) + 8: the optimizer
  counts 2^(w−8) elements, and 192-bit packing has 4/3 the elements of 256-bit, so 192 is
  evaluated 0.415 doublings up (the night's 98 KiB at w = 25 becomes ~100 KB in the row); the
  queries and the list are the larger size's. Flock ARC rows run over GRINDS × FLOORS × RATES
  (now to 1/64, not 1/2..1/8) × F2_FIELDS = (192, 256): bytes = proof + instance, verify = auth
  hashes × BLAKE3_NATIVE + 1e6, `field` in the point AND in `grind_key` (else "best per row"
  keeps one packing, since the prover does not depend on the field); label "rate, F-bit
  packing, list 2^lb, t queries, openings/input, BLAKE3, AND gates". The merge (`f2_merge`) is
  unchanged: ARC openings, tree depth the same since the leaves are 256 bytes either way.
  flock_rec rows likewise over GRINDS, with `f2_rec_merge(floor, grind)`: Ligerito's queries
  now scale with (floor − grind)/100 (linear in the security level, Remark 10) plus the
  grinding check per input, so "best per row" finds a real minimum at 16 bits instead of 0 bits
  (the first run picked 0 because the rec prover did not see the grinding at all). `FRIBINIUS`
  and the 1.3× and WHIR_SCALE on 𝔽₂ bytes are gone. BitZ's Ligerito use is untouched (its
  numbers are its own measurements).
- RESULTING 𝔽₂ ROWS (floor 128, header 2, best per row = 12 bits at rates 1/4..1/64, 16 at 1/2):
  ARC, 192-bit: 257/144/105/84/71/64 KB at rates 1/2..1/64 (256-bit: 285/159/115/92/79/69 KB),
  lists 2^7 (2^6 at 1/64) against 2^15 at 256 bits, queries within one of each other, prover
  3.4e8..6.6e7, merge 74M..15M AND gates, verifier 0.4–1 ms. Recursive (16 bits), 192-bit:
  306/187/143/119/103/93 KB, prover 7.8e8, 173M witness bits, Ligerito 1.3 ms. NEW CONCLUSION:
  rate 1/64 with 192-bit packing (64 KB, 6.6e7, 15M AND gates) is on the post-quantum frontier:
  below Akita over Goldilocks's 68 KB (prover 5.1e7) on bytes at 1.3× its prover; every other
  𝔽₂ row stays dominated. Said on the page in the "Binary-field systems" paragraph.
- PAGE TEXT: the "Binary-field systems" paragraph (rewritten in the night) now matches the
  model; its merge range is "14 to 74 million from rate 1/64 to 1/2"; the "Verifier work" bullet
  splits the 𝔽₂ family into ARC rows (the optimizer's hashes) and recursive rows (Ligerito);
  the lede was stale (the user) and now lists the families (five Akita variants, WHIR ×3,
  Plonky3-style FRI, the 𝔽₂ family, BitZ, each with ARC and recursion, BitZ over Akita as a
  draft), the selectable rate, grinding, floor and zero knowledge, and the Pasta requirement;
  the model's docstring likewise. Republished to the same URL on 2026-10-22 (version 61).
  SUPERSEDED on 2026-10-29 by the entry below: the 64 KB frontier point is gone.

## 2026-10-28/29: a realistic 𝔽₂ cost model, the 192-bit design, and the ARC decider's three trees

Ulrich asked what the page assumed about GF(2^192) arithmetic (version 61 charged nothing: the 𝔽₂
prover was Flock's throughput per merge hash, the verifier a flat 1e6 for arithmetic), then, on
2026-10-23 about version 61, that the 𝔽₂ recursive prover did not grow with lower rates and that
the ARC decider's opening proof must deal with several Merkle trees (the current witness and the
accumulation polynomials), and that a stand-alone FRI-Binius at 2^25 bits and rate 1/64 is about
66 KiB (the model: 67 KB at the merge's 14M bits, 16-bit grinding). The user: use a more realistic
cost model; generalise the optimizer rather than apply ad-hoc adjustments, where the adjustment has
a principled argument. Changes:
- `frib_optimizer.py` now has three extensions, documented in its docstring: `field_bits` (the
  challenge field: agreement bound and later rounds' element size), `first_bytes` (opened bytes per
  256 witness bits in the first round: 32 under ANY packing, since the first oracle is the packed
  bits themselves), `first_trees` (separately committed oracles opened in the first round; the
  schedule is optimised with that cost).
- 192 bits is NOT ruled out. I first said the power-of-two degree ruled it out; the user corrected
  me: the degree 2^kappa gives the packing its sub-hypercube structure and the tensor algebra its
  symmetry, it is not a soundness condition (2024/504 §1.2: "We write 2^kappa for the degree of L
  over K, which we assume is a power of 2"; §1.3 "ring-switching works for any such field
  extension"). The design modelled: pack bits into 𝔽₂^64 (kappa = 6, ring switching as written),
  draw the folding and sum-check challenges from the cubic extension 𝔽₂^192, the field the
  agreement bound sees, as Plonky3 pairs a base field with an extension; it needs the ring-switching
  sum-check restated over L tensor 𝔽₂^64, which the paper does not write down. Since every design's
  first round costs opened bits / 8 per query, the 64/192 sizes equal the night's dense-192 figures
  up to the arity granularity; the later rounds' elements are 24 B against 32. `F2_DESIGNS = {256:
  pack 256, 192: pack 64}`; labels "256-bit field" / "64-bit packing, 192-bit field".
- Cost model (`f2_ops`, `f2_piop`, `f2_prover`, `f2_verify`; the comment block above them in
  pareto-model.py is the documentation). Unit: word multiplications, a 64-bit clmul as one.
  CLMULS = {128: 4, 192: 7, 256: 11} per field multiplication (Karatsuba over 64-bit limbs plus the
  reduction), mixed products one clmul per limb pair; XOR_WEIGHT 1/8; the NTT with 4 butterfly
  stages saved (the paper's interleaving, §5); BLAKE3 at 200 per compression. PIOP = Flock's
  measured 82,100 compressions/s less its PCS (Table 5, BLAKE3: witness gen 5%, zerocheck 37.3% +
  lincheck 9.1%, PCS commit 24.4% + open 24.3%), the zerocheck+lincheck scaled by 1 + (c_L/c_128
  - 1)/2: HALF the PIOP's work assumed to scale with the field's multiplication cost (an
  assumption, stated on the page). PCS commit = NTT + first tree; open = ring-switch XORs (2N x L/64
  words) + sum-checks (7 x packed coefficients x c_L: tensor expansion, ring-switch sum-check,
  BaseFold sum-check) + folds (first step over the packing field, then L x L) + folded trees;
  interpolated geometrically between whole w. Calibrated to FRI-Binius Table 2 (2^28 bits, rate
  1/2, 𝔽₂^128, SHA-256 Merkle, folding factor 4, 100-bit unique decoding, single-threaded on a c7i
  Xeon with AVX-512 and CLMUL: commit 144 ms, open 160 ms) with a hand-built schedule of ell = 2
  per round: F2_SCALE = (1.11, 1.70). ARC step prover = PIOP + k_c (NTT + 2 trees) + k_o (ring
  switch) + grinding; recursive = PIOP + k_c (NTT + tree) + k_o (switch + folds) + grinding.
  Verifier = (auth + opened/64 + grind check) x 200 + field mults x c_L, with field mults = 2 l'
  2^kappa (ring switching, the paper's Remark 3.4) + t x sum 2^ell (folds) + 6 l'. The recursive
  merge now verifies the step's own FRI-Binius proof: hashes x 8192 + field mults x KARATSUBA_ANDS
  {128: 3^7, 192: 6 x 3^6, 256: 3^8} AND gates, replacing the Ligerito verifier for this family
  (BitZ keeps Ligerito); the 2^kappa = 256 factor makes the 256-bit design's recursive merge 263M
  bits against 116M at 192 (rate 1/8). `f2_merge` (the ARC merge: openings x depth) is unchanged.
- Sanity check: at 2^25 bits, rate 1/2, 256-bit, an ARC step is 3.0e8 against Flock's whole
  measured pipeline, 1.5e8, at its own rate 1/2 over 𝔽₂^128; the PIOP alone is 1.4e8 after the
  field scaling.
- The ARC decider's three trees (Ulrich): at the root nobody has yet combined the two child
  accumulators with the root's own witness, so the decider's batched proof opens three oracles in
  its first round, each under its own root (cheaper than a separate accumulation check plus a
  stand-alone proof, which would open four). 𝔽₂: `first_trees=3` for ARC rows, 1 for recursive.
  WHIR/FRI: `whir_extra_trees` adds, per extra tree, first_samples x 16 elements x 32 or 24 B of
  leaves plus the paths as a pruned multiproof, `frib.expected_multiproof_hashes(height,
  first_samples)` x 32 B (the user, 2026-10-29: assume pruning of path segments or a Merkle cap;
  my first version counted full paths, 177 -> 362 KB at rank 13 rate 1/8, which the user
  questioned), x size_factor, to the measured stand-alone bytes, and the same hashes plus the
  leaf permutations to the verifier's hashes (post hoc, since those sizes are measurements;
  `first_samples` is now loaded from the sweep TSV; WHIR_FOLD 16 = the reference
  implementation's default folding factor). The user: pruning counts as a design change if the
  implementation does not do it. Checked: the WHIR crate at the sweep's revision prunes already
  (`src/protocols/merkle_tree.rs`, `opening_sibling_indices` merges neighbouring branches and
  sends no hint for them; the verifier mirrors it), so the measured sizes are pruned multiproofs
  and the extra trees priced the same way are not a design change for WHIR. The 𝔽₂ rows use the
  optimizer's own Merkle-cap accounting (Ulrich's expected multiproof hashes); BitZ's extra is a
  share of its measured Ligerito bytes, so pruning cancels in the ratio. BitZ ARC: the Ligerito part x (1 + 2 x the first level's share of columns and paths,
  `ligerito_first_share`), the verifier likewise as a bound. Effect: WHIR ARC at rank 13, rate
  1/8: 177 -> 326 KB (362 with full paths); the recursive rows (one stand-alone proof) are a
  little over half the ARC rows' bytes; the WHIR-over-Pasta ARC verifier 62 ms at rate 1/8 (31
  under recursion).
- Not changed, noted for later: the merge circuits price ARC as "t openings per input" x 2 inputs
  (ARC, ePrint 2024/1731, §1: "t = 2 lambda / log(1/rho) Merkle path openings per input"); whether
  the step's own witness oracle and the output accumulator add in-circuit openings was not
  re-examined.
- RESULTS (floor 128, header 2, best grinding per row). 𝔽₂ ARC, 192-bit: 446/241/174/140/121/106
  KB at rates 1/2..1/64, prover 6.0e8/4.2e8/4.4e8/5.7e8/8.5e8/1.4e9, merge 74M..14M AND gates,
  verifier 0.25-1.4 ms; the 256-bit design about a tenth larger and costlier. Recursive, 192-bit:
  340/182/131/106/92/81 KB, prover 2.5e9..5.1e9, merge 332M..76M bits; 256-bit: 398..101 KB,
  4.0e9..1.25e10. The 2026-10-22 "frontier point" (64 KB at 1.3x Akita Goldilocks) is GONE: with
  the three trees and the real prover, the smallest 𝔽₂ ARC proof is 106 KB at 1.4e9, 27x Akita
  Goldilocks's prover. 𝔽₂ rows still show on the post-quantum frontier through the accumulation
  measure (40 atoms against Akita's 150-230). WHIR-type ARC rows are now 171 KB-1.3 MB (whir
  197-831 KB).
- Page prose updated: lede unchanged; "Which third measure" (verifier range), "The hash-based
  families" (197-831 KB, the three trees, 226 vs 326 KB, Goldilocks a sixth), "ARC against each
  scheme's own recursion" (proofs now differ; recursion's proof a little over half of ARC's; the 𝔽₂
  family's own recursion), "Verifier work" (13/62 ms ARC, 7/31 recursion; 𝔽₂ 0.2-1.4 ms; BitZ scaled), and the
  𝔽₂ paragraph (two designs, the ring-switching degree, the cost model, the prover and proof
  ranges). Republished to the same URL on 2026-10-29. The 2024/504 and Flock texts extracted for
  this are work/2024-504.txt, work/flock.txt, work/arc.txt.
- 2026-10-30, ZERO-KNOWLEDGE ROWS for the 𝔽₂ family. The user asked whether zk can be added to
  FRI-Binius, by what scheme, and whether we can price it with confidence; then "add the
  defensible ones". Two routes. (a) The full mask: Diamond, "Zero-Knowledge Polynomial Commitment
  in Binary Fields" (ePrint 2025/1015), which is the optimizer's zk='true' option (a mask
  polynomial of witness size under the same root, an init round opening witness and mask at the
  t positions, the commitment doubled; Zook classes it as "overhead at least 2"): priceable with
  reasonable confidence from the optimizer and the cost model. (b) Zook-style (Chiesa, Fenzi,
  Weissenberg, ePrint 2026/391: o(1) overhead, zk sum-check and code-switching IORs, code-agnostic;
  VEIL, Dalal, Hemo, Rabinovich, Rothblum, ePrint 2026/683, is the other route Flock names): NOT
  priceable: the one data point is Plonky3's HVZK-WHIR at 100 bits over KoalaBear's quintic
  extension with WHIR-tuned masks, and scaling it (elements, queries) to FRI-Binius gives ~100-120
  KB additive, MORE than the full mask's bytes, which shows the transfer is untrustworthy. BitZ /
  Ligerito: the classic random-rows zk is cheap, but there is no anchor; BitZ still drops out.
  Added: zk=True rows for flock and flock_rec in both designs. `frib_at(..., zk)` passes zk to the
  optimizer, takes the fold rounds without the init round for the operation counts, adds t field
  multiplications for the combination; `f2_prover(..., zk)` doubles the witness commitment (NTT
  and tree) for the mask; the optimizer's init round is multiplied by `first_trees` (the mask
  round opens each of the ARC decider's three oracles). Results (floor 128, header 2, best
  grinding): ARC 192-bit zk 718/388/280/225/194/171 KB at rates 1/2..1/64 (+265..+63 KiB over
  plain), prover x1.20..x1.52; recursive 192-bit zk 458/247/178/144/121/111 KB (+115..+30 KiB),
  prover x1.5..x2.1 (the commitment dominates the recursive prover). The page's zero-knowledge
  paragraph describes the rows, the upper-bound status, and the two caveats (the ring-switching
  reduction's revealed partial evaluations need their own mask, unwritten; the ARC merge is left
  unchanged, as for WHIR). Republished 2026-10-30.
- 2026-10-30, ZOOK FOR FRI-BINIUS WORKED OUT (the user: "why do the 𝔽₂ zk rows grow so much when
  Zook claims o(1); work out whether Zook's spot checks could be cheaper for FRI-Binius than
  Plonky3's parameters make them for WHIR"). Read Zook §2.2-2.7, §8, §10 (work/zook.txt). Its
  structure: (1) the main oracle is a zk ENCODING of the code (r random coefficients per
  interleaved piece, r >= the queries t; free in bytes, fits the witness padding); (2) the sumcheck
  is masked with k small masks per k-round reduction (one per variable; univariate of degree <
  l_zk), encoded in a zk code C_zk at a low rate and committed as oracles, each queried t_zk
  times, with t_zk from (1 - delta_zk)^t_zk <= 2^-lambda, i.e. t_zk = lambda / log2(1/rate_zk);
  (3) each CODE SWITCH adds a mask encoding (s, r) with l_zk >= r (Theorem 10.2: l_zk >= max r_i),
  so WHIR's masks have message length >= the main code's zk randomness ~ t ~ 100, hence oracles of
  thousands of symbols and 12-level paths (Plonky3's "twelve levels"), one group per round; (4)
  OOD samples need private zero-evaders; (5) the terminal uses the full-mask base case on a tiny
  instance. Check against Plonky3's HVZK-WHIR: 5 groups x 21 checks x (12 x 32 B + leaf) ~ 50 KB +
  OOD, messages, terminal ~ the measured 73 KB. FRI-Binius has NO code switching (oracle skipping)
  and NO OOD samples, so its masks are the sumcheck masks only: degree ~3 -> l_zk ~ 4 (+ r_zk =
  t_zk for the mask's own zk encoding), grouped per committed round (ell masks per group, 3-5
  groups), at mask rate 1/256: t_zk = 16, oracle ~5k positions, path 13 (9 after multiproof
  pruning over 16 queries), leaf ell x 32 B: ~7-9 KB per group -> 30-45 KB; plus ONE larger mask
  for the ring-switching claim (the revealed element of A has 2^kappa L-components, so l_zk >=
  2^kappa: 64 or 256 coefficients, ~8 KB); masks are per proof, not per oracle, so unchanged under
  ARC's three trees. ESTIMATE: ~40 KB (35-55) additive at 128 bits, prover ~x1.0, independent of
  the rate and of the tree count; against the full mask's +35 KiB stand-alone / +103 KiB under
  ARC and x1.4-1.9 prover. So Zook-style IS cheaper for FRI-Binius than Plonky3's WHIR numbers
  suggest, because the expensive part of WHIR's masking is the code-switching masks, which
  FRI-Binius does not have. Confidence: a first-principles count with the Plonky3 measurement as
  the only cross-check (reproduced to the right order); the ring-switch mask is my design.
- 2026-11-02, ZOOK-STYLE ROWS ADDED (the user: "yes please do that second zk variant"): points
  carry `zkv` in (None, "mask", "zook") beside the boolean `zk` (the page's filter), `zkv` in
  `grind_key` so "best per row" keeps both variants; labels ", ZK, full mask" / ", ZK, Zook-style,
  derived". `zook_masks(rounds, terminal, floor, chal, pack)` -> (bytes, hashes, prover ops):
  per folding round a group of ell masks of ZOOK_MASK_COEFFS = 4 coefficients, plus one group
  with a 2^kappa-coefficient mask for the ring-switching claim, each mask with t_zk = floor/8
  random coefficients, encoded at rate 1/256 (ZOOK_MASK_RATE_BITS), t_zk spot checks with
  `frib.expected_multiproof_hashes`, leaves masks x elem bytes, the masks' claimed sums, and the
  terminal's full mask; prover = the masks' NTTs and trees (tiny); the recursive merge verifies
  the spot checks (2 x zook hashes), which is where its prover's +3..15% comes from. `f2_bytes`,
  `f2_prover(..., zk)`, `f2_verify(..., zk)`, `f2_rec_merge(..., zk)` take the variant. RESULTS
  (floor 128, header 2, best grinding, 192-bit; 256 a little more): ARC Zook +44/+30/+27/+27 KiB
  at rates 1/2, 1/8, 1/32, 1/64, prover x1.00-1.02 (full mask +265/+103/+71/+63, x1.2-1.5);
  recursive Zook +45/+36/+32/+34 KiB, prover x1.04-1.15 (full mask +115/+46/+28/+30, x1.5-2.1).
  So under ARC Zook-style is 2.3-6x cheaper in bytes than the full mask; under recursion the two
  are close in bytes (the full mask's init round is one tree there) and Zook wins on prover.
  Page: the zero-knowledge paragraph describes both variants, the upper/lower status, the
  Plonky3 cross-check, and the caveats. Also on 2026-11-02: pareto-model.py got blank lines
  between top-level functions and constant blocks (the user's readability request); only
  whitespace changed. Republished 2026-11-02.
- 2026-11-02, PROSE REVIEW (the user: "review the text for anything stale or incomplete"; the
  extracted prose is work/page-prose.txt). Fixed: the binary-field section's "zero knowledge is
  not modelled"; BitZ's ARC row figures (302 KB / 31M bits / 5 ms -> 500 KB with the three
  trees / 28M / 7.5 ms) and the frontend's "3.4 times smaller" (-> 5.7); "What the axes mean"
  now mentions the extra trees and the 𝔽₂ and BitZ sources for bytes, prover and atoms, and
  AND gates / witness bits for merge gates; the Grinding paragraph's BLAKE3 settings (12 to 18
  bits, not "lower"); the Pasta-requirement list adds BitZ and the frontend; the Knobs list
  gains 𝔽₂ and BitZ entries; the Security-floor paragraph says the 𝔽₂ optimizer runs at the
  floor; the zero-knowledge checkbox label is "(see text)". Republished.
- 2026-11-02, THE DIRECT 191-BIT DESIGN (Ulrich: why pack into GF(2^64) elements for the
  192-bit strategy; "I would have gone for packing into the 191/192 bit field, for the
  efficiency of field arithmetics"; the user: consider a direct 191-bit construction). Added as
  the third design, `F2_DESIGNS[191] = dict(pack=191, twiddle=7, ...)`: bits packed straight
  into GF(2^191), a prime-degree field with the trinomial x^191 + x^9 + 1 and no subfields;
  the witness laid out as 191 columns that the PIOP batches, the ring switching in one step of
  degree 191 (the paper's hypercube packing needs 2^kappa, so this is a design change like the
  64/192 one). Model changes: F2_DESIGNS gained `twiddle` (clmuls per NTT butterfly: 4 for the
  256-bit tower, 1 for 64-bit symbols, 7 = a full-field multiplication for GF(2^191), which has
  no subfield to hold the evaluation domain), used by `f2_ops` instead of pack//64; CLMULS[191]
  = 7 (six limb products + one trinomial reduction) and CLMULS[192] raised 7 -> 8 (six limb
  products + six limb reductions + the cubic reduction) for fairness (the 192 rows' prover
  +2%); KARATSUBA_ANDS[191] = 6 x 3^6; `elem_bytes` (ceil, 24 B for 191) and `limbs` (ceil, 3
  for 191; the earlier `chal // 64` undercounted the ring-switch XORs for 191) helpers; the
  port's FIELD_BYTES is now ceil(field_bits/8). RESULTS (floor 128, header 2, best grinding),
  ARC: bytes identical to the 192 design at every rate (108 vs 106 KB at 1/64, a list of 2^6
  vs 2^7); prover 191 vs 192: -6% at rate 1/2, -2% at 1/4, +3% at 1/8, +7% at 1/16, +10% at
  1/32 and 1/64 (the NTT's full-field twiddles, 2x per bit, outweigh the cheaper reduction and
  the half-size folds at low rates; at rate 1/8 ntt 8.1e7 vs 3.8e7, fold 2.9e7 vs 5.2e7, piop
  1.03e8 vs 1.12e8). Recursive: 191 costs 3-10% more bytes and 8-75% more prover, since the
  in-circuit ring-switching verifier does 2 l' x 191 field multiplications instead of 2 l' x 64
  (168M vs 116M witness bits at rate 1/8). So for Ulrich: packing into GF(2^64) was for the
  ring switching's power-of-two packing and the NTT's subfield twiddles; a direct prime-degree
  field is as good on bytes and a wash on the prover under ARC (better at high rates, worse at
  low), and worse under recursion. Page: the binary-field paragraph (three designs, the
  trinomial, the twiddles, the clmul counts 4/8/11 and 7, the prover comparison), the
  recursion paragraph (168M bits), the Knobs entry; the zk ratios re-read (1.8x rec full mask;
  Zook one to four percent). Republished 2026-11-02.
- 2026-11-02, later: the hover text wraps the row label at commas into lines of about 60
  characters (`wrapLabel` in the template; the user: the detail window was too wide to read).
  A Signal summary for Ulrich of the 2026-10-28 to 11-02 changes is keep/ulrich-summary-2026-11-02.md.
- 2026-11-02, STATE OF THE STUDY: the user and Ulrich agree that refining the estimates without
  an implementation has reached diminishing returns; Suyash (Shielded Labs) is exploring the
  hash-based branch by implementation, and the plan is two prototypes, one hash-based and one
  lattice-based, to decide on. Ulrich is "not so much convinced of using ARC, or maybe not
  baked into each recursive proof". The user's reading of the 191-bit result: it does not pay
  off, except a little in prover cost at larger proof sizes (high rates). Open design question
  from the user: Pasta is needed only for the Ironwood recovery circuit, but recovery and
  non-recovery transactions must aggregate together; can Goldilocks and the Pasta-claims
  variant be combined? (Answered in the chat: emulate Pasta non-natively inside the recovery
  circuit over a Goldilocks arithmetization, or carry a second Pasta-claims accumulator.) The
  user: the Merkle path is native, since the Ironwood commitment tree is public and can be
  rehashed with whatever hash the arithmetization likes; so the recovery circuit's Pasta-only
  content is the two full-width Pallas scalar multiplications and the two Sinsemilla
  commitments, 3-6k Pasta multiplications, 0.3-0.6M Goldilocks constraints non-natively, while
  its seven BLAKE2b compressions get cheaper over a 64-bit field; the emulated recovery leaf is
  plausibly no larger than the native Pasta one, so the Goldilocks route wins at any recovery
  share. RETRACTED 2026-11-03 by keep/recovery-circuit-cost.md (the user: estimate more
  precisely in Ragu's R1CS variant, read ZIP 2005): Ragu has no lookups, so an emulated Pallas
  multiplication is ~1,100 gates (nine 29-bit limbs, the user: limbs need not be powers of
  two); the recovery circuit is ~570k gates native over Pasta (the hashes and Sinsemilla's
  generator selections dominate, field-independent) against ~16.5M over Goldilocks (the five
  fixed-base and one variable-base complete scalar multiplications, 160 Sinsemilla additions
  and the nullifier's Poseidon over Pallas's base field, ~14.5k emulated multiplications); a
  recovery leaf costs 6x more under Goldilocks at the page's per-coefficient prices, so
  Goldilocks wins only below a 6-10% recovery share. The user's remarks: lookups are possible
  in Bootle16 but probably do not pay off here, and would also make XOR cheap, not only the
  selection and range checks. The rehashed Merkle path is priced two ways at the user's
  request (designs are moving to conventional hashes for assurance): Poseidon 1.1 in the
  arithmetization's field at a free width (the user: not Poseidon2, because of cryptanalysis
  against it and out-of-circuit optimisations of Poseidon 1.1 that close most of the gap;
  Pasta width 3 at 288, Goldilocks width 12 at ~470 since 128-bit collision resistance needs
  a four-element capacity: 9.5k / 15.6k gates for 33 nodes) or BLAKE3, the cheapest conventional hash in a lookup-free R1CS at 14.9k per
  compression, 492k for the path in either field, which nearly doubles the native circuit to
  ~1.05M and costs every Ironwood step with a path the same; break-even then 6-19%.
  The user's reading (2026-11-03): 16-30x gate overhead for the recovery circuit without
  native Pasta, against 4.12x slower prover with Pasta claims (the page's 1.98e8 / 4.81e7), so
  the trade-off runs toward Goldilocks. Other fields considered in chat: 31-bit fields
  (BabyBear, KoalaBear, Mersenne31) make the emulation ~3x worse (12-bit limbs) and need a
  quartic extension for soundness, for a commitment only ~2x cheaper, and Akita's p32 variant
  is slower by the paper's own verifier numbers; a 128-bit field eases the emulation to ~700
  gates per multiplication (61-bit limbs) but costs 6.5x per coefficient (the page's 2,600
  against 400); Mersenne-61 lacks the 2-adicity Akita's ring X^64 + 1 needs (q = 1 mod 128);
  a quadratic-extension circuit field over Goldilocks doubles every coefficient for a third
  off the emulation, a wash. A prime just above 2^64 (the user: 2^64 + 13, 2^64 + 2^21 - 1,
  with a flag for the 65th bit) does NOT pay the 128-bit cost, which I first claimed: one
  64x64 product and a fold 2^64 = -c, like Goldilocks's reduction, with only c residues
  needing the flag; it lets 64-bit hash words fit whole (BLAKE2b additions 65 instead of 67
  gates, ~1% of the native circuit), buys nothing for the emulation (30-bit limbs already fit
  Goldilocks's column bound; 29 was used), and loses the NTT structure unless chosen with
  q = 1 mod 128 for Akita's ring (those two examples have 2-adicity 2 and 1). The user asked
  for a search: prime-search.py (p = 2^n -+ c, 64 <= n <= 68, c of signed weight <= 3 below
  2^48, 2-adicity >= 7; 563 primes; log work/prime-search.log; write-up
  keep/field-candidates.md). The user's pick, 2^65 - 2^42 + 1: 65 bits (one flag bit),
  2-adicity 42, p - 1 = 2^42 x 47 x 178481, α = 3 allowed, quadratic extension x^2 - 3
  (130 bits; no binomial cubic since 3 does not divide p - 1); Poseidon with α 3 at width
  12 is 278 gates against Goldilocks's 472 (R_F 8, R_P 43 from the official
  calc_round_numbers.py in the user's fork ~/olddaira/research/pasta-hadeshash/code, which
  reproduces halo2's 8/56 and Plonky2's 8/22 exactly; width 14: 310; width 3: 130; α 5
  would be 369), so option A's path ~9.2k and the lattice merge's absorption ~40% cheaper;
  native multiplication folds three times where Goldilocks folds twice; the emulation is
  unchanged.
- 2026-11-03, LOOKUPS EMULATED IN RAGU (the user: consider the cost, halo2's argument, Plookup,
  logUp etc.; survey the literature and papers citing logUp; assume a challenge after committed
  values is possible even if not implemented for application circuits; the user saved the
  papers under keep/: 2022-1530 logUp, 2022-1763 cq, 2023-1216 Lasso, 2025-946 logUp*,
  2025-1876 the SoK). Write-up: keep/lookups-in-ragu.md; the width sweep is spread-widths.py
  (log work/spread-widths.log). Findings: Ragu's staging chapter already describes
  commit-then-hash-to-a-challenge; logUp is the one to emulate (1 gate per lookup, 2 per
  table entry, sums free; halo2/Plookup 3-6 per row; Lasso/cq need sumcheck or pairings);
  tables are paid per step circuit; the user's pointers: table widths need not be powers of
  two, and halo2_gadgets' SHA-256 spread technique (the gadget was unsound, the technique was
  not) gives XOR by adding spread forms, one (tag, dense, spread) table for every width, and
  free rotations by cutting pieces at the rotation amounts. The decisive point: soundness
  (lookups + entries)/|F| per challenge, so Goldilocks and the 65-bit field need three
  challenges (3 gates per lookup) where Pasta needs one. The spread width w must be weighed
  against the per-step table (the sum of 2^k over the width classes used, times 2L): the
  sweep over w = 4..16 at ranks 13-16 is in the note. Caveats since logUp: the characteristic
  bound (Eagen-Haböck 2024/2067 lifts it for binary fields; vacuous here), logUp* (no
  commitment of looked-up values in sumcheck systems; no effect on gates), the SoK's
  projective-ratio warning, and lookup accumulation (Protostar, nLookup, FLI) as the
  design-change route that would remove the in-circuit challenge cost. The sweep: over Pasta
  w = 8 is best from rank 14 (BLAKE2b 10.7k effective at rank 16 against 51.6k) and w = 6 at
  rank 13 (18k); over Goldilocks lookups cost more than they save below rank 15 and give 28%
  on hashes and 38% on an emulated multiplication at rank 16 (w = 8). Recovery circuit at rank
  16 with lookups: ~110k over Pasta claims (5x smaller), ~12.0M over Goldilocks (1.4x).
  WHAT IT DOES TO THE BREAK-EVEN (the user's question): without lookups Goldilocks wins below
  a 5-19% recovery share (keep/recovery-circuit-cost.md). With lookups the recovery gap widens
  (2.2e8 against 4.8e9 per leaf at rank 16) AND the ordinary steps' gap narrows, because a
  hash-heavy ordinary step shrinks 5x over Pasta and 1.4x over Goldilocks, which cancels most
  of Goldilocks's 4x per-coefficient advantage: with S = 200k hash-heavy, the ordinary step
  costs 8.0e7 over Pasta against 5.7e7 over Goldilocks, so the break-even falls to about 0.5%;
  if the ordinary step does not benefit from lookups, 6.5%. At rank 13 (Pasta lookups only,
  w = 6, no Sinsemilla table): 1.3% to 5%. So adopting lookups makes Pasta claims the better
  route unless recoveries are very rare; the lever that would restore Goldilocks is lookup
  accumulation (fractional sums proven by GKR or folded in the accumulator), a Ragu design
  change.

## 2026-11-03: moved into the Post-Quantum Zcash repository

This directory is now `ragu-pcs/` in the pqzcash repository (private at zodl-inc/pqzcash for
now), whose book presents the study as a comparison of candidates; no commitment scheme has
been chosen, and the directory's name was chosen not to suggest otherwise. Tracked: the notes,
the scripts, the page template, `estimates/`, and the FRI-Binius optimizer with its port.
Not tracked: `work/` (the scratch clones, logs and texts; the `akita-src-150` worktree link
was repaired after the move), `keep/` (the three 2026-11-03 write-ups and the saved papers),
`hash-based/` (the user's paper PDFs), `pareto.html`, and the nine TSVs of 2026-10-13 at the
top level, which are older copies of what `estimates/` holds. The book is built from the
repository root with `nix develop --command scripts/build-book.sh`, which regenerates
`pareto.html` and serves it as the book's PCS frontier page. Open: the optimizer's licence
(Ulrich's script came without one) must be settled before the repository goes public.

## 2026-11-04: the masked witness's length charged to the zero-knowledge layer only

The user: the 14 MB masked accumulator applies to the split accumulation of zk steps, not to
the folds above them. Agreed, from the note's own protocol: §3.2 step 5 decomposes z into nine
digit slices, each committed; the aggregator's first fold range-checks them and folds them
back to N digits with its other inputs, as every lattice fold decomposes and folds. What
persists above is the Module-SIS rank, 2.4x, since §5.2's extraction argument needs one
matrix for the whole chain. Changes: pareto-model.py no longer adds log2(9) to the decider's
`log_len` (opening bytes and verifier) and no longer multiplies the verifier by 1.15;
MASK_RANK stays on the rows term everywhere; MASK_SUMCHECK_ATOMS, now derived from
MASK_LENGTH, stays in the merge, which the page describes as one at the zk layer, merges
above paying the rows term only. Effect at 128 bits: the zk rows' bytes equal the plain rows'
(before: +1.5 KB Goldilocks to +7 KB Pasta variants), the verifier is 13% lower, prover and
atoms unchanged (Goldilocks rank 13: 67,866 B both; prover 4.81e7 -> 9.84e7; atoms 231 ->
249). Prose: the page's zk paragraph and verifier bullet; zk-fiat-shamir-with-aborts.md §5.4,
whose witness-size bullet is corrected and which gains a bullet on where refinements change
the figures (the shared matrix; the digit base, α and the challenge weight; the witness
size); pasta-proof-size.md's accumulator-witness paragraph. Then, the same day (the user: model the masked
rank's effect on the opening and the verifier): the masked rank composes with the floor's
factor (`rank_factor = rank_scale * MASK_RANK`) and goes through the 150-bit mechanism, the
inner images' share of the opening and of the verifier. The user then asked whether the zk
bytes had grown (they had, from this) and for corrections based on the inner-image share, so
IMAGE_SHARE is now derived from the shipped terminal geometry (pasta-proof-size.md §6.1:
1,344 clear t coordinates, 16 B each at fp128, the same bytes at a 64-bit modulus, 32 B with
Pasta for everything) over the opening at K = 0: fp128 0.33, Goldilocks 0.35, q64 0.30,
pasta_sis 0.26 (was 0.5), pasta 0.42 (was 0.5); the verifier scales through the same share
(was: wholesale), which also lowers the 150-bit verifier figures a little. At 128 bits, rank
13, header 2, plain -> zk: fp128 72,253 -> 105,093 B (+45%), verify 8.1e6 -> 1.21e7 (x1.49);
goldilocks 67,866 -> 100,581 (+48%); pasta_q64 83,371 -> 118,136 (+42%); pasta_sis 96,941 ->
131,763 (+36%); pasta 122,849 -> 195,203 (+59%); prover x2 as before; atoms +19 (18 plus one
circuit). Caveat stated on the page: the share is the shipped geometry's, and a schedule
planned at the masked rank would replace it. The same day: the cross-references between the notes and from the page
became links; 𝔽₂ is written with the double-struck letter; the table's unit heading no longer
reads MS under the CSS uppercase transform. The book is rebuilt after every change the user
is to review: `nix develop --command scripts/build-book.sh` from the repository root.

Later on 2026-11-04 (the user: try harder to reduce the zk proof-size overhead; why does the
DL trick, folding with a random proof, not transfer; zk could be applied only at a trust
boundary): re-examining which matrices the masked bound binds showed that it is the
accumulation matrix only. The fold identity is checked under it and every accumulator shares
it; Akita's internal levels and terminal open the final accumulator's ordinary witness under
their own matrices (Akita §5: inner images are carried onward as digit-decomposed auxiliary
data of lower order; the terminal's images are under A_term). So the masked-rank effect on
the opening and the verifier modelled earlier in the day (+36 to 59% bytes, x1.4 to 1.6
verifier) was the floor's mechanism misapplied and is withdrawn; the zk rows' bytes and
verifier equal the plain rows' again, and the mask is charged to the prover's rows term and
the zk-layer merge only. IMAGE_SHARE keeps its derivation from the terminal geometry, which
the floor's factor still uses. The page, both notes and the model's comments say which
matrix the mask binds. Consequence for the user's aim: Akita's zk overhead in the final
proof is essentially nil; what the mask costs is the prover's 2x (root rows), the zk-layer
accumulator (14 MB) and the zk-layer merge's sum-checks, and the levers (α, the challenge
set's ℓ1 norm, block-wise masking) act on those. The hash-based families' 73 KB of masks
remain the real zk proof-size overhead on the page. Exact extraction (an opening
(c - c')^{-1}(z - z') instead of a relaxed one) was explained as unlikely to beat the relaxed
bound: it needs the inverse's operator norm, 1 over the smallest canonical embedding of
c - c', to be small for every pair in a 2^128-size set, and the quotient to be integral,
neither of which holds for large ternary challenge sets; monomial sets have small
denominators but a factor of order d and far too few challenges.

Same day, the user's list (reduce the zk overhead), items 1 and 2: (1) the mask's parameters
are priced in zk-fiat-shamir-with-aborts.md §5.6 (α and the challenge set's ℓ1 norm, with the
challenge-set sizes at the accumulation matrix's ring dimension, 512 in the catalog at 2^14):
α = 6 with weight-20 challenges in dimension 512 brings the rank factor 2.37 -> 2.11 and the
masked accumulator 14.2 -> 12.6 MB for 7.5 attempts; pareto-model.py now derives MASK_RANK
(2.372, was the rounded 2.4), MASK_LENGTH and MASK_SUMCHECK_ATOMS from MASK_ALPHA and
MASK_CHALLENGE_L1 via `masked_log_beta`, keeping the note's α = 12, ‖c‖₁ = 32 as the page's
default; the page's zk paragraph says so. (2) §5.7 is the block-wise masking write-up for the
user to judge: per-block challenges need B commitments per vector (12,000 atoms at B = 256,
not attractive); one challenge with k candidate masks per block and a published index (the
index leaks nothing, the acceptance probability being independent of the secret) costs k
times the sampling and a binding of kB candidates, a Merkle tree over compressed images
opened at B leaves in the zk-layer merge (about a million gates at B = 256), and would give
four bits off the bound (factor 1.94, or 1.70 with §5.6's parameters) and an 11 MB
accumulator; open. Items 3 (re-plan the accumulation matrix under Akita's policy) and the
exact-extraction lever were not pursued.

Same day, later (the user: the fold's seconds are too expensive for one zk step on a cheap
phone): §5.4 now derives the per-attempt cost (2^24.6 multiplications for the commitment at
340 Pasta rows, 0.3 s at 3e9 word mults/s; Karney sampling of 2^22 coordinates comparable;
about a second per attempt, 3 s per fold at α 12, 8-10 s at α 6) and §5.8 moves it off the
device: precomputed candidate masks (sampled and committed in idle time, bound before the
challenge, first accepted index published, batch discarded; k+1 rewinds for extraction) and
deferral of the slice decomposition and the range/norm obligations to the aggregator's first
fold (open point 7), leaving online a sparse ring product and a vector addition (~2^27
additions, 0.1 s on a phone core) and the ~13 MB transfer of z, which is intrinsic.

Later on 2026-11-04 (the clock had not yet passed midnight in the user's zone): the page's default challenge set is weight 20 in the accumulation matrix's ring
dimension 512 (MASK_CHALLENGE_L1 = 20; free, §5.6), rank factor 2.22 instead of 2.37; α stays
12. The zk note's §5.8 (candidate masks precomputed offline, obligations deferred to the
cross-transaction aggregator's first fold, which is the party untrusted for privacy) answers
the user's point that seconds of masking work are too much for one zk step on a phone.

Later on 2026-11-04 (the user: the zk effect on a typical transaction is hard to see, since
the rejection is a large fraction of it; expose it as a third measure): the page has a
fourth third measure, "transaction prover", with a knob for the transaction's size in
application gates (2^16 to 2^20, default 2^17). Per point the model supplies `step_prover`
(one application step circuit's commitments at the family's per-coefficient cost; for the
𝔽₂ family, which has no rank, BitZ's convention of 510 bits per Pasta gate in steps of 2^13) and `fold`
(Akita zk rows: `mask_fold` = MASK_ATTEMPTS x N x (masked per-digit commitment cost + 900
word-mult equivalents of Karney sampling at 300 ns), plus the fold's own merge; 0 elsewhere);
the page computes transaction = (G / 2^rank) x (step_prover + prover) + fold and uses it in
the dominance test, the hover, a table column and the axis title. At G = 2^17, rank 13, 128
bits: fp128 1.6 s plain -> 5.0 s zk (fold 42%), Goldilocks 0.3 -> 1.5 s (64%), pasta_q64 1.2
-> 6.1 s (61%), Pedersen 29 s, WHIR ARC rate 1/2 about 3,000 s (Pasta) / 630 s (Goldilocks).
The page's prose (Which third measure; a Transaction prover paragraph after Grinding) says
it is total work, not latency, §5.8 moving the fold off the device. Republished.

## 2026-11-11 22:36 UTC: hashes in circuits, pruning, ranks 12 and 17, the licence, LaBinius

Ulrich (relayed by the user) asked whether the page took Akita's transcript hashing into account
or assumed Poseidon; it assumed Poseidon 1.1 everywhere but the 𝔽₂ family and BitZ. The user's
ruling: arithmetic hashes on the merits (Tachyon uses Poseidon 1.1; no attack near a break at
large fields and our widths), but conventional hashes by default for future-proofing (decisive
for long-term storage), with an "arithmetic allowed" option. Done, six commits on main (the user
pushes): ad39215 licence headers (Ulrich agreed MIT or Apache-2.0 for frib_optimizer.sage,
2026-11-11; the port the same, extensions as the repo), c6f24db the hash-policy setting
(`HASH_POLICIES`, points carry `hashes` in blake3/poseidon/any; Akita's transcript at 14,900
gates per 64 bytes absorbed, `akita_absorbed_bytes` = sum-check elements and claims at the claim
width + K × 128; `hv(variant, hp)` swaps the WHIR-type trees to BLAKE3 at one compression per
node and the leaf's bytes in 64-byte blocks; Pedersen rows hashes="poseidon"; `akita_circuits`
returns None where a circuit's claim costs more to absorb than the budget: ranks 13-14, and 15
for Pasta claims, under BLAKE3), 06623b8 pruning (rows dominated within their family on every
plottable measure among rows selectable only together: rates, and the post-quantum header-4
twins; the header knob now acts on Pedersen only; family_label dropped from the JSON; the
table's assumption column covers the _rec, bitz and bits_q64 families; page 21 → 8.7 MB),
5a16e26 marker sizes on a log scale over the plotted points (5-22 px; the 50-px cap had every
hash-based marker at the cap), 22d1292 prose (lede's four third measures, per-circuit claims in
the bytes and atoms bullets, docstring), then ranks 12 and 17 (RANKS 12-17; HASH_RANKS 13-16 for
the WHIR-type rows; Pedersen skips ranks where no binder challenge fits). Verified: each of the
first five commits runs the model on its own (git archive + run). Numbers at 128 bits, header
2, no zk: Akita BLAKE3 rank 16: fp128 75.7 KB / 8.55e9 / 0.83M gates / 51 circuits (Poseidon
rank 16: 72.2 KB / 3.35e8 / 25k / 2); Goldilocks 70.7 KB / 1.31e9; pasta_q64 97.7 KB / 1.61e10 /
2.0M / 122; rank 17: fp128 7.38e9, Goldilocks 1.13e9, pasta_q64 1.14e10 (−14 to −29%). WHIR
Pasta ARC rate 1/8 rank 13: BLAKE3 385 KB / 1.49e12 / 64.6M gates / 31,536 circuits / verify
2.5e6, Poseidon 326 KB / 7.7e11 / 1.07M / 524 / 1.86e8; the asymmetry is real: the hash-based
prover was hashing-dominated (180k → 5k per coefficient), so cheaper hashing offsets the 60×
circuits, while Akita's per-coefficient cost is Ajtai and unchanged, so its 26× circuits go
straight to the merge prover. Rank 12: BitZ −1% bytes, −12% merge prover; Pedersen infeasible.
Page prose: a "Hashes in circuits" paragraph (rationale in the user's words, the figures), the
Knobs entry, the Circuit budget paragraph (claims fixed point; splitting a compression across
circuits assumed free), the Rank paragraph (12 and 17), and policy qualifiers wherever
Poseidon figures are quoted. Artifact republished to the same URL. The screenshot script
work/pup/default-shot.mjs shoots the default view under both policies.

Ulrich's updated optimizer (github.com/ulrich-haboeck/scripts, ada1e779, 2026-11-10; revisions
saved under work/ulrich-scripts/): automatic list size (his counts the codeword in elements,
w − 8 + rate_bits, where the original and our port count bits: 8 bits of slack); zk restructured
(CORRECTED, see the 2026-11-12 entry: the first version of this paragraph said his model charged
MORE than ours; it charges much less): the separate opening round of the original (witness and a
witness-size mask opened at t positions of the full tree, which our rows used) is gone; since
c5bef266 "corrected leaf blinders" the FIRST round's leaves carry one mask row (a field element)
plus a 32-byte blinder, the recursion passes zk='false' so later rounds carry neither, and a
schedule with no reduction opens witness, mask and blinder before the reveal; the header
comment still says "dense mask of the same size as the witness", which is the state before
c5bef266 (2^ell mask rows); a constant 2 KiB Galois-orbit overhead; verifier hashes = pruned
paths + opened leaves (our port counted unpruned paths). He says the full-entropy mask in a
batching step before FRI is the only secure randomization for FRI-Binius, which contradicts our
derived Zook-style rows. Questions sent to him (keep/ulrich-zk-question-2026-11-12.txt): one
mask row or witness-size; what hides the opened columns of the first oracle (a zk encoding with
random padding, with the row masking only the batched row?); mask and blinders in the first
round only, and the direct-reveal case.

LaBinius (ePrint 2026/2103; the user asked why it is not on the graph): the old reason (no Pasta
circuits) lapsed with the 𝔽₂ family's own accounting. The paper gives a decider only: native
proofs are the amortised opening v = W c, √N-sized (307 KiB at 2^18 elements to 2.9 MiB at 2^24,
commitments 283 KiB to 2.4 MiB), LaBRADOR compresses to 73-86 KiB constant at a 10× prover and a
77-713 ms verifier, all at 100 bits over 𝔽₂₁₆₂; Table 1 = PCS alone vs BaseFold/WHIR/Ligerito/
Brakedown, Tables 2-4 Binius outer system (Keccak/SHA-256/BLAKE3), Tables 5-6 Flock outer system.
No accumulation or recursion layer: folding the √N commitment in a Boolean circuit ~1e8-1e9 AND
gates, in-circuit LaBRADOR unpriced. The practical combination is Akita's binary groups:
LayerZero-Labs/akita#285 (tracking; the LaBinius root reduction and nested PCS of PR #229 are
REPLACED by binary groups opening inside one ordinary grouped Akita opening on `dev`, feature
`binary`; LaBinius crates deleted in #421). Data: PR #312 (full-size binary-source measurements,
2^22/2^23 F128 carriers = 2^29/2^30 bits: 82.7-84.6 KB proofs) and PR #428 (P64/E64 root, stage
6: at 2^22 carriers P128 82.8 KB / prove 648 ms / verify 8.5 ms, P64 79.2 KB / 1,045 ms / 11 ms;
plus-ordinary shapes 84 KB; shared M4 Max, parallelism unstated; security ledger open, q24
certificate open, "no security claim"). Specs saved under work/akita-binary/*.md. The user
wants it on the graph: the row is a Flock-style Boolean arithmetization over Akita's binary
groups, priced like bits_q64 (Akita per-digit prover at one digit per bit, Akita merge in AND
gates with BLAKE3 absorption native and the Z_q folding emulated, the decider from #312/#428
scaled to the merge's bits, pasta=False, zk=False, 510 bits per Pasta gate in the transaction
measure), flagged experimental. NOT DONE YET.

Also pending: the user's knob-simplification question (proposal in chat: merge Header and Fixed
circuits into a Pedersen-IPA group; cut Grinding to best/none/16/20/24; merge Axes, Scale and
Camera into one View group; fold Transaction size into Third measure); rates that are not
negative powers of two (answered in chat: possible over prime fields with mixed-radix FFT domains
and for expander codes, not over 𝔽₂'s additive domains; the trade-off is smooth between the
powers of two, so nothing new on the frontier); BitZ reruns on mains and the recovery circuit
per component (older).

## 2026-11-11 23:49 UTC: the optimizer port and fewer knobs

Commits 2f8a28a (port) and ccb2921 (knobs) on main, unpushed. `frib_optimizer.py` is now his
ada1e779 with our three extensions (`field_bits`, `first_bytes`, `first_trees`) and an optional
`list_bits` (automatic by default, as his). The mask row is charged at FIELD_BYTES + HASH_BYTES
per opened leaf of the first round, times `first_trees` under ARC; `frib_at` no longer searches
the list (F2_LIST_CAP gone), takes `out["list_bits"]`, counts the verifier's auth hashes over
pruned paths, and returns `mask_share` = 2^-ell1, the mask row's commitment as a fraction of the
witness's, which `f2_prover` uses instead of doubling. Results (192-bit design, best grinding,
rates 1/4..1/64; rate 1/2 rows are pruned as dominated by 1/4): ARC plain 235/169/138/119/105 KiB
(unchanged within 1 KiB; lists 2^8-2^9 instead of 2^7; 256-bit lists 2^20-2^21 instead of the old
2^15 cap, queries equal), mask +19/+12/+9/+8/+6 KiB at x1.07-1.13 (was +143..+63 KiB at
x1.27-1.52), Zook unchanged (+35..+27 KiB), now above the mask rows everywhere; recursive plain
165/123/98/92/75 KiB with provers 1.05e9..4.2e9 (was 177..79 KiB, 1.6e9..5.2e9: the in-circuit
verifier hashes pruned paths, merge 85M bits at 1/8 instead of 116M), mask +7..+2 KiB at
x1.06-1.10 (was +64..+29 at x1.5-2.1); 𝔽₂ verifier 0.1-0.4 ms (was 0.2-1.4). Page text updated
(binary-field paragraph: lists, margins, ranges, verifier; recursion paragraph: merge bits and
prover ratio; zk paragraph: his model, the question, the Zook rows' status; verifier bullet).
Knobs: Header + Fixed circuits merged into a "Pedersen-IPA" group; Grinding select = best per
row, none, 16, 20, 24 (GRIND_OPTIONS filters the other measured settings out of the data after
the best-per-row choice); Axes + Scale + Camera = one "View" group; Transaction size under the
transaction-prover radio. Page 4.3 MB, 9,363 points. Artifact republished (version 81).
Pending: Ulrich's answers (then drop or keep the Zook rows; revisit the mask row's prover charge);
the Flock-style-over-Akita-binary-groups family; the 150-bit re-plan (staged, ~1 h on mains,
expected single-digit percent); BitZ reruns on mains; the recovery circuit per component.

## 2026-11-12 00:42 UTC: zero knowledge paid at the handoff

The user: in our model the cost of zk is paid when moving from private to public accumulation; the
port does not change that. Fixed what did not match it: the hash-based zk rows charged the masked
prover per merge (𝔽₂ x1.07-1.13, WHIR's Plonky3 factor). Now (commit after 5c1234a): per-merge
prover of a zk row = plain; fold = the masked prover's extra (𝔽₂ ARC at 1/8: 4.1e7 against a
4.45e8 step; WHIR Goldilocks ARC: 3.1e7); under ARC the masks stay in the decider's bytes and
verify (𝔽₂ +12 KiB, WHIR +91 KiB at 128 bits); under recursion the zk rows equal plain but for
the fold (the decider verifies a public proof). The dedup key (meant for Pedersen's E variants)
had folded the now-identical rec zk rows into their plain twins; it keys on zk/zkv/grind/rate/
field now. Page text: the zk paragraph (WHIR and 𝔽₂ parts), Which third measure, Transaction
prover. Also earlier today: the held camera is passed back explicitly in the 3D view (5c1234a;
the user's report that toggling zk turned the camera; a second report for the floor was a stale
page). The binary-groups family: data gathered (specs under work/akita-binary/, the measurement
table of binary-p64-root.md: 2^22/2^23 carriers, P128/P64, 79-85 KB, prove 0.65-1.65 s, verify
8.5-20 ms on a loaded M4 Max, parallelism unstated), NOT yet modelled.

## 2026-11-12 01:10 UTC: the two-matrix design written up

The user asked whether Akita can avoid every step paying the masked rows term. Written up as
§5.9 of zk-fiat-shamir-with-aborts.md (commit f1f2b99; §5.2 and §5.4 point to it; open point
10; the page's zk paragraph refers to it): a second matrix A' for the zero-knowledge layer,
with the user's chain and the public merges under the ordinary A, would confine the rank, but
the change of matrix at the handoff must be PROVED (the claims do not bind the witness: a
dishonest user could mask a different short s' with the same claim values), and no
homomorphic route exists (nothing linear takes As to A's). A sum-check proof of A's = C'
needs the verifier to evaluate the multilinear extension of A'^T r, dense and pseudo-random,
so Θ(N) work; the stacked-matrix variant is §5.2's prefix construction. The form that works is
an opening at the boundary (Akita's levels down to a terminal the verifier recomputes),
verified in the first public merge: that seals the handoff as recursion does, but its
transcript alone (an ~85 KB opening proof absorbed in-circuit) is ~2e7 gates with BLAKE3 or
~2e5 with Poseidon, against the rows term it saves (~0.25 s of a 1.5 s zk transaction over
Goldilocks at 2^17 gates), so dearer with conventional hashes and close with Poseidon.
Conclusion: the rank stays with the shared matrix; revisit if a succinct switch for a
structured A' appears or an in-circuit opening becomes cheap. Artifact at version 85.

## 2026-11-12 01:22 UTC: STATE for resumption (context low)

Everything through 6f8740d is pushed and CI is green (book, Lean, zizmor). Artifact version 85
(https://claude.ai/artifact/CrW3rrJ8D7gUAk27y92LLm; this session published it, so a publish with
that url updates it). Page: 4.3 MB, ~9,400 points. Pending Ulrich's answers to
keep/ulrich-zk-question-2026-11-12.txt (sent on Signal, attributed to Claude): then drop or keep
the Zook-style rows and revisit the mask row's prover charge (now 2^-ell1 of the witness's
commitment, in the fold).

NEXT: the Flock-style-Boolean-over-Akita-binary-groups family ("bits over Akita's binary groups",
experimental). Facts gathered: LayerZero-Labs/akita#285 is the tracking issue; binary groups
(bits) open inside one ordinary grouped Akita opening on `dev`, feature `binary`; PR #229's
LaBinius root reduction and nested PCS are replaced and deleted (#421). Measurements: PR #428's
table (copied in work/akita-binary/binary-p64-root.md lines 197-210): 2^22 carriers (a carrier =
128 bits, so 2^29 bits) P128 binary-claim 82,764 B, commit 174 ms, prove 648 ms, verify 8.5 ms;
P64 79,236 B / 207 / 1,045 / 11.0; 2^23 carriers P128 84,590 B / 296 / 922 / 9.5 (so ~1.8 KB
per doubling of the witness); "plus-ordinary" shapes ~84 KB. CONDITIONS: scripts/binary-full-size.sh
builds with features parallel,binary-measurements,transcript-blake2b, so the times are
MULTI-THREADED on a shared M4 Max (load 7.7-13.9): assume ~10x for a single-thread equivalent
and say so. Security: the q24 SIS certificate and the full ledger are open; "no security claim"
(#312); P64 root grinding to 2^-128 per query. Specs saved: work/akita-binary/{binary-groups,
binary-checkpoint,binary-multigroup,binary-p64-root,binary-q24-certificate}.md; the per-stage
byte/atom tables are in specs/binary-opening.md on dev (298 KB; NOT fetched; path
`specs/binary-source-opening.md` no longer exists).

Pricing plan (state the assumptions on the page): family `bits_akita`, pq, pasta=False, no
rank (like flock), zk=False, hashes="any" (its merge hashes natively in a Boolean circuit at
8,192 AND gates per BLAKE3 compression under either policy), change="design", assumption
Module-SIS + random oracle, label "experimental: Akita dev branch, security ledger open".
- bytes: the measured opening extrapolated down from 2^22 carriers to the merge's witness
  (14-37M bits = 2^17-2^18 carriers) at 1.8 KB per doubling (82.8 KB - 4-5 x 1.8 = ~74-76 KB)
  + the instance (6 images x 128 B + claims), header 2.
- prover per merge: the merge's AND-gate witness x per-bit cost; per-bit cost = (commit + prove)
  single-thread-equivalent / 2^29 bits = (174 + 648) ms x ~10 / 2^29 = ~15 ns/bit = ~45
  word-mult equivalents per bit at 3e9/s (against ~18 for the FRI-Binius step). Flag the x10.
- merge (gates, in AND gates): Akita's merge in a Boolean circuit: the transcript's ~3 KB
  absorbed in BLAKE3 at 8,192 AND per 64 B (~45 compressions = 0.37M), the fold of 6 images x
  128 B in Z_q24 arithmetic (~0.1M), the sum-check verifier (120 atoms in E64/F_{2^128},
  ~0.4M) => ~1M AND gates, i.e. 25x smaller than the F2 family's ARC merge at rate 1/8 (25M).
  OUR ESTIMATE; say so.
- accumulation atoms: Akita's (~170).
- verify: measured 8.5 ms (P128) scaled to the merge's bits by the Akita slope (0.4 ms per
  doubling): ~7 ms => 2.1e7 word mults.
- transaction measure: BitZ's convention, 510 committed bits per Pasta gate in steps of 2^13.
Expected result: ~75 KB, merge prover ~4e7 (1M bits x 45), verify 7 ms: would dominate the F2
family on bytes and merge prover (169 KiB / 4.45e8) and lose on the verifier (0.3 ms). Present
with the caveats (parallelism, our merge estimate, open security ledger, no Pasta, no zk).

Then: the 150-bit re-plan (staged; work/akita-150-replan.sh; ~1 h on mains; expected
single-digit percent); the lookup option as a flagged design change (logUp emulated: hash gates
/5 over Pasta claims, -28% over Goldilocks; from keep/lookups-in-ragu.md); BitZ reruns on mains;
the recovery circuit per component in the bit arithmetization.

## 2026-11-12 03:30 UTC: the binary-groups family, the transaction's application, the bit arithmetizations

Six commits on main after 74362f3, unpushed: 9933707 (the 𝔽₂ decider absorbs its proof), c90fad1
(the transaction's application in each arithmetization), fad0db7 (the draft frontend's merge in
digits), f376237 (Flock-style circuits over Akita's binary groups), 7b1835d (the measure is called
decider work), 6f799fb (ranks to 24 for BitZ and 23 for the frontend). Each runs the model on its
own (git archive + run, work/verify/). The split was done by work/split-commits.py with per-line
pairing for the template's adjacent paragraphs (PAIR_BY_POSITION). Artifact republished.

- FAMILY `bits_akita` ("Flock/Binius-style over Akita's binary groups, lattice (experimental)",
  brown): P128 root measurements (82,764 B at 2^29 bits, commit 174 + prove 648 ms, verify 8.5 ms,
  parallel feature, loaded M4 Max; BINARY_MEASURED). Merge = Akita's fold in AND gates
  (bits_akita_merge_ands): transcript 2.7 KB by BLAKE3 at 8,192 AND (0.35M), the twelve images
  folded by adders at the page's challenge weight 20 (0.27M), 120 proof-field multiplications at
  `mult_ands(128) + reduce_ands(128)` = 16,366 + 768 (2.1M): 2.7M AND gates in all (the user asked
  whether Karatsuba or Toom-Cook help: `mult_ands` takes the cheapest of schoolbook, Karatsuba and
  Toom-Cook 3 at each width, free XOR, one AND per full adder; schoolbook 32,640 at 128 bits,
  Karatsuba 16,664, Toom-3 16,366, i.e. a few percent, not the 10-15% I first said). Bytes: the
  measured opening extrapolated to the merge's 2^21.3 bits at the planner's 563 B/doubling with the
  stage groups at fp128's growth (the measured pair's 1.8 KB/doubling is one difference between
  single runs, not a slope): 84,780 B. Prover: (commit + prove) × 10 for one thread / 2^29 = 46
  word mults per bit + Flock's PIOP 2.3 → 1.29e8 per merge (upper bound). Decider 5 ms. Pasta=False,
  floor 128 only, zk none, hashes="any", security ledger open. On the post-quantum frontier under
  BLAKE3. Under the recovery-circuit transaction it is 46 s (a Boolean circuit pays 120k AND gates
  per Pallas multiplication), so it is a row for Boolean applications.
- TRANSACTION MEASURE (the user: "Please try to compensate for" the Goldilocks rows' application
  being priced as native gates; then "the application gates measure is unclear. we need to
  estimate it for the recovery circuit and for a circuit with a given number of Merkle path
  checks (the latter should respect whether Poseidon is allowed)"): the knob is now an application
  (`#txapp`: the Ironwood recovery circuit, or 1/2/4/8/16/64 Merkle path checks of 33 nodes),
  costed in each arithmetization's unit under the hash policy (DATA.applications, from
  `recovery_cost`/`path_cost`), divided by the step's capacity `step_units` (2^(rank-2) gates of
  four coefficients for the field families, which the old G/2^rank formula undercounted 4×;
  2^rank bits/digits for BitZ and the frontend; 2^22 ANDs for the Boolean rows), rounded up (a
  transaction smaller than a step pays a whole step). Recovery circuit: Pasta 567,600 (Poseidon
  path) / 1,049,800 (BLAKE3) gates; Goldilocks 16.5M/17.0M (1,100 per emulated multiplication);
  fp128 10.7M/11.2M (700, the 2026-11-03 figure); Boolean 1.73G ANDs (14,500 × 2.5 × 47,824: the
  product plus a Montgomery reduction at 1.5 products; hashes 24,576 ANDs per BLAKE2b); BitZ 8.43M
  bits (510 per multiplication, 50,560 per BLAKE2b, one per wire bit); draft frontend 4.73M digits
  (255 per multiplication, no quotient). One path: 9,500 Pasta / 15,600 Goldilocks or fp128
  (Poseidon), 491,700 gates (BLAKE3), 270,336 ANDs, 497,376 bits/digits. The table is in
  keep/recovery-circuit-cost.md ("The bit arithmetizations"). Costing the recovery circuit
  component by component in the bit arithmetization, the open step of 2026-10-15, is thereby done.
- THE DRAFT FRONTEND'S MERGE IN DIGITS (the user: "make the recosting cover the merge circuit"):
  `frontend_merge_digits`: a bit gate one digit (BLAKE3 compression 15,072, image reductions one
  per bit, the projection's 3.1M-coefficient scan), a multiplication 255 (Poseidon 72 × 255 per
  atom, sum-check 400, claims 4 per circuit, the Booleanity sum-check's verifier 3,000); a step
  commits 2^rank digits; circuits at a fixed point, None where a claim's digits exceed the circuit
  (rank 13; rank 14 under Poseidon). BLAKE3 is now cheaper than Poseidon for this family's merge.
  Rank 17 BLAKE3 sumcheck: 81,718 B, 7.5e7, 2.1M digits, decider 7 ms; Poseidon 84,005 B, 1.5e8,
  4.4M. The 64-bit Pasta-claims variant's BLAKE3 merge prover is 150× larger (1.14e10 at rank 17)
  because every hash wire is a 255-bit value (four coefficients per gate, 8,064 word mults per
  bit gate against 26 here). BitZ's step witness is 2^rank bits (was 2^rank × 510).
- RESULTS, recovery circuit per note, one core: frontend 0.97 s at rank 17 → 0.14 s at rank 21
  (3 merges); BitZ with ARC 5.9 s at 17 → 0.30 s at 24 (one step); Pasta claims/64-bit Poseidon
  3.2 s at rank 17 (18 steps; its floor is the step commitment, 1.5 s, of which the seven
  BLAKE2b are two thirds) and 128 s with BLAKE3; Goldilocks Poseidon 26 s, BLAKE3 204 s; bits_akita
  46 s; 𝔽₂ ARC 72 s; Pedersen rank 14 243 s (139 steps × 1.7 s merges). The user: "we clearly have
  a problem: proving the recovery circuit is *very* expensive, especially considering that it's
  per recovered note"; then, on the single-core figures and the rank extension, "we have a clear
  winner" (the draft frontend). Caveats recorded in the chat reply of 03:30: no zk modelled for
  the frontend (its rows drop out under the zk toggle; the projection form reveals coordinates,
  the sum-check form could take Akita's mask), the Booleanity draft is provisional with
  conditional certificates, the decoupled commitment modulus has no soundness argument yet, the
  figures are our component counts (BitZ's PCS is measured, the frontend's is not), and Quang
  thinks the frontend's prover is overestimated (which would widen the win). Levers for the field
  arithmetizations: lookups (hash gates /5), Poseidon in the path (1.8×), batching notes under one
  key (≤ 2×: 45% of the gates are per key).
- SMALLER: the 𝔽₂ decider now absorbs its proof bytes (1,200-3,700 compressions; 0.2-0.5 ms; the
  FRI-Binius paper: under a millisecond at 2^28 bits, 0.35 MiB); "verifier work" → "decider
  work" everywhere; the BitZ ranks under the transaction measure stay on the frontier because
  the merge count falls with rank while the proof grows slightly (the user asked why they do not
  collapse). work/pup/tx-probe.mjs selects the transaction measure and dumps the table.
- PENDING: zero-knowledge rows for the draft frontend (Akita's mask on the rows term plus a zk
  Booleanity sum-check; the user will want them, since Ironwood transactions are private);
  Ulrich's answers (Zook rows); the 150-bit re-plan; BitZ reruns on mains; the notes' older
  items. The nine root TSVs are still untracked.

## 2026-11-12 03:40 UTC: zero-knowledge rows for the draft frontend; four recovery inputs

The user pushed everything through c604d95. Then f629ddd (zk rows) and 2a01e16 (the option),
unpushed, each verified from git archive; artifact v87.

- ZK ROWS (`bits_q64`, sum-check form only; the projection form reveals coordinates and has
  none): Akita's mask as the lattice rows have it. The per-digit price at the masked rank (23.7
  → 45.3 word mults, ×1.9) on every step; 18 more atoms in the zk-layer merge, hashed in digits
  (+136k under BLAKE3, +330k under Poseidon); the fold = MASK_ATTEMPTS × K × 2^rank digits ×
  (masked per-digit + 900 for Karney sampling) + the fold's own merge; opening and decider
  unchanged. The accumulator is K × 2^rank digits, one per committed bit (the lattice rows'
  mask_fold has 85 per coefficient), so the fold grows with the rank where the merges shrink.
  Recovery circuit per note, one core, BLAKE3: rank 17 2.41 s, 18 2.31 s (the minimum; the
  fold 4.2e9 is 1.4 s of it), 19 3.3 s, 21 11.2 s, 23 43.7 s; without zk 0.97 → 0.14 s at 21.
  Poseidon: 3.08 s at rank 18. Akita with Pasta claims, zk: 44.7 s at rank 13 (fold 1.1e10),
  63.7 s at 17 (fold 1.7e11). So zero knowledge costs the frontend 16× at its optimum, nearly
  all of it the mask's sampling at 300 ns a sample (900 word mults); the levers are a faster
  Gaussian sampler, fewer attempts (α) and a smaller zk-layer accumulator; §5.8 moves the work
  off the device but not away.
- THE OPTION `recovery:4`, "a transaction with 4 Ironwood recovery inputs" (the user: "4
  Ironwood recovery inputs in a single tx, so only one zk step"): the page's formula already
  added the fold once per transaction whatever it proves, since the masked accumulator is the
  step's size; the text says so now. Four inputs on the frontend: without zk 0.47 s at rank 21;
  with zk 4.9 s at rank 18 or 19 (the fold amortises: 2.3 s for one input); Pasta claims zk 73
  s at rank 15; BitZ without zk 0.91 s at rank 24.
- The user's reading: "it's interesting that we actually need the faster prover of the
  post-quantum schemes to make it fast enough to prove the recovery circuit": Pedersen-Ragu at
  rank 14 is 243 s per note in the model (139 merges of about fifty 2^14 commitments; the
  Pippenger price of 6,400 per coefficient is on the pessimistic side, a 2^14 Pasta MSM being
  nearer 1,000 to 2,000 in practice, so one to four minutes), against 0.14 s on the frontend;
  the enabling ingredient is the bit arithmetization (a hash bit as one committed bit, 26 word
  mults, against four field elements), which BitZ also has at 0.30 s; the lattice adds the
  tiny merge and the small proof.

## 2026-11-12 04:06 UTC: BitZ's zero-knowledge rows; the hash option adds rows

Pushed through e0d9202 by the user. Then d514dc9 (BitZ zk rows) and 6972628 (the hash option adds rows), unpushed;
artifact v89.

- BITZ ZK ROWS (the user: the hash-based BitZ options dropped out under zk; "yes please"):
  derived, since the paper offers succinctness only. Ligero's random row per Ligerito level
  (one symbol of 16 B in every opened column: 491 columns × floor/100 × (1 + the ARC decider's
  extra trees) → about 20 KB under ARC at 128 bits, nothing under recursion) and a Libra-style
  mask polynomial per sum-check (zero-check, lincheck, Zinc+'s PIOP, and each GKR layer: 4 ×
  (3 log N + log N (log N + 1)/2) elements, 1,600 at 2^25 bits) committed as extra rows of the
  same Ligerito matrix and opened with the witness; the masks' share of the witness goes to the
  fold (2-3e6 word mults, under a percent). Zook-style spot-checked oracles were considered and
  rejected: with ~325 GKR rounds they would cost ~100 KB (masks × 16 spot checks × 16 B). So
  the zk BitZ row stays at 0.30 s per recovery note at rank 24 with 20 KB more proof. ARC's zk
  preservation unexamined, as for the other hash-based rows. `bitz_point(..., zk)`,
  BITZ_ZK_ELEM, BITZ_ZK_SUMCHECKS, bitz_zk_queries, bitz_mask_elements.
- THE HASH OPTION (the user: "saying 'Poseidon allowed' should just add extra points for the
  Poseidon options, unless they are dominated"): the page's filter now keeps the BLAKE3-priced
  rows always and adds the Poseidon-priced ones under the option (`p.hashes === 'any' ||
  p.hashes === 'blake3' || hashes === 'poseidon'`); the transaction's application is hashed
  under the row's own policy (`p.hashes`), the "any" rows under the selected one; the model's
  frontier printout follows. The within-family pruning still keys on `hashes`, so a BLAKE3 row
  dominated by its Poseidon twin stays (it is selectable alone).

## 2026-11-12 04:40 UTC: the 150-bit re-plan is blocked on the compression maps

work/akita-150-replan.sh ran on mains (log work/akita-150-replan.log; outputs
work/akita-150-out/replan/): every planner step failed at once, for two reasons.
1. `--catalog-report` needs `--check-catalog` or `--catalog-baseline`; the 128-bit script never
   used it. Drop it, or add `--check-catalog`; the rank growth can also be read from the
   catalog snapshots and the reprice TSVs.
2. The real one: "no compression SIS rank for profile=Q128OffsetA7F7 d=16 width=4096", for every
   fp128 family and every group run (fp64 families would hit the Q64 cells the same way).
   Akita's compression maps are rank one by construction: crates/akita-params/src/compression.rs
   rejects any other rank ("compression map must be rank one"), sis/compression.rs's
   `min_compression_secure_rank` returns 1 only when the width fits the cell's rank-one maximum,
   and compression/chain.rs always builds rank 1. The six rank-one cells re-sized at 150 bits
   give Q128 at d=16 a maximum width of 3,806 (7,077 at 128 bits; generated_sis_table/q128.rs,
   row (16, 1): [3806, 214722, 4083861, ...] by rank), and the chain's first map at d=16 has
   width 4,096 (512 coefficients × 128 bits / 16). So at 150 bits the rank-one compression maps
   do NOT hold at the catalog's geometry, which the page assumes ("the rank-one compression
   maps, which reach 147 bits, are assumed to hold"). Fixing it is a design change to Akita,
   the user's call: (A) allow rank-2 maps (rank 2 covers width 214,722 at d=16): take the
   secure rank from the table's ladder in CompressionMapPlan::new, pass it through chain.rs,
   and let output_coefficients = rank × d flow into the planner's bytes (the tests that pin
   "exactly the six rank-one cells" and the rank-one assertions would change); or (B) split the
   first map's input into two rank-one maps of width 2,048 with the same total output. Either
   doubles the compressed images at that level, so the 150-bit page figures would move by more
   than the single-digit percent expected. Not started; the worktree is as it was.

## 2026-11-14 02:40 UTC: the floor is 147 bits and re-planned; Ulrich's answer; the slopes

Three commits on main after 068f61b, unpushed: 02d519d (Ulrich's mask correction), 56b31d3
(the opening slope over ten doublings), 0ba0035 (the 147-bit floor, re-planned). Separate by
the user's request. Artifact to republish.

- THE USER'S DECISION on the compression maps: neither rank 2 nor the split; "change 150 bits
  to 147 bits", the most the rank-one maps allow (the d=16 map at width 4,096 certifies at
  147.34 bits with the proven-pruned profile; 150.255+ at widths 3,806 and 2,048 and for rank 2
  at 4,096; the d=8 map at width 256 above target and 128.0 at 512; 128.26 at 7,077). The
  certified figures come from `sis_estimator_once --profile proven-pruned` in the worktree.
  Rank 2 and splitting are equal in bytes (both double the images at both levels, since the
  second map's input doubles too) and splitting halves the maps' arithmetic; recorded for later.
- THE PIPELINE work/akita-147-pipeline.sh (run under `caffeinate -i`): commits the 150-bit
  state in the worktree (branch pasta-widths-150, 81a489e), branches pasta-widths-147, renames
  Quantum150BitADPS16 → Quantum147BitADPS16 everywhere (the generated tables' module names it
  too, which the first run missed), sets minimum_log2_rop and the Euclidean target to 147,
  regenerates the runtime tables (the certified infinity table took 11,164 s, three hours, not
  the hour of 2026-10-15), re-sizes the six compression cells from the "(d, 1)" rows (q128 d=8
  302, d=16 4,138; q64 d=16 151, d=32 2,069; q32 d=32 75, d=64 1,034), rebuilds, commits
  (2478c43), and runs the re-plan without `--catalog-report` (work/akita-147-replan.sh,
  outputs work/akita-147-out/replan/, 21 minutes, every step ok). Resumable with
  SKIP_TABLES=1. The commit inside the background script waited an hour on a permission
  prompt, which the log cannot show.
- PAGE INPUTS: `python work/akita-150-page-inputs.py work/akita-147-out/replan` gives AKITA_147
  (fp128 72,443 at K=0 .. 82,521 at K=12; goldilocks 65,669 .. 69,810, planned in the fp64
  geometry; pasta_q64 77,227 .. 86,697; pasta_sis 91,755 .. 104,425; pasta 110,106 ..
  139,881). The base and q64 runs selected the same schedule at K=0 (the q64 pricing override
  was applied; see replan-q64.log). RANK GROWTH by work/rank-scale.py (the production rust
  tables for each instance's own profile; the Goldilocks CSV tables for the 64-bit mapping,
  since the production q64 table lacks the other profiles' cells; the 147 Goldilocks CSV took
  79 minutes): own 121 → 150, 1.240, 29 move; q64 185 → 211, 1.141, 26 move; the method
  reproduces the recorded 150-bit 1.273 and 1.162 exactly. Pallas: 1.01 carried from 150 (its
  147 table would take an hour). WHIR_SCALE 1.16 and the verifier-hash factor 1.13 at 147 are
  interpolated from the 150-bit measurements (1.18, 1.15).
- MODEL: AKITA and SLOPE are keyed by floor; `akita_bytes(variant, K, log_len, floor)`; at 147
  the opening is the plan (no rank_factor_share on bytes; it stays on verify); FLOORS = (128,
  147); RANK_SCALE_147 = {fp128 1.24, goldilocks 1.14, pasta_q64 1.14, pasta_sis 1.01, pasta
  1.01}. Results at rank 17 under BLAKE3: Goldilocks 76,133 B (70,145 at 128), fp128 85,538
  (75,076), pasta_q64 95,352 (87,654), pasta_sis 112,430, pasta 146,830; the frontend 87,102
  (81,054). The page: radio "147 quantum bits (the most Akita's rank-one compression maps
  allow; the catalog re-planned)", the Security floor paragraph, the margin paragraph, the
  zk and binary-groups mentions; pasta-proof-size.md §9's margin paragraph rewritten with the
  history (150 tried, blocked by the maps, 147 planned).
- THE SLOPES (56b31d3): the page's per-doubling opening slope was the 2^14 → 2^16 rows
  (steepest; fp128's 563 was even half of that pair's 1,126). Now the 2^14 → 2^24 rows at
  both floors: 128: fp128 592, goldilocks 555 (scaled), pasta_q64 953, pasta_sis 1,112,
  pasta 1,371; 147: 584, 662 (2^14 → 2^26), 1,104, 1,118, 1,175. Rows with many circuits
  lose a few KB (pasta_q64 rank 17 BLAKE3 94 → 88 KB; the frontend 82 → 81, 84 → 83; the
  Hashes paragraph's per-claim growth 3 to 4 KB / 9 to 12 KB).
- ULRICH'S ANSWER (02d519d; keep/ulrich-zk-answer-2026-11-12.txt; his commit 1187ef3c
  "corrected zk mask size", saved as work/ulrich-scripts/frib_optimizer-1187ef3c.sage): the
  mask must be as large as the witness (double rows in the first round; one row was a slip),
  the full-entropy mask lets later rounds run non-zk, the leaf blinders could be dropped but
  stay for a clean analysis, and only the private witness needs masking, not public
  polynomials. Port: `rows = 2 if zk`, `blinder = HASH_BYTES`, leaf = rows × 2^ell × unit +
  blinder; `mask_share = 1`. 𝔽₂ ARC mask rows: +40/+27/+20/+17/+14 KiB at rates 1/4..1/64 with
  fold 0.50–0.93× a step (were +19..+6 KiB, 0.07–0.13×); Zook rows +35..+27 KiB, fold ≈ 0.01×,
  kept as the derived lower estimate ("ways to be more stingy ... zk-ify also the sumcheck
  rounds"). The ARC decider masking all three first-round oracles is an upper bound by his
  "only the private witness" remark; said on the page.
- PENDING: the Pallas factor at 147 (an hour's table) if wanted; BitZ reruns on mains; the
  zk-fold levers for the frontend; the 128-bit slopes' effect on older notes' figures (notes
  keep history).

## 2026-11-14 13:24 UTC: Ragu upstream at 8109a41c; the online polynomials; the TSVs; BitZ scripts

- The nine root TSVs (older copies of estimates/) moved to work/.
- RAGU UPSTREAM (the checkout's main fast-forwarded 526b0e3e → 8109a41c, 2026-11-13; 268 commits;
  udon unchanged at zakura-udon 0.1.0). Our uncommitted `encoded_len` was superseded by upstream's
  wire format (PR #875: `crates/ragu_pcd/src/wire/`, a 28-byte versioned envelope,
  `CompressedProof::encoded_len::<R, HEADER_SIZE>()`, fuse fixtures pinning payload bytes) and
  dropped; the user keeps branch `encoded-len-probe` (1e75f342 over 8109a41c) with a test that
  prints the sizes (`cargo test -p ragu_pcd --lib probe_sizes_for_the_study -- --nocapture`; the
  crate is no_std, so `std::println!`). MEASURED: compressed r13 h4 7,936 B (7,908 payload), r13
  h2 7,808, r14 h4 8,064, r14 h2 7,936; uncompressed Proof r13 h4 26,480,800 B; Standard profile
  50 native + 45 nested components; Derived 5, OPENED 4, NUM_ONLINE_POLYNOMIALS 2. The +448 B over
  7,460 is exactly the ONLINE POLYNOMIALS (PRs #944, #961 "polynomial oracles"): two unblinded
  polynomial slots per proof, six (point, value) openings per step at ζ (left, right, output
  slots), one opening each, Schwartz–Zippel identities between committed polynomials without
  coefficients in the circuit; Tachyon (research/tachyon at 73031f7, 2026-11-13) uses them for
  tachygram set polynomials (relations/enforce.rs: poly_equal, poly_product, poly_roots). This
  is the commit-then-challenge mechanism keep/lookups-in-ragu.md assumed. Model: ragu-size-model.py
  gained ONLINE_POLYS = 2 and the `online` term (7,908 at CHECKED_IN; minima 6,436 at rank 14
  packed, 6,148 at rank 15; the 1,120 B and 288 B endoscaling savings unchanged); prose updated in
  pareto-model.py, pareto-template.html (Proof bytes bullet), pasta-proof-size.md §8 and §8.1.
  STILL STALE: the circuit-budget constants (NATIVE_FIXED, NESTED_FIXED, STEP_*): upstream's
  internal/tests.rs pins them now: native Hashes1 1793, Hashes2 1874, Collapse 1455 (the two
  collapses merged), ComputeV 1948, BindChallenges 2032–2048 (FOUR binders), BindBeta 1889,
  BindEndoscalar 940, EndoscalingStep 1995; nested EndoscalingStep 2016, Collapse 1598 (Export
  merged in), ComputeV 1504, Loading 566; stage sizes: native OuterError 186 → 20, InnerError
  399 → 42 (quotient folding, PR #921), PointsWalk 89 → 144; nested inner_error 254 → 37,
  outer_error 73 → 11. ProductionRank still R<13>, 4 endoscalings per step; R<14> added
  2026-10-28 for the extension profiles (the user and Tal found 14 optimal). Refreshing the
  constants is an hour and a separate commit; it moves the Pedersen rows' feasibility at ranks
  14–16 by a few percent.
- THE ACCUMULATION-PROOF PROXY (the user asked): the page prices a fold from first principles
  (SUMCHECK_ATOMS 120 + K images + claims), not from the 4.4 KB level figure, which is a
  cross-check within ~20%; the real uncertainty (whether Ragu's step under Akita needs exactly a
  level's two norm sum-checks and images) is within ×1.5 on ~5 KB: ±2.5 KB per edge, ±25% on the
  Akita rows' atoms and BLAKE3 merge gates; decider bytes and prover unaffected.
- SPIKE OF BITZ OVER AKITA (the user asked): two stages, a Python toy (Booleanity sum-check,
  projection norm bound, one Pasta claim; 2–3 days) then Akita's binary groups on `dev` with GKR
  replaced by the Booleanity check (1–3 weeks; risk: the claim machinery for a custom prime).
- BITZ RERUNS: work/bitz-rerun.sh (per profile; `build` was a no-op, the binary already has the
  native flag and `parallel`) and work/bitz-summary.py; outputs bitz-out/rerun/. Not yet run.

## 2026-11-14 14:45 UTC: header 9, the spike, Ragu against Halo 2 measured, BitZ reruns

Commits on main after 5747218: aed6141 (Pedersen header 9, Tachyon's HEADER_SIZE; 8,228 B at rank
13; artifact v91), 5411a14 (spike/: the Python spike of the Booleanity-by-projection frontend,
tracked at the user's request; README.md maps it to the page's bits_q64 row). All pushed? No: the
user pushes.

- RAGU AGAINST HALO 2, MEASURED ON THIS M4 MAX (16 cores, mains). Ragu 8109a41c, zakura-udon 0.1.0,
  `cargo bench -p ragu_pcd --features multicore --bench criterion_fuse` (the nontrivial Merge2 step
  at the production rank; logs ragu/work/bench-fuse*.log): one worker 1.45 s (1.46 on rustc
  1.100.0), 16 workers 0.65 s (0.63–0.70); the accelerated backend equals the reference one. So
  the page's 1.81 s per Pedersen step (pedersen_per_coefficient 6,905 at rank 13) is 24% high, not
  the 3–6× the notes once guessed; a calibration would be ~5,630 word mults per coefficient (NOT
  applied yet). Ragu's capacity chapter's 0.2 s per fuse was another machine. Orchard
  (research/orchard at be4f6594 = 0.15.5, halo2_proofs 0.3.5, halo2_gadgets 0.5.0, pasta_curves
  0.5.2 glv; and crates.io 0.16.0 with halo2_proofs 0.4.1, halo2_gadgets 0.6.0, pasta_curves
  0.6.1), its benches/circuit.rs proving group with the recipients widened to 1, 2, 4, 8, 16 in
  scratch projects orchard/work/bench-0.15 and bench-0.16 (the checkout untouched; 0.16's own bench
  copied from the registry for its rand 0.10 `UnwrapErr<SysRng>`; rustc 1.100.0 via
  RUSTUP_TOOLCHAIN=stable since aes 0.9.4 needs 1.89 and the checkout pins 1.88; logs bench-*.log
  there). Seconds per bundle (a 1-recipient bundle is padded to 2 actions):

  | actions | 0.15.5 all cores | 0.16.0 all cores | 0.15.5 one thread | 0.16.0 one thread |
  |---|---|---|---|---|
  | 2 | 0.48 | 0.46 | 3.05 | 2.77 |
  | 4 | 0.89 | 0.83 | 5.77 | 4.89 |
  | 8 | 1.68 | 1.60 | | |
  | 16 | 3.31 | 3.15 | | |

  The compiler (1.88 vs 1.100) made no difference to 0.15.5. TACHYON'S STEPS per transaction
  (stamp.rs `Stamp::prove`): a spend is SpendBind + SpendAction (two fuses, plus an ActionLift per
  anchor span when the spendable lags the plan's anchor); an output is OutputBind (a seed) +
  OutputAction (a fuse); ActionMerge per action beyond the first; FeeFuse; a rerandomize (counted
  as a fuse; its cost unmeasured). The capacity chapter puts a seed at 1.75 fuses. On this machine:
  1 spend + 1 output 11 s one thread / 5.0 s all cores (6 fuses + 1 seed); 2 + 2: 21 / 9.4 s;
  8 + 8: 79 / 35 s (41 fuses + 8 seeds). Against Halo 2's 3.0 / 0.48 s (2 actions) and 22 / 3.4 s
  (16, the one-thread figure extrapolated at 1.4 s per action): 3.5–7× on one thread, 10–20× on
  all cores, because the fuse parallelizes 2.2× on 16 cores against Halo 2's 6.3× (the user: scope
  for optimization; also proving the tree's independent leaves concurrently, which Stamp::prove
  does not). Not counted on either side: Tachyon's per-note background proofs (NoteSeed/
  NullifierDerive, SpendableInit/UnspentFuse per epoch, AnchorSpan) and Ragu compression (left to
  aggregation). Phones, by Geekbench-6 single-core ratios (8 Gen 3 ≈ 1.8× slower, A54's Exynos
  1380 ≈ 4×) and multi-core gains of 1.5–2 for Ragu and ~3 for Halo 2: 1+1 actions A54 25–45 s
  Ragu vs 4–12 s Halo 2, 8 Gen 3 11–20 vs 2–5.5 s; 8+8 actions A54 3–5 min vs 0.5–1.5 min, 8 Gen 3
  1.3–2.4 min vs 13–40 s. Extrapolations, not measurements. The user's concern (a regression over
  Orchard/Ironwood proving) is confirmed by the model and the measurements; whether the Tachyon
  project has compared against Orchard is not visible in its repositories. IDEAS: calibrate the
  Pedersen step to the measured fuse; add "Tachyon transaction" application options (1+1 and 8+8
  actions in Tachyon's own step shapes) beside the Merkle paths.
- BITZ RERUNS DONE (work/bitz-rerun.sh, bitz-out/rerun/{results,summary}.txt; mains; the build was a
  no-op, the binary already had the native flag and `parallel`): the three profiles at 2^25..2^28,
  threads 1 and 10, 5 reps, plus the 2^27 rate-1/8 cell at 10 reps. Everything within 3–5% of the
  2026-10-15 overnight run (slightly faster): e.g. udrg:3:4:128 at 2^27 one thread prove 469–471 ms
  (487), Ligerito 122–123 ms (133); 2^28 806 ms (840). The 2^27 rate-1/8 Ligerito rise (33 → 122 ms
  from 2^26) is real and stable. No model change; the 2026-10-15 TO DO is closed.
- PENDING: calibrate the Pedersen step cost; Tachyon transaction applications on the page; refresh
  the circuit-budget constants from ragu's internal/tests.rs table; the zk-fold levers for the
  frontend; the Pallas rank factor at 147 if wanted.

2026-11-14 14:59 UTC, addendum: with assembly. Neither benchmark above used assembly: pasta_curves 0.6.1 has an `asm` feature (AArch64 and
x86_64 backends; the user's ARMv7E-M work is separate) that orchard does not enable, and
zakura-udon 0.1.0 has `aarch64-asm`, which ragu's workspace does not enable (features traits,
poseidon only). Rebuilt with them on rustc 1.100.0: Orchard 0.16.0 (bench-0.16 with
`pasta_curves = { version = "0.6.1", features = ["asm"] }`): all cores 0.34 / 0.35 / 0.62 / 1.16 /
2.35 s at 1 / 2 / 4 / 8 / 16 actions (was 0.47 / 0.46 / 0.83 / 1.60 / 3.15), one thread 1.83 /
1.88 / 3.75 s at 1 / 2 / 4 (was 2.55 / 2.77 / 4.89): 24–32% faster. Ragu fuse with
`--features multicore,udon/aarch64-asm`: one worker 1.27 s (was 1.46), 16 workers 0.59 s (was
0.63–0.70): 8–13% faster; the accelerated backend still equals the reference. So with assembly on
both sides a Tachyon 1+1-action transaction is 9.8 s one thread / 4.6 s all cores against Halo 2's
1.88 / 0.35 s for two actions (5.2× / 13×), and 8+8 actions 70 / 33 s against 16 actions' ~14
(extrapolated at 0.93 s per action) / 2.35 s (5× / 14×). Logs: orchard/work/bench-0.16/bench-*-asm.log,
ragu/work/bench-fuse-asm.log.

## 2026-11-14 16:08 UTC: Tachyon statements written; Tachyon runs Ragu's MOCK; gate-count probe blocked

- THE STATEMENTS (the user: "write the circuit in the same style it is written in the protocol
  spec and ZIP 2005 ... the high-level statement, with algorithms spelled out"):
  keep/tachyon-statements.md, from tachyon 73031f7's stamp/proof/{output,spend,stamp}.rs,
  digest/poseidon.rs, gadgets/, keys/, value.rs, primitives/sets.rs, relations/enforce.rs:
  Notation (tagged Poseidon sponge, generators, fixed-base scalar forms, amounts, value
  commitments, notes and keys, epochs and nullifier groups, actions, set polynomials and their
  Pedersen commitments on Vesta, bridge hash, headers), then Output Bind, Output Action, Spend
  Bind, Spend Action, Action Merge, Fee Fuse statements with named conditions, what a stamp
  proof states and what Proof::verify checks natively, and a cost table from the step comments.
  Rendered dark with pandoc + MathJax to work/tachyon-statements.html (work/dark.css inlined);
  the user viewed it in Firefox. Not tracked; the user may want it tracked.
- POSEIDON (the user asked whether the tree uses Poseidon 1.1 and what the circuit commitments
  are): all in-circuit hashing is zakura-udon's Poseidon over Fp, width 5, rate 4, x^5, 8 full +
  56 partial rounds, constants from hadeshash via the daira/pasta-hadeshash fork (same
  generation as Orchard's, width 5 not 3; udon does not say "1.1"); tagged sponge, capacity =
  16-byte domain as an LE integer, no padding (ragu_primitives Sponge). No Merkle path per
  spend: membership via the spendable lineage and set polynomials; the evidence tree is a
  Poseidon 4-ary tree over sealed QR buckets. Commitments: cv = [v]V + [rcv]R with Orchard's
  z.cash:Orchard-cv generators ([-v] for outputs), rk = ak + [alpha]G (Orchard's G), fee
  commitment with a derived trapdoor; sets = prod (X - m) committed as Pedersen vector
  commitments under Ragu's host generators (Vesta), carried as the two online polynomials;
  BridgeHash(C) = [x(C)]G_x + [y(C)]G_y (nested generators of the bridge stage).
- TACHYON RUNS RAGU'S MOCK. crates/tachyon/Cargo.toml depends on the `ragu` facade crate (git
  rev a1395401) with features ["mock"] (dev: + "test-utils"); the facade's `mock` feature
  re-exports src/mock/ (1,675 lines), "an API-level mock of ragu_pcd ... so downstream
  consumers can integrate against it ahead of the real implementation". Its Application::fuse
  commits the online polynomials with real Pedersen generators and checks them, derives zeta by
  BLAKE2b over the step index, the children's header hashes, the commitments and the staged
  values, runs the step's `witness` with a `Simulator` driver (gadget execution, no circuit
  synthesis), and makes a "proof" of BLAKE2b hashes (proof.rs). So: Tachyon's steps implement
  the MOCK's `Step` trait; no real Ragu proof is produced anywhere in Tachyon today; the Ragu
  fuse benchmark and the step counts from Stamp::prove are a projection of what Tachyon will
  cost once ported to ragu_pcd, with the same step shapes (the mock mirrors the API: seed/fuse,
  headers, two online polynomials, staging, bridge hash). The 2,048-gate budget is not checked
  by the mock except for the stage. The Ragu capacity chapter's "0.2 s per fuse" and the user's
  question whether the project has compared with Orchard: the project could not have measured
  transaction proving on Tachyon itself yet.
- GATE-COUNT PROBE (the user: "measure the gate counts"), BLOCKED by the above. Built:
  worktree ~/olddaira/research/ragu-tachyon-pin (branch tachyon-pin-probe at a1395401, the rev
  Tachyon pins) with `pub fn step_synthesis_counts<C, S: Step<C>, R, const HEADER_SIZE>(step,
  stage_size) -> Result<(gates, constraints)>` appended to crates/ragu_pcd/src/lib.rs
  (uncommitted; uses step::internal::adapter::Adapter::with_stage and
  ragu_circuits::testing::synthesis_counts, which needs ragu_circuits' `test-utils` feature);
  probe crate tachyon/work/gates (Cargo.toml: zcash_tachyon by path, ragu_pcd/core/circuits
  by the same git rev, [patch."https://github.com/tachyon-zcash/ragu"] mapping all eight ragu
  crates to the worktree; src/main.rs lists the 39 registered steps, stage size 5, header 9).
  It fails to compile because Tachyon's steps implement ragu's mock `Step<Pasta>`, not
  ragu_pcd::step::Step. Ways forward: (a) a wrapper implementing ragu_pcd's Step for a mock
  Step, delegating witness/staged/polynomials (the Oracles types differ: the mock's
  step/oracles.rs vs ragu_pcd's step/oracles.rs; both expose zeta/query/staged/bridge_hash, so
  a thin adapter may work); (b) a counting Simulator-like driver inside the mock (count mul
  gates and linear constraints as the Simulator executes `witness`) — simplest and faithful to
  what the real Adapter would synthesize, since gadgets are the same; (c) ask the Tachyon team.
  Not pursued further (context low).
- STATE: pqzcash main has 7 commits after 539ccca unpushed (through 0896b50); the artifact is
  v91; the Ragu checkout is clean on main 8109a41c with branch encoded-len-probe (1e75f342) and
  the worktree above; the Orchard checkout is clean with scratch projects under work/; Tachyon
  is clean on main 73031f7 with work/gates. PENDING: calibrate the Pedersen step to the measured
  fuse (1.46 s one core; pedersen_per_coefficient ~5,630); Tachyon-transaction application
  options on the page; refresh the circuit-budget constants from ragu's internal/tests.rs; the
  gate-count probe via (b); the zk-fold levers; the Pallas factor at 147.

## 2026-11-14 17:28 UTC: gate counts measured through the mock; the Pedersen step calibrated; Tachyon transactions on the page

- GATE COUNTS (the user: "measure the gate counts") DONE, through a counting adapter added to
  Ragu's mock in the worktree ~/olddaira/research/ragu-tachyon-pin (branch tachyon-pin-probe over
  a1395401, the rev Tachyon pins): ff0e4eba adds ragu_pcd's own check, the adapter's counts for
  its test step (11 gates, 28 constraints: SYSTEM gate, zeta and bridge hash, the step's packed
  pair, one query and five openings at zeta; 27 instance elements and ONE); 8ad598ed adds
  `ragu::counting::step_synthesis_counts` (feature `test-utils`, which now also enables
  ragu_circuits/test-utils): a `Circuit` that mirrors ragu_pcd's adapter over the mock's types
  (stage block, staged values bound by equalities, the mock Oracles, the step's `witness`, the
  unqueried slots opened at zeta by a new `Oracles::finish`, the instance of zeta, twelve
  opening elements, bridge hash and three padded headers) run through ragu_circuits' Counter;
  its test gets the same 11/28 for the same step, so the two adapters agree. The probe crate is
  tachyon/work/gates (ragu by git rev with features mock,test-utils, every ragu crate patched to
  the worktree; `cargo run`; run.log). The earlier ragu_pcd-side helper was dropped.
  BUDGET at rank 13: 2,048 gates (n = 2^(rank-2)) and 8,191 constraints; Tachyon's HEADER_SIZE
  9, stage 5. ALL 39 STEPS FIT, and all compile under the Empty counting driver, so they are
  written against the driver abstraction as the real Ragu needs. Gates/constraints: FeeFuse
  1934/3910 (94% of the budget), SpendAction 1649/3329, FeeSeed 1639/3316, SpendBind 1630/3270,
  OutputBind 1467/2948, NullifierDerive 1378/2767, OutputAction 1351/2739, EvidenceTreeDescend
  1226/2432, EvidenceTreeLeafPair 1221/2433, NoteSeed 987/1984, QrBucketSeal 656/1321,
  EvidenceTreeOpen 616/1238, UnspentLift 454/878, QrUnspentInit 409/792, SpendableInit 366/743,
  EvidenceTreeFuse 353/705, SummaryAdvance 326/665, EvidenceTreeCap 326/660, QrStampIntakeSeed
  325/663, AnchorSpanSeed 325/665, SummarySeed 324/663, QrSpendableInit 126/253, UnspentFuse
  102/212, UnspentBind 101/210, NullifierFuse 100/212, SpendableLift 81/169, QrSideDescend 81/160,
  QrIntakeMerge 66/133, EvidenceTreePairFuse 63/129, QrSideSelect 42/86, QrIntakeSplit 41/89,
  QrSummaryIntake 37/85, QrEmptyIntakeSeed 36/85, StampMerge 21/50, StampUnmerge 21/50,
  StampLift 19/48, AnchorSpanFuse 18/47, ActionMerge 17/50, ActionLift 17/48. The adapter's
  share at stage 5 and header 9 is about 13 gates and 43 constraints.
- CALIBRATION (commit ba52493): pedersen_per_coefficient is now the measured fuse, 1.46 s x
  3e9 / (96 commitments x 2^13) x 13/rank, about 5,570 at rank 13 (was 6,905, +24%); an
  assertion holds the checked-in row's step and merge to 1.46 s; the knob text, the
  Transaction paragraph and pasta-proof-size.md's prover table say so. Pedersen for the
  recovery circuit: 406 s in 278 steps at the checked-in configuration, 151 s at rank 17 with
  70 endoscalings. The paragraph's Goldilocks (17 s) and zero-knowledge Pasta-claims (29 s at
  rank 15) figures no longer matched the model and were corrected: the prose figures are hand
  maintained; a table generated from the model would stop the drift (TO DO).
- TACHYON TRANSACTIONS (commits 3956b76 and c5807b6; artifact v93): txapp options tachyon2, 4,
  8, 16 (half spends, half outputs; placed before the Merkle paths at the user's request).
  APPLICATIONS["tachyonN"] is a per-node list in each arithmetization and policy: nodes
  SpendBind + SpendAction per spend, OutputBind + OutputAction per output, ActionMerge per
  action after the first, FeeFuse, Rerandomize (20 gates, the adapter's); the page sums
  ceil(node / step_units) over the nodes. A node costs perms x hash(policy) + windows x (2 in
  Ragu's Pasta gates, 4 bit monomials elsewhere) + the rest x mult(arith), the rest taken as
  Pallas multiplications (an overstatement where a gate checks a bit). Figures at floor 128 on
  one core: 2 tachyactions, 7 nodes: Pedersen checked-in 10.2 s (7 fuses), Akita Pasta claims
  64-bit 0.54 s (rank 13), BitZ 0.70 s (rank 20), frontend 0.20 s (rank 19, BLAKE3), Goldilocks
  5.2 s in 153 steps, F2 20 s in 130 steps; zk: Pasta claims 3.7 s, frontend 1.4 s, BitZ
  unchanged. 16 tachyactions, 49 nodes: 71.5 / 3.8 / 4.9 / 1.4 / 35 s. The range of step counts
  is the emulation of Pallas arithmetic: 27-36 Goldilocks steps of rank 17 or 23-30 Boolean
  steps per node. HEADER RULE (c5807b6, the user's point): a Tachyon application needs header
  9, so the page then shows the Pedersen rows at header 9 only and adds 7 x 64 bytes to the
  post-quantum rows (every family prices a header element at 2 x 32 bytes; the model exports
  TACHYON_HEADER and HEADER_ELEMENT_BYTES); the 2 and 4 boxes are disabled meanwhile.
- ANSWERED IN CHAT: Qr in Tachyon's step names is quadratic residuosity (qr.rs: an epoch's
  tachygrams partitioned by the residue side of x + R_j); Ragu's fuse samples its blindings
  (application stage blinded, eval-stage blindings rejection-sampled) but fuse/mod.rs says the
  construction does not yet establish zero knowledge, which `rerandomize` is meant to provide,
  so the measured fuse is the only fuse and the rerandomization is counted as a node; the
  Recovery Statement's primary input (ZIP 2005: rt, rk, nf, SigHash) is 5-6 field elements,
  so its header is 6-7 with the suffix and fits Tachyon's 9, which header 2 or 4 does not.
- STATE: pqzcash main at c5807b6 plus this entry, unpushed after f642051; the Ragu worktree
  ragu-tachyon-pin clean at 8ad598ed; the Ragu checkout clean on main; Tachyon clean (the probe
  under work/). PENDING: refresh the circuit-budget constants from ragu's internal/tests.rs;
  the zk-fold levers for the frontend; the Pallas factor at 147; generate the Transaction
  paragraph's figures from the model; a header for the recovery application as for Tachyon's;
  keep/tachyon-statements.md's cost table now carries the measured counts (its HTML render is
  stale).

## 2026-11-14 18:14 UTC: the recovery header; the circuit budget refreshed; the Tachyon tree re-packed per rank; a 3D unit fix

- HEADER (the user): the recovery-circuit options force header 9 as the Tachyon ones do
  (2c80e92), since the Recovery Statement's primary input (ZIP 2005: rt, rk, nf, SigHash) needs
  six or seven elements with the suffix.
- CIRCUIT BUDGET REFRESHED (c78874c) from ragu 8109a41c's internal/tests.rs: native fixed
  circuits Hashes1 1793, Hashes2 1874, Collapse 1455 (the two collapses merged), ComputeV 1948,
  BindBeta 1889, BindEndoscalar 940; nested Collapse 1598 (Export merged in), ComputeV 1504,
  Loading 566; an endoscaling step of four points 1995 gates / 3502 constraints (nested 2016),
  split as 451 per point + 191 (constraints 874 + 6), only the four-point step being pinned;
  binders: NUM_BINDERS = challenges::NUM / 2 = 4, so EIGHT challenges, two per binder,
  2032-2048 gates each (590 per challenge + 860 overhead, derived), CHECKED_IN binders 4 (was
  5), rows up to 4 binders, "code" below 4. The model's point counts were wrong by the online
  openings: nested::num_endoscaling_points = 1 + 2(native_rx + 4) + 6 + NUM_ONLINE_QUERIES
  while nested::pcs::num_batched_points = 1 + 2(nested_rx + 4) + 6; with that the fixed point
  is 48 native + 43 nested rx (25 and 29 endoscaling steps; native rx = 19 + 4 binders + 25),
  matching upstream's 50 + 45 components (+2 each) and the measured 7,908 bytes at header 4.
  Emax per rank unchanged (4, 8, 17, 35; 72 at rank 17); min binders 4, 2, 1, 1. Budget
  report: rank 14 E8 2 binders 6,692 / 6,820 B (H2 / H4), packed 6,468 / 6,596; rank 15 packed
  6,244 / 6,372; today 7,780 / 7,908. Prose updated in the page (budget paragraph, knobs) and
  pasta-proof-size.md (§8: 50 + 45 components, 54 steps, 4 binders; 6,372 at rank 14 E16 1
  binder H2; floor about 6.2 KB; smallest 6,468 / 6,244 against 7,780). The PEDERSEN_FUSE_
  COMMITMENTS = 96 assertion still holds (91 circuits + 4 + the step).
- 3D UNIT FIX (da24f36, the user's report): with the view held and transaction prover as the
  third measure, a unit change rescaled the points but not the held z range (only the decider
  measure carried it): now both work-unit measures carry it.
- TACHYON TREE RE-PACKED PER RANK (166e65e, the user: "the proof tree should be automatically
  optimized per-rank"): the page bins the nodes' circuits first-fit decreasing into the rank's
  step capacity (a node larger than a step takes whole steps, its remainder joins the rest; the
  rerandomization is its own step). Two tachyactions: rank 13 six steps (the 17-gate merge
  rides with FeeFuse), rank 15 two steps; Pedersen checked-in 8.76 s (Tachyon's own 7-fuse tree
  10.2 s), rank 15 / 16 endoscalings / 4 binders 5.4 s (2 steps), best code-change row 4.2 s;
  Akita Pasta claims 0.18 s (rank 15, 2 steps), BitZ 0.27 s (rank 22), frontend 0.09 s (rank 21,
  BLAKE3), Goldilocks 5.2 s / 151 steps, F2 20 s / 129; zk: Pasta claims 3.4 s, frontend 1.3 s.
  Sixteen tachyactions: Pedersen 49.6 s / 34 steps at rank 13, 21.5 s / 8 steps at rank 15;
  Pasta claims 0.53, BitZ 0.56, frontend 0.28, Goldilocks 35 s. The recovery and path options
  were already packed to the capacity (ceil(units / step_units), a circuit may straddle steps).
  Artifact v94. Both intermediate commits of the split were checked by running the model from
  git archive (the first split put two line-for-line constants lines in the wrong commit; the
  class regexes were widened and the split redone).
- STATE: pqzcash main at 166e65e plus this entry, unpushed after aedc6a2. PENDING: the zk-fold
  levers for the frontend; the Pallas factor at 147; generate the Transaction paragraph's
  figures from the model; re-render keep/tachyon-statements.md.

## 2026-11-14 18:26 UTC: the second and third measures chosen independently

- (the user) The page's vertical axis was always prover work. Commit b1a58a0: a "Second
  measure" radio group (prover work by default) beside the third (merge gates by default), both
  over the same five measures (prover, merge gates, accumulation atoms, decider work,
  transaction prover); the choice on one side is greyed out on the other. `frontierAmong(pts,
  second, third)` takes the frontier on bytes and both; `measureTitle(m)` replaces
  `thirdTitle`; each axis takes its type (atoms linear, the rest per the scale radio), title
  and held range from its measure, with the work-unit carry on whichever axes are in work
  units (WORK_MEASURES); the transaction select is its own group and applies to either side,
  as does the forced header. The "Which measures" paragraph says so ("Merge gates is the
  default third measure since every family has an estimate of them", the user's wording).
  Artifact v95. The model's pruning is unchanged (PRUNE_MEASURES plus step+merge prover and
  fold, so a row better on any shown measure survives).
- STATE: pqzcash main at b1a58a0 plus this entry, unpushed after aedc6a2 (seven commits).
  PENDING unchanged: the zk-fold levers for the frontend; the Pallas factor at 147; generate
  the Transaction paragraph's figures from the model; re-render keep/tachyon-statements.md.
- 18:32 UTC, addendum: the two measure groups share one full-width group laid out in two columns (bbd7dbe), since the two-column controls grid had put them diagonally; artifact v96. Main at bbd7dbe plus this line.

## 2026-11-14 19:22 UTC: the accumulation prover measure (the fold's sum-checks were missing)

- THE USER noticed the frontend's merge prover is flat over ranks 18-21. Two causes: (1) the
  prover measure is the merge circuits' commitments, and the merge circuit (~1.97M digits with
  BLAKE3, ~3.76M with Poseidon) rounds up to the same 2^21 (2^22) digits however it is chopped,
  with the per-circuit claim absorption (8,500 / 19,000 digits a circuit) the only rank term
  below 18 and the padding of one circuit above 21; (2) the model LEFT OUT the fold's own
  prover work: Akita's two norm and range sum-checks over the accumulator, K groups of 2^rank
  coefficients in digits, linear in the step size, where the merge circuit verifies them in
  log size ("Folding and sum-check work is not in these figures", which the user's intuition
  caught). Fold prover (the accumulation argument's native prover) vs merge prover (committing
  the merge circuits): clarified in chat; the page's `fold` field is the zk mask handoff, so the
  new term is called the ACCUMULATION PROVER.
- COMMIT c2a9cf6 (artifact v97): accumulation_prover = prover + accumulation_sumchecks(variant,
  K, rank, digits): (2 sum-check passes x 5 field mults + 1 for the fold's linear combination)
  x WORD_MULTS[variant] x K x 2^rank x digits (DIGITS[variant], or 1 per bit for the
  frontend); the 5 field mults per digit a pass come from the frontend's measured Booleanity
  sum-check (437.7 ms / 2^27 bits one core = 9.8 word mults per 64-bit digit; an assertion
  ties the constant to BOOL_CHECK). Other rows: accumulation_prover = prover (Pedersen: the
  measured fuse includes its native folding, batching 95 polynomials of 2^13 (2.5e7) and a
  100-point linear combination (1.8e7) = 1% of the fuse; hash-based: the ARC step already
  hashes the new accumulator, one of its two trees, <10% with BLAKE3 and ~half with Poseidon;
  binary groups: the measured opening includes its sum-checks). The measure is the default
  second measure (radio value accumulation_prover, in WORK_MEASURES, table column, hover); the
  transaction measure charges step_prover + accumulation_prover per step; PRUNE_MEASURES
  includes it. Effect: frontend BLAKE3 accumulation prover 1.05e8 at rank 18 -> 3.5e8 at 21
  (prover 7.0e7 flat); Akita Pasta claims rank 17: 1.73e9 vs prover 2.6e8 (85 digits per
  coefficient). Transaction figures (floor 128, one core): recovery: Pasta claims 12 s (was
  3.2), BLAKE3 144 s, Goldilocks 65 s (was 17), frontend 0.41 s at rank 20 (was 0.14 at 21),
  zk frontend 2.5 s, zk Pasta claims 38 s; 2 tachyactions: Pasta claims 0.42 s (was 0.18),
  frontend 0.21 s, Goldilocks 20 s; 16: Pasta claims 1.7 s, frontend 0.83 s, Goldilocks 132 s.
  Pedersen, BitZ, F2 unchanged. Prose: the Which measures and knobs (new Accumulation prover
  bullet) paragraphs, the Transaction, Tachyon and Zero knowledge figures, pasta-proof-size.md
  (prover table caveat; "commitments nearly flat in rank, the sum-checks grow").
- OPEN MODELLING QUESTIONS the user asked about (what else is left out): the claim-field
  sum-check for the Pasta-claims rows (if the evaluation claim's sum-check runs in Pasta's
  field it adds 5 x 32 x K x 2^rank per fuse: under 10% of the digit sum-checks for Akita's
  85-digit coefficients, but up to 8x the frontend's accumulation term if its claims are not
  limb-wise over the small field; the spike says limbs, so probably not); witness generation
  (native hashing for the merge circuit's witness, small against commitments); the
  aggregator's opening/compression of the final accumulator (Akita's catalog levels and
  compression maps; Pedersen's IPA ~2% of a fuse), paid once per transaction off the device
  under the zk note's handoff; accumulator MEMORY (Akita Pasta claims at rank 17: 6 x 2^17 x 85
  digits x 8 B = 535 MB per accumulator; the frontend at rank 21: 100 MB; Pedersen 25 MB), a
  phone constraint the page does not show; native transcript hashing (tiny); phone
  parallelism (the fuse's 2.2x on 16 cores). Not changed.
- STATE: pqzcash main at c2a9cf6 plus this entry, unpushed after aedc6a2. PENDING unchanged:
  the zk-fold levers; the Pallas factor at 147; generate the prose figures from the model;
  re-render keep/tachyon-statements.md; maybe a memory column or note.
- 19:44 UTC, addendum: a crosshair pointer over the plot in both views (ad78671, CSS on Plotly's drag layer and 3D canvas), since the arrow covered the hover box; artifact v98. Main at ad78671 plus this line.
- 20:00 UTC, addendum: the measure radio labels are "accumulation prover" and "prover work (commitments only)" (3e2e255); artifact v99. Main at 3e2e255 plus this line.

## 2026-11-14 20:07 UTC: accumulator memory as a measure

- (the user) Commit 31f4a07, artifact v100: `memory` per row, bytes the prover holds between
  fuses, a seventh measure for either axis, in the table (Accumulator bytes column) and the
  hover, and in PRUNE_MEASURES. Lattice rows: accumulator_bytes(variant, K, rank, digits) =
  K x 2^rank x digits x DIGIT_BYTES[variant] (the commitment field's element: 8 B at 64 bits
  (pasta_q64, goldilocks), 16 at fp128, 32 at Pasta's modulus; packed 4-byte storage would be
  a quarter or less since the accumulated norm is below 2^32); the frontend one digit per bit
  at 8 B. Pedersen: commitments x 2^rank x 32 B = 24.9 MB at the checked-in rank 13 (the
  uncompressed Proof measured 26,480,800 B). Hash-based under ARC: arc_accumulator_bytes =
  the codeword (2^log_len x elems x 1/rate elements at ELEM_BYTES, 32 Pasta / 24 Goldilocks
  cubic extension) plus the tree at 2 nodes of 32 B per 16-element leaf; under recursion the
  previous proof (the setdefault to bytes). BitZ (ARC) and F2: packed codeword bits x 1/rate x
  5/32 B (the codeword at 1/8 B per bit plus a tree of 256-byte leaves); bitz_rec the proof;
  binary groups K x 2^bits_akita_log / 8. Figures: Pedersen rank 13 25 MB; Akita Pasta claims
  rank 17 535 MB, Goldilocks rank 17 138 MB; frontend rank 21 101 MB; BitZ rank 20 rate 1/8
  40 MB; F2 rate 1/8 37 MB; binary groups 2 MB; WHIR + ARC with BLAKE3 at rank 13 rate 1/8
  92 GB (39,115 merge circuits x 2^13 x 8 x 32 B), with Poseidon at rank 16 about 3 GB: the
  BLAKE3 merge circuits multiply the accumulator too. The knob text says a fuse holds the
  step's witness and one or two accumulators: two with two real children, one when the other
  child is the bootstrap proof (the fixed base case, recognised by its dummy suffix), as in a
  chain or Tachyon's SpendAction/OutputAction (the user asked; answered in chat).
- STATE: pqzcash main at 31f4a07 plus this entry, unpushed after aedc6a2. PENDING unchanged:
  the zk-fold levers; the Pallas factor at 147; generate the prose figures from the model;
  re-render keep/tachyon-statements.md.
- 20:15 UTC, addendum: the memory knob's "packed storage a quarter or less" was wrong for the 64-bit rows; corrected in 904d78e (32-bit integers: half at 64 bits, a quarter at 128, an eighth at Pasta's modulus; the field form made on the fly per sum-check pass), artifact v101. The Akita and frontend rows' memory is the same under either hash policy (K x 2^rank digits); WHIR + ARC at rank 16 rate 1/8 is 74 GB with BLAKE3 and 1.2 GB with Poseidon. The user pushed main through 50ddcfc.
- 20:23 UTC, addendum: the memory measure now counts the lattice rows' accumulator at the packed width of its norm bound (65f58f7, artifact v102; the user: a known per-level bound lets each accumulator be stored at its exact width): 21 bits a digit at the handoff, the certified l2 bound of about 2^19 plus a sign, five bits fewer per level below the top, the measure being of the top level; the field form (8/16/32 B) is computation. Figures: Akita Pasta claims rank 17 175 MB (was 535), Goldilocks 45 MB, fp128 89 MB, frontend rank 21 33 MB, BitZ rank 20 32 MB, F2 29 MB, Pedersen 25 MB. Norm growth: each fold multiplies the entries by up to 40 (ternary challenges of l1 weight 20, two children), about five bits a level, so the 2^19 handoff bound is a tree of three or four levels; growing beyond costs rows as the square of the bound's bits (five more bits about +40%), decomposing costs a recommitment of the accumulator, so within a transaction growth is the design and the aggregator decomposes (answered in chat).

## 2026-11-14 21:13 UTC: BitZ's prover in two phases; the family named Kishu; the review of Ulrich's and Quang's statements begun

- BITZ PROVER (the user: check the GKR handling; then "price the two phases separately"; commit
  da6d65f, artifact v103): the rows scaled Table 10's whole prover by 1.25 at rate 1/8, a ratio
  measured at 2^27. The reruns' phase timings (work/bitz-out/rerun/summary.txt, one thread,
  mains) show the grand-product GKR, which lifts the integer claims into the exponent of a
  generator of F_2^128 and does not depend on the rate, at 79-85% of the prover from 2^25 to
  2^28 (custom:1:4: 82/104, 154/194, 310/367, 566/663 ms), and the whole-prover rate-1/8 ratio
  at 1.00, 1.09, 1.28, 1.18 by size (the Ligerito phase's jump at 2^27). BITZ_PHASES holds the
  GKR share and the Ligerito factor by log bits; bitz_prover_scale(rate, log_bits) = share +
  (1 - share) x factor; BITZ_RATE keeps only the Ligerito bytes. The frontier rows at 2^24.7 to
  2^25.4 bits lose about a fifth: rank 13 rate 1/8 prover 2.1e8 (the page said 3.5e8, stale);
  recovery 0.25 s (was 0.30), two tachyactions 0.21 s (was 0.27), sixteen 0.45 s (was 0.56).
  Also checked: Table 10 is near-linear in bits (2.0-2.4 ns a bit), so the log-linear
  interpolation errs under 2%; the 128-bit prover factor 1.0 holds (the GKR phase is the same at
  100 and 128 bits); this M4 Max is 1.25-1.3x the paper's M5 on one thread; the GKR
  parallelizes 3x (2^25) to 6.5x (2^28) on ten threads, not shown by the one-core figures.
- KISHU (the user chose the name; "Shiba" has no prior use among proof systems but is the
  memecoin; commit 2a7e271, artifact v104): the BitZ-over-Akita family is Kishu, a Japanese
  breed like Akita and Hachi (the lattice PCS names are dog breeds: Greyhound, Hachi, Akita,
  Grand Danois, Maltese, Jindo); the label, the page's prose, pasta-proof-size.md and the spike
  README say Kishu; the key bits_q64 and the frontend_* identifiers stay.
- THE REVIEW OF ULRICH'S AND QUANG'S STATEMENTS (the user: "check everything they've said that
  was not already contradicted"; the session logs also hold private security-triage material,
  which is excluded): statements collected from WORKING-NOTES, keep/ulrich-*.{md,txt} and the
  user turns of the session logs since 2026-10-13 (the scratch extraction is not kept). Quang:
  (1) price each hash-based scheme with its own recursion rather than ARC; (2) the grand-product
  GKR is the expensive part of BitZ; (3) Kishu's prover is probably overestimated, the loose
  security analysis assuming too much grinding; (4) for a fixed norm bound SIS gets harder as
  the modulus grows, so the module rank shrinks by about the ratio of bit lengths; (5) the QROM
  proof of Akita "in progress, not long" (2026-10-14). Ulrich: (6) 86 openings per input is
  more than the list-decoding regime needs; (7) a field over 128 bits is needed to reach the
  Johnson bound, then far fewer samples; (8) query-phase grinding cuts the samples; (9) a
  stand-alone FRI-Binius at 2^25 bits, rate 1/64 is about 66 KiB; (10) packing straight into a
  191/192-bit field would be more efficient; (11) the ARC decider's first round opens three
  oracles; (12) for FRI-Binius the only secure randomisation is a full-entropy mask in a batching
  step before FRI, while Ligerito takes Zook-style randomisation at negligible cost; (13) the mask
  must be witness-size, blinders droppable, only the private witness masked. Already settled in
  the record: his one-row mask (his own slip, corrected the same day) and (10) (a wash on the
  model). CHECKED SO FAR: (2) holds, 79-85% of the prover measured; (5) NOT DONE as of the
  2026-10-15 revision of ePrint 2026/1983, which says the proofs are in the ROM and the QROM is
  future work (introduction, sections 10 and 14), and none of Quang's later ePrints (2501, 2056,
  2424, 2157) is it; the user will ask him. FINDING on the way: Kishu's rows omit the application's
  constraint PIOP (Zinc+'s UCS sum-checks over the digit table), which BitZ's rows charge at 1.6x
  the PCS prover on the application's share; for the recovery circuit (4.7M application digits
  against 2M of merge) that is roughly a third more on Kishu's figure; not yet modelled. Also
  explained in chat: Kishu has no GKR (a prime field makes the integer recomposition linear; the
  Booleanity certificate replaces what the binary field gave for free), and it beats BitZ on the
  transaction measure through its merge (2.0M digits against 28M bits), not per bit (26-33
  against 9 word multiplications). TO CHECK NEXT: (1), (3), (4), (6)-(9), (11)-(13).
- STATE: pqzcash main at 2a7e271 plus this entry, unpushed after 50ddcfc (nine commits).
  PENDING: the review's remaining checks and its record under keep/; Kishu's application PIOP;
  the zk-fold levers; the Pallas factor at 147; generate the prose figures from the model;
  re-render keep/tachyon-statements.md.
- 21:19 UTC, addendum: Kishu's application digits now pay Zinc+'s constraint PIOP (4cfc722, artifact v105): ZINC_PIOP_PER_DIGIT = 1.6 x BitZ's Table 10 prover per bit at 2^25 = 11.4 word multiplications a digit, on the step's digits only (the merge circuit's own PIOP is not charged, as for BitZ). Effect about 5%, since the fold's sum-checks dominate Kishu's step at ranks 19-21: recovery 0.43 s (was 0.41), zk 2.6 s, two tachyactions 0.22 s, sixteen 0.88 s; the earlier "a third more" guess predated the accumulation prover. The review finding is closed; the other checks continue.
- 21:23 UTC, addendum: the review of Ulrich's and Quang's statements is done, record keep/ulrich-quang-review.md (fourteen statements with verdicts and evidence; all hold or are judgements except the Akita QROM proof, still future work, and "86 openings is more than needed", true only up to the refuted capacity regime; the 2026-10-21 sweep had settled U1-U3). Main at fede238 plus this line, unpushed after 50ddcfc.
- 21:49 UTC, addendum: EVIDENCE PLAN agreed with the user (pen and paper with computational checks first, Lean once the statements hold still; the decoupled modulus first). The statements are drafted in keep/kishu-soundness-note.md for review before any proof. Findings while writing them: Kishu does NOT use the decoupled modulus (its claims live in F_q = 2^64 - 59 = the commitment modulus, over E = F_q[u]/(u^2 - 2); Pasta values come from 32-bit limbs, Lemma B3), so its obligations are Akita's own 64-bit soundness, the Booleanity certificate and the limb lemma, and the page's "same open soundness obligation" is wrong; design A (pasta_q64) is the one needing the no-wrap knowledge-soundness proof, where two details may bite: the quotient k's width grows with the accumulated norm (up to 2^49 at N = 2^22, 17 digits, not the 11 of pasta-proof-size.md 6.3), and a digit-range product identity over F_p cannot lift for accumulated witnesses (magnitude 2^270), so the range check must be the l2 norm or apply to fresh digits only. Cost consequence: design A's fold sum-checks run over F_p (32 word multiplications a multiplication), so the pasta_q64 accumulation term is low by 3-4x (Kishu unaffected: E at 64 bits, measured). Not yet changed on the page.

## 2026-11-14 21:54 UTC: STATE for resumption (context low); the Pasta-claims sum-check field fixed

- PASTA-CLAIMS FIX (c8aa330, artifact v106): accumulation_sumchecks takes the CLAIM field's
  multiplication cost (CLAIM_WORD_MULTS: 32 for the Pasta variants, 8 fp128, 1.5 Goldilocks);
  Kishu passes the 64-bit rate explicitly (its claims live in F_q = 2^64 - 59, E-extension,
  Pasta values from 32-bit limbs). pasta_q64 figures: recovery about 140 s at rank 16 (was 12),
  zk about 170 s; two tachyactions 3.2 s at rank 12 (was 0.42), zk 5.9 s; sixteen 16 s (was
  1.7). Page text: the Kishu paragraph no longer says Kishu shares the decoupled commitment's
  obligation; the accumulation-prover knob says the sum-checks are in the claim field. The
  BLAKE3 figure for the Pasta-claims recovery row was dropped from the Transaction paragraph
  (not recomputed).
- THE EVIDENCE PLAN (agreed): pen and paper with computational checks first; Lean (Lemma L, the
  limb lemma, then the reduction in VCVio, CertifiedJL's tails imported) once the statements
  hold still. The statements are in keep/kishu-soundness-note.md, AWAITING THE USER'S REVIEW:
  Lemma L (no wrap), Lemma B3 (limbs), Theorem B (Kishu's claim reduction: Booleanity via
  Theorem 1 + the projection certificate, the batched sum-check with limb terms, error
  eps_proj + (2m+2)/|E| + Akita's), Theorem A (the decoupled variant's knowledge soundness, to
  be stated once the protocol is written; the non-mechanical points: the quotient k's width per
  level, up to 2^49 = 17 digits at N = 2^22 and the handoff norm against the note's 11; and the
  range check, which must be the l2 norm or fresh digits only, since a digit-range product
  identity cannot lift at 2^270). Proposed order: Theorem B first (Kishu's), with the spike
  extended by the adversarial cases named in the note's §6; then the independent recomputation
  of the draft's 2^-136 certificate at its parameters (four chains 43,43,43,43,40; radices
  2^14,16,8,8,8; geometric grid 1/1024 ratio 33/32, 192-bit CDF rounding, moment order 20);
  then Theorem A adapted from LaBinius; then Lean. Three decisions for the user: the statements
  as written; Theorem B first; (the page fix is now done).
- ASK QUANG (the user will): the QROM proof of Akita (future work as of the 2026-10-15
  revision); whether the composed-chain certificate is on CertifiedJL's roadmap; whether a
  tighter analysis of the rows term exists.
- STATE: pqzcash main at c8aa330 plus this entry, unpushed after e822512 (two commits plus
  this). Untracked: keep/kishu-soundness-note.md, keep/ulrich-quang-review.md (both to keep),
  the scratch extraction of the session logs is in the session scratchpad only. Artifact v106.
  PENDING: the review-record items above; the zk-fold levers; the Pallas factor at 147; generate
  the prose figures from the model (they drift: this entry's figures were hand-updated again);
  re-render keep/tachyon-statements.md; the Transaction paragraph's BLAKE3 figure for the
  Pasta-claims row.

## 2026-11-15 01:00 UTC: the soundness note tracked

- THE SOUNDNESS NOTE is tracked as ragu-pcs/kishu-soundness-note.md (2644176), updated to
  record that the PCS frontier page's Kishu paragraph and the sum-check pricing were corrected
  in c8aa330, with the draft cited by title and date in place of its local path. The statements
  themselves are unchanged and still await the user's review (Lemma L, Lemma B3, Theorem B,
  Theorem A; Theorem B first). The review of Ulrich's and Quang's statements stays under keep/
  (the user's decision): keep/ulrich-quang-review.md.
- PASTA-PROOF-SIZE.MD's BitZ paragraph said Kishu's Pasta claims go "through the decoupled
  commitment"; corrected to the limb recomposition in the 64-bit field. The rest of that
  paragraph's Kishu figures (88 KB at rank 15, 6.6e8 or 8.4e8, "the 64-bit Akita variant
  dominates it") predate the accumulation prover measure and the Pasta-field sum-check fix, so
  they belong to the pending "generate the prose figures from the model" item.
- STATE: pqzcash main at 6f030d0 plus this entry, unpushed after c8aa330 (e1f8fd1, 2644176,
  6f030d0 and this). Untracked and kept: keep/ulrich-quang-review.md. Artifact v106. PENDING:
  unchanged from the 21:54 entry, less the note.

## 2026-11-15 02:17 UTC: the prose figures generated from the model; claims guard the wording; sizes in kbytes

- PROSE FIGURES (the user: "please do the generation of figures from the model"; commits
  7588e3a, 58f2f77, 95da46e, 09d379d; artifact v108): every model-derived figure in
  pareto-template.html and pasta-proof-size.md sits between markers,
  <!--fig:NAME-->value<!--/fig-->, invisible when rendered. The model fills them when it writes
  pareto.html; `python pareto-model.py --fill` writes the values back into the tracked files;
  the default run (and so the book build) FAILS when a tracked value is stale or a claim no
  longer holds, printing the stale markers as old -> new. `--figures` lists every figure.
  The definitions are in define_figures() at the end of the model: shown(family, policy, zk,
  floor, **where) selects rows as the page does (grind "auto" only, the Poseidon option adding
  rows), pick() one row, best_for(family, app, policy) the least-transaction row with tx_steps
  and tx_work, a Python copy of the page's txStepsFor; the page checks the two copies against
  each other on the quoted rows (DATA.tx_checks, a red line at the top if they differ). Names:
  _s seconds, _ms milliseconds, _minutes, _kb kbytes, _pct percent, _min/_max a range's ends.
  Formatting: sig() two significant figures, three from 100 up for sizes and millions.
- CLAIMS (the user: "for wording that is too difficult to generate, you can write assertions
  that will be broken if the wording goes stale"): claim(text, holds) entries fail the run;
  e.g. rank 14 packed beats rank 13 on bytes, prover and atoms; Kishu dominates the 64-bit
  variant under BLAKE3 on every measure but the merge's count; BitZ's zk prover unchanged.
- WHAT THE FIRST FILL CORRECTED: the budget table (binders 4 not 5 at rank 13; 3, 1 fixed
  circuits packed at rank 14, not 4, 2; 72 endoscalings at rank 17, not 70); Pedersen's best
  recovery row 1.9 minutes at rank 17 (was "two and a half"); rank-15 Tachyon 4.2 s and 17 s
  (were 5.4 and 22); Kishu zk 2.5 s (was 2.6); the hash-based ranges widened (WHIR with
  Poseidon 171 to 1,280 kbytes, 27 to 1,900 times Pedersen's prover). Claims that FAILED and
  the wording fixed: BitZ's recursion row has a SMALLER proof than its ARC row (381 against
  489 kbytes) at 7.4 times the prover, so "the proof grows with the merge" was wrong; the limb
  hybrid's prover FALLS 2.2 times under BLAKE3 (its Poseidon over limbs is dear natively), so
  "the prover 1.3 to 2 times" holds for the other three WHIR-type rows only; the F2 family's
  rate-1/2 row is no longer pruned (its accumulator memory is smaller); the 256-bit design is
  up to 7 percent dearer, not a tenth; rank 17 under BLAKE3 saves 0.6 kbytes at the small
  fields, not "a few kilobytes"; BitZ at rank 13 is no longer unbeaten among Pasta-claims rows
  (Kishu beats it on bytes and prover), so the claim is restricted to the hash-based families;
  "the 192- and 191-bit proofs equal" (173 against 174 kbytes) dropped. pasta-proof-size.md:
  the BitZ row (489 kbytes, 2.1e8, 28 million bits, 7.4 ms; was 302, 3.8e8, 31, 5), the WHIR
  measured sizes in kbytes, Goldilocks WHIR 273 to 658 kbytes (was 115 to 228), the F2 row 173
  kbytes and 4.4e8 (was 194 and 1.3e8), the smallest Pedersen proofs with six and three fixed
  circuits packed into three and one (was seven and four into four and two; 6,468 and 6,244
  bytes, 6,372 for the infeasible rank-14 E16 one-binder configuration), the eight challenges
  (was ten), and the Kishu passage rewritten (it said the 64-bit variant dominates Kishu and
  that costing the recovery circuit was the open step). Also fixed: the lede, the frontier
  chapter and the note said "a third measure".
- UNITS (the user: KB is ambiguous; "use kbytes for units of 1000 bytes"): kb() writes
  kbytes, mb() Mbytes; every KB/KiB/MB in the template and the three notes is now kbytes or
  Mbytes (KiB figures converted: 307 KiB -> 314 kbytes, 73 to 86 KiB -> 75 to 88 kbytes, Flock
  200 to 386 KiB -> 205 to 395 kbytes, LaBinius under 100 KiB -> under 103 kbytes, 8 KiB ->
  8192 bytes). The user's other wording fixes: "between BLAKE3 which is the default, and
  Poseidon 1.1"; "Japanese dog breed"; the transaction-prover description in short sentences.
- STATE: pqzcash main at 09d379d plus this entry, unpushed after c8aa330 (e1f8fd1, 2644176,
  6f030d0, a763ce7, 95da46e, 7588e3a, 7f08ab5, 58f2f77, 09d379d and this). Each commit was
  checked by running the model from its archive. Artifact v108. PENDING: the user's review of
  the soundness statements (ragu-pcs/kishu-soundness-note.md), then Theorem B; the zk-fold
  levers; the Pallas factor at 147; re-render keep/tachyon-statements.md; the Transaction
  paragraph's BLAKE3 figure for the Pasta-claims recovery row (now easy as a figure).
- 02:37 UTC, addendum: CLAIMS for ARC against recursion (the user asked whether ARC rows are now
  dominated by recursive ones: not under BLAKE3, nor BitZ's or the F2 family's under either hash;
  with Poseidon trees the rate-1/2 recursive rows of WHIR over either field and the limb hybrid
  dominate their ARC rows on all seven measures; both sentences are on the page and claimed), and
  for the page's NEGATIVE statements (rows that do not exist, measures that do not move; the
  user: "the negative claims also need to be guarded"). Two caught stale text: under BLAKE3 the
  small fields have Akita rows from rank 14 (1,740 circuits) and the Pasta variants from 15
  (1,471), not 15 and 16; zero knowledge moves Akita's decider by up to 7% where the 18 atoms
  need one more circuit (edb7659). LAYOUT (the user: walls of text; narrow margins; 70-80
  characters too narrow; tables full width, the budget table may stay in the column; the
  Configuration column wider): bold lead-ins -> h3, the axes list -> headed paragraphs, long
  paragraphs split at topic changes (27 headings, 137 paragraphs), text in a centred column of
  64em at 16px (about 120 characters); the tables sit in the column too, the frontier table
  scrolling sideways, and only the plot keeps the full width (04320b3). Artifact v111.
  STATE: main at 04320b3 plus this line, unpushed after c8aa330.

## 2026-11-15 09:34 UTC: the Pallas factor at 147 computed; WHIR measured at 147; the width shrink recovered and recomputed; the regeneration document; one family per paragraph

- PALLAS AT 147 (8828a4f): the Pallas infinity-norm width table at 147 bits ran overnight in the
  147 worktree (`infinity_width_table --policy Quantum147BitADPS16 --profiles pallas --format csv
  --profile local-minimum`, work/akita-147-out/linf-width-table-147-pallas.csv and .log): 19,834 s,
  5.5 hours, since the pipeline's estimator build lacks the `parallel` feature (the 150-bit run
  with it took 58 minutes). rank-scale.py now takes the Pallas CSVs as a third mapping; against
  the 150 table it reproduces 1.009, and at 147 the result is the same: 117 -> 118, one instance
  moves, factor 1.009 -> 1.01 (the carried bound stands as computed; rounding up is the
  conservative side). The model holds RANK_INSTANCES = 115 (one row per catalog schedule: 79
  fp128, 17 fp64, 19 fp32) and RANK_SUMS_147 per mapping, derives RANK_SCALE_147 from them, and
  the margin paragraph's sums, factors and moves are figures.
- WHIR AT 147 (same commit; scripts/whir-sweep-147.sh, work/whir-sweep-147.log): the reference
  binary at 2^17, both fields, rates 1/2 to 1/8, pow 20, Johnson, --reps 3, at 128 and 147 bits:
  proof ratios 1.164/1.156/1.161 (Field256) and 1.154/1.151/1.152 (Goldilocks3), mean 1.156 ->
  WHIR_SCALE[147] = 1.16 as interpolated; hash ratios mean 1.116 -> WHIR_HASHES_SCALE[147] = 1.12
  (was the interpolated 1.13 literal). WHIR_147 holds the measurements; ARC_FLOOR_PCT = 15. The
  user was confused by the margin paragraph running the WHIR sentence after the Module-SIS rank
  growth (and by my message implying the WHIR change depended on the overnight table); the
  hash-based rows' lambda-only adjustments now have their own heading.
- WIDTH SHRINK (961032a): the 150-bit medians' method was not in the notes; recovered from the
  2026-10-15 session log (an inline script: policy_audit.csv at 128 against the 150-bit CSVs,
  cells with w150 < w128, median of w128/w150 by ring dimension). Reviewed: it did not consult
  hit_cap, so a cell capped at 128 but finite at 150 counted as cap/width; with hit_cap excluded
  the medians change little (the x62 cells at the largest dimensions are genuine) so the old
  sentence was sound. My first recomputation (rust-split tables, no strict-decrease filter) was the
  wrong one. scripts/width-shrink.py is the cap-aware method; at 147: 2.1-3.0 at d <= 32, 64:
  q128 10.0, pallas 9.7, goldilocks 5.3, q64 4.9, q32 4.4; 128: 11.5-12.5 (q32 4.5); 256:
  12.9-13.3 (q32 5.3); 512: 14.0-15.3 (q32 6.1, pallas 35.8); 1024: 14.7 (q128 36.2, q32 6.3);
  2048: 36.1. WIDTH_SHRINK_147 in the model; the page's and the note's sentences are figures
  (ranges by dimension group, the 32-bit modulus at the low end, the ~36-fold outliers apart).
- REGENERATING.md (ca65312; the user: "make sure that it is documented how to regenerate all the
  numbers", current situation only, no history, no mains-power requirement, a one-line
  `caffeinate -i` note): the figure/claim mechanism, the external checkouts with revisions and
  patches, and per input group the script, invocation and outputs. The scripts moved from work/
  to ragu-pcs/scripts/ (copies; work/ keeps the originals) with the checkout directory taken from
  RAGU_PCS_WORK (default ../work); scripts/patches/ has akita-pasta-widths.patch (moved),
  akita-147-policy.patch (code-only diff 60b82bc..2478c43 of the worktree; the tables are
  regenerated by the pipeline) and ragu-counting-adapter.patch (a1395401..8ad598ed);
  scripts/tachyon-gates/ is the probe crate (its manifest expects ../../crates/tachyon and the
  worktree ../../../ragu-tachyon-pin).
- PARAGRAPHS (2a20f4f; the user: "look for other cases where putting different families in the
  same paragraph might cause confusion"): a script listed paragraphs naming three or more
  families; the comparisons stay, the walk-throughs split (Rank's tail, Proof bytes, Accumulator
  memory, Prover work, Decider work, Security floor, BitZ's zk tail, the zk section's Pedersen and
  WHIR paragraph, the transaction paragraph's arithmetizations).
- STATE: pqzcash main at 2a20f4f plus this entry, unpushed after 3ab8793 (the user pushed through
  it). Artifact v114. PENDING: the user's review of the soundness statements, then Theorem B; the
  zk-fold levers; re-render keep/tachyon-statements.md; the Pasta-claims recovery row's BLAKE3
  figure. The Pallas factor at 147 is done.
- 09:38 UTC, addendum: the 2D view opened scaled to the whole dataset (the hold box was on from the
  start and its first ranges came from DATA.points), so Pedersen-IPA's hidden rows set the axes; the
  hold box now starts unticked, and ranges taken under the hold come from the plotted points
  (32e212c). Zero knowledge is on by default (e47747c). Artifact v115. STATE: main at e47747c plus
  this line, unpushed after 3ab8793.
- 09:56 UTC, addendum: DEFAULTS and CONTROLS (the user): third measure = transaction prover (recovery
  circuit), unit = microseconds (ae592ea); controls reordered: families; measures with the
  transaction selector (now full width); view, unit, frontier; floor, zk, hashes, changes; rank,
  "PCD headers" (was labelled Pedersen-IPA; it sets every family's headers), Pedersen-IPA's fixed
  circuits, grinding (936d7d0). Artifact v116.
- 10:22 UTC, addendum: the WHIR-type families and Plonky3 start unticked (the user; Akita dominates
  them and their rows crowd the picture), said in the hash-based families paragraph (8afe39b). Artifact
  v117.
- 10:41 UTC, addendum: WHIR-type and Plonky3 unticked by default (8afe39b); the Orchard all-cores
  sentence reworded (0a0f478); the controls REGROUPED after a headless-Chrome render (the user:
  look first; `Google Chrome --headless=new --screenshot --window-size=1920,2300` on a copy with the
  panel's max-height removed, cropped with sips; work/layout-controls*.png): View | unit and
  frontier; Security (floor, zk) | Allowed changes (hashes, parameter filter); rank boxes wrapped
  full width; PCD headers | Family knobs (fixed circuits, grinding) (215ddbb). Artifact v120.
- 10:45 UTC, addendum: the regrouping revised after the user's look at the render: unit and frontier,
  and fixed circuits and grinding, are separate groups stacked beside View and PCD headers;
  eyebrows simplified and item labels clarified ("conventional hashes only (BLAKE3)" etc.); the
  ranks a 7-column grid of bare numbers, their meaning in the Rank paragraph (073a408). Artifact v121.
- 10:49 UTC, addendum: the grinding select full width below the headers row with "best per row
  (smallest prover)" (the row's prover, which for the hash-based rows is also the accumulation
  prover) (1e2a9a9). Artifact v122.
- 10:52 UTC, addendum: thin rules between the controls sharing a group (View: projection, scale,
  hold; Security: floor, zk; Allowed changes: hashes, parameter filter) (9f530ce). Artifact v123.
- 11:02 UTC, addendum: every heading has an id and the cross-references are fragment links that say
  "section" (the user: the former paragraphs are sections now); links in the accent colour;
  the Rank section's Pedersen-IPA sentences in their own paragraph (852af0a, 1a84ce4).
  Artifact v125.
- 11:15 UTC, addendum: the table references link to #frontier-table; the table takes its natural
  width (it was squeezed to the column, wrapping the Assumption and Changes cells and setting
  every row's height), the short text columns nowrap, Family 26-30ch and Configuration 40-46ch,
  so rows take up to four lines (checked in the headless render) (6ccd8c9). Artifact v127.
- 12:38 UTC, addendum: the unit option is MILLISECONDS (unitFactor 1/3e6; fmtWork: three significant
  figures below a second, whole ms from a second up; the hold carry uses the same factor); the
  model's secs()/minutes()/decider ms figures are three significant figures; the BitZ "unchanged
  with zk" claims allow 1% (3456ff3). Artifact v128.

## 2026-11-15 12:41 UTC: STATE for resumption (context low)

- DONE TODAY, all committed: the prose figures generated from the model with markers and claims
  (REGENERATING.md documents the regeneration; scripts/ holds the scripts and patches); sizes
  in kbytes/Mbytes; the Pallas factor at 147 computed (1.01 stands); WHIR measured at 147 (16%,
  hashes 12%); the width shrink recovered, reviewed and recomputed at 147; one family per
  paragraph; headings with ids and section links, "section" not "paragraph"; the page's
  defaults (transaction prover as the third measure with the recovery circuit, milliseconds, zk
  on, hold off, WHIR-type and Plonky3 unticked, axes from the plotted points); the controls
  reordered and regrouped after headless-Chrome renders (Google Chrome --headless=new
  --screenshot; crop with sips; work/layout-*.png, table-test*.png); the frontier table's
  references linked, its natural width with Family 26-30ch and Configuration 40-46ch (rows up
  to four lines); milliseconds with three significant figures below a second and whole ms
  above, prose times at three significant figures.
- STATE: pqzcash main at the notes commit after 3456ff3; the user pushed everything through
  3456ff3, so only this entry is unpushed. Artifact v128. Tree clean. Shannon's memory-seed has uncommitted edits
  to feedback_durable_prose, feedback_git_safety, feedback_external_reports and
  feedback_readable_prose (the generated-figures rule, the bare-rebase rule, machine details
  out of tracked files, one subject per paragraph).
- PENDING: the user's review of the soundness statements (ragu-pcs/kishu-soundness-note.md),
  then Theorem B with the spike's adversarial cases, the certificate recomputation, Theorem A,
  Lean; the zk-fold levers; re-render keep/tachyon-statements.md; the Pasta-claims recovery
  row's BLAKE3 figure (one more fig()); the user to ask Quang about the QROM proof and
  CertifiedJL's roadmap. Open question from the user: whether the prose seconds should be at
  millisecond resolution too (they are at three significant figures).

## 2026-11-15 14:55 UTC: the zero-knowledge note joins the prose files; the decider ranges; the claims' layout; table units

- The user edited REGENERATING.md (pasta_curves 0.6.1 for the Halo 2 benchmark; e8fa64e). The
  bench crate's Cargo.lock confirms 0.6.1 (orchard 0.16.0, halo2_proofs 0.4.1); its compiled
  artifacts are gone, so the lock file is the record. The table row now says a crate over the
  orchard release, not an Orchard checkout (0817985).
- The BitZ "unchanged with zero knowledge" claims lost their `secs(w) == figure or` branch
  (d5056ce). The user's point: an `or` in a check makes it only as strong as its weaker branch,
  and nothing had established which that was. A failing assertion is replaced by the intended
  test, never widened.
- zk-fiat-shamir-with-aborts.md is a PROSE_FILE (5154b04): §5.4's commitment 0.275 s, sampling
  1.26 s at 300 ns a coordinate (4.6 times the commitment), attempt 1.53 s, fold 4.18 s at
  α = 12 and 11.4 s at α = 6 at the note's own parameters (the §5.3 rows in dimension 128,
  N = 2^22); the user proof it is compared with is two to four dozen rank-13 steps over Pasta,
  23.9 to 47.8 s at the page's step plus accumulation prover (0.957 s a step); §5.6's attempt
  about 1.5 s. The old "about a second / three seconds / eight to ten / about ten seconds" had
  assumed ~200 ns sampling and no accumulation prover. Claims guard §5.8's "seconds" and §5.4's
  "noticeable fraction" (4.18 s is a sixth of 23.9 s). pasta-proof-size.md's "about five seconds
  a row" is the planner's runtime, no model figure, left as is.
- Every claim's predicate on its own line aligned under the text (30217a7). Python layout rule
  from the user: blank lines between functions and around compound statements inside one, none
  at the start of a block; ruff format next session.
- The decider sentence (c907d44): the Pasta variants, Kishu and BitZ 7.09 to 26.7 ms, Pedersen-IPA
  41.9 to 384, WHIR over Goldilocks with Poseidon 4.76 to 30.8, WHIR over Pasta 22.4 to 158, as
  figures; a claim holds the 64/128-bit lattice, binary-field and BLAKE3 hash-based deciders
  under 10 ms. The "a few milliseconds" at the hashes section was already claimed.
- The frontier table's units are in each cell (816a30a): headings Proof size, Prover,
  Accumulation prover, Decider, Transaction, Accumulator memory, Accumulation, Merge circuit;
  cells "x bytes", "x ms" or "x 64‑bit muls", "x atoms", "x gates"; the JS heading update and
  the `.unit` rule removed. NOT yet looked at in a render.
- STATE: main at 0817985 plus this entry; unpushed from 0151e0a on. Artifact v129. PENDING: ruff
  format over pareto-model.py; a look at the table's render; the user's review of the soundness
  statements, then Theorem B; the zk-fold levers; re-render keep/tachyon-statements.md; the
  Pasta-claims recovery row's BLAKE3 figure; the user to ask Quang about the QROM proof and
  CertifiedJL's roadmap; whether the prose seconds should be at millisecond resolution.
- 14:59 UTC, addendum: the page's fmtMs drops trailing zeros (8.9 ms for 8.90: `Number(v.toPrecision(3))` before `toLocaleString`); the model's sig() is right. Fix next session: keep toPrecision's digits, separators only for the whole-millisecond branch.

## 2026-11-16 19:27 UTC: ruff at 100; the millisecond formatter; the table render; the PCD-headers eyebrow

- The user pushed through d22b90f.
- fmtMs keeps a trailing zero (7934d2a): `v.toPrecision(3)` alone below a second. The frontier
  table's render checked in headless Chrome: units in each cell, rows at most four lines.
- pareto-model.py is formatted with ruff at line length 100 (ragu-pcs/ruff.toml; 719f51b), the
  user's choice from 88/100/120/150 with 3,136/2,598/1,984/1,607 changed lines; the page is
  byte-identical before and after. Ruff's choices stand even where odd (a subscript split as
  `CLAIM_BYTES[` / `variant` / `] + K * 128`): the user wants no hand-edits of the formatter's
  output. No format option affects such splits (the options are exclude, preview, indent-style,
  quote-style, nested-string-quote-style, skip-magic-trailing-comma, line-ending,
  docstring-code-format, docstring-code-line-length; preview and skip-magic-trailing-comma were
  tried, same result); only the line length does. After editing the model run
  `ruff format pareto-model.py`; `ruff format --check` passes. The other Python files under
  ragu-pcs/ are not formatted yet, though ruff.toml covers them.
- The PCD-headers eyebrow (61d2681): the post-quantum rows sit at header 2, since the header
  boxes select Pedersen-IPA's rows only, so the header-4 post-quantum rows are dominated within
  their families and pruned (9,606 post-quantum rows, all at 2; Pedersen-IPA 178 at each of 2, 4
  and 9), and a Tachyon or recovery transaction reprices them at 9 with 448 bytes more. The
  eyebrow had explained the first half; it now refers to the Proof bytes section, which says
  both, and a claim guards the headers. Control eyebrows refer to the text rather than explain
  (the user).
- The width question: at 120 ruff would avoid the CLAIM_BYTES split but not a `math.log2(` /
  `circuits` / `)` split caused by a long trailing comment; at 150 neither. The user: leave it
  at 100.
- STATE: main at 61d2681 plus this entry; unpushed from 7934d2a on. Artifact v132. PENDING: the
  user's review of the soundness statements, then Theorem B; the zk-fold levers; re-render
  keep/tachyon-statements.md; the Pasta-claims recovery row's BLAKE3 figure; the user to ask
  Quang about the QROM proof and CertifiedJL's roadmap; whether the prose seconds should be at
  millisecond resolution; the other Python files under ragu-pcs/ through ruff, if wanted.

## 2026-11-16 19:59 UTC: the PCD header is one application-level setting

- The user: the PCD header is an application-level choice set by its circuit tree, so a row at
  one header is not an alternative to the same row at another and cannot be dominated by it;
  each header entry is a packed Pasta field element for every scheme alike (the native field
  would not be a fair comparison). Done (77680dd): the rows carry no header and are priced
  without one (every byte formula lost its 2 · H · 32 term; Pedersen-IPA's size() is called with
  H = 0, so it has one row per configuration, 178 instead of 534); the control is a radio of
  PCD_HEADERS = (2, 4, 9), default 2; the page adds the chosen header's bytes to every row
  (HEADER_ELEMENT_BYTES = 64: one packed Pasta element in each of the left and right child's
  copies, the two headers that a merge's instance carries in ragu-size-model.py); a Tachyon or
  recovery transaction forces 9, greys the radio out, and the user's choice returns afterwards
  (userHeader / lastForced in the page). The new rows were checked against the old page: each
  of the 9,784 rows is its old header-2 twin less 128 bytes, and the recursive rows' memory,
  which is their proof, is also 128 less and is left without the header on the page (at most
  576 bytes). The eyebrow refers to the Knobs section, whose new first paragraph explains the
  header; the per-family "header size" knobs are gone; the figures in the text are without a
  header unless they say otherwise, which the note's two least-proof figures do (kept at header
  2, as their sentence says). Three kbytes figures fell by one. PEDERSEN_FUSE_RANK stays (the
  user: fine as is).
- STATE: main at 77680dd plus this entry; unpushed from 7934d2a on. Artifact v133. PENDING as
  before: the user's review of the soundness statements, then Theorem B; the zk-fold levers;
  re-render keep/tachyon-statements.md; the Pasta-claims recovery row's BLAKE3 figure; the user
  to ask Quang about the QROM proof and CertifiedJL's roadmap; whether the prose seconds should
  be at millisecond resolution; the other Python files under ragu-pcs/ through ruff, if wanted.
- 20:13 UTC, addendum: the Booleanity draft ("Efficient Booleanity Checking via Structured Modular Projections", 2026-09-23) and its extracted text moved from work/ to keep/bool-checking-private-main3.pdf and .txt, at the user's request; the 2026-10-15 entry names the old paths.

## 2026-11-16 20:53 UTC: the Booleanity exposition, on a private branch

- The user: the Booleanity-by-projection technique "sounds plausible but it's exactly the kind of
  thing I would want a Lean proof of", and the draft PDF is obviously AI-written (Quang said it
  needed a lot of cleanup); so an expository book chapter that teaches how it works, for
  cryptographic engineers without a lattice background, with the background results
  referenced (Cauchy–Schwarz, Johnson–Lindenstrauss, Markov, Schwartz–Zippel, Thaler's book
  for sum-check and multilinear extensions; Fiat–Shamir assumed known). The draft is
  unpublished and the user will not scoop or preempt Quang and his colleagues, so the chapter
  lives on the branch `booleanity-exposition` (3225356: book/src/proof-systems/
  booleanity-by-projection.md and its SUMMARY.md line), kept in the private repository even
  when the rest is published, until they agree. Its last section lists the proof obligations
  in dependency order as the Lean targets. CertifiedJL's repository is private (404), so the
  chapter names it without a link; VCVio is linked.
- Rendering gotcha: with mdbook-katex, `\tilde` renders a literal `~` inside KaTeX's spans, and
  mdbook's Markdown pass then pairs the tildes as strikethrough ("unclosed HTML tag `<span>`
  while exiting Strikethrough"); `\widetilde{...}` renders as an SVG and is safe. The included
  notes use no `\tilde`.
- The user cut a paragraph naming "a multiple of q in [0, q) is zero" as Lemma L from the
  chapter as trivial ("AIs often have difficulty deciding which things humans will consider
  trivial"); the soundness note still has Lemma L as its own shared lemma.
- STATE: main at this entry; unpushed: the Booleanity draft's move (1e4cf45) and this entry;
  the branch booleanity-exposition at 3225356 is unpushed too (the user decides where it goes).
  Artifact v133. PENDING as before.
- 01:42 UTC, addendum: the chapter revised on the branch after the user's reading (its commit amended, now db32ab6): "Composing the layers" is a subsection; it recalls the lower-tail estimate where $z$ is used, explains that $z$ is the argument of $Z_c$'s distribution function (not a chosen ratio: the one-layer bound holds for all $z$ at once, $z = 0$ being the zero-output event of probability $K^c$), defines stochastic dominance with a link and the coupling in plain words (quantile functions of one uniform); a figure of the law of $Z_c$ at widths 43 and 40 (density, and the distribution function on a log scale), drawn by ragu-pcs/scripts/zc-figure.py into book/src/proof-systems/booleanity-zc.svg, with a caption; the Lemma L paragraph cut as trivial; sentences split after the long-sentences check. The user left for a meeting with the chapter open in Firefox. STATE: main at this entry (unpushed from 1e4cf45 on: the draft's move and two notes commits); branch booleanity-exposition at db32ab6, unpushed, the checkout left on it. Artifact v133.
- 02:01 UTC, addendum: the chapter's commit amended again (now 1033e1f on booleanity-exposition): the composition subsection is four paragraphs with the figure after the one that defines $Z_c$; "the ratio" is named as the energy ratio $E'/Q$; the magnitude paragraph says the zero-ratio atom is the floor of any certificate on this estimate, with the draft's within about a bit of it; the figure's labels have real subscripts and superscripts (shifted tspans from zc-figure.py's fmt()); every inline math span is on one source line (my first re-wrap cut spans at spaces; mdbook-katex does not join them; the check is an odd count of `$` on a line without `$$`), and §3's display equations are back on their own lines inside the list items. The user asked, for n = 2^27, the valid range of r (the revealed coordinates) and its prover/verifier trade-off; answered in chat: r ≥ 156 from the terminal atoms alone at 2^-136 (K^r), 160 is near the floor, r barely moves either party's cost; the geometry at fixed r is the trade-off, and n enters through Theorem 1's cap on Q_0.
- 02:52 UTC, addendum: KISHU USES THE CONVENTIONAL BOOLEANITY SUM-CHECK, NOT THE PROJECTION (the user, after the shares and the recursion trade-off were computed). The Booleanity check is 22% of Kishu's step prover, 29% of its merge commitments, 10-15% of the accumulation prover, 12-16% of the transaction prover, 0.3% of the decider and 39% of the merge gates in the sum-check form at the page's rows (ranks 19 and 20); the projection form exists only from rank 23, where it saves 7% of the transaction at 0.8 ms more decider and twice the merge. In recursion each projection coefficient is a committed digit of the merge (26 word mults) against the 7.3 per bit the projection saves, so it is ahead only where 2^rank ≳ 3.6 V − 4.6 V_s − H (rank 23 at the draft's geometry); the widths are set by the error target and the first layer's V × S = (g c_1)^2 n, so geometry trades verifier description for prover memory only; one digit per coefficient is generous (regeneration and E-arithmetic per coefficient, ~100 digits). Ranks of 21 and up are too slow for a Zcash transaction (the user). So formally verifying the projection is NOT a blocker for Zcash's use of Kishu: the model's comment says so (ba6021a); the soundness note's Theorem B is restated for the sum-check form, error (4m+1)/|E| plus Akita's, no integer lift, with the projection form kept as Theorem B′ and its certificate recomputation marked not a blocker (9ca1aa1, amended); the chapter's §7 on the branch says the same (its commit amended). r at n = 2^27: floor 156 from the terminal atoms (K^r) at 2^-136, 160 near it; r barely moves either party's cost.
- 03:17 UTC, addendum: a cheaper Booleanity for Kishu was proposed and REFUTED against the Akita paper (ragu-pcs/work/akita.txt): taking the energy bound from Akita's own norm certification and checking the unweighted identity Σ s² = Σ s (one evaluation claim at (1/2, …, 1/2)) does not work, because Akita's range and norm checks (§6) cover the successor witness, the decomposed response, and the fresh source is bound only as a weak opening (Definition 10.22, a short unit times the source is short), so nothing certifies the committed table's integer energy; and a field identity Σ s² = v cannot bound integers by itself. Smallness per entry is certified by a vanishing identity per entry under random weights, i.e. the conventional check; the group-sum range check the user floated has the same gap (small field sums do not lift; x² − x − 1 = 0 has roots when 5 is a square). The saving left is batching the Booleanity identity into another sum-check over the same table (the step's constraint check). The chapter's §7 records both the recursion trade-off and this dead end (branch commit 87aecbc). The pinned Akita checkout's book (mdbook-katex + mermaid) renders with `mdbook build --dest-dir` inside the nix shell to ragu-pcs/work/akita-book/ (opened once in Firefox; the user reloads); its chapters on the fold, the sum-check stages, security and binding are the relevant ones; main's book may be newer, which needs the user's fetch.
- 03:28 UTC, addendum: the user fetched the Akita checkout; a worktree ragu-pcs/work/akita-main at origin/main (d50f700, 2026-11-12) has its book rendered to ragu-pcs/work/akita-book-main/ (41 chapters differ from the pinned 60b82bc; the pinned render is ragu-pcs/work/akita-book/). The book's Jolt chapter is Jolt proving Akita's verifier, not Akita as Jolt's commitment. Answered in chat: (1) Akita's "optimized digit range check" (§2.3, §6.1) is not the projection: it is the per-entry vanishing check of the alphabet, made cheaper by the involution w -> w(w+1) that halves the degree and by a product tree of degree-2/4 sum-checks, still under random equality weights; the projection replaces the weighted per-entry check by an unweighted integer identity plus a sketched norm bound. (2) Lookups for Booleanity: for a bit-valued committed table a lookup into {0,1} is no cheaper, since logUp needs committed inverses (a field element, ~22 Akita digits, per bit) plus a per-entry product identity of the same shape as s(s-1) = 0, or LogUp-GKR with a log^2-round verifier in the merge; the real form of the idea is a word-level arithmetization (k-bit words committed as one digit each, ranges and bit operations by lookups, Lasso-style small committed values suiting Akita), a Jolt-style frontend rather than Kishu's, whose lookup verifier must be accumulated in Ragu's PCD to pay, as keep/lookups-in-ragu.md concluded (logUp is the argument to emulate; accumulation is a Ragu design change).
- 03:38 UTC, addendum: the user asked whether q = 2^64 − 59 can be exploited, e.g. a 64-bit value as i + j with i any field element and 0 <= j < 59. Answered: j needs 60 values (0 <= j <= 59) to reach 2^64 − 1, since i <= q − 1 = 2^64 − 60; any field element is already an integer in [0, q), so the range of i costs nothing and only j (6 bits, excluding 60..63) and carries need Booleanity; and 2^64 ≡ 59 (mod q) turns 64-bit carries into a + b = c + 59·carry in F_q and 128-bit limb products into a·b = lo + 59·hi, both with free-range field elements lo, hi. So a word-level arithmetization over F_q (non-native Pasta arithmetic in four 64-bit limbs, each a field element plus a 6-bit correction) would confine Booleanity to corrections, carries and genuinely bitwise values, commit about 112 Akita digits per Pasta value (4 × (22 base-8 digits + 6 bits)) against Kishu's 255 bits, cut the constraint work for field arithmetic from bit circuits to a few quadratic constraints per limb product, and give four limb claims instead of eight; its soundness is elementary lifts with explicit bounds, with no decoupling (it sidesteps Theorem A). Canonical form: j > 0 only with i = q − 1, enforced by j·(i − (q−1)) = 0. A new frontend to price, not a change to Kishu as modelled.
- 03:49 UTC, addendum: the 64-bit-word frontend was NOT built: checked before pricing, the representation is unsound for arithmetic over F_q. The field identity a + b = c + 59·carry for a 64-bit addition also accepts (c − 59, carry + 1) and (c + q, carry), since the identity only fixes the integer relation modulo q and q is the word size; a 64 × 64 -> 128-bit split a·b = lo + 59·hi has one passing lo for every hi, so it fixes nothing. Disambiguation needs sub-word information, i.e. range-checked decompositions, which the free range of a field element does not compose with (i = low + 64·high is not unique without bounding high). So the only sound word-level route is the standard small-limb emulation already on the page as the Goldilocks variant (a 64-bit field is a 64-bit field; 1,100 gates a Pasta multiplication without lookups), dominated by Kishu. Verified numerically. FOUND MEANWHILE, to raise with the user: Kishu's recovery cost still charges 255 digits per Pasta multiplication "no quotient", the 2026-11-12 accounting for the DECOUPLED design (claims native over Pasta); since 2026-11-14 Kishu is design B (F_q claims, limbs, Zinc+'s integer PIOP), under which a·b = k·p + r needs the committed quotient as BitZ's 510 bits do. With 510 digits a multiplication the recovery circuit is 8.4M digits instead of 4.7M (see the chat for the transaction figures).
- 03:56 UTC, addendum: the user's refinement, a free-range 64-bit word plus 32 Booleanity checks implicitly checking the other 32 bits, for 32 × 32 -> 64-bit products: also not sound. W = L + 2^32·H with L the checked low half leaves H free: a fake L + 1 has a passing H = (W − L − 1)·2^−32 mod q, a 64-bit field element; and a·b = W with a 32-bit and W free pins b only modulo q, so any b passes. A field identity pins an integer relation only when every term is bounded within one modulus; the free range of one element never bounds a term scaled by 2^32 or by an unbounded factor. The one sound use is a product of two already bounded 32-bit values, which is below q (margin 2^33) and so needs no range check on its output; but in a limb multiplication the products are single constraints anyway, and the cost is the carries' and limbs' bounds (about 1,000 bits a Pasta multiplication, the Goldilocks-style 1,100), worse than the integer PIOP's 510 bits. Numerically checked. No frontend built.

## 2026-11-19 02:37 UTC: Kishu's Pasta multiplication carries its quotient; the Flock zk rows' history

- The user agreed: Kishu's claims are in the 64-bit field, so a Pasta multiplication is BitZ's
  integer relation with the value and the quotient committed, 510 digits, not the 255 of the
  decoupled design (f419f57). The recovery circuit is 8.4 million digits as in BitZ; per note
  on one core Kishu takes 0.736 s at rank 21 (was 0.426 s at rank 20), 3.40 s with zero
  knowledge (was 2.55 s); two tachyactions 0.326 s (was 0.217 s; BitZ 0.214 s), sixteen
  1.47 s. The page's arithmetization paragraph says so; the model's comment likewise. Checked
  from the archive: figures and claims pass, the page identical. Artifact v134.
- OPEN, the same origin: the merge's arithmetic is still priced at 255 digits a multiplication
  (the Poseidon permutations, which are Pasta arithmetic, so 510 by the same argument; and the
  sum-check, claim and Booleanity-verifier multiplications, which are over E = F_q[u]/(u^2 - 2),
  where an F_q product is a 64-bit value and a 64-bit quotient, 128 digits, and an E product
  three of them, about 384). A scratch run with those (Poseidon at 510, E at 384) moves the
  Kishu rows a little further: recovery 0.853 s, two tachyactions 0.361 s, rank-17 merge
  2.6 million digits under BLAKE3 and 10.0 million under Poseidon, and the claim that Kishu's
  Poseidon merge prover is about half the 64-bit variant's fails (0.65 to 2.5 of BitZ's). For
  the user's decision.
- The Flock/Binius proof sizes the user remembered were the 2026-11-11 rows (d3c6211): the
  recursion rows' zero-knowledge variants then priced the full mask into the final proof
  (124,480 B at rate 1/64, floor 128, no grinding, against 92,720 plain). Commit 58e60ae
  (2026-11-12, zero knowledge paid once per transaction at the handoff) made the recursion
  rows' zk proofs equal the plain rows, since the public merges and the decider's proof are of
  public data and only the user's handoff is masked, so that row became 89,023 B (now 88,895,
  the header removed). The ARC rows keep the mask in the decider's proof: at rate 1/8 the
  surcharge is 32 kbytes after Ulrich's witness-size mask (6ef6bea). Otherwise the family's
  minima have moved by at most 4% since 2026-11-11 (list size 2^7 -> 2^8 from his updated
  optimizer; the header).

## 2026-11-19 04:43 UTC: Kishu's merge arithmetic native over the 64-bit field; both hashes as variants, each a family

- BITZ'S ARITHMETIZATION, read from the paper (§1.2, §2.1, §2.4, §5, §7.4) for the user's
  question whether it can express 64-bit-field constraints or is purely bit-oriented. BitZ is a
  PCS, bit-oriented only in how it commits (every witness element as its bits, pay per bit) and
  in how it proves the one final linear claim (bits in the exponent of F_2^128). Constraints
  live in a separate PIOP over the ring itself (R1CS, CCS, AIR or Zinc+'s UCS), native, one
  constraint per multiplication, no bits; for a finite field the fingerprinting step is skipped
  (§5 step 2). Every witness element of that PIOP is committed, so native F_q arithmetic costs
  64 committed bits per wire and 128 per E wire, with no quotient ("both schemes commit to all
  the bits of witness elements separately", §7.4). The 510 for a Pasta multiplication comes from
  writing Pasta arithmetic as an integer relation with a committed quotient so that the PIOP can
  run over a small random prime (Zinc+'s v - u^2 + n mu in (X - 2)); §5 also allows a PIOP
  natively over F_p at 255 bits a wire with a 255-bit sum-check field. For Kishu the quotient is
  forced, since its PIOP field is F_q. The user's R1CS analogy (bits only at the inputs and
  outputs) holds for constraints and fails for the commitment, which would hold only for a
  layered, GKR-style PIOP that Kishu does not have.
- THE MERGE RE-PRICED (f4abfe8; artifact v135): `frontend_merge_digits` charges the sum-check,
  claim and Booleanity-verifier multiplications at E_MULT_DIGITS = 128 (was BITS_PER_VALUE =
  255), and the Poseidon option as Poseidon over F_q at width 12, rate 8, with the x^3 S-box (3
  does not divide q - 1): R_F 8, R_P 42 at 128 bits with the margin from the user's fork of
  calc_round_numbers.py, which reproduces the Goldilocks 8/22 and the 65-bit prime's 8/43 rows
  exactly; 138 S-boxes, 276 multiplications a permutation at 64 digits each (was Pasta's
  Poseidon, 72 x 255 per atom). At rank 17: BLAKE3 1.6M digits in 13 circuits, prover 5.7e7 (was
  2.1M, 17, 7.5e7); Poseidon 1.9M digits, 6.6e7 (was 4.4M, 1.5e8); Kishu's merge prover against
  the 64-bit variant's 200x under BLAKE3 (was 150x) and 4.0x under Poseidon (was about 2x);
  against BitZ 3.3 to 3.8x (was 1.4 to 2.9x); recovery with zk 3.07 s (was 3.40), two
  tachyactions 0.291 s (was 0.326), with zk 1.56 s (was 1.76); the recovery figure 0.736 s at
  rank 21 unchanged. Rows now exist at rank 13 under BLAKE3 (the per-circuit claim 8,000 digits
  of 8,192; 10,365 circuits) and at rank 14 under Poseidon (9,300). Claims restated: the ranks;
  "Poseidon merge prover about half the 64-bit variant's" became a figure (4.0) with a claim
  that it is smaller. The recovery paragraph's hand-written "4.7 million digits", missed by
  f419f57, is now the generated 8.4 million. The comment introducing the family no longer says
  the claims go through the decoupled commitment.
- BLAKE3 AGAINST POSEIDON FOR KISHU'S MERGE (the user's point): the digit measure charges no
  constraints, and the merge circuit's own PIOP is not charged (as for BitZ), while a BLAKE3
  compression is 7,904 constraints (one relation per 32-bit addition, one per XOR bit;
  BLAKE3_CONSTRAINTS) against a Poseidon permutation's 276, so constraints favour Poseidon. On
  digits Poseidon is 17% more per absorbed byte; the break-even is a constraint at about a third
  of a committed digit (a digit about 56 word multiplications: Ajtai 24, Booleanity 10, the
  fold's sum-checks 22; a degree-2 sum-check row 18 to 24), right where a plausible estimate
  sits. The user: too close to call, many modelling choices could sway it either way, so both
  hashes are kept as variants of Kishu, and the arithmetic-hash option must show both; the
  dominance checking and the frontier collapse then do the right thing. The former sentence
  "with a conventional hash the merge is cheaper here" is gone from the page and the comment.
- EACH VARIANT A FAMILY (8e85e06; artifact v136): the Poseidon rows are the family
  `bits_q64_poseidon` ("Kishu ..., Poseidon (draft)", gold: #c9a000 light, #ffd740 dark), the
  BLAKE3 rows stay `bits_q64` ("..., BLAKE3 (draft)"), so each has its own colour, checkbox and
  per-family frontier; the page's filter shows the BLAKE3 family under either option and adds
  the Poseidon one under the arithmetic-hash option, the prune key already included the policy,
  and `kishu_best` takes the better of the two for the figures that quote Kishu's best row.
  The family list is in three sections separated by rules (`GROUPS` in the template):
  Pedersen-IPA; the lattice-based schemes (the five Akita variants, the two Kishu variants, the
  binary groups); the hash-based ones. Checked in a headless-Chrome render
  (work/shot-families.png).
- FOUND, NOT CHANGED: Kishu's transcript and instance bytes use pasta_q64's 32-byte claim width
  (`akita_absorbed_bytes("pasta_q64")`, `CLAIM_BYTES["pasta_q64"]`), whereas Kishu's sum-check
  messages and evaluation claims are E values of 16 bytes (plus 32 bytes of limb values per
  circuit's Pasta claim), so its absorbed bytes and claim bytes are overstated by up to 2x. Also:
  a 64-bit decomposition of an F_q element is not canonical for values in [q, 2^64), harmless
  inside field arithmetic, needing a cheap range check where a wire's bits are hashed. For the
  user's decision.
- STATE: main at 8e85e06 plus this entry, unpushed from 1e4cf45 on (the user pushes); the
  branch booleanity-exposition at 87aecbc, unpushed. Artifact v136. PENDING as before: the
  user's review of the soundness statements, then Theorem B; the zk-fold levers; re-render
  keep/tachyon-statements.md; the Pasta-claims recovery row's BLAKE3 figure; ask Quang about
  the QROM proof and CertifiedJL's roadmap; the other Python files through ruff, if wanted.
- 05:08 UTC, addendum: BitZ and Flock first in the family list's hash-based section (b7a94f2). Then the three items found, in 784d422 (artifact v138): Kishu's transcript and claims at E's 16 bytes (`CLAIM_BYTES["kishu"]`, `ATOMS_PER_COMMITMENT["kishu"]` = 8, a pseudo-variant outside VARIANTS), the Booleanity sum-check's 1,744-byte transcript absorbed with them, and under BLAKE3 a range check against q on every prover-supplied word before hashing (RANGE_CHECK_DIGITS = 63: 57 products for bits 63 to 6, about five for the low six, one constraint; the images are instance data and need none; Poseidon absorbs field elements and needs none). Effects: the per-circuit claim 4,400 digits under BLAKE3 and 4,900 under Poseidon (were 8,000 and 9,300), so Kishu has rows from rank 13 under both hashes (402 circuits at rank 13 under BLAKE3) and the rank claim is restated; rank-17 proofs 80 kbytes; the Poseidon merge 1.7M digits, prover 6.1e7. The family list's swatch box now takes the label's first line, level with the checkbox (the user's report; checked in a render). FOUND, NOT CHANGED: Kishu's decider is priced with the Pasta-claims factor of four (`akita_verify("pasta_q64")`) although its claims are E values at the 64-bit profile, where the Goldilocks entry applies; and its opening bytes come from the Pasta-claims plan (`akita_bytes("pasta_q64")`), whose extra bytes over the Goldilocks plan are Pasta-width elements. For the user's decision. The user asked how a claim's prose is kept in sync with it: it is not, mechanically; the claim's text is a label, the sentence has no marker, and the correspondence is by reading (answered in chat, with a marker-and-hash mechanism proposed).
- 05:27 UTC, addendum: CLAIMS TIED TO THEIR SENTENCES (7fc1cf4; the user: "tie claims to a short name in the same way we do for figures"). `claim(name, text, holds)`; the guarded sentence sits between `<!--claim:NAME:HASH-->` and `<!--/claim-->` in the page or a note, HASH the first six hex digits of SHA-256 over the claim's text (several claims on one sentence: names comma-separated, the hash over their texts joined); the run fails on a stale hash, a failed claim, a claim with no marker in any file, a marker naming no claim, or unbalanced markers; `--fill` writes the hashes and prints each reworded claim's text; `--figures` lists the claims too. Sixty-three claims (one was a single-line call the first pass missed), fifty-eight sentences: 41 in the template, 7 in pasta-proof-size.md, 2 in the zk note. The mapping from claim to sentence was made by a scratch keyword-and-neighbouring-figure matcher over the prose, then reviewed by hand; the scratch scripts are not kept. REGENERATING.md describes the markers. FOUND BY THE MAPPING: pasta-proof-size.md's BitZ sentence still said "nothing with Pasta claims has both a smaller proof and a cheaper prover", which Kishu falsified on 2026-11-15 when the page's copy was restricted to the hash-based families; it now matches the page. Then (d2ef4f5; artifact v139): the family list under the headings Pre-quantum, Lattice-based and Hash-based in place of the group's eyebrow and the two rules, and the labels shorn of "(not post-quantum)", ", hash-based" and ", lattice" (the user). Checked in a render.
- 05:30 UTC, addendum: KISHU ON THE GOLDILOCKS PLAN (9f77d80; artifact v140): its opening bytes and decider follow the Goldilocks variant (`akita_bytes("goldilocks")`, `akita_verify("goldilocks")`, log_len in that variant's 22-digit coefficients, its rank scale and image share), since Kishu's claims are at the 64-bit profile in a small extension as that variant's are; the Pasta-claims plan had Pasta-width elements and the decider the Pasta factor of four. Rank 17: proof 69 kbytes (was 80), decider 2.26 ms (was 6.55), 7.1 times smaller than BitZ's proof (was 6.1), the Pasta-group decider range from 2.22 ms; under Poseidon Kishu's proof is 10 kbytes smaller than the 64-bit variant's (new claim kishu_poseidon_proof_smaller on that sentence's marker). The two items found and not changed earlier today are thereby closed. STATE: main at this entry, unpushed from 1e4cf45 on; artifact v140. PENDING: constraint costs for the bit arithmetizations (not charged anywhere); the 2026-11-14 open modelling questions; the Pasta-claims recovery row's BLAKE3 figure; the zk-fold levers; the user's review of the soundness statements.
- 05:38 UTC, addendum: the frontier table sorted every column as text since the units moved into the cells (816a30a): the sort now takes the leading number and ignores the unit (bf12dd4; artifact v141; the user's report).

## 2026-11-19 13:06 UTC: constraint costs charged; Kishu's multiplication by two routes; the Pasta arithmetic column; the 3D default view

- THE PASTA COLUMN (ad3a842; the user: "native" conflated support for Pasta claims with the
  efficiency of Pasta arithmetic, and "claims are over Pasta" overstated it too). Setting
  efficiency aside, every scheme can prove statements about Pasta values, so the dominance
  requirement is a threshold on cost. The table's column is now "Pasta arithmetic", per row:
  native (a gate over Pasta's field), relation (integer relations over committed bits with the
  result, quotient and carries committed and no committed intermediate wires), limbs (limb
  products as committed wires in another field), bits (a Boolean circuit); PASTA_ARITH in the
  model sets it per family, the Kishu and BitZ rows add their route; the dominance rule counts
  native and relation (PASTA_COUNTS); the page's "Pasta as a requirement" section says so, and
  that how efficiently each realisation performs is what the transaction measure's application
  costs show. The claim pasta_native_list was restated, and its marker's hash went stale and
  was refilled, as designed.
- KISHU'S PASTA MULTIPLICATION IS NOT ONE RELATION (found while counting constraints): BitZ
  checks a b = k p + r over the integers by projecting it to a random prime, which needs
  evaluation claims modulo that prime; Akita gives claims in one fixed field, and modulo a
  fixed q the relation is unsound (the prover chooses r). Two sound routes, BOTH modelled as
  rows of each Kishu family (the user: "both ... the point of the comparison matrix is to
  compare"), a `route` attribute in the label, the prune and dedup keys and the Pasta column:
  limbs, the relation checked coefficient by coefficient over 29-bit limbs that are linear in
  the bits (virtual), 17 coefficient constraints of up to 9 product terms each bounded below
  q/2, a committed carry of 34 bits per coefficient, so 1,088 digits and 98 product terms a
  multiplication; fingerprint, BitZ's check in three PIOP instances over random 52-bit primes
  (a nonzero 510-bit integer vanishes modulo one with probability about 2^-43; three
  independent instances for 128 bits), 510 digits a multiplication, and per step about
  sqrt(2^rank) integer column sums per instance from BitZ's tensor split, each exact as one
  claim in F_q (below q/2), committed as 61-bit digits (265,000 digits a step at rank 21) with
  three more transcripts for the merge above. The fingerprint route is about half the limb
  route's prover on arithmetic-heavy circuits and heavier in design and verifier; the user had
  guessed the opposite. BitZ keeps its single relation (its commitment proves integer claims
  exactly). The soundness note does not yet state either route's lemmas: the limb route's
  coefficient identities (Lemma L at each coefficient, the carry ranges) and the fingerprint
  route's exactness of the column sums; to add when the user reviews it.
- CONSTRAINT COSTS CHARGED (0dd5f71; the user: "let's charge the constraint costs"). For Kishu:
  a product term of a constraint costs CONSTRAINT_TERM_WORD_MULTS = 9.8 word multiplications
  (the measured Booleanity sum-check's per-entry rate, a degree-2 relation under eq weights;
  asserted equal to BOOL_CHECK), a nonzero of a linear form 2 (small or power-of-two constant)
  or 4 (field constant) as one extension-element multiplication in the matrix-evaluation
  phase, linear forms over word entries (the table laid out by bit position, a word's
  evaluation a batch of column claims). Per component (terms, nonzeros): an XOR bit (1, 4), a
  32-bit addition (1, 4) with 33 bits, a 64-bit addition two halves (2, 8) with 66 bits since
  a 64-bit sum can wrap modulo q (BLAKE2B_BITS_KISHU 50,944), BLAKE3 (7,904, 31,616), BLAKE2b
  (26,368, 105,472), a Sinsemilla chunk its 1,013 products plus two selected coordinates
  materialized as 510 committed bits with one 1,279-nonzero linear constraint each (otherwise
  a 1,024-bit linear form enters every limb product), the reductions (4,000, 12,000), Poseidon
  over F_q (276, 13,800 field nonzeros: about fifty state words per form after the partial
  rounds' layers), range checks (63, 189), an E multiplication (3, 12), a bit gate (1, 3).
  The application's PIOP work per application and route is PIOP_WORK, exported as DATA.piop
  and added by the page's txWork and the model's tx_work (recovery: 0.0120 s by limbs,
  0.00409 s by fingerprint on one core); ZINC_PIOP_PER_DIGIT is gone. The merge: its own
  constraints' PIOP (now in the accumulation prover, 88aa22a, after the user's question what
  "prover work" means: the merge's commitments alone), its own sum-check transcript absorbed
  by the merge above (four E elements a round, log2(digits) + 1 rounds) and the child's
  transcript verified (four multiplications a round); an application step pays its
  transcripts' absorption and verification in the merge above and, by the fingerprint route,
  its column sums (kishu_step_overhead_digits). The circuits-per-merge fixed point measures
  the marginal circuit at six against five, since at two against one the merge's own
  transcript gains a round. With commitments and constraints charged, per 64 bytes absorbed,
  BLAKE3 costs 670,000 word multiplications and Poseidon over F_q 650,000, within 3% (claim
  hash_within_quarter); both stay as variants. The page documents the BLAKE3 accounting (the
  user asked). Results at rank 17 under BLAKE3: merge 1.9M digits in 15 circuits (was 1.6M,
  13), prover 6.6e7, proof 69 kbytes, decider 2.33 ms; the recovery circuit 17 million digits
  by limbs and 8.5 million by fingerprint; best rows: recovery 0.781 s at rank 21 by
  fingerprint (was 0.736 by the single relation), with zero knowledge 3.90 s, two tachyactions
  0.385 s at rank 20 with Poseidon by fingerprint, sixteen 1.56 s; Kishu's merge prover 170x
  the 64-bit variant's under BLAKE3 and 3.5x under Poseidon; 2.9 to 3.3x BitZ's.
- THE PAGE (5730da6, 0f55a46): the 3D view is the default, camera eye (-1.25, -1.25, 1.0) at
  the corner where bytes and both measures are smallest, bytes receding to the right and the
  second measure to the left, perspective (the user: orthographic looked wrong as the default),
  with an "orthographic projection in 3D" checkbox in the View group; a swap button between
  the measure groups exchanges the second and third measures. The default axes stay
  accumulation prover and transaction prover with the recovery circuit, log, milliseconds.
- STATE: main at the commits above plus this entry, unpushed from ad3a842 on (the user pushes).
  Artifact v145. PENDING: the soundness note's lemmas for the two routes and the user's review
  of it; the 2026-11-14 open modelling questions (the Pasta-claims rows' claim-field sum-check,
  witness generation, the aggregator's opening, phone parallelism); the Pasta-claims recovery
  row's BLAKE3 figure; the zk-fold levers; constraint costs for the other families' merges
  (Ragu's PIOP is evaluation-based and in the claims already, but the hash-based rows' PIOP
  verifiers in their merges are not counted, as the BitZ paragraph says).
- 13:10 UTC, addendum: toggling the orthographic projection carries the live camera, so only the projection changes (0d5b4a4); the measure eyebrows shortened to "2D vertical axis" and "2D marker size, 3D vertical axis" with two lines reserved, since the swap column had made them wrap unequally (the user's report). Artifact v146.
- 13:20 UTC, addendum: the commitments-only measure is "prover commitment work" everywhere it is named (4bceec6; the user), the two rank claims restated with it and their marker refilled; artifact v147; unpushed from 4bceec6.
- 13:36 UTC, addendum: the user asked why the table never shows "relation, limbs": the two routes differ only in the application's cost, so under the transaction measure the fingerprint row dominates its limb twin (half the digits on the recovery circuit) and under any other third measure the rows are identical and both appear. Found on the way: the fingerprint route's per-step cost was charged on every step; now only on applications with multiplications (`route_step`, DATA.has_mults), so the routes tie on the path applications. The Pasta classes are a list on the page. Commits 4bceec6, 7c23f5a, b748596 and this one, unpushed; artifact v150.

## 2026-11-20 03:08 UTC: Kishu's zero-knowledge cost; the mask's width and the sampler; rounded Gaussians

- WHERE KISHU'S ZERO-KNOWLEDGE COST GOES (the user, late on 2026-11-19: "Kishu is paying a lot
  in tx prover cost for zk. can we improve it?"). The 3.90 s recovery with zk (rank 18,
  fingerprint route) is: the fold 1.39 s (the sampling 1.29 s at 300 ns a coordinate, the masks'
  commitments under the masked matrix 0.065 s, the fold's own merge 0.039 s); the steps and
  merges 2.50 s, 33 at 75.8 ms, against 0.777 s plain (5 steps at rank 21), since the masked
  rank factor 2.22 raises the Ajtai rate from 23.7 to 45.3 word multiplications a digit and the
  fold, which grows with the rank, pulls the optimum down to rank 18; the constraint PIOP 4 ms.
  Why rejection sampling (the user's question): flooding would need σ about 2^λ times ‖cs‖ and
  the rank with it; rejection sampling gives the exact centred Gaussian at σ = α‖cs‖ for
  M = exp(12/α + 1/(2α²)) attempts; a one-shot abort-free mask by a Rényi argument is a
  judgement call, not taken.
- THE COST OF A WIDER MASK (the user's question): each doubling of α adds one bit to the masked
  bound's log (39.2 / 40.2 / 41.2 / 42.2 / 43.2 at α = 6 / 12 / 24 / 48 / 96, against 27
  unmasked), so the rank factor is 2.11 / 2.22 / 2.33 / 2.45 / 2.56, the masked digit 43.4 /
  45.3 / 47.3 / 49.3 / 51.4 word multiplications, the slices a coordinate 8 / 9 / 9 / 9 / 10, the
  attempts 7.5 / 2.7 / 1.7 / 1.3 / 1.1, and the recovery with zk 6.09 / 3.90 / 3.31 / 3.00 /
  2.89 s at ranks 17 / 18 / 19 / 19 / 19. Bytes and the decider do not move. A sampler at
  100 ns gives 2.62 s (rank 19) and, with α = 24, 2.28 s. A transaction with four recovery
  inputs pays the fold once: 2.21 s a note at rank 19.
- THE MODEL (8d7efa7; artifact v151): `kishu_costs(K, circuits, rank, hp, check, floor, zk,
  route, alpha, sample)` returns a Kishu row's fields and the fold's parts (sampling, masks,
  merge), and the row loop takes its fields from it; `mask_rank`, `mask_length` and
  `mask_attempts` take α, `ajtai_per_coefficient` takes α; `kishu_zk_best(app, alpha, sample,
  count)` recomputes the page's zk rows at another width or sampler cost (the circuits stay,
  since the zk-layer merge's extra atoms depend only on the slices' rounded log, asserted) and
  `kishu_zk_optimum` minimises over MASK_ALPHA_GRID (4 to 1024 by quarter octaves) at
  SAMPLER_RATES page / fast / cheap / free (900 / 300 / 60 / 0 word multiplications, 300 / 100
  / 20 / 0 ns); `--figures` prints the per-application table (KISHU_ZK_ALPHA). The row data is
  unchanged (both pages' DATA parsed and compared; only the self-check list grew). The page's
  zero-knowledge section has the breakdown, the sampler, the α table and the sweeps, guarded by
  the claims kishu_zk_steps_over_fold, kishu_zk_rank_below_plain, kishu_zk_falls_with_alpha,
  kishu_zk_sampler_larger_lever, rounded_gaussian_negligible and alpha_choice_near_optimum.
  `th .sym` keeps α and β out of the table headings' uppercase, which rendered them as Latin A
  and B (the user's report; the µs fix of 96c8748 had gone with the microseconds).
- THE WIDTH THAT MINIMISES EACH APPLICATION'S ZK TRANSACTION (the user's question), with the
  recovery per note and the seconds at the optimum against α = 12:

  | application | 300 ns | 100 ns | 20 ns | free sampler |
  |---|---|---|---|---|
  | recovery | 181: 2.87 (3.90) | 181: 2.09 | 76: 1.54 | 64: 1.32 |
  | 4 recovery inputs | 181: 6.79 (8.84) | 181: 5.21 | 64: 4.09 | 32: 3.76 |
  | 2 tachyactions | 152: 1.51 (2.05) | 181: 1.06 | 64: 0.778 | 32: 0.697 |
  | 4 tachyactions | 304: 2.14 (2.83) | 108: 1.47 | 90: 1.13 | 45: 0.977 |
  | 8 tachyactions | 181: 2.97 (4.05) | 181: 2.23 | 64: 1.67 | 32: 1.51 |
  | 16 tachyactions | 108: 4.61 (5.93) | 108: 3.34 | 90: 2.64 | 45: 2.34 |
  | 1 path | 215: 0.567 (0.801) | 256: 0.388 | 90: 0.252 | 90: 0.193 |
  | 2 paths | 128: 0.824 (1.17) | 152: 0.535 | 128: 0.354 | 64: 0.282 |
  | 4 paths | 256: 1.16 (1.63) | 256: 0.804 | 90: 0.533 | 90: 0.415 |
  | 8 paths | 128: 1.75 (2.45) | 152: 1.17 | 128: 0.807 | 64: 0.664 |
  | 16 paths | 215: 2.57 (3.44) | 256: 1.85 | 90: 1.31 | 90: 1.07 |
  | 64 paths | 215: 6.13 (7.85) | 90: 4.76 | 76: 3.71 | 38: 3.39 |

  The optima are high (the user: "much higher alphas than I expected") because each attempt
  samples and commits the accumulator's K·2^rank digits, six steps' worth, while a doubling of
  α costs about four percent on each step's digits, and because the measure counts the user's
  prover only: the rows term on every public merge (the matrix is shared), the masked
  accumulator's tenth slice from α = 64 (the transfer and the aggregator's range checks) and
  the memory are outside it. Even a free sampler leaves the optima at 32 to 91, since each
  attempt still commits the mask. The minimum is shallow: within two percent from 76 to 860 at
  300 ns and from 32 to 260 at 20 ns for the recovery circuit. The user: about 80 is more than
  sufficient; checked, α = 80 is within 2.6% of the least for every application at every
  sampler rate (the claim alpha_choice_near_optimum). The page keeps α = 12.
- ROUNDED GAUSSIANS IN PLACE OF THE EXACT DISCRETE SAMPLER (the user's question: has it been
  considered, how hard, and the saving; papers in keep/ as 2017-1025.pdf, 2026-2583.pdf,
  2019-1011.pdf, 2008.03855v1.pdf, 2017-480.pdf, 10770212.pdf). Hülsing, Lange and Smeets (PKC
  2018, ePrint 2017/1025) put rounded Gaussians into Lyubashevsky's scheme and BLISS: the
  rejection lemma's analogue holds with the same M (their Lemma 3.1 and Theorem 3.1, σ =
  ω(‖v‖√log m)), the rejection rate unchanged; their AVX Box–Muller sampler takes 27,672
  cycles per 1,024 coordinates, 47,576 with its ChaCha20 randomness, on a 3.5 GHz Haswell (7.7
  and 13 ns); their §5.2 bounds the finite-precision loss by the Rényi divergence of order ∞.
  Jeudy (ePrint 2026/2583, October 2026), Theorem 3.1: with Sheppard's correction σ(s) =
  s − 1/(24s), the rounded Gaussian over Z^n at any centre is the discrete Gaussian of
  parameter s to a Rényi divergence of order a of 1 + 73an/(33177600 s^8) + o(s^-9); so the
  proof replaces the real rounded mask by the ideal discrete one at that loss, which at our s
  of 2^20.9 (α = 12) and N = 2^22 is below 2^-163: the rejection-sampling theorem and the
  simulation of the note's §4 are untouched. The remaining question is finite precision. The
  PKC 2018 bound is about 2τσ·2^-p a coordinate for p bits: at p = 53 and τσ = 14σ = 2^24.7
  that is 2^-27 a coordinate and 2^-5 over a fold of 2^22, enough for search-type security by
  Prest's order-a Rényi bound (ASIACRYPT 2017, ePrint 2017/480) but not for the simulation's
  closeness. The same 2^-27 is the fraction of coordinates that double precision leaves
  undecided between two integers (a coordinate's error is its size times 2^-53), one coordinate
  in 32 folds; refining those in higher precision, with a rigorous error bound on the double
  computation (the error from the uniforms' 53-bit truncation is about 2^-29 a coordinate by
  the Box–Muller derivatives, and a correctly rounded libm gives the evaluation's), makes the
  rounding exact and leaves no precision argument. COSAC (PQCrypto 2020, ePrint 2019/1011) is
  the other route, rejection from the rounded Gaussian to the exact discrete one at about two
  trials a sample, which needs an exp per trial. Karney's 300 ns is corroborated: Du, Fan and
  Wei (arXiv 2008.03855, Table 1) measured RandomLib's exact normal sampler at 2.1 to 3.5
  million samples a second on an i7-8550U. The saving, at 20 ns a coordinate (the measured
  rate with randomness plus the boundary check and scaling, MASK_CHEAP_SAMPLE_WORD_MULTS = 60):
  recovery with zk 1.80 s at α = 12 (rank 20) and 1.54 s at α about 76, against 3.90 s; what
  remains is the masked rank on the steps. Difficulty: low; a paragraph in the zero-knowledge
  note citing Jeudy, and the exact-rounding sampler as implementation work. The note's §5.4
  sentence that Karney's sampler or a high-precision CDT is the standard answer is now out of
  date; not changed, for the user's wording.
- STATE: main at 8d7efa7 plus this entry, unpushed from 8d7efa7 (everything through 3336531
  was pushed). Artifact v151. PENDING: whether to set α (80?) on the page and in the note's
  example; the note's §5.4 sampler sentence and a remark in its §5.6 that the transaction
  measure prefers a wider mask; then as before: the soundness note's lemmas for the two
  routes and the user's review; the 2026-11-14 open modelling questions; the Pasta-claims
  recovery row's BLAKE3 figure; the hash-based rows' PIOP verifiers in their merges.
- 03:30 UTC, addendum: THE PAGE'S MASK IS NOW α = 48 WITH THE 20 NS ROUNDED-GAUSSIAN SAMPLER (847ec5f; artifact v152; the user: "use α = 48 and 20 ns", after the comparison of 48, 64 and 80: the worst excess over each application's optimum across the four sampler rates is 6.5% at 48, 3.7% at 64 and 2.6% at 80, all at Karney's rate on the path-only shapes, and under 1% at 20 ns or free; 48 is the widest of the sweep's widths with nine slices a coordinate, 64 and 80 take ten, and its rows term on the public merges is 3% below 80's). MASK_ALPHA = 48 (rank factor 2.45, log β 42.2, 49.3 word multiplications a masked digit, 1.28 attempts), MASK_SAMPLE_WORD_MULTS = 60; KARNEY_SAMPLE_WORD_MULTS = 900 and NOTE_MASK_ALPHA = 12 keep the zero-knowledge note's §5.3 and §5.4 example as it was, under the note's own figure names note_mask_attempts and note_sample_ns (its figures did not move). SAMPLER_RATES are now page (20 ns), karney (300), fast (100) and free. Results: Kishu's recovery with zk 1.54 s a note at rank 20 (was 3.90 at rank 18): fold 0.336 s (sampling 0.162, the masks' commitments 0.133, the fold's merge 0.041), nine steps at 134 ms, 1.20 s; with Karney's sampler it would be 3.00 s at rank 19, at 100 ns 2.19 s; four recovery inputs 1.02 s a note at rank 21; two tachyactions 0.780 s (was 2.05); Akita with Pasta claims 149 s (was 167) and two tachyactions 4.25 s (was 5.86). The α table on the page is at the page's sampler: 6 / 12 / 24 / 48 / 96 give 2.41 / 1.80 / 1.59 / 1.54 / 1.54 s at ranks 19 / 20 / 20 / 20 / 20, so the claim kishu_zk_falls_with_alpha now says it falls to 48 and is within two percent at 96. The optima at the page's sampler are 64 to 130 (recovery 76, within two percent from 32 to 260), at Karney's 110 to 300, at 100 ns 91 to 260, free 32 to 91; the page's 48 is within 2.8% of every application's optimum at its sampler (2 and 8 paths are the worst) and 6.5% at Karney's (the claim alpha_page_near_optimum, at three and seven percent). The page's zero-knowledge prose now says the page's sampler is the rounded Gaussian and quotes Karney's as the exact alternative; "a Gaussian width of twelve times the norm" became the figure mask_alpha; the transaction-prover paragraph no longer says the sampling is the larger part, which the Pasta variants' masked digit now outweighs. The zk note's §5.4 sentence on Karney and the CDT is still to be reworded, and its §5.6 could say what the page chose. The per-application table of the 03:08 entry stands, with the "20 ns" column now the page's.
- 03:43 UTC, addendum: THE ZERO-KNOWLEDGE NOTE'S WORKED EXAMPLE IS AT THE PAGE'S PARAMETERS (b584a44; the user: "use the new parameters for the zk notes"). §5.3 now assumes weight-20 challenges in the accumulation matrix's ring dimension of 512 and α = 48: ‖cs‖₂ ≤ 2^17.3, σ ≈ 2^22.9, ‖z‖₂ ≈ 2^34.9, ‖z‖∞ ≈ 2^26.7, J = 9, masked β ≈ 2^42.2, masked rank 350 field elements (11.2 kbytes) by the (log β)² rule that §5.5 confirms at its bounds (Akita's estimator at 2^42.2 was started in the background at the end of the session, `cargo run --release --example pasta_rank -- 128 4194304 42.2 42.6 43.2` in work/akita-src, log work/pasta-rank-48.log; if it gives a different row count, the §5.3 row and note_masked_rows in the model should take it), padding ≈ 30K digits; the mask costs 2.45 times the rank, 9 times the witness, 1.3 attempts. §5.4: the commitment is N/d = 2^13 NTTs of size 512, 2^24.4 multiplications, 2^29.4 word multiplications, 0.232 s; the sampling 0.0839 s at 20 ns as a rounded Gaussian, an attempt 0.316 s, a fold 0.406 s (0.854 s at α = 12, 2.33 s at α = 6, 1.91 s with Karney's sampler); the fold is under three percent of a two-dozen-step proof (claim mask_fold_small_fraction, which replaces mask_fold_noticeable_fraction); the challenge-set point says why d = 512 and weight 20; the sampling point now carries Jeudy's theorem, the PKC 2018 sampler's rates, the exact-rounding argument and Karney's rate as the alternative (the §5.4 sentence "Karney's exact sampler or a high-precision CDT is the standard answer" is gone). §5.6's table has the weight-20 rows for α = 96, 48, 24, 12, 6, 4 first (10 slices and 15.7 Mbytes at 96), then the weight-32 and weight-16 rows, and its text records the page's choice and the measure's limits. §5.7: the block factor 2.00 instead of 2.45, eight digits, 12.6 Mbytes; k = 9 candidates a block. §5.8: the claim mask_fold_phone_seconds (renamed from mask_fold_under_second at the user's request, for what the sentence says: a fraction of a second on a fast core, a few seconds on a phone) replaces mask_fold_seconds; batches of 4 / 11 / 33 candidates for one percent at α = 48 / 12 / 6; the transfer 14 Mbytes at 27 bits a coordinate. §5.9: 350 rows, a fold of under half a second. The example's figures are generated from the page's constants (note_* figures in define_figures; NOTE_MASK_ALPHA is gone). The page itself did not change (artifact v152 stands). The sentence-length check was run on the rewritten passages and the new sentences split; the pre-existing long ones in §5.8 were left.
- STATE: main at b584a44 plus this entry, unpushed from 8d7efa7 (the user pushes). Artifact v152. PENDING: the estimator's row count at 2^42.2 for §5.3 (above); then as before: the soundness note's lemmas for the two routes and the user's review; the 2026-11-14 open modelling questions; the Pasta-claims recovery row's BLAKE3 figure; the hash-based rows' PIOP verifiers in their merges. A measurement of a rounded-Gaussian sampler on the M4 Max (Box–Muller in doubles with the boundary check) would replace the 20 ns assumption; not started.
- 03:44 UTC, addendum: the estimator run finished in seconds (726f62b): Pallas needs 349 rows at 2^42.2 (the rule's 350), 356 at 2^42.6 and 366 at 2^43.2, all at block 484; §5.3's masked rank row is the estimator's again (NOTE_MASKED_ROWS = 349 in the model, asserted within a percent of the rule), §5.5's ladder has the three new bounds, estimates/pasta-rank.csv was regenerated with them (the earlier rows reproduced exactly) and scripts/akita-pasta-estimates.sh lists them. So nothing is left to run overnight; the one open measurement is the rounded-Gaussian sampler's rate on the M4 Max. STATE: main at this entry, unpushed from 8d7efa7 (the user pushes); artifact v152 (the page did not change after 847ec5f).
- 03:54 UTC, addendum: SHORTER SENTENCES ON THE PAGE (3eefd98; the user, on the zero-knowledge section's first sentence: "this is too long; look for other long sentences in existing prose"): a scan of the template's paragraphs found 127 sentences of 40 words or more; the zero-knowledge section's long ones (about twenty) and every sentence of 60 words or more elsewhere were split at clause boundaries, one claim to a sentence, with the markers kept; the eight of 60 or more that remain are lists of parallel values (the decider ranges, the three packings, the NTT's operations, the BLAKE3 accounting, the Boolean merge's parts, the per-scheme result lists, the shrink ranges). About ninety sentences of 40 to 59 words are left for a later pass. The claim bitz_recovery_zk_unchanged's sentence now says "since the masking fold grows with the rank" (it said the mask's sampling, which is small now). Artifact v153. STATE: main at this entry, unpushed from 8d7efa7.
- 10:11 UTC, addendum: the two parenthetical section links, "prover commitment work (the section below)" and "with exact rounding (the zero-knowledge section)", are links on the phrases themselves (0809eb1; the user: "Just link \"prover commitment work\". Look for similar cases"); the other in-page links are clauses ("as the Hashes section says") and the controls' "(see text)" is the deliberate pattern, both left; the notes' "(§5.5)" references are section numbers, left. Artifact v154.
- 10:14 UTC, addendum: the controls' "(see text)" and "(see the Rank/Knobs section)" are gone; the zero-knowledge checkbox label and the Rank and PCD header eyebrows are the links themselves, with the page's ordinary link underline and colour (ecee0e1; the user: "(see text) can also just make the label a link", "they should have the normal underline and highlight cues"; checked in a render of the three groups). Artifact v155.
- 10:19 UTC, addendum: EVERY CONTROL EYEBROW IS A LINK (43854d8; the user: "all of the eyebrows have things they can usefully link to", and "can't that just be <a href class=eyebrow>"): second and third measure to #measures, the transaction select to #transaction-prover, view to #axes, work unit to #prover-work, frontier to #frontiers, security floor to #security-floor and zero knowledge to #zero-knowledge, allowed changes to #changes, rank, PCD header to #knobs, the fixed circuits to #circuit-budget, grinding to #grinding, and the family headings (GROUPS carries the href now) Pre-quantum to #circuit-budget, Lattice-based to #trust, Hash-based to #hash-based. An eyebrow that is wholly a link is `<a class="eyebrow">`, with `.group a.eyebrow { color: var(--accent-ink) }` so the muted eyebrow colour does not win over the link colour; one with a tail keeps `<span class="eyebrow"><a>…</a> tail</span>`. Checked in renders. Artifact v156.
- 10:20 UTC, addendum: zero knowledge is its own control group with its own linked eyebrow, stacked under the security floor in the left column with the allowed changes on the right, as the view row is laid out (4319af9; the user: "make Zero knowledge its own eyebrow"); the checkbox label is plain again. Checked in a render. Artifact v157.
- 10:25 UTC, addendum: the grinding eyebrow's tail is "(query phase proof-of-work)" so that it fits on one line (7f3429f; the user). Artifact v158.
- 10:27 UTC, addendum: the limb hybrid is defined at its first mention in the ARC-against-recursion section (WHIR with the Pasta witness as four 64-bit limbs a coefficient tested over Goldilocks, a Pasta merge circuit; the family list's "Pasta claims, 64-bit limbs" rows), with an id that the later mentions link to, and the Knobs entry calls it the limb hybrid too (8ad075e; the user: "the limb hybrid is not explained"). Artifact v159.
- 10:27 UTC, addendum: the lede's sentence on the drafts is the user's wording, naming Kishu ("Two experimental drafts join them: BitZ's arithmetization over Akita, called Kishu; and Flock-style Boolean circuits over Akita's binary groups.") (39bd038). Artifact v160.
- 10:32 UTC, addendum: THE SCHEME SECTIONS ARE REGROUPED (08a868d; the user: headings "Pedersen-IPA", "Lattice-based" and "Hash-based" at the same level, "families" rather than "schemes" for consistency; "Knobs" is "Control knobs"): h2 Pedersen-IPA (h3 Circuit budget, id kept), h2 Lattice-based families (h3 Akita: the merge estimate and the circuits fixed point that were in Circuit budget; h3 Kishu; h3 the binary groups), h2 Hash-based families (h3 WHIR and FRI: the hash-based merge estimate from Circuit budget; h3 The 𝔽₂ family, id binary-field-systems kept; h3 BitZ). The Frontiers subsection "The hash-based families" is "Where the hash-based families stand" to avoid the clash; the family-list headings link to the three new sections; the two "binary-field section" links say "𝔽₂ family section"; Kishu's first mention of BitZ links to its section, which now follows it. The trust section stays its own h2. Artifact v161.
- 10:36 UTC, addendum: the Frontiers subsection "Where the hash-based families stand" is gone (47af194; the user): its first sentence, that the WHIR-type and Plonky3 families start unticked since Akita dominates them, is the lede's last sentence, and the rest (Poseidon-tree figures, WHIR with ARC dominated, the decider's three oracles, the lower rates and grinding, Goldilocks and the limb hybrid, what the hash-based route has) opens the Hash-based families section before "WHIR and FRI"; the id hash-based had no other links. Artifact v162.
- 10:40 UTC, addendum: the Hash-based families section opens with two short paragraphs (bbdaf48; the user: an introduction that reads first, without excessive detail): the families and what the route has that Akita does not, then the Poseidon-tree convention and a one-sentence verdict (WHIR with ARC dominated; the F2 family and BitZ the efficient end). The WHIR and FRI subsection took the detail: the dominance figures, the decider's three oracles, the rates and grinding with the extrapolation, Goldilocks and the limb hybrid, then its merge estimate ("The merge is estimated, as Akita's is", no longer "also"). The claims whir_rate32_third_off and whir_gold_sixth_off moved with their paragraphs. Artifact v163.
- 11:03 UTC, addendum: THE PAGE IS A NATIVE BOOK CHAPTER (429af2d; the user: the iframe integration was clunky; keep the artifact updating; "the plot and controls should retain the dark background for contrast; the rest can follow the theme of the book"). One template, two outputs: `pareto.html` as before for the artifact, and for the book `pareto-book.html` (the text, no h1, no blank lines, so Markdown sees one HTML block; included by `{{#include}}` in pcs-frontier.md, which is now just the heading, a full-width style line and the include), `pareto.css` (write_book_files/scope_css in the model: every rule under `#pareto`, the page's variables mapped to mdbook's `--bg`, `--fg`, `--icons`, `--quote-border`, `--links`, `--mono-font`; the light family palette on `#pareto` and the dark one under `.coal`, `.navy`, `.ayu`; `#pareto .top` carries the standalone dark theme for the plot and controls; the page's body, h1–h3 and p rules and its font families dropped so the book's typography applies; mdbook's table striping and header background undone inside the page), `pareto.js` (the script in an IIFE over `window.PARETO_DATA`, with a message in #selfcheck if the data is missing) and `pareto-data.js` (the data as a script, not JSON fetched: a fetch fails from a file: URL, which the user hit, and a script keeps the 5 Mbytes out of mdbook's search index, which now holds the page's text). build-book.sh copies the four into book/src/proof-systems/ (ignored); the old pareto.html copy there is gone. The template now reads its theme from `#pareto .top` and the swatches use `var(--c-…)` in place, so the same script serves both pages; `#plot` is border-box so it matches the controls' height (the user noticed the 2 px). Checked: the built chapter from a file: URL in headless Chrome with software WebGL (rust theme; the prose area follows the theme, the panels stay dark; the frontier table in the theme), the standalone page unchanged in look, the search index holds the prose and not the data. mdbook-katex sees no `$` since the script is external and the prose has none. Artifact v164.
- 11:08 UTC, addendum: the plot overlapped the controls after the book's sidebar was toggled (the user's screenshot): Plotly's responsive option follows window resizes only, so a ResizeObserver on #plot now calls Plotly.Plots.resize, debounced to a frame, and #plot clips its overflow (07043b2). Artifact v165.
- 11:25 UTC, addendum: the one-column layout is a container query on `.wrap` (container-type: inline-size), so it applies at the page's own width in the book's column as in the standalone page (the user: that behaviour is good and should be retained in both); the camera's eye scales by max(1, 600 / plot width) at the first render and on width changes, through the ResizeObserver, since Plotly's vertical field of view is fixed and a narrow plot crops the scene sideways; css_rules skipped no whitespace before a comment, so the rule after a comment came out unscoped, found when the container rule did not fire in the book (bf73221). Checked at 1300 px (one column), 1700 px (two) and the standalone at 900 px (one). Artifact v166.
- 12:11 UTC, addendum: FIREFOX WHEEL GESTURES OVER THE EMBEDDED PLOT, OPEN. The user (Firefox 158 on the MacBook, trackpad): on the book chapter the plot zooms much faster under a two-finger vertical scroll than on the artifact, and a horizontal scroll rotates only when zoomed far out; the standalone `pareto.html` opened as a file: URL behaves like the artifact, so the book page is the difference; Chrome is fine on both. Firefox's console warns on the book page about a scroll-linked positioning effect, which is mdbook's menu bar positioned from a document scroll handler (book.js `controllMenu`); staktrace.com/spout/entry.php?id=834 explains that Firefox scrolls wheel input on the compositor without waiting for the page. Plotly 2.27's 3D wheel handler (3d-view-controls): if |dx| > |dy| it rolls the camera about the view axis by dx·π·rotateSpeed/innerWidth, else it zooms by exp(zoomSpeed·dy/innerHeight·(now − lastT)/20), lastT the camera clock that the scene's rAF loop refreshes each frame; mouse-wheel scales line-mode deltas by the canvas's ex height. Measured, and all the same on both pages: the camera clock stays 17–25 ms behind (user's Firefox and headless); the user's event captures show pixel-mode deltas of 1–3 at 8–20 ms spacing, dy 1 → factor 1.0011, 2 → 1.0024, 3 → 1.0025–1.0065, exactly the rule, on both pages; dragmode and camera mode are turntable on both; headless Firefox through geckodriver with real WebDriver wheel input (bursts of 20 × 8 px) zooms ×1.07 per 50 px on both and never rolls on dx; one wheel listener on the canvas on both (render() re-runs on mdbook's root-class changes at load but Plotly.react adds no listener); no Plotly resize, relayout or react calls and one ResizeObserver callback over 3 s idle and 15 wheel events on both. Ruled out: a stale camera clock, doubled listeners, a resize feedback loop, line-mode deltas, the camera mode, my MutationObserver. Still open: whether the document scrolls under the pointer during the gesture on the book page (Firefox's compositor may scroll before the page's handler prevents it; the user was asked to log document scroll events); the plot is narrower in the book (574 px against 890 at a 1400 px window with the sidebar), with the eye scaled out by 600/574. The harnesses are ragu-pcs/work/firefox-wheel*.py, firefox-count.py and firefox-resize.py (geckodriver and python selenium are now in the user's nix profile; headless Firefox renders WebGL). Everything above 8d7efa7 is unpushed; artifact v166.
- 12:12 UTC, addendum: the document does not move while scrolling over the plot on either page (the user), so page scrolling under the pointer is ruled out too; every measured quantity is now identical between the two pages and the Firefox difference stays unexplained. Untested ideas for the next session: compare the pages at the same plot width (the book's plot is 574 px against 890, which changes the eye scale and the scene's size in the view); the `container-type: inline-size` and `overflow: hidden` on the plot's box interacting with Firefox's wheel transactions; mdbook's `<html>` being in standards mode where the standalone, with no doctype, is in quirks mode; and recording a whole gesture's events and camera on both pages into a file for a side-by-side plot of distance against time.
- 12:37 UTC, addendum: THE FIREFOX DIFFERENCE WAS STATE IN THE TAB, NOT THE PAGE. The user suggested quirks mode first: the standalone with a doctype added (standards mode) and the built chapter with its doctype removed (quirks mode) both behaved correctly on the trackpad. So did seven more variants in standards mode: the chapter without book.js, without the chrome stylesheet, with the content column's overflow visible, with the body's horizontal overflow visible, with the sidebar and menu bar hidden, with the menu bar alone hidden, and the standalone at the chapter's column width (plot 576 px). The original chapter still misbehaved in its own tab; then the user reloaded that tab and the misbehaviour did not reproduce. Nothing had changed: the tree is at 624b213 and the book's copies of pareto.js, pareto.css, pareto-data.js and pareto-book.html are identical to the model's outputs. The four slashes in the user's URL were a red herring (headless Firefox keeps `file:////` as the href and lays the page out the same). Headless probe (work/firefox-compat.py, log work/firefox-compat.log): the only quirks-mode differences are the scrolling element (body against html) and which of the two carries the viewport height. The plot box, the canvas, the camera and the zoom from twenty 8 px wheel events are the same on all four pages. The user's conclusion: something in the browser's state was broken and is no longer broken; closed, not to be pursued unless it recurs (reload first). The variant files are work/pareto-standards.html, work/pareto-standards-narrow.html and pcs-frontier-*.html in the book's output directory, which the next build wipes; the harnesses work/firefox-compat.py, firefox-loadcheck.py and firefox-href.py. STATE: main at this entry, unpushed from 8d7efa7 (the user pushes); artifact v166.
- 12:51 UTC, addendum: THE BOOK'S TABLES FILL EVERY ROW (647547f; the user: the cells had the page's background, which looked odd, and after a first fix with mdbook's own striping, "I'd mildly prefer alternating between slightly contrasting and slightly more contrasting"). The book stylesheet's extra rules had switched off mdbook's header fill and striping, and `--surface` is the book's `--bg`, so the tables were flat. Now odd rows take `--table-alternate-bg`, even rows `color-mix(in srgb, var(--table-alternate-bg), var(--fg) 6%)`, the header mdbook's `--table-header-bg`, and the page's rule under each row stays in place of mdbook's cell grid. Checked in headless Firefox element screenshots (work/firefox-tables.py; rust and navy; work/tables-*.png); the user: "significantly better in all themes". The standalone page is byte-identical, so the artifact stays at v166. STATE: main at this entry, unpushed from 8d7efa7 (the user pushes).
- 13:49 UTC, addendum: THE PAGE'S FORMULAS ARE LATEX, RENDERED BY KATEX (18de138; the user: "can we have the math in KaTeX? (not plain numbers…)", "use your judgement about what counts as a plain number"): exponents, Greek symbols, norms, the binary fields (written `\mathbb{F}_{2^n}` throughout, GF dropped at the user's request), the attempts, openings and BKZ expressions are in `$…$`; counts, times, sizes, rates and ranks stay plain, as do the data labels. mdbook-katex renders them inside the included HTML block (tested with a marker: katex runs after links). The standalone page loads KaTeX 0.16.11 and its auto-render from cdnjs with MathML output, which needs no stylesheet, so the artifact's host cannot block it. The page now has a doctype: auto-render finds nothing to render in quirks mode (a minimal page: standards mode renders, the same page without a doctype renders nothing, Plotly irrelevant; the standards-mode copy had already passed the user's Firefox test with the same layout). `th .katex, th math { text-transform: none }` replaces `th .sym`. The conversion was work/tex-prose.py (a hand list of the composite expressions plus patterns); checked by counting formulas and leftover dollar signs on both pages (work/firefox-math.py) and by screenshots. A FIGURE MARKER NEVER SITS INSIDE A MATH SPAN (d403159): the zero-knowledge note's thirteen markers inside `$2^{…}$` had rendered the comment text literally since the 03:43 change (the user: "where are the figure markers in $...$?"); the twelve figures that stand as powers of two carry the whole span through tex_pow2 (note_cs_bound, note_sigma, note_z2, note_zinf, note_beta, note_ntts, note_pointwise, note_mults, note_word_mults, mask_rounded_divergence, mask_double_undecided, mask_double_undecided_folds), the note's and the page's markers wrap the span, and the relation sits in its own `$\le$` or `$\approx$`. HEADINGS IN THE BOOK (546c458; the user: clicking a section title gave no link or » cue): the book writer wraps each h2 and h3's text in `<a class="header" href="#id">` as mdbook does for Markdown headings, with `#pareto a.header { color: inherit }`; that also put the section outline in the sidebar (the user: "great"). WORDING (c746056, be37f4f; the user): Kishu's merge paragraph is three (the BLAKE3 accounting with the range check, the arithmetic over the extension, the Poseidon option and the consequence), "Kishu's merge is Akita's", the projection zero-knowledge sentence says what the projection reveals and the draft-certificates remark is its own paragraph, the naming sentence links the breed's Wikipedia article, "the merge prover does 2.9 to 3.3 times less work", the reference to an earlier version of the page is gone, and the Pasta-requirement list has "relation, limbs" and "relation, fingerprint" as separate entries. The user asked where the WHIR zero-knowledge sentence's 30.9 and 37.5 kbytes come from: they are the plain WHIR baseline of Plonky3's zk_overhead benchmark run on 2026-10-15 (entry above; work/plonky3-zk-overhead.log), at 100 bits under the capacity bound with 16 bits of grinding over KoalaBear's quintic extension, well below the page's floors; the sentence serves only the additive 73 kbytes. Artifact v167. STATE: main at this entry, unpushed from 8d7efa7 (the user pushes).
- 14:19 UTC, addendum: CITATIONS AND REFERENCES (bc3d34d; the user: References a level higher; "there are plain text citations such as (ePrint 2026/2583) that should be reference citations"; "the zero-knowledge note's section references can be made into links (when in the book)"): References is an h2; every plain-text citation on the page is a bracketed key in the style of the trust section's, linked to its entry (`<li id="ref-key">`), and the existing keys are linked too (38 links, checked against the ids); twelve entries added from the local PDFs and the ePrint/arXiv metadata pages (OS26 LaBinius, DP24 FRI-Binius, Ska26 the small-field survey, BGK+26 BitZ, AGK+26 Zinc+, CFW26 Zook, BRW26 Flock, Jeu26, HLS18, DFW20, Kar16, ZIP-2005), with "[DP24, §1.3]" for a section of a paper. References to the note's sections are `<span class="noteref" data-section="5.9">§5.9</span>` in the template; write_book_files turns them into links to working-notes/zk-fiat-shamir-with-aborts.html at the ids mdbook gives the note's headings (mdbook_id reproduces mdbook's rule, checked against the built ids; ten links, one to the chapter itself, which replaced the page's only direct link into the note, dead on the standalone); the standalone shows them as text. work/cite-prose.py did the rewrite. Checked: every link's target exists in the built book, a click lands on "5.3 A worked example". WORDING (bc3d34d, fe1c516; the user): "The rule counts the first three (native and the two relation variants)"; the binary-groups paragraph says the 80,000 word multiplications per Pasta gate are the recovery circuit's cost in that family and that the family would suit an application that is a Boolean circuit in its own right, such as Flock's hash batches (the user: "what boolean application?"). Artifact v168. STATE: main at this entry, unpushed from 8d7efa7 (the user pushes); about 52 commits.
- 14:29 UTC, addendum: SUBSECTIONS (a0509a1; the user: "the Zero knowledge section should be split into subsections", "in particular, the three things referred to by 'Three things set it.' should be subsections", "paragraph anchors might be needed in some cases, but only where it doesn't make more sense as a subsection"). Zero knowledge (h3) has h4s Akita's mask, Pedersen-IPA, WHIR and FRI, the F2 family, Kishu (with h5s The sampler, The width of the mask, The transaction's shape) and BitZ; "rejection sampling" in its first paragraph is a noteref to the note's §2; "explained below" links to the width subsection. Kishu has h4s Digits and constraints, Pasta multiplication by two routes, The merge, Costs at rank 17, The recovery circuit, Zero knowledge and status, LaBinius; Transaction prover has The application in each arithmetization, The masking fold, Results. The Pasta-as-a-requirement list links each approach to its section (Pedersen-IPA, Akita, WHIR, the limb hybrid, the two routes, BitZ, the application costs, the F2 family, the binary groups; the user: the list "should itself link to the detailed explanations for each approach"), and the Transaction prover's emulation sentence refers to that list (the user). The standalone styles h4 and h5; the book drops those rules and gives the headings header links (write_book_files handles h2 to h5). Checked: every in-page link on both pages has a target, 57 headings with header links in the book, no KaTeX errors. Artifact v169. STATE: main at this entry, unpushed from 8d7efa7 (the user pushes).
- 15:14 UTC, addendum: TACHYON NODES OFF PASTA: BIT-LEVEL GATES PRICED AS BITS (4f44829; the user, on "the remaining gates are taken as Pallas multiplications, an overstatement where a gate only checks a bit": "Isn't that potentially quite a large error?"; yes). A node's gates beyond its permutations and window selections were all priced as Pallas multiplications (1,100 Goldilocks gates, 510 Kishu digits, 120,000 AND gates each), yet 55 to 64 percent of every step is that remainder and most of it is bit-level: the scalars' bit checks (3 a window), the digest canonicity comparison, the amount's range check and comparison, the step's glue. Now TACHYON_STEPS carries the openings at ζ (0, 2, 0, 2, 6, 4, 0 for SpendBind, SpendAction, OutputBind, OutputAction, ActionMerge, FeeFuse, Rerandomize); tachyon_node_cost prices the window additions (2 gates each) and the openings (2 gates each, from the action merge's 17 for six) as multiplications and the rest as bit operations, one gate, AND gate or committed bit each (BIT_GATE_OFF_PASTA; BIT_CHECK_PIOP (1, 2, 0) in Kishu's PIOP); `bits_as_mults=True` gives the old pricing for the prose's bound (claim tachyon_bits_as_mults_more_steps). Results: a node is 6 to 13 Goldilocks steps of rank 17 (was 27 to 36; the bound 27 to 36 stays in the prose) and 5 to 11 Boolean steps (was 23 to 30); two tachyactions: Goldilocks 5.30 s in 41 steps (was 19.5 in 151), the F2 family 5.48 s in 35 (was 20.2 in 129), Kishu 0.193 s (was 0.385; with zk 0.484, was 0.780), BitZ 0.160 s at rank 20 (was 0.214 at 22); sixteen: Goldilocks 29.8 s (was 132), Kishu 0.580 (was 1.56), BitZ 0.303 (was 0.454); the Karney-rate zk optima 91 to 260 (were 110 to 300). Pedersen-IPA and Akita with Pasta claims are native and unchanged, so the headline Tachyon comparison stands. The prose now says the post-quantum families are costed as a post-quantum variant of Tachyon in a new shielded pool, whose hashes follow the page's policy, and that the recovery circuit recovers notes of the existing pool, so its nullifier stays Poseidon over Pasta (the user; it is inside RECOVERY_MULTS, so it always was). The Poseidon permutations per step, for the record: Spend Bind the two nullifier derivations (epochs e and e + 1), Output Bind the note commitment and the padding tachygram, Spend Action the proof authorizing key, the randomizer and the action digest, Output Action the randomizer and the digest, Fee Fuse the fee blind, the fee digest, the change commitment and a fourth not named in the statements note. Artifact v170. STATE: main at this entry, unpushed from 8d7efa7 (the user pushes).
- 15:23 UTC, addendum: the width subsection's sensitivity sentence quotes Karney's rate alone (70ae607): after the Tachyon change the 100 ns range coincided with Karney's (91 to 260), so the 100 ns optimum figures are no longer defined (the fast rate itself stays, for the sampler subsection's 2.19 s). The user asked whether "48 keeps nine slices … within 2.8 percent … and within 6.5 percent at Karney's" still holds: it does; the claim alpha_page_near_optimum passed and `--figures` shows the worst cases are still the path shapes (2 paths at the page's sampler, 1 path at Karney's), the Tachyon shapes being within 2 percent at the page's sampler and 6.4 at Karney's (16 tachyactions). Artifact v171. STATE: main at this entry, unpushed from 8d7efa7 (the user pushes).
- 22:32 UTC, addendum: THE FEE FUSE STEP, READ OFF TACHYON'S CODE (448d899; the user: "please check the fee fuse step"). `FeeFuse::witness` (crates/tachyon/src/stamp/proof/stamp.rs at 73031f7) runs three sponges: `feemax_blind` inside `Note::cv_feemax` (gadgets/note.rs), `fee_digest`, and the change note's `commitment`; Ragu's circuit sponge (ragu_primitives poseidon/mod.rs) permutes only when four absorbed elements are followed by a fifth or by a squeeze, so each tagged hash of at most four elements is one permutation, and a nullifier group (two absorbed, four squeezed) is one too. The step's multiplications are two: `R_BASE.mul_digest` of the derived blind (255 bits, canonical) and `FEE_V_BASE.mul_amount` of the 51-bit slack onto the blind point; the maximum-money term is a constant point. So TACHYON_STEPS["FeeFuse"] is (1934, 3, 102, 4), not (1934, 4, 187, 4), and keep/tachyon-statements.md's cost table row is corrected with a note on the sponge. The other steps' counts match the code (SpendBind two nullifier groups and two multiplications, SpendAction three sponges and one, OutputBind two and two, OutputAction two and one). Results: a node is 6 to 8 Goldilocks steps of rank 17 (the bound 27 to 39), 5 to 7 Boolean; two tachyactions 4.53 s over Goldilocks in 35 steps (was 5.30 in 41), the F2 family 4.69 s in 30 (was 5.48 in 35); sixteen over Goldilocks 29.0 s; the Karney-rate zk optima 64 to 260. Artifact v172. STATE: main at this entry; everything through f9e3359 was pushed by the user at about 15:20 UTC; 448d899 and this entry are unpushed.
- 22:42 UTC, addendum: the Rank section's "Mostly the field choice trades" sentence is "The more significant trade is the field choice: a smaller field buys fewer bytes and less prover commitment work at the cost of more atoms absorbed per merge" (cf4a779; the user: odd wording). Artifact v173. STATE: main at this entry; 448d899 and after are unpushed.
- 22:49 UTC, addendum: the book's table headings are in `--fg` (a6c3128; the user: low-contrast in rust, navy and ayu, nearly invisible in coal, since `--muted` maps to mdbook's `--icons`); checked in the four themes with work/firefox-tables-th.py; the standalone is unchanged, artifact v174. STATE: main at this entry; 448d899 and after are unpushed.
- 22:53 UTC, addendum: the frontier table's accent bar on each row's first cell now runs through the header too (64545ee; the user: the header's left edge was a lighter colour; "that's better"). Artifact v175. STATE: main at this entry; 448d899 and after are unpushed.

## 2026-11-20 23:20 UTC: the mask sampler measured

- THE SAMPLER'S RATE IS MEASURED (ae3ec50; the user: "sampler first. I'll plug in to mains"). scripts/sampler-bench.c, plain C with no dependencies: ChaCha20 (RFC 8439, scalar) or, with a fourth argument `aes`, AES-128-CTR through CommonCrypto (macOS; the M4's AES instructions); two 53-bit uniforms a Box–Muller pair in doubles; Sheppard's correction σ' = σ − 1/(24σ); the scaling; the tail check |x| ≤ 14σ; rounding with rint; a coordinate within |x|·2^-50 of a half-integer counted as undecided (the fold would refine it; one in 2^27 observed, none in most runs, against the page's bound of 2^-25). On one core of the M4 Max on mains, medians of three runs of 32 × 2^22 coordinates at σ = 2^22.9: AES-CTR 7.1 ns a coordinate (randomness 1.5), ChaCha20 14.0 ns (randomness 7.7). A run that straddled a switch to battery gave 11.9 ns for AES and was discarded (the user: invalid). Keystream alone (work/rng-bench.c): AES-128-CTR 0.37 ns per 8 bytes (21 GB/s), AES-256 0.50, scalar ChaCha20 7.2 (1.1 GB/s), so hardware AES is about twenty times cheaper than unvectorised ChaCha20 (the user: "thought so"); a first version of that benchmark reported 126 GB/s for ChaCha20 because the compiler dropped the unused words of each block. The page takes AES-CTR: MASK_SAMPLE_NS = 7.1, MASK_SAMPLE_WORD_MULTS = 21 (was 60 for the assumed 20 ns), with MASK_SAMPLE_RNG_NS, MASK_SAMPLE_CHACHA_NS and MASK_SAMPLE_CHACHA_RNG_NS as figures beside it; REGENERATING.md has the procedure. Results: the recovery with zk 1.44 s a note (was 1.54; the fold 0.231 s, of which the sampling 0.0566, was 0.336 and 0.162); four recovery inputs 0.971 s a note; two tachyactions with zk 0.432 s; the zk note's §5.4 attempt 0.261 s and fold 0.335 s (were 0.316 and 0.405), the sampling 0.13 times the commitment (was 0.36; "about a third" dropped from the sentence); the optimum width for the recovery circuit 91 (was 76), the page's optima 45 to 130, the recovery band 27 to 360, 48 within 2.5 percent at the page's sampler. HLS18's 7.7 to 13 ns on a 2014 Haswell is quoted beside the measurement. Artifact v176. STATE: main at this entry; everything through b4ab849 pushed; ae3ec50 and this entry unpushed. PENDING: the user's review of the soundness note; the 2026-11-14 open modelling questions; the Pasta-claims recovery row's BLAKE3 figure; the hash-based rows' PIOP verifiers in their merges; the readability pass over the 40-to-59-word sentences; classifying the Tachyon nodes' remaining gates from Ragu's synthesis analysis, if the counting adapter can tell a bit check from a multiplication.
- 23:31 UTC, addendum: the Pasta-claims recovery row's BLAKE3 figure, pending since 2026-11-14, is on the page (1523b1f): tx_recovery_q64_blake3_s = 387 s at rank 17 under the default trees, beside the 142 s with Poseidon, from best_for("pasta_q64", "recovery", "blake3", hashes="blake3"). Artifact v177. STATE: main at this entry; ae3ec50 and after unpushed.
- 23:39 UTC, addendum: THE READABILITY PASS (11494ab; the user: "3 first, then your suggested order"): of the 84 sentences of 40 to 59 words in the prose, 55 that joined a claim to a consequence or a qualification were split at the joint by exact fragment edits (work/split-sentences.py; one fragment had to carry the limb-hybrid link); the 35 left and the 6 of 60 or more are enumerations of parallel values or cases, kept whole. The claims' markers wrap the split sentences as before and every check passes. Artifact v178. STATE: main at this entry; everything through f426b3f pushed.
- 00:02 UTC, addendum: THE HASH-BASED MERGES VERIFY THEIR PIOPs (3e24191). f2_piop_verifier_mults(log_bits) = 4 × (2 log N + 3 log2(BLAKE3_ANDS)) field multiplications an input (the zerocheck, the lincheck and a sum-check per base matrix of one compression's R1CS, in place of the native verifier's own evaluation of the small matrices, which a circuit should delegate to a committed evaluation that ARC accumulates); bitz_piop_verifier_mults adds the GKR's n(n+1)/2 rounds; a round is four multiplications (a degree-three univariate at the challenge and the eq factor); the Boolean merge multiplies by KARATSUBA_ANDS[chal] (f2_merge takes the design's challenge field now), BitZ's hybrid merge commits 128-bit products. At rate 1/8: the F2 family 350 multiplications an input, 1.5 million AND gates, 5.7 percent of the merge (claim f2_piop_verifier_small, under a fifth at every rate); BitZ 1,700 products, 424 thousand bits, 1.4 percent (claim bitz_piop_verifier_small, under two percent; the page had said "a few thousand constraints that are not counted"). The F2 merges are 17 to 77 million AND gates (were 14 to 74), two tachyactions 5.07 s (was 4.69); the F2 prover is least at rate 1/4 alone, 1/8 within a tenth (claim f2_prover_least_rate_4 replaces f2_prover_least_rates_4_8 and its two markers). TOOM–COOK FOR THE BINARY-FIELD MULTIPLICATIONS (the user: "Did we check Toom–Cook?", then "check whether Toom-k for larger k (8, 16) is worthwhile"): not adopted. A first count assumed Toom-k's 2k − 1 pointwise products have n/k bits and gave 1,875 (Toom-3) and 1,029 (Toom-3 and 4) AND gates at 128 bits against Karatsuba's 2,187; that is wrong in characteristic 2, where the evaluation points beyond 0, 1 and ∞ are polynomials x^d + … (Bodrato, WAIFI 2007) and evaluating a k-piece operand at one lengthens the piece by d(k − 1) bits, so for Toom-4 at 128 bits the pieces are 32 bits but the products at x and x + 1 are 35-bit and at x² and x² + 1 are 38-bit. Counting that, Toom-k for any k up to 16 gives no gain at 128 or 256 bits, where Karatsuba's halving is exact (2,187 and 6,075 against 6,561 by the model's constant at 256, a 7 percent gain only there), and at 192 bits 4,185 against the model's 4,374 (4 percent); larger k only lengthens the pieces more. Under a bit-level Karatsuba recursion a 35-bit product costs as much as a 64-bit one; with schoolbook on the extra bits it is about 444 AND gates and Toom-4 at 128 bits about 2,943, still above Karatsuba. The constants stay. Artifact v179. STATE: main at this entry; everything through f426b3f pushed. NEXT (the user): pause ragu-pcs for FROST analysis. PENDING: the user's review of the soundness note; the 2026-11-14 open modelling questions (the Pasta-claims rows' claim-field sum-check, witness generation, the aggregator's opening and compression, phone parallelism); classifying the Tachyon nodes' remaining gates from Ragu's synthesis analysis.
- 00:06 UTC, addendum: TOOM-3 AT 192 BITS after all (d8f091d; the user: "it's worth accounting for Toom-3 being slightly better at 192-bit"): CLMUL_ANDS (was KARATSUBA_ANDS) prices a 192-bit (and 191-bit) carry-less product at 3 × 729 + 2 × (729 + 2 × 2 × 64 + 4) = 4,165 AND gates, Toom-3's five products (three of 64 bits at 0, 1 and ∞, two of 66 bits at x and x + 1) against the three-limb Karatsuba's six, 4,374; 128 and 256 bits stay Karatsuba. The F2 recursion rows' merges fall a little (the 192-bit design 87 million witness bits at rate 1/8, was 89; the 191-bit 133, was 137), two tachyactions 5.05 s. The PIOP commit is 3e24191 after the Pasta note's refreshed figures were folded in. Artifact v180. STATE: main at this entry; everything through f426b3f pushed; the five commits after it unpushed.

## 2026-11-21 05:10 UTC: the hardware wallet's part of the recovery statement as applications

Context: ZIP 2005's Option A makes `SoK^qsk` on the hardware wallet that holds `qsk`, and the
host's Recovery Statement proves the rest. Whether the device can prove its part at all was
analysed on 2026-11-21 (the device statement as a Kishu leaf; an MPC-in-the-head proof of the
preimage; a hash-based signature on the device with its verifier in the host's proof), and the
verifier route looked feasible from the model's figures, so the page now prices it.

Three applications joined the transaction measure (`hash_app_cost`, `hash_app_piop`,
`HASH_UNITS`, `HASH_PIOPS` in the model; the option list, the application subsection and
three references in the template):

- `qk`: the device's own statement, one BLAKE3 compression for `H^qk(qsk) = qk`, the linking
  commitment left out for now. 14,900 gates in a prime field, 8,192 AND gates, 15,072 bits or
  digits.
- `leansphincs_blake2s` and `leansphincs_keccak`: a leanSPHINCS verifier, for a device that
  signs SigHash with post-quantum Ethereum's stateless hash-based signature (EthLib's
  Cryptography/Sphincs module; EIP-8288; the draft EIP of ethereum/EIPs#12672, 2026-11-17). The
  counts are sphincs.art's layered two-level WOTS forest key of lifetime 2^30 (checkout at
  8157875, `python scripts/scheme.py --json`: height 26 as layers 10 + 8 + 8, WOTS+C with 64
  chains of 4 positions and target sum 128, 8 forest coordinates): 462 BLAKE2s compressions or
  408 Keccak-f permutations, plus the 6,332-byte signature as input bits. Ethereum's provisional
  set, FORS of 24 trees of height 10 in place of the forest, is 515 permutations and 7,740
  bytes; every parameter in that draft is marked provisional, and the hash is Keccak-256 there
  ("the only primitive every client already implements") while sphincs.art keeps a
  Keccak / BLAKE2s / SHA-256 toggle.

Hash costs in the arithmetizations: a Keccak-f[1600] permutation is 24 rounds of theta's 3,200
XOR bits and chi's 1,600 ANDs and 1,600 XORs, 153,600 committed bits or prime-field gates and
as many product terms, since XOR is not free there; in a Boolean circuit 38,400 ANDs. A BLAKE2s
compression is ten rounds of BLAKE3's G, 21,312 bits or gates (11,072 terms), 10,752 ANDs.

Figures (one M4 core, zero knowledge, Kishu's least row): the BLAKE2s verifier 9.90M digits,
1.38 s at rank 21; the Keccak verifier 62.7M digits, 6.39 s at rank 21, 6.3 times the digits
(3.2 in a Boolean circuit), against 1.44 s for the recovery circuit; the device's statement
alone 0.109 s at rank 15, of which the merge is 48 percent and the masking fold 47 percent,
the circuit itself a few percent. The mask-width sweep leaves `qk` out (its optimum is no
transaction's; the transaction-sized applications' optima are 32 to 130 at the page's
sampler). Claims: `leansphincs_keccak_dearer` (five to eight times), `qk_merge_and_fold`
(over nine tenths).

Two things the `qk` figure shows, not yet in the model: the merge is the host's work, not the
device's, so the device's own share is the step and the fold; and the fold is priced at the
whole accumulator, K × 2^rank = 196k coordinates at rank 15 for a 15k-digit leaf. A mask sized
to the leaf's occupied digits would cut the fold about thirteenfold, if the handoff can mask
only what the host learns. And zero knowledge need not come from the fold at all: the page
masks at the handoff because Ragu's Pedersen-IPA design does, but a leaf this small can be a
hiding commitment with a direct zero-knowledge proof of its relation, whose verifier the host
proves, and the fold's cost is gone. The model prices neither yet. Also open: the linking
commitment's two compressions in `qk`, and a `qk` row for an MPC-in-the-head proof with native
verification.

## 2026-11-21 05:44 UTC: the wallet's own share of the device statement, with the host proving the handoff

The `qk` figure of the previous entry charges the user the handoff fold, 47 percent of the
transaction, most of it the merge NARK that proves the fold. That merge need not be the
wallet's: the zero-knowledge note's §4.2 lists the handoff merge's witness (the hiding
commitment, the mask's commitment, the challenge, the claims, the obligation transcripts) as
simulatable, so the host can derive the challenge, prove the fold's merge and the obligations
(the note's §5.8 deferral) and verify the leaf's sum-checks in its own merge. The one addition:
the wallet's constraint and Booleanity sum-checks must be zero-knowledge, since the host sees
their transcripts where the user's own merges consumed them before; Libra-style masking
polynomials, ℓ (d + 1) committed elements each (120 here). The revealed evaluation claims
are blinded by the hiding padding. The wallet keeps what touches the secret: the leaf's
commitment with the padding at the masked rank, the sum-checks, the mask sampled and committed
in idle time, and z = y + cs with the rejection test.

Pricing (figures `qk_device_*`, claim `qk_device_share_small`): the padding is computational,
5,000 uniform bits (`HIDING_PADDING_BITS`), on the assumption that Aρ is pseudorandom when
knapsack-LWE is hard at the masked matrix's 1,385 rows at q64: by the Micciancio–Mol duality
that is LWE of dimension bits − rows with binary error at the 64-bit modulus, and the primal
uSVP estimate at block 484 (δ = 1.0035) needs about 3,300 dimensions, so 5,000 bits is a
margin of a third; to be confirmed with the lattice estimator. The note's leftover-hash padding
would be 1,385 × 64 + 256 ≈ 89k bits, six times the statement. So the wallet commits 27,800
digits: 0.603 ms online on one M4 core (the commitment at the masked rank and the Booleanity
rate, the constraint PIOP, the response), 0.836 ms idle (1.28 attempts of sampling and
committing the mask), against the 154M word multiplications (51 ms) the measure charges the
user's handoff. The response z is 22 bits a coordinate at σ = 48 · 20 · √27,800, 76 kbytes.
Device rates are assumptions scaled from sphincs.art's hardware-wallet benchmark (a Nano S+
hashes BLAKE2s about 500 times below a laptop core; 64-bit modular multiplication fares worse
on a 32-bit core): 10^7 word multiplications a second for an MCU-class device, 3 × 10^6 for a
secure element, so 0.18 s and 0.60 s; the transfer of z at the Nano S+'s measured 21 kbytes a
second is 3.6 s, 1.3 s with the benchmark's pipelined transport, and is the cost that does not
move. A leaf-sized mask is sound (the theorem is per vector, the unoccupied coordinates are
public zeros, Ay keeps its entropy) and is what these figures use; it mattered little under the
statistical padding, which dominated the leaf.

Open: the lattice estimator on the padding; whether the host's zk-layer merge needs more than
its 18 extra elements for the three-way fold (leaf, mask, its other child); the linking
commitment; an MPC-in-the-head row with native verification.

## 2026-11-21 13:07 UTC: the hardware wallets page

A book chapter, `hardware-wallets.md` beside the notes and included from
`book/src/hardware-wallets.md` (top level in SUMMARY.md), with its figures filled by the model
like the notes' (`PROSE_FILES`). It records the device split, the two shapes of the wallet's
proof with the page's figures, why a Kishu-style proof cannot be small enough for an animated
QR channel, and how the signature of knowledge is argued. New figures: `qk_z_floor_kbytes`
(the leaf alone, no padding or masking elements: 40 kbytes), `qk_min_rank` (14),
`qk_succinct_proof_kbytes` (68 kbytes: one circuit at rank 14, the opening at the planner's
floor), `leansphincs_pruned_sig_bytes` (4,276), `leansphincs_ethereum_bytes` (7,740),
`sok_second_preimage_pct` (63) and `sok_loss_factor` (3.2); claims `qk_qr_channel_too_big`
and `sok_loss_small`. The opening and decider extrapolations are floored at the planner's
smallest geometry (43a0268): the decider's line, fitted at 2^27 bits, went negative at a
one-compression leaf.

The signature-of-knowledge section: a proof of knowledge of a preimage would be replayed, and
the unforgeability reduction must simulate signatures, so simulation extractability with the
message as label is what is needed (Chase–Lysyanskaya 2006). Binding the message into the
instance before the first challenge is proved classically (Faust–Kohlweiss–Marson–Venturi 2012
for sigma protocols; Dao–Grubbs 2023, Faonio–Fiore–Kohlweiss–Russo–Zajac 2023 and
Kohlweiss–Pancholi–Takahashi 2023 for sum-check and PIOP SNARKs), but in the QROM only sigma
protocols and the knowledge soundness of Fiat–Shamir IOPs are settled, the multi-round bound of
Don–Fehr–Majenz 2020 is exponential in the rounds, and the SE proofs rewind. The route that is
available: H^qk maps 256 bits to 256 bits, a random qsk has a second preimage with probability
1 − 1/e, and the reduction to collision resistance holds a preimage, signs honestly and extracts
one from the forgery, which by witness indistinguishability differs from its own with
probability about a half; loss about 3.2; needs only zero knowledge and knowledge soundness
with auxiliary input (the two-witness argument of Katz–Wang 2003 with the hash's
non-injectivity as the second key).

Corrections from the user: a wallet does not necessarily export ak (a single-signer wallet
derives and exports it; with FROST it is the DKG's output), which the page now says; the
use_qsk = false path is not considered, since use_qsk = true is the one whose costs a hardware
wallet optimizes; and the tag byte for qk's derivation, proposed in chat, is withdrawn: H^qk is
already domain-separated, so a signature route would define its own derivation of qk from the
public key under another context when the scheme is known, and the Recovery Statement takes it
as another arm of its tagged union, with keys derived before then being preimage-route keys.

## 2026-11-21 14:45 UTC: the Boolean row's fold counted, the carry-less multiplication measured, k-ary merges

The user noticed that the Boolean-over-Akita row did exceptionally well on the leanSPHINCS
verifiers (0.44 s on the Keccak one against Kishu's 4.68) and asked for the best of both
worlds for Kishu. Most of that win was an accounting gap: the row's prover took the measured
commit and open times per bit, the open time standing in for the fold's sum-checks, and had no
accumulation_prover of its own, so it never paid the fold's sum-checks over the K groups that
the lattice rows pay (accumulation_sumchecks, 11 field multiplications per accumulator digit per
merge, which for Kishu at rank 22 is 554M of the 708M word multiplications a merge costs,
against 141M of merge commitments and 14M of merge PIOP). Fixed (830529c): the per-bit cost is
the commit alone (9.7 word multiplications) plus Flock's PIOP, and the accumulation prover
adds the fold's sum-checks over the six groups at the binary field's multiplication cost.

That cost was measured, since the user suspected CLMULS overestimated it with wide carry-less
instructions. scripts/clmul-bench.c times a GF(2^128) multiplication by PMULL (Karatsuba and a
three-step reduction modulo the GCM polynomial, six PMULLs) against a scalar Goldilocks
multiplication, in independent chains, on one M4 Max core on mains. The first version let the
compiler keep the chains in memory and bounce the Karatsuba cross term through general
registers (four fmov and two scalar eor per multiply); formed in the vector unit with the
chains unrolled, it is 0.94 ns with sixteen chains (1.04 with eight), the scalar Goldilocks
0.52 ns. At the page's word multiplication of 0.33 ns that is 2.8 against the table's 4, so
CLMUL_WORD_MULTS = 0.7 scales every width's count to the measurement (GF128_MEASURED_NS);
REGENERATING.md has the procedure. The F2 family's figures moved by a few percent.

After both: the Keccak verifier 0.77 s on the Boolean row against Kishu's 4.68 (6×, the bit
count's 4× and a cheaper commit per bit), BLAKE2s 0.39 against 0.77 (2×), the recovery circuit
80 s against 0.79, one Merkle path 0.19 against 0.062. So the merge is no longer where the
Boolean row wins; the unit count is. The best of both worlds for Kishu is therefore Akita's
binary group kind as a second group kind inside a Kishu step for XOR-heavy wires, with Flock's
PIOP over GF(2^128) for them and Kishu's over F_q for the integer relations, the merge hybrid,
crossings by salted digests unless the binary groups' bits also carry F_q claims (to check in
akita#285's specs/binary-p64-root.md). XOR cannot be made free inside the F_q PIOP: the
integer-sum-with-committed-carries parity loses to the product form for two-way XOR (a committed
digit is 33.5 word multiplications against 9.8 per product term) and to the shared column
parities for Keccak's theta. The gain is for XOR-heavy verifiers; the recovery circuit's hashes
are about 13 percent of its digits.

k-ary merges, the user's suggestion for the merge-side cost, look worth modelling. Kishu's
accumulation prover per step is dominated by the fold's sum-checks, which run over the folded
accumulator's K × 2^rank digits whatever the number of children, while a k-ary tree has
(steps − 1)/(k − 1) merges instead of steps − 1. With the merge circuit taken as half fixed and
half per child, and the extra children's linear combinations at one word multiplication per
digit, the merge-side cost per step at rank 22 falls from 708M to about 300M at k = 4 and 180M
at k = 8, so the transaction prover roughly halves at k = 4 (the recovery circuit from 0.79 s
toward 0.4) and gains a further quarter at 8. Open: Akita's fold with k children (the
pre-decomposition norm grows about k-fold, a slice at most), the merge circuit's per-child share
(the children's Booleanity and PIOP verifiers may be more than half), and that it is a design
change to Ragu's merge step. Not in the model; a merge-arity parameter would price it.

## 2026-11-21 14:55 UTC: the leanSPHINCS verifier at the pruned key

The user chose the pruned key as the simplest change for the leanSPHINCS verifier under Kishu.
The page's two verifier applications now price sphincs.art's pruned key of lifetime 2^30 (one
tree of height 26, kept subtree of height 12): 262 Keccak-f permutations or 298 BLAKE2s
compressions a verification, a 4,276-byte signature, 16,384 grinding digests per signature
on the signer (2.8 s with Keccak on a Nano S+ at the benchmark's 5,800 a second, 0.50 s with
BLAKE2s at 32,600), and 126,900 proved signatures, one per recovery transaction. Kishu with
zero knowledge: BLAKE2s 1.09 s at rank 20 (was 1.38 at the layered key's 462 compressions),
Keccak 4.39 s (was 6.39 at 408); 6.39M and 40.3M digits. The layered key's and Ethereum's
counts stay as comparison figures (`LEANSPHINCS_LAYERED_*`, `LEANSPHINCS_ETHEREUM_*`;
`LEDGER_HASH_PER_S` holds the benchmark's rates). The option labels carry the counts as figures.

Considered and dropped: fusing Keccak's chi, and theta's D, into degree-3 constraints would cut
a permutation's digits by about 30 percent (6,400 to 4,480 bits a round), but the user's
experience from Halo 2 is that the complexity of higher-degree constraints does not pay, which
is why Halo 2's recursion was never fully implemented; the saving would only be worth having
if a degree-2 proof system could express it, and it cannot without the intermediate bit.

## 2026-11-21 15:25 UTC: a future spend protocol without Pasta, in progress

STATE: the model carries UNCOMMITTED edits for two new transaction applications; the template
has not been edited for them yet, so `python pareto-model.py` will report their figures as
unused until the paragraph and options below exist. Everything before this entry is committed
(eb88548 is the last commit; four commits after a49be05 are unpushed).

The user's sketch, to price for two inputs and two outputs: a spend protocol with no Pasta
arithmetic. A note commitment is a BLAKE3 hash of the note's four fields (128 bytes, two
compressions); a nullifier one BLAKE3 compression over the key and rho; the payment key one
BLAKE3 compression over the authorizing key; amounts range-checked (51 bits) and summed in the
PCD headers, so no value commitments and no binding signature; the Merkle path hashed under the
page's policy as the path application is. Spend authorization per input, usually the same for
all: a Sprout-like preimage check (the payment key's hash alone), or a leanSPHINCS signature
with BLAKE2s (the pruned key, 298 compressions, 4,276 bytes as input bits) over a transaction
digest of 8 BLAKE3 compressions, verified in the circuit with the public key as a witness,
since the zero-knowledge fold hides it and no re-randomized signature is needed.

In the model (done): constants FUTURE_INPUTS/OUTPUTS = 2, FUTURE_NOTE_COMPRESSIONS = 2,
FUTURE_NULLIFIER_COMPRESSIONS = 1, FUTURE_KEY_COMPRESSIONS = 1, FUTURE_SIGHASH_COMPRESSIONS = 8,
FUTURE_AMOUNT_BYTES = 7, FUTURE_AUTHS; `future_cost(field, hp, auth)` and `future_piop(auth)`
after `hash_app_piop`; APPLICATIONS, PIOP_WORK and APPLICATION_MULTS entries `future_preimage`
and `future_leansphincs`; both in PAGE_APPLICATIONS; in define_figures after the leanSPHINCS
grinding figures: figs future_spend_blake3 (4), future_sighash_blake3 (8), and per application
app_{app}_kishu (digits), tx_{app}_kishu_s, tx_{app}_kishu_zk_s, tx_{app}_kishu_zk_rank,
tx_{app}_bitz_zk_s, tx_{app}_bits_akita_s, tx_{app}_flock_s, tx_{app}_goldilocks_s (Poseidon
policy), and the claim future_preimage_quarter (the preimage transaction under a quarter of the
signature one in Kishu with zk). By hand, Kishu digits: preimage 2 × (497k path + 4 × 15,072
+ 56) + 2 × (2 × 15,072 + 56) ≈ 1.18M; leanSPHINCS adds 2 × 6.39M + 8 × 15,072 ≈ 13.9M.

To finish: (1) template option lines after the leanSPHINCS ones, values `future_preimage` and
`future_leansphincs`, labels "a future protocol without Pasta: 2 inputs by BLAKE3 preimage, 2
outputs" and "... 2 inputs by leanSPHINCS (BLAKE2s), 2 outputs"; (2) a paragraph in the
application subsection after the wallet-share paragraph, stating the assumptions above and
carrying every figure named here plus `<!--claim:future_preimage_quarter:000000-->`; (3) a
mention in the Transaction prover measure's sentence (the one listing the applications);
(4) `ruff format`, `python pareto-model.py --fill`, the default run, `nix develop --command
scripts/build-book.sh`, then commit model + template ("pareto: a future spend protocol without
Pasta as applications"), republish pareto.html to the artifact, and a notes entry with the
figures. The alpha-sweep claim (alpha_page_near_optimum) covers every page application but
`qk`; if the new ones break its three percent, exclude them as `qk` is excluded, with a reason.

## 2026-11-21 17:01 UTC: Zoodles named and rebuilt on Tachyon's architecture; the BLAKE3 AND counts split

The user named the Pasta-free sketch Zoodles, after the pasta-free noodle, and the model's
keys are `zoodles_*` (bc26c38 priced the first cut: two inputs by preimage or leanSPHINCS,
two outputs, a Merkle path in each spend; 1.18M Kishu digits, 0.398 s with zero knowledge at
rank 19 against 14.1M and 1.77 s).

The BLAKE3 to BLAKE2s ratio (the user: "should be roughly 7/10"): 0.71 in digits and 0.70 in
prime-field gates, but 0.76 in AND gates, because BLAKE3_ANDS was 8,192 and BLAKE2S_ANDS
carried 512 finalisation XORs. Flock's paper (§4.1) lays a batch out as a stack of
per-instance blocks of 2^m0 committed bits, and a BLAKE3 compression's 6,944 carries (31 per
32-bit addition) and 896 input bits fit a block of 2^13, which is where 8,192 came from; the
paper's 82.1k compressions a second is at that layout, and the 1.5 × 2^14 Keccak batches are
three permutations packed per block of 2^17. Commit c1d85d5: `BLAKE3_ANDS_PADDED` = 8,192
where the count is Flock's witness or hypercube (the per-bit rate from the measured batches,
the base matrix's 13 sum-check rounds, the F2 merges' hashes, BitZ's HASH_BITS, the
Boolean-over-Akita merge's transcript hashing); `BLAKE3_ANDS` = 7 × 8 × 4 × 32 = 7,168 for the
applications, where the 2^22 step does the padding; `BLAKE2S_ANDS` = 10,240. Figures moved:
a path 240,000 AND gates (was 270,000), the device statement 7,170 (8,190), the Keccak to
BLAKE2s Boolean ratio 3.3 (3.1); the Boolean rows' seconds did not, since their applications
fill the same number of 2^22-gate steps. Not done: counting a compression's input bits in the
Boolean unit (hash_app_cost leaves them free there), and Flock's block padding on the
applications (4.5 percent for BLAKE3, about one for BLAKE2s at three per 2^15, 8.5 for Keccak
at three per 2^17).

Tachyon's membership technique, from the source at 73031f7 (stamp/proof/spendable.rs,
evidence.rs): no Merkle path over note commitments in a spend. The spendable header is
(cm, epoch, anchor); SpendableInit opens the creation stamp's tachygram-set polynomial at cm
and enforces zero and folds the anchor (a Poseidon hash chain over the stamps' bridge hashes);
SpendableLift advances over NoteUnspent segments that open each epoch's sets at the nullifier
and enforce nonzero. The evidence tree is a quaternary Poseidon Merkle tree over sealed
buckets for the sync service (EvidenceTreeDescend walks four levels a step), not something a
spend proves. The technique needs only a binding polynomial commitment opened at a
circuit-chosen point, Schwartz–Zippel at ζ, and a hash chain, so it ports to Akita or Kishu
unchanged; the instantiation does not: the set polynomials are Pedersen vector commitments
under Ragu's host generators and the bridge hash a Pedersen hash onto Pallas. The page's
Tachyon rows keep the value commitments and rk on Pallas too, so they are Tachyon's circuits
in a post-quantum proof system, not a post-quantum protocol.

The user: a post-quantum Tachyon with the set commitments as the PCS's own and BLAKE3 for
the plain hashes, plus the dynamic fee, is what Zoodles is; the simpler Merkle-path version
stays as a note that it still beats Tachyon on the transaction prover. Commit 70cd427:
Zoodles is Tachyon's tree without the rerandomization (12 nodes for two spends and two
outputs), priced per node as BLAKE3 compressions, roots or products of set polynomials,
openings at the challenge and bits (ZOODLES_NODES): a spend's bind step derives two epoch
nullifiers (2 compressions) and range-checks the epoch (20 bits, Tachyon's EPOCH_MAX + 1 =
2^32/4096) and the amount (51); its action step derives the payment key (1) and roots the
nullifiers (2 roots, 1 opening); an output's bind step hashes cm and pad (4) and its action
step roots them; a merge multiplies the sets (1 product, 3 openings) and sums the amounts (64
bits); the fee step hashes the change note (2), range-checks slack, fee and change, and roots
the change commitment (1 root, 2 openings). A tachygram is an element of a 256-bit extension
of the claim field (Pasta itself; quadratic over a 128-bit field or Kishu's E; quartic over
Goldilocks), so a root is 1, 3 or 9 claim-field multiplications (claim_mult_cost: a gate, a
CLMUL_ANDS[128] product, or E_MULT_DIGITS), and an opening one more claim: CLAIM_BYTES
absorbed by the merge above plus CLAIM_GATES multiplications, 4,410 Kishu digits. The
leanSPHINCS variant adds the verifier to each spend's action step and the 8-compression digest
to the fee step. The lineage runs in the background and is not counted, as Tachyon's is not.
The Merkle variants (`zoodles_merkle_preimage`, `zoodles_merkle_leansphincs`, the second at
the user's request for regularity) open the note in the spend, derive one nullifier and the
payment key, prove the path under the policy, and have the fee step too. The packing rule that
gave Tachyon's rerandomization its own step was giving Zoodles' fee step one as well, which
doubled the hash-based rows' Zoodles figures (two steps of 2^22 gates for one circuit); now
only the trees in OWN_LAST_STEP (DATA.own_last_step, the page's txStepsFor mirrors it) have a
last node of their own. Q64_DIGITS, E_MULT_DIGITS, the Poseidon-q64 constants, RANGE_CHECK_*,
absorb_digits/absorb_piop and CLMUL_ANDS moved before the applications, which price with them.

Figures, transaction prover on one core, two inputs and two outputs; Tachyon's four
tachyactions beside:

| family | Zoodles, preimage | Zoodles, leanSPHINCS | Merkle, preimage | Merkle, leanSPHINCS | Tachyon |
|---|---|---|---|---|---|
| Kishu digits | 313,000 | 13.2M | 1.21M | 14.1M | 1.22M |
| Kishu zk | 0.223 s (rank 19) | 1.77 s (21) | 0.398 s (19) | 1.77 s | 0.531 s |
| Kishu | 0.0593 s | 1.06 s | 0.149 s | | 0.265 s |
| BitZ zk | 0.0770 s | 0.254 s | 0.0903 s | | 0.180 s |
| Boolean over Akita | 0.193 s | 0.387 s | 0.193 s | | 10.2 s |
| Flock | 0.169 s | 0.338 s | 0.169 s | | 8.97 s |
| Akita Goldilocks, Poseidon tree | 1.03 s | 52.0 s | 0.905 s | | 8.02 s |
| Pedersen-IPA, Poseidon | | | 44.3 s | | 6.33 s |

Zoodles by preimage is 42 percent of Tachyon with zero knowledge in Kishu, the Merkle variant
75; claims zoodles_preimage_beats_tachyon and zoodles_merkle_beats_tachyon (Kishu with and
without zk, BitZ zk), zoodles_merkle_paths_most, zoodles_preimage_quarter. The Pasta-native
rows reverse the order (a path's hashes cost a prime field more than the curve), and Flock
pays 53 times more on Tachyon than on Zoodles (the Pallas multiplications in a Boolean
circuit). The α sweep now includes the Zoodles applications; the page's 48 stays within its
bound. Artifact version 191. The page's self-check (DATA.tx_checks against txWork) is empty
in headless Chrome (--dump-dom); next time pass a scratch --user-data-dir and
--disable-features=MediaRouter --disable-background-networking, since Chrome's startup
discovery raised the OS's local-network prompt for the terminal.

Assumptions to revisit: the set polynomials over a 64-bit field need the quartic extension
(or four polynomials) for 256-bit tachygrams, and ζ in that extension; an opening priced as
one more claim ignores that a committed online vector per step adds a group to the fold; the
Boolean families' claim field taken as F_{2^128}; the lineage's per-epoch cost (unspent
segments, bucket openings) is the real price of dropping the path and is not modelled;
Zoodles' sighash binding for the preimage route is the signature-of-knowledge argument of the
hardware-wallets chapter.

STATE: main at this entry's commit; eight commits after a49be05 unpushed (c87382c, 71fa025,
c6cbbf3, eb88548, 845248c, bc26c38, c1d85d5, 70cd427, and this one). PENDING: as before
(the soundness note's review, the 2026-11-14 modelling questions, the Tachyon gate
classification, k-ary merges, Kishu with binary groups, the lattice estimator on the 5,000-bit
padding, the host's zk-layer merge for the three-way fold, the linking commitment in qk, an
MPCitH row), plus the Zoodles assumptions above and the Boolean unit's input bits and block
padding.

## 2026-11-21 17:50 UTC: the lineage step as an application; the frontier collapse checked; leanSPHINCS pruning

The user asked for the wallet's witness update as an application (521490d, `zoodles_epoch`):
one note's lineage advanced one epoch of 4,096 blocks (3.6 days at 75 s), Tachyon's UnspentLift
read from stamp/proof/pool.rs and qr.rs. The step takes the epoch's bucket proof as its right
input (a bucket: one quadratic-residue profile's share of the epoch's tachygrams, at most 2^13
members, Tachyon's online slot, built once per epoch for everyone), tests the nullifier's
profile at QrProfile::MAX_DEPTH = 32 positions (a squaring and a selection each), opens the
bucket's contents at the nullifier and enforces nonzero (a private point: the merge above
evaluates the point's tensor, 2 × 13 multiplications), appends the member to the elapsed
sequence (two openings and a root), range-checks the epoch and derives the epoch's nullifier
(one compression). The bind, lift and fuse steps that close a segment run once per spend and
are left out. The step's own circuit is 40,200 Kishu digits; the bucket's 8,192 tachygrams are
2.10 million bits or digits, folded element by element by every lattice and hash-based row
(zoodles_bucket_units; Pasta's unit carries the step's gates alone, since Pedersen-IPA folds the
builder's commitment, which understates Akita's Pasta-claims rows). Figures: Kishu 0.262 s a
note an epoch at rank 20 without zk (the lineage never leaves the wallet), BitZ 0.107, Flock
0.169, Akita over Goldilocks 0.259, Pedersen-IPA 3.56 s; 12 percent of the Kishu figure is
committing the bucket's digits, the builder's work. Consequences in the text: the lineage's
accumulator stays at the bucket's rank and the spend inherits it (Zoodles by preimage with zk
at rank 20: 0.351 s against 0.223 at 19) unless the buckets are sized to the spend's rank; a
sorted Merkle tree over an epoch of 2^24 tachygrams would make the exclusion proof 24
compressions, 362,000 digits, under a fifth of the bucket's, with no profile revealed to the
server (claims zoodles_epoch_bucket_most, zoodles_sorted_tree_cheaper). Set polynomials suit
Pedersen, where a commitment folds in one multiplication, not digits.

The frontier collapse is not broken (the user: F2 recursive points with small proofs drop out
when "within each family separately" is unticked). work/frontier-probe.py reproduces the
page's rule (a dominator has bytes, second and third measures at most the point's, Pasta
support at least, and not all equal) over the page's selection. In the user's state (second
measure the transaction prover on the Merkle-path Zoodles by preimage, third the accumulation
prover, floor 128, zk, conventional hashes, default families) 5 of the 34 F2 recursive rows are
on their own frontier and 1 on the class frontier; the other 4 are dominated by Kishu rows
(69,285 B at rank 21, accumulation prover 4.15e8, transaction 1.83e9) against the best F2
recursive proof of 77,376 B at rate 1/64 (4.19e9, 4.48e9). Kishu's smallest proof is smaller
than every F2 recursive proof; the impression came from comparing with BitZ (510 kB) and Flock
ARC (125 kB), which survive on other measures. The table's Frontier column says "family" for
such rows.

leanSPHINCS pruning, from formal/sphincs/README.md and Scheme/Pruning.lean (the user is a
SPHINCS co-designer and asked for the construction): d = 1, height h = log2(lifetime) − 4 (26
at 2^30), WOTS+C leaves (64 chains × 4 positions, target sum 128) each signing a two-level WOTS
forest of T = 8 trees (or FORS); one digest hash gives h index bits + 26T forest bits;
signature 16 + 352T + 1028d + 16h = 4,276 B. Keygen builds only a subtree of height b at a
seed-chosen position and fills the h − b spine siblings with surrogates, seed-derived digests
with nothing beneath: 226·2^b + 2(h − b) hashes. Signing walks R0, R0 + δ, … (δ odd, both from
H(seed, m)) until the index lands in the kept subtree: 2^(h−b) digests expected. The verifier
is unchanged and cannot tell a pruned key from a full one (the slides' privacy property).
Lifetimes at 127 bits, h = 26: full 1.38e9, b = 20: 26.0M, b = 14: 480,100, b = 12: 126,900,
b = 8: 8,830, i.e. 20.6 to 34.5 signatures per leaf: 14 bits of grinding buy about 1.5× the
load per leaf. Against a plain tree of height b (the README's rule 21.45·2^h in the cover
model at the proved shares, an extrapolation below h = 20): matching 126,900 needs about 0.8
more levels, 1.7× keygen once, against 16,384 digests per signature, 224 bytes and 14 verifier
hashes (0.3M Kishu digits, 5 percent). The user's points: the leaves are seed-derived, so a
full root computed at keygen lets the signer regenerate any subtree later and choose or widen
its landing region at will (the surrogates exist only to avoid the full keygen on a device);
and the device need only produce the leaf hashes (226 per leaf, secret-dependent), the host
building and storing the tree and serving paths. Then no grind is needed, the lifetime is the
full key's, and the device's cost is keygen: 226·2^h hashes at the Nano S+ rates (BLAKE2s
32.6k/s, Keccak 5.8k/s): h = 12: 28 s / 2.7 min; h = 16: 7.6 min / 43 min; h = 18: 30 min /
2.9 h; h = 20: 2 h / 11.5 h; the leaf export 16·2^h bytes (16 MB at h = 20, 13 min at 21 kB/s).
Open: the pruned theorems assume surrogates; with real unused subtrees in their place the
forger gains only zero-load instances, to be checked. Also noted (the user): the Merkle paths
matter far less than the signature: per spend 33 BLAKE3 compressions against 298 BLAKE2s, 9×
in count and 12.8× in digits; in time the two paths add 0.18 s and the two signatures 1.55 s
to the Kishu zk transaction; a BLAKE3-based leanSPHINCS would still be 9× the path.

STATE: main at this entry's commit; eleven commits after a49be05 unpushed (through 521490d
and this one). Artifact version 192. PENDING: as the previous entry, plus: the lineage's
rank coupling with the spend (bucket size as a parameter), the sorted-tree exclusion proof as
an alternative lineage, the bind/lift/fuse steps per spend, the Boolean unit's input bits and
block padding; the hardware-wallets chapter could take the host-assisted keygen point.

## 2026-11-21 18:06 UTC: the security assumption as the second dominance requirement

The frontier check above led the user to the real gap: a lattice row could dominate a
hash-based one although it rests on an extra assumption. Now (the commit before this one) the
dominance test is Pareto dominance on five axes, bytes, the two chosen measures, Pasta support
(more is better), and the assumption level (less is better: 0 a random oracle alone, the
hash-based families; 1 Module-SIS with a random oracle, Akita's and Kishu's rows and
Pedersen-IPA in its own class; 2 the Boolean-over-Akita row, whose security ledger is open, so
it can dominate nothing, the user's ruling), a dominator being at least as good on all five and
better on one. The old rule required the strict improvement on one of the three costs; the
user asked that the two requirements behave as separate axes, so the strictness now runs over
all five (`ASSUMPTION_LEVEL`, `p["assumption"]`, `pareto()`, the page's `frontierAmong`; the
section "Pasta and the assumption as requirements" says so; the lede's "Akita dominates" the
WHIR-type families became "beats", since it no longer dominates them). In the page's default
state the frontier table has 57 overall rows and 8 family-only rows; the model's own printout
is unchanged (its measures are bytes, prover and atoms, where no hash-based row was dominated
by a lattice row). Artifact version 193. The commit's sentence on the ranking was reworded
at the user's request for its mixed commas.

STATE: main at this entry's commit; thirteen commits after a49be05 unpushed.

## 2026-11-21 18:18 UTC: the changes needed as the third dominance requirement; Oxford commas

The user: "parameters only" is another dominance axis. Now (the commit before this one) the
dominance test runs on six axes: bytes, the two chosen measures, Pasta support (more is
better), the assumption level, and CHANGE_LEVEL (none 0, code 1, design 2; less is better),
a dominator at least as good on all six and better on one. With the changes as an axis the
best parameter-only configurations are on the class frontier by the rule itself, so the union
of the class's frontier with its parameter-only frontier, and the table's "parameter-only"
label, are gone: the Frontier column says "overall" or "family". The requirements section
(id `requirements`, was `pasta`, the user having caught a link whose anchor still said Pasta)
describes all three requirements; the lede names them. In the page's default state the
frontier table has 58 overall rows (57 with the assumption axis alone) and 8 family rows; the
model's own printout rose to 9 Pedersen-IPA, 210 post-quantum and 234 zero-knowledge frontier
points. The user asked for Oxford commas in lists (the commit message's "Pasta support, and the
assumption"); the earlier commits' lists and this file's were fixed by fixups folded in with an
autosquash rebase from c1d85d5, and the model's and page's rule comments reworded to shorter
sentences. Artifact version 194.

STATE: main at this entry's commit; fifteen commits after a49be05 unpushed.

## 2026-11-21 18:52 UTC: the transaction prover on both measures

The user asked to choose two transaction applications at once (the commit before this one):
the transaction prover is never greyed out on the other side, so both measures may be it, each
with its own application list (`#txapp2`, `#txapp3`; the third's options are a copy of the
second's made by the script). A point carries `transaction_second` and `transaction_third`,
the measure keys the sides read (`measureKey`); the axis titles name the application
(`txShort`, the option text cut at a colon or parenthesis); the hover and the table's
Transaction column show the sides that have the measure; the header is forced to nine when
either side's application is a Tachyon transaction or the recovery circuit; the swap button
exchanges the applications with the measures. The lists: one at full width when one side has
the measure, both side by side (eyebrows "Transaction prover, second" and ", third") when both,
and with neither the second's list alone under "Transaction prover: the transaction proves",
the hidden third following its value. A `[hidden] { display: none !important }` rule was
needed: the groups' `display: flex` beat the attribute, so both lists showed at first (the
user). The user's stale book build had shown TypeErrors and no plot; a reload fixed it, and
headless Chrome and Firefox (work/firefox-errors.py, work/firefox-txapps.py, which drives the
three states) show no errors. The user: "it's now possible to see which schemes favour
particular transaction types". Artifact version 196.

STATE: main at this entry's commit; everything through 1388a24 was pushed by the user; the
two commits after it are unpushed.

## 2026-11-21 19:33 UTC: prose revisions around the frontier and the measures

A round of wording changes at the user's requests, after the two application lists landed
(a7993f2), squashed into one commit at the user's request:

- The lede's paragraph on a point's coordinates, the settings, the two frontiers and the
  unticked families moved under the plot, headed "The frontier plot" (id `frontiers`, so the
  Frontier control still links there). Its "frontier" link, which had low contrast against the
  lede's grey, went with the move, and the lede now says only what the page costs.
- The "Frontiers" heading went. The frontier's definition, the six-axis test naming the three
  requirements, follows that paragraph directly, in place of the stale sentence that the
  frontier was taken on bytes and the two measures alone.
- The requirements section is "Pasta and the scheme assumption" (id `requirements`). The
  changes requirement has its own section in place of the redundant "Parameter changes
  against design changes" paragraph, which kept its table and per-family sentences.
- The seven measures are listed once each, with semicolons; the transaction prover had
  appeared twice. The defaults have a sentence of their own.
- The changes axis's example sentence ends at "for example".
- The open security ledger "is treated as making a stronger assumption".
- The Tachyon rows are described as Tachyon's own circuits, a pre-quantum protocol proven in a
  post-quantum proof system: not a deployment, which Zoodles is, but the same application for
  comparing the proof systems. The measure's paragraph, the Tachyon section and the model's
  comment say so; the comment was rewrapped.
- A link in the lede, should one return, takes the ink colour with an accent underline (its own
  commit, after the squash), since the link colour read poorly against the lede's grey.

Artifact version 204.

STATE: main at this entry's commit; everything through 2f83321 was pushed by the user; the two
commits after it are unpushed.

## 2026-11-21 19:47 UTC: the masked accumulator and the memory measure

The zero-knowledge section's "Not modelled: the masked accumulator itself, about 14 Mbytes
against 1.6 Mbytes" read as if the ordinary accumulator were unmodelled too (the user). The
accumulator memory measure counts the ordinary accumulator at the handoff's norm bound, 21 bits
a digit; the two figures in that sentence are the zero-knowledge note's digit vector and its
masked slices packed at 3 bits a base-8 digit, so the sentence now says what the measure counts
and that both figures are in digit slices (the commit before this one). Artifact version 206.

STATE: main at this entry's commit; everything through dde4643 was pushed by the user; the two
commits after it are unpushed.

## 2026-11-21 19:56 UTC: the statements of what is not modelled

The user asked for every statement that something is unmodelled to be checked (the commit before
this one). Checked on the page: the Boolean row's fold sentence and its "Not modelled" list, the
planner's 2^14 groups, the merges above the zero-knowledge layer, the masked accumulator (fixed
earlier), the F2 zk mask's commitment, the mask-width sweep's omissions, the linking
commitment in qk, the Zoodles lineage, the Tachyon bit-priced gates and per-note steps, and the
estimator's dimensions for free; in the notes files, the planner's two statements. Three were
wrong:

- The Boolean-over-Akita row's merge left out the Flock PIOP verifier "as for the F2 family",
  but the F2 family's merge has counted it since 3e24191. The merge now counts the two inputs'
  verifiers at a fixed point of its own size (bits_akita_merge_parts): 1.5M of 4.1M AND gates
  (was 2.7M), 6.9 times fewer than the F2 ARC merge at rate 1/8 (the "a ninth" claim is now a
  figure with a smaller-than claim); the row's prover 5e7, decider 5.34 ms, proof 85 kbytes,
  and the Zoodles figures 0.289/0.578 s. The merge paragraph's parts (transcript 2.7 kbytes,
  hashing 0.35M, fold 0.27M, sum-check 2.1M, verifier 1.5M) are generated figures with a claim
  that the sum-check multiplications dominate.
- The Zoodles paragraph said the lineage's steps were not counted, although `zoodles_epoch`
  prices one epoch; the sentence and the model's comment now say they are not in the
  transaction and point to it.
- BitZ's model comment said its PIOP and GKR verifiers were a few thousand constraints not
  counted; its hybrid merge commits their products (bitz_point), so the comment says that.

Also: the Tachyon section's per-note sentence points to the Zoodles lineage step as their
counterpart; two sentences describing the Boolean row's fold as a change describe the present.
Artifact version 207.

STATE: main at this entry's commit; everything through dde4643 was pushed by the user; the four
commits after it are unpushed.

## 2026-11-21 21:01 UTC: why zero knowledge is dear in Kishu; the stage groups; Akita's groups; the Neo paper

Nothing committed in this stretch beyond the notes; it is analysis towards a model change.

**Zero knowledge in Kishu.** The user: the masking fold was inherited from Ragu's Pedersen version,
where zero knowledge is nearly free; for Kishu it is most of the cost, so it deserves optimizing
(the conclusion reached for the hardware wallet applies generally). At rank 19, Zoodles by
preimage is 0.062 s plain (step 0.009, merge 0.051) and 0.223 s with zk: step 0.017 and merge
0.069 under the masked matrix's 2.45× rows, and the fold 0.136 = sampling 0.028 + the mask's
commitment 0.066 + the fold's merge 0.041 (work/zk-parts-probe.py). Why: hiding in lattice
accumulation means masking the witness (the aggregator must receive a foldable witness; Ulrich's
"the mask is witness-size"), the mask runs over the whole accumulator, K = 6 groups of 2^rank,
and each mask coordinate is a 27-bit sample committed at the masked rank (49 wm against 24 for a
bit), so one attempt costs about seven times committing the step. Levers: the mask's length (see
the stage groups), §5.8 deferral of the fold's merge to the aggregator (0.041 s), §5.9's separate
matrix for the 2.45× (0.026 s here), block masking for the bound.

**The masked accumulator's memory.** Could be the zk rows' accumulator memory; the note masks a
fresh small-digit witness (‖s‖₂ ≤ 2^13, N = 2^22 digits), as a one-step transaction has, so the
masked response is 9 slices × 3 bits = 27 bits a coordinate against the measure's 21 at the
handoff bound: 1.3× the measure (10.6 against 8.3 Mbytes for Kishu at rank 19); the note's "14
against 1.6 Mbytes" compares to the fresh digits at 3 bits. Neo's Π_DEC (below) re-decomposes the
folded witness into k binary pieces after every fold, the same small-digit convention. The first
level's extra auxiliary digits need the planner run at the masked rows (the catalog pipeline).

**The stage groups.** K = STAGES + 1 = 6: the fuse's five stage polynomials, committed
separately because a challenge is drawn between them, plus one batch of every step circuit's
witness (Akita opens a batch at the cost of one). In Ragu the trace r(X) = a(X) + … + f(X) splits
by wire position; a stage holds its values at the a and d wires of its reserved gates (two a
gate, `stage_gates`), zero elsewhere, and bonding circuits enforce the non-overlap; so a stage's
zeros are structural and public. Sizes from Ragu 8109a41c (`values()` of each native stage), for
the Standard profile (2 online polynomials, 6 online queries, 39 unified wires, 4 binders, 23
fixed and 48 rx polynomials, 28 fixed and 53 internal circuits with the walk's 25 steps, 103
claims in 15 fold groups of 7, sponge width 5): at header 9, preamble 2 × (3·9 + 12 + 1 + 39) =
158, query 53 + 1 + 2·(48 + 5) + 12 = 172, eval 2·(48 + 4) + 6 + 6 + 2·3 = 122, inner error 15 × 6
= 90, outer error 14 + 15 + 8 + 5 = 42: 584 values in all (about 1,100 at header 96); only the
preamble depends on the header. The model charges the five stage groups as dense 2^rank vectors
in the mask (K·2^rank) and in the fold's sum-checks (accumulation_sumchecks over K·2^rank); the
planner's bytes already treat them as small. Correcting both at rank 19: the mask's sampling and
commitment 0.094 → ~0.016 s, the fold's sum-checks in every merge 0.023 → ~0.004 s; Zoodles by
preimage ~0.11 s with zk and ~0.04 s without, and every lattice row's accumulation prover moves.
The user asked that Akita's grouped opening admit unequal group lengths: the paper says "every
group uses the opening method prescribed for the fold's absolute level, though the groups'
dimensions and points may differ" (work/akita.txt line 3182), its planning policy sets per-group
size limits, and the opening profile follows "the shapes of separately committed objects"; its
density options are the source kinds, dense, one-hot and binary, which do not matter here: a
stage is a short dense source of its support's length. The lattice fuse's stages, an estimate,
carry the same kinds of values.

**Neo and SuperNeo (keep/2026-242.pdf, ePrint 2026/242, cited by Akita [82, 83]).** Lattice
folding for CCS with Ajtai commitments: norm-preserving embeddings of field vectors into ring
vectors (Neo along coefficient slots; SuperNeo packed, a transform making a ring product simulate
a field inner product), pay-per-bit commitment cost (a bit costs the added rotations where it is
nonzero), a field-native sum-check over F_{q^2}, Π_RLC then Π_DEC, which splits the folded
witness base b = 2 into k pieces, each committed; parameters at Goldilocks (d = 54, Φ = X^54 +
X^27 + 1, κ = 18, k = 14, B = 2^14, 129 bits), Almost Goldilocks (d = 64, κ = 15, k = 13) and
M61. No zero knowledge. Akita cites it for pay-per-bit and takes SuperNeo's strong/weak
reduction interfaces for its extraction (akita.txt 7034–7065); Akita handles the ring's partial
splitting itself (its §1599–1622), so Neo's remark on fully splitting rings is not an issue for
Akita's X^64 + 1 as far as the paper goes. Under pay-per-bit a mask coordinate costs like 27 bits
against 1 for a witness bit, worse than the model's 49 against 24; Akita's NTT-style commitment,
as the model prices it, is value-independent.

NEXT: implement the stage-support correction (STAGE_VALUES from the formulas above; the mask and
the fold's sum-checks over 2^rank plus the stages' supports in the variant's digits; the memory
measure likewise), then the §5.8 deferral as Kishu's zero-knowledge route and the masked
accumulator at 27 bits a coordinate as the zk rows' memory, with the text rewritten; then re-read
the zero-knowledge figures and claims. Probes: work/zk-parts-probe.py, work/frontier-probe.py;
the Neo text at work/2026-242.txt.

STATE: main at this entry's commit; everything through dde4643 was pushed by the user; the five
commits after it are unpushed.

## 2026-11-21 23:54 UTC: the accumulator's length, the leaf handoff, the digest, peak fuse memory, the width

Nine commits after 385528c, ed01f37 to 737e690, all on main.

- **The Akita paper has a reference key**, [DBK+26] (ed01f37).
- **The stage groups are priced at their support** (fc896ed). A stage holds its values at the
  wires of its reserved gates and is zero elsewhere, so what is committed and folded is its
  support: 584 values at header 9 (STAGE_VALUES; preamble 2 × (3·9 + 12 + 1 + 39), query 172,
  eval 122, inner error 90, outer error 42, from Ragu 8109a41c), a claim-field element each (two
  coefficients over Goldilocks, 128 bits in Kishu and the binary groups). Akita's grouped opening
  admits groups of different dimensions ([DBK+26], §5).
- **The batch group is circuits × 2^rank** (aa2e515). The user asked why Pedersen's accumulator
  memory was so high (it is the measured uncompressed proof, 96 polynomials of 2^13), which
  exposed that the batch group was 2^rank in the mask, the sum-checks and the memory but
  circuits × 2^rank in the opening and the merge's one image. The user ruled for circuits ×
  2^rank (accumulator_coefficients). So the accumulation prover, the fold and the memory are
  nearly flat in rank until one circuit holds the merge (rank 21 for Kishu) and double per rank
  beyond. Kishu's recovery 0.399 s plain, 0.743 s zk, both at rank 21 with five merges; Pasta
  claims 26.8 s at rank 17 with Poseidon, 1,980 s under BLAKE3; Zoodles by preimage 0.186 s zk.
- **The device statement masks its leaf alone** (d6f1616; the user: the wallet proves one
  circuit). LEAF_HANDOFF = {qk}, a row's fold_leaf over 2^rank digits, DATA.leaf_handoff in the
  page's txWork; qk 0.113 s at rank 16, 56% the host's merge, 38% the fold.
- **The Zoodles signature's digest** (2b62fce; the user's design). The preimage check needs no
  digest, being proved inside the spend step that the tree binds. A signature's message must
  bind the effecting data: each spend's two nullifiers, each output's commitment, the change
  commitment, the fee, and the epoch, 235 bytes or 4 compressions, not 8. The prover passes it as
  a PCD header, each spend verifies its signature over it, and the fee step recomputes it from
  the tachygrams as a witness, re-rooted against its children's set products (8
  multiplications). The paddings need not be in it (the user: the digest is never visible outside
  the step). The figures barely moved.
- **Peak fuse memory** is the eighth measure (b619b23; the user's definition): two accumulators
  with the output over one, the second-round sum-check table (half the digits as claim-field
  elements, the first round streamed), the mask at 27 bits a coordinate under zk; other rows
  two accumulators. Kishu rank 21: 36 Mbytes zk, 29 plain; Pasta claims rank 17: 238; Pedersen
  rank 13: 50. Radios, hover, table (16 columns), pruning, an axes section.
- **The width stays 48** (dd91f26). The user asked to re-optimize α. With the accumulator at the
  merge's size the optima spread from 13 (recovery with four inputs) to 91 (Zoodles by preimage,
  whose fold is most of its cost); 48 is the minimax of the widths with nine slices: the worst
  application 2.7% off its least, against 4.3% at 32 and 8.3% at 24 (claim alpha_page_minimax);
  at Karney's rate 20%. Akita's estimator at the other bounds (work/pasta-rank-alphas.log):
  40.2 → 317 Pasta rows / 1,257 at q64; 40.6 → 323 / 1,282; 41.2 → 333 / 1,320; 41.6 → 340 /
  1,346; 42.2 → 349 / 1,385, within 1% of the (log β)² rule throughout.
- Copy-edits in the Zoodles paragraphs (1f28a3f) and the chapter's correction (737e690): the
  pruned key's grind is the wallet's, since it is keyed and the key would reveal the kept leaves
  (the user); a full tree with the host building and storing it has no grind.
- Explained on the way: the printout's Kishu rows at 17 and 21 only (its frontier is bytes,
  prover and atoms; ranks 18 to 20 chop the same 2^21 digits); the peak estimate and the
  in-place fold.

NEXT, from the user's remarks:

- Does Zoodles need a 9-element header? The header could be the recovery circuit's size, with
  Zoodles fitted in it.
- The lineage should not use set polynomials over digits ("no need to use polynomials here"),
  so re-price zoodles_epoch as the sorted Merkle-tree exclusion proof, two neighbours and their
  paths, with smaller epochs than 2^24 tachygrams (the user's intuition). The trade-off is steps
  per note against tree height.
- The frontier page's hardware-wallet paragraphs belong in the hardware-wallets chapter, which
  exists (the user, on being reminded of it).

Still open: the §5.8 deferral as Kishu's zero-knowledge route; MASK_LOG_N = 22 is the note's N,
so a per-row N would shave the rank factor for small accumulators; and the older list.

STATE: main at this entry's commit; everything through dde4643 was pushed by the user; the 15
commits after it, this one included, are unpushed. Artifact version 208; the book builds.

## 2026-11-22 00:26 UTC: the hardware-wallet paragraphs move to the chapter

The frontier page's two hardware-wallet paragraphs (the device statement and the leanSPHINCS
verifier in detail, the host proving the handoff, the device's share and the transfer) are in
the hardware-wallets chapter, which already had nearly all of it (the user: the material should
move there). The page keeps one paragraph: the two applications' costs in each arithmetization
and a link to the chapter. The claims qk_merge_and_fold, qk_device_share_small and
leansphincs_keccak_dearer sit in the chapter's sentences now, with the Boolean ratio and the
zero-knowledge timings. The `noteref` span takes `data-note` (NOTE_CHAPTERS: zk,
hardware-wallets), so the page links any note's chapter in the book and shows text standalone.
In the chapter the QR-code section is §2.1.1 under the Kishu leaf, since it applies to that
route alone, and the signature is §2.2 (the user).

STATE: main at this entry's commit; everything through dde4643 was pushed by the user; the 17
commits after it, this one included, are unpushed. Artifact version 209.

## 2026-11-22 01:36 UTC: the lineage as a sorted tree, the masked bound per row, the §5.8 deferral

Four commits, in the order the user chose: the lineage first, then the deferral, with a digest
correction and the per-row bound between.

- **The lineage is a sorted Merkle tree** (9fd0791). The user agreed that set polynomials are the
  wrong tool over digits, so `zoodles_epoch` is the exclusion proof from a sorted tree over the
  epoch's tachygrams: the builder hashes consecutive pairs into the leaves, and the proof is one
  leaf (the nullifier's two neighbours) with its path, plus the nullifier derivation, two
  256-bit comparisons and the epoch range check. The tree holds 2^20 tachygrams an epoch (the
  user's choice; 256 a block at Tachyon's 4,096-block epoch), 22 hashes, 332,000 Kishu digits,
  under a sixth of the bucket's 2.10M, which stays as the comparison. Kishu 0.052 s a note an
  epoch at rank 19, the zero-knowledge spend's own rank (claim zoodles_lineage_rank_is_spends),
  so the rank coupling is gone; Goldilocks 0.050, BitZ 0.077, Flock 0.169, Pedersen 6.33 s.
  `tree_path_cost(field, hp, levels)` scales the 32-level path by (levels + 1)/33.
- **The digest without re-rooting** (cabbd77; the user caught the stale sentence). The fee step
  hashes the nullifiers and commitments its children's headers carry, as the Merkle variant's
  did; ZOODLES_SIGHASH_ROOTS went. Built from a saved copy of the model so that it could be a
  commit of its own.
- **The masked bound at each row's own N** (cd8c4bb). `masked_log_beta`, `mask_rank` and
  `ajtai_per_coefficient` take `log_n`; the Akita rows pass their accumulator in digits, Kishu
  its bits, the width table and the device leaf their rows'. The factor ranges 2.4 to 3.1 over
  the lattice rows (figures mask_rank_min/max); Kishu's accumulator is just under 2^22 bits, so
  its masked rate fell from 49.3 to 48.4 word multiplications a digit and the recovery from
  0.743 to 0.733 s. The note's figures keep MASK_LOG_N = 22.
- **The §5.8 deferral** (37eaff2). The user's handoff merge is the challenge derivation (the
  mask's K images and its claim evaluations absorbed), the commitment identity on the images, and
  the claims' fold, in whole step circuits of the rank at the masked rate (handoff_merge_cost,
  handoff_merge_digits); the decomposition and the range and norm proofs are the aggregator's
  first fold's, already in the zk-layer merge. The saving is where the merge spanned several
  circuits: qk 0.111 → 0.079 s (fold 13%, the host's merge 78%), Zoodles by preimage 0.184 →
  0.154 s, two tachyactions 0.310 → 0.290. Where one circuit held the merge the handoff still
  fills a whole circuit, so the recovery stays 0.733 s: the padding to the rank's step is the
  floor. The wallet's online share is under a tenth of its fold (was a twentieth). The width
  sweep moved: optima 13 to 130 at the page's sampler, 48 still the minimax (2.8%; 6.4% at 32,
  11% at 24).
- **Discussed, not modelled:** leanSPHINCS's verifier hashes split 184 forest / 64 chains / 17
  leaf / 26 path / 6 other of 298; the WOTS forest beats FORS (184 against about 271 under the
  same call format); levers are a forest sized to the real lifetime (the Lean lifetime proof is
  parameterized), or a stateful one-time leaf with indices partitioned by member (about 110
  compressions; state loss on restore is the hazard); Jive gains nothing with BLAKE2s, a few
  permutations with Keccak, and in Kishu Poseidon costs about what BLAKE3 does per call. The
  pruned key's grind is keyed and stays on the wallet.

NEXT: Zoodles' header (does it need 9 elements; the recovery circuit's is six or seven), with a
node-by-node inventory first; the handoff merge's padding (a smaller rank for the handoff step
would need a second matrix); the older list.

STATE: main at this entry's commit; everything through 08d9937 was pushed by the user; the 5
commits after it, this one included, are unpushed.

## 2026-11-22 10:49 UTC: the Boolean step size, the accumulation matrix as the catalog has it, Ragu at ef7668fb

A morning of design discussion with one commit of changes (15a137e); the rest is recorded here
for the work to come.

- **The Boolean step size.** The user: a fixed step of 2^22 AND gates fails to optimize the
  step overhead. Why it is fixed: the 𝔽₂ family's and the binary-groups row's configurations
  are their merge circuits (17 to 77M ANDs), and the step was priced afterwards as 2^22 ANDs at
  the merge's per-bit rate. For the Ragu-architecture families the step and the merge's
  circuits share one rank, so the rank is one parameter for both; for the Boolean families the
  step's witness and the merge's witness are separate commitments, so their sizes are
  independent (what the user was missing). Constraints on a Boolean step: a power of two of bits
  (FRI-Binius's code), a power-of-two number of Flock blocks, the optimizer prices any size, and
  the merge sees the step only through its proof (query count and tree height, logarithmic).
  Plan: a per-row step log size swept 2^20 to 2^28 for the 𝔽₂ family and the binary groups,
  priced by `f2_prover(bits, …)` at each size, labels carrying the step, the merge unchanged.
  "Rank" stays Ragu's name (the trait's doc: the log of the coefficient vector's size; it is
  not a matrix rank) and "Module-SIS rank" stays as is (the user). Ragu's `Reach.rank` in its
  fuse randomizer is a third sense, a linear map's rank.
- **Rows by family.** The 𝔽₂ family has none (hashing); the binary groups' research root
  (branch specs binary-source-groups.md): a q24 profile, binary ring root of degree 648 at
  module rank 3 (4 at the larger geometry), about 24-bit modulus, so 1,944 or 2,592 scalar rows,
  ~47 kbits a column, certificate not issued; Kishu 567 scalar rows at q64 (the fold ledger's
  bound, not the bits' own), ~1,355 masked.
- **The accumulation matrix as Akita's catalog has it** (not yet in the model; the user asked
  for rounding to whole ring rows, and this is what it uncovered). The shipped fp128 schedule's
  root group: inner (A, accumulation) matrix rank 1 at ring degree 1,024, ℓ∞ route, coefficient
  bound 27,380,416,308 ≈ 2^34.7, width 4,096 ring elements; outer matrix rank 1 at degree 64,
  ℓ∞ bound 7; opening by subring coefficient packing, challenge subring dimension 64. The
  re-plans (estimates/replan-*.tsv policy strings): L0 dA=512 sec=Linf, later levels dA=64. The
  model prices the accumulation matrix as the Euclidean estimator's scalar rows (143/284/567)
  as fractional ring rows at degree 64: rows/64 + 3 multiplications a digit. The catalog's shape
  gives rank + log2(d)/2 = 5.5 (d 512) or 6 (d 1024) a digit for every modulus, against the
  model's 5.2 Pasta / 7.4 fp128 / 11.9 q64: the 64-bit variants and Kishu are overpriced about
  2×. The mask: a masked coordinate is ≤ 14σ ≈ 2^26.7, inside the shipped root's 2^34.7 bound,
  so if the re-plans' bounds are similar the masked witness needs no extra rows and the rows
  term, most of Kishu's zero-knowledge cost, vanishes. TO DO: re-price the accumulation matrix
  from the catalog's (rank, degree) per variant, certify the masked bound with the ℓ∞
  estimator (the re-plans' ranks and bounds still to read; the full schedules are in the 147
  worktree's artifacts), round to whole ring rows; keep the Euclidean route in the note.
- **Euclidean against ℓ∞** (explained to the user): same attack and cost model; a solution is
  an ℓ2 ball against a box; the ℓ∞ estimator (fixed β and ζ, LGSA profile) takes the
  probability that a reduced vector's coordinates all fall in the box; for digit witnesses the
  box is the digit size where the ball carries √N, so the ℓ∞ route certifies far fewer rows.
- **Ragu at ef7668fb** (tachyon-zcash/ragu origin/main, 271 commits past 8109a41c; the user
  fetched and added a worktree of the checkout at it, beside it). Step 1 done (15a137e): the
  note's §1.1 and open points 1 and 3 describe the fuse randomizers (two fold randomizers and a
  batch mask a side, uniform, folded as claims of their own; rerandomization fuses twice with the
  public bootstrap; the IPA unblinded by design; bootstrap linkability; hiding argued per value
  with a rank test, unaudited by its book's own word); the page's Pedersen zk paragraph; the
  Tachyon tree's last two nodes are the rerandomization fuses, each its own step
  (OWN_LAST_STEPS, DATA.own_last_steps; `zoodles_nodes` drops two). The user's stance, written
  into open point 1: the study does not adopt Ragu's argument; its route is §4.3's one-fold
  statement under hiding commitments with a simulator, DL first. The user's two problems with
  pricing by Ragu's approach: not known to be zk; it penalizes the pq schemes against
  Pedersen-IPA, whose zk is priced free, which the catalog finding above may largely answer.
  Facts gathered for steps 2 and 3: the new `values()` formulas (preamble per child HEADER + 1
  + StepBindingLen + 39 wires + mesh claims + 2 × nested online polys + Present<Native,2>;
  query: InternalCircuitIndex::num + 1 + 3 + 2 randomizers + 2 × (RxIndex::num + 4) + Present
  <Nested,2> + PhaseCoordinatesLen<Nested,3>; eval: 2 × (RxIndex::num + 4) + 11 + online Fp
  queries + 2 × (NUM_BINDERS − 1) + Present<Nested,2>; inner error: groups × error terms + 1;
  outer error: N − 1 + N + 6 + sponge 5); the pinned circuits at the tests' header 195:
  Hashes1 1,787, Hashes2 1,873, Collapse 1,603, ComputeV 1,981, BindChallenges 2,031 to 2,047
  (four), BindBeta 1,888, BindEndoscalar 970, EndoscalingStep 2,004 (last 1,567); nested
  EndoscalingStep 2,023 (last 712), Collapse 1,714, ComputeV 1,588, Loading 601; the sizes
  come from `Proof::encoded_len()` and `CompressedProof::encoded_len::<R>()` (wire/format.rs),
  and the user's branch encoded-len-probe has a probe test to rebase. Steps 2 to 4 remain:
  stage counts at header 9 from a probe test in the worktree, the proof size and the fuse's
  commitment count (96 + the six randomizers), then the fuse's time measured on mains.

NEXT, in order: the catalog re-pricing of the accumulation matrix with the ℓ∞ check (it decides
the page's main comparison); Ragu steps 2 to 4; the Boolean step-size knob; Zoodles' header
size; the handoff step's padding.

STATE: main at this entry's commit; everything through 46c1d8b was pushed by the user; the 2
commits after it, this one included, are unpushed. Artifact version 210 (before 15a137e).

## 2026-11-23 04:39 UTC: the accumulation matrix on Akita's ℓ∞ route, the mask per row, the hiding padding checked, the 147-bit default

Four commits after 9e29be5: 8035755 (the width table and its script), 23d23c4 (the
re-pricing), 2da6558 (the padding check), and 37e9684 (the 147-bit default). The user's
thoughts note was checked against the model in chat, before and after.

- **The accumulation matrix is priced as Akita's catalog shapes it** (23d23c4). A module of
  `rank` rows over a ring of degree 512 or 1,024, the catalog's accumulation degrees, at
  rank + log2(d)/2 field multiplications a digit. The rank and degree are the cheapest that
  Akita's ℓ∞ estimator certifies at the floor for the row's bound and its accumulator's width
  (`accumulation_matrix`, `LINF_WIDTHS`). The table, `estimates/linf-accumulation-widths.tsv`,
  is extracted by `scripts/linf-accumulation-widths.py` from the estimator's own tables: the
  64-bit and 128-bit moduli's production tables at 128 and 147 and their CSVs at 150, Pallas's
  CSVs, and the Goldilocks CSVs, checked to coincide with the 64-bit modulus's to a tenth of a
  percent. The estimator evaluates only the catalog's own cells, so a bound is rounded up to
  the ladder. The bounds are the note's extraction argument's on the coefficient ℓ∞ norm.
  Without the mask the bound is a fold's output, two children at the challenge's weight plus
  the step's digits, times the slack 2 · 2‖c‖₁ · 2: 2^14.6 for base-8 digits, 2^12.6 for
  Kishu's bits. With the mask it is the slack times 14σ, with σ = α‖c‖₁‖s‖₂ at the row's own
  ‖s‖₂ = DIGIT_MAX √N. Before, the rows were the Euclidean estimator's scalar rows at the ℓ2 bound 2^27 spread over
  degree 64, rows/64 + 3 a digit, times the (log β)² rule under the mask and the planner's
  rank growth at 147. Now every unmasked row is rank 1, 5.5 multiplications a digit at degree
  512 or 6.0 at 1,024 (the widest 64-bit-modulus accumulators); the mask costs a factor of 1.0
  to 1.33 on the rate, 14/11 for Kishu (rank 2 at 1,024 against rank 1 at 512), where the
  Euclidean route charged 2.4 to 3.1. Per digit in word multiplications, plain and masked:
  Pasta modulus 167/410 → 176/176; 128-bit 60/146 → 44/48; 64-bit Pasta claims 23.7/58 →
  11.0/14.0; Goldilocks 17.8/44 → 8.2/10.5; Kishu per bit 23.7/48.4 → 11.0/14.0. The 147-bit
  floor's rank-growth factor now scales the verifier's inner-image share only.
- **Figures that moved.** Kishu's recovery 0.399 → 0.283 s plain and 0.733 → 0.370 s with
  zero knowledge, the same at both floors since the matrices coincide; Zoodles by preimage
  0.154 → 0.0824 s zk; four tachyactions 0.481 → 0.241 s; qk 0.0790 → 0.0456 s; leanSPHINCS
  with BLAKE2s 0.561 → 0.297 s; the 64-bit variants' provers halve and the Pasta modulus's
  rise 5 percent; Kishu against BitZ's merge prover 2.9–3.3 → 4.7–5.3; the 𝔽₂ family's least
  prover is 0.81 of Akita over Goldilocks's with BLAKE3 at the 147-bit default (was a third
  at 128 before the re-pricing). Claims reworded: blake3_prover_ratios,
  f2_prover_fraction_of_gold_blake3.
- **The floor.** Of the 186 lattice rows shown at both floors, 10 take a larger matrix at 147
  than at 128, all BLAKE3 rows (the widest accumulators); Kishu's rows keep theirs at 128,
  147, and 150; at 150 the unmasked matrix of the Pasta-claims rows with 64-bit commitments
  would move from degree 512 to 1,024 (the 150-bit tables are in the TSV for this). So the
  accumulation matrix agrees with the compression maps about where the floor's cost begins,
  which the margin section now says with claims. The 147 explanation stands: the rank-one
  compression maps certify at 147.3 bits, block size 556.
- **The mask per row.** σ, the coordinate width (25 to 32 bits across the rows; the note's
  27 at its N = 2^22), the slices (9 to 11), and the peak memory's mask term follow each row's
  accumulator, with Kishu's digits as bits. The width sweep changed character: Kishu's masked
  matrix is rank 2 at degree 1,024 from α = 4 to 1,024, so the measure's optimum is the
  grid's top for every application at every sampler rate, and 48 is 9.1 percent off it (25 at
  Karney's rate). The page keeps 48 (nine slices to about α = 300, where the attempts are
  1.04; a tenth slice from about 360); what a wider mask costs is outside the measure: the
  coordinate bits (25 at 48, 29 at 1,024), the tenth slice, and the public merges' rate, which
  does not move. The user may widen within nine slices; the width paragraph and its claims
  (alpha_optimum_at_grid_top, alpha_page_excess) say this.
- **The hiding padding checked** (2da6558). Aρ pseudorandom is knapsack-LWE, which is LWE of
  dimension bits − rows with rows samples and binary secret and error by Micciancio and Mol's
  change of coordinates, with no loss (the note's new §5.10 writes the argument down, with the
  two heuristics shared with Akita's own estimates: the module structure treated as
  unstructured, and the uniform binary error centred). The pinned lattice estimator under
  ADPS16 quantum (`scripts/knapsack-lwe-check.py`, about an hour under Sage): the dual hybrid
  attack is the cheapest, about a hundred bits below the primal attacks, so the earlier
  primal-only estimate of 3,300 dimensions overstated the margin; at 5,000 bits it is 159
  bits at the device's 1,024 rows, 140 at the note's Euclidean 1,385, and 107 at 2,048. The
  padding is sized per floor as the least on the sweep's grid (250 bits, 50 where the floors
  are crossed) whose cheapest attack reaches the floor, so the 147-bit hedge covers it (the
  user): 4,400 bits (128.3) at 128 and 4,800 (148.9) at 147, `HIDING_PADDING_BITS` by floor.
  The dispute over the dual attack's analysis (Ducas and Pulles 2023) is noted; keeping the
  estimator's figure is the conservative choice. The statistical padding is 66 thousand bits
  at 1,024 rows, 4.4 times the statement, still an order of magnitude dearer.
- **The 147-bit floor is the default** (37e9684; the user). `DEFAULT_FLOOR` is the figure
  helpers' default; Pedersen-IPA and the binary groups, at 128 alone, are pinned explicitly
  where quoted, and under the default hash policy Pedersen-IPA was not shown anyway. The
  cost-model table carries both floors' block sizes, 484 and 556, with the bits under each
  model computed from the exponents (classical 162, paranoid 115 at 147). The page's own ARC
  comparisons take their openings at the default floor; the proof-size note's stay at 128.
- **Thoughts note.** Checked against the model before and after (see the chat): the figures
  it quotes hold, with the corrections given there, the proof at 74 kbytes at the 147-bit
  default being the one that moved.

A modelling inconsistency to decide (raised in chat, not changed): the accumulator memory
measure stores digits at 21 bits, from the Euclidean ledger's ℓ2 bound of about 2^19 taken as
a per-entry bound and the entries growing 40× a level, while the mask's σ takes the masked
vector as small digits (‖s‖₂ = DIGIT_MAX √N) and the fold's sum-checks are a decomposition's.
If every fuse decomposes and recombines, the stored entries are a few hundred at most, about 9
bits, and the memory measures fall by over half; if not, the masked vector's entries are not
small digits and σ is six bits larger. The two should be made consistent one way or the other.

NEXT: the Zoodles lineage priced both ways side by side (the user's decision: Tachyon's
bucket route with a capacity chosen for digits and the evidence proof folded as Tachyon folds
it, beside the sorted tree; the lift's shape from Tachyon's proof-tree chapter: QR profile
tests, the bucket opened at the value, the elapsed product; a per-application folded public
vector priced at the fold rate); Ragu steps 2 to 4 at ef7668fb; the Boolean step-size knob;
Zoodles' header size; the handoff step's padding; the ledger decision above.

STATE: main at this entry's commit; everything through 46c1d8b was pushed by the user; the
commits after it, this one included, are unpushed. Artifact version 212; the book builds.

## 2026-11-23 12:41 UTC: the book published, updates by pull request, the note on the ℓ∞ route, the sidebar

- **Published.** zcash/pqzcash is public. PR #1 (branch publish-book, merged by the user)
  removed the README's private-repository caveat, enabled the book workflow's deploy job on
  pushes to main, and trimmed the workflows' checkout comments to the remaining reason for the
  full fetch. The first runs of all three workflows passed. The deploy job is skipped on pull
  requests by its own condition, and the deploy action creates `gh-pages` itself, so the user
  set that branch as the Pages source afterwards; the book is live at zcash.github.io/pqzcash.
- **Updates go through pull requests from now on** (the user): a branch, the user's push,
  `gh pr create`, as a draft when asked, and the user's merge. Local main lags the remote until
  the user pulls.
- **PR #2, draft, branch note-page-consistency** (f1b7557). The zero-knowledge note and the
  page share the scheme: the masking fold with α = 48 and weight-20 challenges in degree 512,
  the one-fold statement, the §5.8 deferral. The matrix sizing differs by design, the note's
  own Euclidean analysis beside the page's ℓ∞ route in its §5.5. Two paragraphs still quoted
  the page's former results: §5.6 the sweep's least at 64 to 130 with 48 within three percent,
  now the ℓ∞ route's widest-is-least with 48 within nine percent, the Euclidean trade-off kept
  as the note's own; §5.9 the two-matrix saving of 1.7 to 1.9, now beside the ℓ∞ route's 1.0
  to 1.33. The page's lede says "proof bytes".
- **This branch.** The ragu-commitments chapter links the study's files by relative paths,
  which work in an editor and on GitHub's view of the source; `book/preprocessor-repo-links.py`
  rewrites links that leave `book/src` into GitHub URLs for the rendered book, `blob/main` for
  a file and `tree/main` for a directory.
- **The sidebar.** mdbook's head script hides the sidebar on every page load when the
  viewport is under 1,080 CSS pixels, zoom counted, so a click in the sidebar of a narrow
  window closes it. A theme override of `index.hbs` with a lower threshold would change that,
  a copy of the 0.5.4 template to maintain; the user's decision is pending.
- **The thoughts note**, re-reviewed at the 147-bit default (chat): its figures hold; 7.3
  Mbytes with zero knowledge is the masked accumulator as slices (6.8 stored compactly); its
  Fiat–Shamir-with-aborts link, labelled 2012, points to the 2009 paper; "13 percent more on
  each step and merge" holds on the same configuration (recovery 13, Zoodles 15); a Kishu step
  of 2^19 to 2^21 bits is a quarter to the whole of Ragu's 2^13 Pallas coefficients, not more.

NEXT, each on its own branch: the pages' references to "the note", which are unclear, made
links to the chapter and its section (the user); the Zoodles lineage both ways; Ragu steps 2
to 4; the Boolean step-size knob; Zoodles' header size; the handoff step's padding; the ledger
decision; and the user's calls on the mask's width and the sidebar's threshold.

STATE: branch repo-links-and-notes at this entry's commit, on main a672d13, which the user
pushed; PR #1 merged, PR #2 a draft; artifact version 212; the book builds.

## 2026-11-23 13:35 UTC: PRs #2 and #3 merged, the branch protection, the Akita checkout script, the patches as series

- **PRs #2 and #3 merged** (the user). #3, the repo-links-and-notes branch, was rebased onto
  main first, since the branch rule requires an up-to-date branch. The zcash remote's fetch
  URL is HTTPS now, so this shell can fetch the public repository; the user asks to be asked
  before each fetch, to keep track of the state.
- **Branch protection**, a ruleset on the default branch: no deletion or force-push, a pull
  request required with no approvals, the three aggregate checks required (`Post-Quantum
  Zcash book CI`, `Lean CI`, `Workflow CI`, each from the GitHub Actions app), and branches
  must be up to date with main before merging.
- **The Akita checkout is scripted** (2345bd0). `scripts/akita-checkout.sh` clones the pinned
  revision, initialises the lattice-estimator submodule, and applies the patches with `git am`:
  the Pasta-widths series in the clone on the branch `pasta-widths`, that and the 147-bit
  policy in the worktree on `pasta-widths-147`, from which the 147-bit pipeline resumes at the
  table regeneration. Tested offline with the local clone as the mirror: both checkouts came
  out identical to the patches' commits, and a second run leaves them alone. The patches are
  per-repository series under `scripts/patches/akita/` and `scripts/patches/ragu/` in
  `git format-patch` form (the user's rule: ordered patches use the `0001-` convention, and
  patches for different repositories go in different subdirectories). The 147-bit patch became
  the delta over the Pasta-widths patch, derived from the worktree's commit 2478c43 (the 32
  files it changes outside the generated tables, checked identical), plus the policy's rename in
  the shipped width tables so that the crates build before the regeneration. The regenerated
  tables stay out of the patch: their diff is 8.3 Mbytes, mostly `policy_audit.csv`, and the
  pipeline regenerates them.
- **The proof-size note** (2437c17) names the patch, the scripts under `scripts/`, and
  `estimates/` instead of paths under the scratch directory (the user: make it reproducible).
  The model's comments still name the scratch logs of the BitZ runs, which are developer-facing,
  and `estimates/summary.txt` is a generated log.
- **Cross-references are links** (2813c5a, dac2c36, b506373). The repo-links preprocessor
  resolves an included note's links from the note's own directory and maps a target that is a
  chapter to the chapter (`pareto-template.html` stands for the frontier chapter,
  `REGENERATING.md` for the regenerating one), so a note writes its links as neighbours
  (`scripts/x.py`, `zk-fiat-shamir-with-aborts.md#…`) that work on GitHub and in the book
  alike, and a link to a file that does not exist fails the build. The regenerating chapter
  and the two notes link every tracked file they name (`work/link-files.py`); bare section
  numbers link their headings, a section of another paper staying bare
  (`work/section-links.py`); the zero-knowledge note is "the zk note" after a first mention in
  each document, with a link on every reference, noteref spans in the frontier page and links
  in the notes (the user: abbreviate so that every reference reads "in the zk note";
  `work/note-refs.py`); the zk note links the frontier page's sections, the proof-size note,
  the hardware-wallets chapter, and its open points; the hardware-wallets note's two
  book-relative links are note-relative. A reference to another page gives the page's title as
  the link text (the user: not its filename), and the preprocessor sends a link whose text is a
  code span to the file on GitHub, a title to the chapter. The proof-size note's bare "§5.5",
  which it has no section for, is read as the zk note's §5.5; the user checked the §5.5 links. The rendered chapters' 555 links were
  checked by `work/check-links.py` (GitHub paths tracked, pages and ids present).
- **References give authors' first names in full** (dd9a302; the user's rule, for the reason
  that initials can hide diversity in gender and culture), taken from the papers' own pages
  where the lists had initials: Zinc+, Akita, BitZ, Flock, Zook, the small-field SoK, and the
  leanSPHINCS EIP, cited by its number 8504 now (`work/ref-names.py`).

- **The regeneration notes are a book chapter**, "Regenerating the Study's Numbers" at
  `book/src/proof-systems/regenerating.md`, moved there from `ragu-pcs/REGENERATING.md`, which
  is a stub with an include pointing at the chapter (the user's choice); the Ragu commitments
  chapter links it. The chapter's paths stay relative to `ragu-pcs/`, as its first paragraph
  says.

NEXT: the queue as before: the Zoodles lineage both ways; Ragu steps 2 to 4; the Boolean
step-size knob; Zoodles' header size; the handoff step's padding; the ledger decision; and the
user's calls on the mask's width and the sidebar's threshold. Low priority, for completeness
(the user, after the question whether Pasta was re-planned): a native Pasta profile for Akita,
the proof-size note's §7, two to three days of which the challenge families for a fully
splitting prime are the uncertain part. It would refine the two Pallas-modulus rows' bytes by
a few percent (the re-plan at Pallas widths saved under two percent a row) and leave their
prover, which the 255-bit arithmetic sets at 15 times fp128's, so it does not change where
those rows stand; the 64-bit-commitment row already gives native Pasta claims at a twelfth of
their prover.

STATE: branch akita-checkout-script at this entry's commit, on 94d1383, the tip of #3 before
its merge; to be rebased onto main after a fetch, then pushed by the user and opened as a
draft PR; the book builds and its links check.

## 2026-11-23 20:24 UTC: the book by scheme, a Zoodles page, the soundness notes split, the citations linked

PR #4 (branch akita-checkout-script) is open; this branch is stacked on it.

- **Sections** (8cc5f66, 42028db, 2b786a8): 1.3 Kishu with the zero-knowledge note and Kishu's
  soundness statements under it, 1.4 Other Schemes with the Pasta proof-size note and the
  Pasta-claims variant's statement, 2 Zoodles, 3 Hardware Wallets and the Recovery Statement (its
  page's title); "Working Notes" is gone and its two addresses redirect. Both new sections have
  pages, since a page-less section renders in mdbook's draft colour, which sits near the sidebar's
  background in every theme (1.6:1 on the rust theme); the colour is now derived from the
  sidebar's text for any future draft.
- **The soundness note is two pages** (b39849a; the user's request): `kishu-soundness.md` and
  `pasta-q64-soundness.md`, the statements unchanged, Lemma L on both with a note that it is the
  same.
- **The Kishu page** (af8a1a4) says what Kishu is made of and carries the acknowledgement
  paragraph in the user's exact words (the designers of Akita and BitZ; Quang Dao, Albert
  Garreta, Tal Derei; Ulrich Haböck's suggestions).
- **Zoodles** (2b786a8, 7b7a7b6): `ragu-pcs/zoodles.md`, a prose file with figure markers, from
  the user's thoughts.md text expanded section by section, with the Tachyon team's
  acknowledgement; marked in progress. The user corrected the tree sentence: Kishu's step holds
  as many spends and outputs as fit in the same step as the fee, which is what `tx_steps` packs
  (first-fit decreasing); Tachyon as built gives each circuit a step at rank 13 (all 39 circuits
  under 2,048 gates), so the packing is the design's, and the packed step's interface is an open
  point on the page. Figures `tx_zoodles_*_kishu_zk_steps`.
- **A marker never starts a line** (8830f4f). CommonMark starts an HTML block at a line beginning
  with `<!--`, inside a paragraph too, and renders the rest literally: the zero-knowledge note's
  §5.8 paragraph began with its claim marker, which is why the user saw `[§3](…)` and `[§5.4](…)`
  as text. The marker follows the first word now; the model fails on any note line that begins
  with a marker; `work/rewrap-markers.py` refills a hard-wrapped note with markers glued to the
  word before.
- **The zero-knowledge note cites every paper it names** (5810b06; the user: all the papers need
  to be referenced/linked): links to anchored References entries, five entries added (Dilithium's
  specification, Hülsing–Lange–Smeets, Jeudy, Karney, Du–Fan–Wei), and §5.2 gives the 147-bit
  target first (block size 556, log₂ δ 0.00454, against 484 and 0.00502).
- **Preprocessor** (d86a252): an included note's `../book/src/…` link is written relative to the
  chapter, so the Zoodles page links the Kishu page.
- **Answered in chat.** Akita's committed digits are balanced base 8 catalog-wide (every
  proof-optimized preset has `log_basis = 3`; the compression levels use binary digits), so the
  zk note's sentence holds for every variant. The sampling attempts cannot share the mask or its
  commitment (a mask derived from a rejected attempt is correlated with the secret through the
  test), but masks are independent of the secret, so a stock of them can be drawn and committed
  in idle time and consumed once each, which is what §5.8 relies on.

Decided (the user): the online/offline split of the prover is shown as a MEASURE, "transaction
prover (online)", the total less the fold's offline share (the mask sampling and commitments of
the expected attempts; for the leaf handoff the leaf's), plottable against the transaction prover
for the same application; Flock's zero-knowledge mask split is wanted, WHIR's only if cheap.

NEXT: the online measure, on its own branch; then the queue as before: the Zoodles lineage both
ways; Ragu steps 2 to 4; the Boolean step-size knob; Zoodles' header size; the handoff step's
padding; the ledger decision; the user's calls on the mask's width and the sidebar's threshold;
and, low priority, the native Pasta profile.

STATE: branch book-reorganization at this entry's commit, stacked on akita-checkout-script (PR #4,
open), pushed by the user up to the commit before this one; the book builds, 655 links check.

## 2026-11-23 21:57 UTC: the epoch-set page; compression, the bucketed table, the QR profile

- **PR #5**, book-reorganization against main, is a draft, opened after #4 merged and the branch
  was rebased; the two commits of this entry follow its pushed tip aaa9fd2.
- **The epoch-set page** (48d42d4; `ragu-pcs/zoodles-epoch-set.md`, 2.1 under Zoodles; the
  user: a page of its own, not weight on the Zoodles page): the sorted tree against set
  polynomials and the bucketed table of zcash/zcash#4062, whose "to be continued" probability
  analysis is done: the capacity K from the Poisson tail of a bucket's load under a union bound
  over the buckets (`bucket_capacity`, figures `bucket_*`, claim `bucket_table_dearer`); the
  tags variant, two-choice placement, filters; the attacker a table has. The table I gave in
  chat had K a few too high, a constant slipped in a scratch script; the page's figures are the
  model's. The user has the permissions to unarchive zcash/zcash and means to transfer its
  design issues out of it later; archived repositories refuse transfers.
- **Compression of tachygrams** (chat): a 128-bit image survives a single-target roadblock on
  the Grover-depth reading, since the mempool exposes a value before it is final, but not the
  multi-target membership search at 2^128 / N over every commitment ever created; an
  exclusion-only compressed set would split the one structure that serves both checks, which
  the user wants to keep. So full width everywhere, and the recommendation stands to drop set
  polynomials from the transaction tree for hashed lists when the lineage task redoes the
  Zoodles row's inventory.
- **"Quadratic-residue profile"** (Tachyon's primitives/qr.rs at 73031f7): the bucket routing
  is a binary trie whose split at depth j is whether x + R_0 + j is a square in F_p, R_0 a
  prover-chosen random discriminant threaded through the network, at most 32 deep; a side is
  proved by a square root y² = c(x + s), one squaring and a selection, and a whole class by an
  interpolant u with u² − c(X + s) = q·h against the class's set polynomial q. The profile's bits
  are the Legendre PRF of the tachygram at consecutive inputs.
- **Hashing an epoch's tree** (chat): about 2^20 compressions of 64 bytes, 67 Mbytes, tens of
  milliseconds a core with BLAKE3's lane batching and a quarter of a second scalar, plus a sort
  of 2^20 values; BLAKE3's own tree mode would give 1 KiB leaves and a 31-compression inclusion
  proof against the custom tree's 21, at the same native speed, so the custom tree is right.

NEXT: the online measure, "transaction prover (online)", the user's choice (a): the total less
the fold's offline share, Flock's mask split wanted, WHIR's only if cheap; then the queue as
before.

STATE: branch book-reorganization at this entry's commit, two commits beyond PR #5's pushed tip
aaa9fd2; the book builds, 682 links check.

## 2026-11-23 23:20 UTC: Spend Authorization under Zoodles, CAPSS, ZIP 2005's qk derivation in all three protocols

PR #5 (book-reorganization, a draft) carries this entry's work; its pushed tip is 9e3bce6, and the
commits after it are the section, the derivation and binding, CAPSS, and this one.

- **Spend Authorization** (the user's reorganization: most of the hardware-wallets
  chapter was about the two authorization methods, which are not recovery-specific). Section
  2.2 has a page that motivates the two methods (the preimage is ZIP 2005's and much the
  cheaper for a signer with no key separation or no bandwidth or memory constraint; leanSPHINCS
  reaches a wider range of devices and may be compatible with Ethereum's choice) and defines
  quantum recovery for Ironwood and Tachyon alike, and under it Hash Preimage (with the
  signature-of-knowledge argument), leanSPHINCS, CAPSS, Recovery from Ironwood, Recovery from
  Tachyon, and Hardware Wallets (the device split, the Kishu leaf and the QR channel, the
  signature on the device). The figures and claims moved with their sentences, the old chapter
  address redirects, and the frontier page refers to the section (`NOTE_CHAPTERS`
  "spend-authorization").
- **Recovery from Tachyon.** Tachyon's owner field is $\mathsf{pk} = \mathsf{Com}(\mathsf{ak},
  \mathsf{nk})$ (its book, revisit.html#payment-key), so its recovery witness is viewing-key
  material: no counterpart of ZIP 2005's $\mathsf{qsk}$, hence no threshold-held recovery secret
  for a FROST group and viewing keys that spend after the break. The user calls it a regression
  and easily fixable: the proof-authorizing key $(\mathsf{ak}, \mathsf{nk}, \mathsf{qk})$ with
  $\mathsf{qk} = \mathsf{H^{qk}}(\mathsf{qsk})$. The migration transaction is a recovery spend
  of a Tachyon note plus a Zoodles output, queued as an application; the frontier page's
  sentence that Tachyon's circuits in a post-quantum proof system are not a useful deployment is
  to be revised. Tachyon's book sketches the post-quantum upgrade and leaves it there; Zoodles
  is that upgrade. The book's URL is tachyon.z.cash/book/revisit.html.
- **ZIP 2005's qk derivation in all three protocols** (the user: it is $\mathsf{H^{qk}}$ that
  is the same, not the keys). The preimage method's image is derived from its preimage by the
  ZIP's $\mathsf{H^{qk}}$, whose personalization names no pool on purpose (any domain
  separation between the protocols affects how $\mathsf{qsk}$ is obtained, not the derivation;
  a footnote on the page), so a native Zoodles spend, an Ironwood recovery on the
  $\mathsf{use\_qsk}$ path, and a Tachyon recovery make the same check with keys of their own. What binds a Zoodles
  note to its action without Tachyon's randomizer (the user's question from the book's
  #pq-rerand): every published value is derived in the step that opens the note, the lineage's
  attestation arrives as a header the step checks, and the tree and the digest carry the rest.
- **CAPSS** (the user: worth analysing as a third option). ePrint 2025/061 read from
  keep/2025-061.pdf; its Tables 2, 3, and 6 typed as `CAPSS_*`. Anemoi is set aside for the
  FreeLunch attacks (CRYPTO 2024, keep/crypto-2024.pdf) and Campa–Roy's Gröbner-basis
  cryptanalysis (ePrint 2025/814, keep/2025-814.pdf), the Poseidon instances read; the
  framework takes any permutation cheap in the proof system at hand (the user), so a Poseidon
  instance over Kishu's field is estimated at the model's rates: a verifier of about 10.1
  million digits by the call counts or 6.4 million by the paper's constraint estimate, against
  leanSPHINCS's 6.39 million; signing about 40,000 permutations, 1.1 s at the MCU rate; about
  20 kbytes. Not adopted: the method for a prime-field proof system; a row would be a day's
  work.

NEXT: the Zoodles statements page (the user: a page giving the Zoodles statements, in the
style of Tachyon's proof-statement section); the online measure; the Tachyon → Zoodles
application; the queue as before.

STATE: branch book-reorganization at this entry's commit, five commits beyond PR #5's pushed
tip 9e3bce6; the book builds, 771 links check.

## 2026-11-24 01:28 UTC: review of the Spend Authorization and Zoodles pages; the commit messages at 72 columns

PR #5 (book-reorganization, a draft) was reviewed page by page; its history was rewritten, so the
next push is a force-push (`git push --force-with-lease zcash book-reorganization`).

- **Commit messages.** Every message in the PR is rewrapped at 72 columns with its long sentences
  split, and subjects over 72 characters are shortened (`work/pr5-new-messages.txt`,
  `work/amend-messages.py`: one empty `amend!` commit per message, folded by one autosquash
  rebase; the tree is unchanged). The user: "it's typical to wrap commit comments to about 72
  characters". Keep to it in this repository.
- **Wording on the Spend Authorization pages** (folded into the commits that introduced the
  prose): "authorization method" in each page's opening; the CAPSS page says up front that
  Zoodles does not adopt it; the preimage page's bullet on Tachyon links the key-structure
  section; every bracketed citation on the six pages links to an anchored References entry
  (`work/auth-cites.py`), and ZIP 2005 is cited at its first mention, with entries added to the
  preimage and leanSPHINCS pages; long sentences split across the section page and the CAPSS,
  recovery, and hardware-wallet pages (the ones of forty words and more; a few of 30 to 39
  remain, and the checker's 70-word flags on the hardware-wallets page are sentences that begin
  with a math span, which it does not split).
- **The Zoodles page.** The packing paragraph counts in actions, an action a spend or an output
  (the model's figure: the average of a spend and an output with its merge); the two-by-two
  transaction is four actions in one step at rank 19 against the twelve steps of Tachyon's tree
  before it rerandomizes; the packing is its own paragraph. Amounts are range-checked to
  [0, MAX_MONEY], as Tachyon's output statement checks them. Long sentences split and the page
  rewrapped. The spend-authorization section is one paragraph, since it repeated the section's
  pages; the leanSPHINCS page gained "The message" with the digest's contents and the fee step's
  check (the figures moved with the text). The bullets link the section and the epoch-set page.
  A **Pool accounting** section (the user's design): a transaction with Ironwood or Tachyon
  recovery spends reveals the total it spends from each of those pools and its Zoodles balance,
  so that consensus keeps the pools' balances and rejects a transaction ZIP 209 forbids; the
  headers carry the sums; the whole transaction is one Kishu proof, since Halo 2 and Ragu proofs
  will have to be disabled before Q-day; the two recovery pages refer to it, and the page has a
  References list (ZIP 209, ZIP 2005). Blocks are 25 seconds since NU7, so an epoch of 4,096
  blocks is 1.2 days (`ZOODLES_BLOCK_SECONDS`; the frontier page's sentence too).
- **Tachyon's pk with qk** (the user's question whether `Com(ak, nk, qk)` still fits one hash):
  Tachyon's sponge absorbs four field elements a permutation and `pk` takes three, so `qk` fits
  as the fourth if it enters as one Pallas element, reduced modulo p, since a 256-bit output is
  not one; the recovery proof pays a 256-bit range check for the reduction. Said on the Tachyon
  page. (Two limbs would cost a second permutation, which in Kishu is a Pallas Poseidon
  permutation by limbs or fingerprint, far dearer than the range check.)
- **The book.** The Raleway fonts the stylesheet names were missing (the user saw the failed
  downloads); they are now under `book/src/fonts/` with their OFL, as the ironwood book ships
  them. `\tilde` in Kishu's soundness note rendered as strikethrough (mdbook-katex passes a
  literal `~`); `\widetilde` now. 819 links check, 0 bad; the build warns of nothing.

Answered in chat (to record):

- **Actions and Faerie gold.** Tachyon and Zoodles do not bundle a spend with an output as Orchard
  does; an action is one spend or one output (Spend Action, Output Action). Orchard bundled them
  for a unique ρ from the spend's nullifier; Tachyon has no canonical note position and pushes
  Faerie-gold detection to the recipient's wallet, which computes a received note's nullifier at
  a fixed reference epoch and rejects a collision with a note it holds (revisit.md, "Faerie-gold
  via the wallet" and "Note Spendability"; keys.rs, note.rs, nullifier.rs say the same). Zoodles
  inherits that, since its nullifiers have the same shape.
- **SmallWood with BLAKE3** (the user: CAPSS is SmallWood plus arithmetic hashes; does SmallWood
  make sense for BLAKE3?). It would make ZIP 2005's SoK^qsk a standalone hash-only proof of a
  BLAKE3 preimage, usable with existing preimage-route keys and under hash assumptions alone, but
  the statement becomes ~15k bit constraints instead of a few hundred field constraints, so the
  proof is tens of kbytes (over a QR channel's budget), signing is seconds and a few Mbytes on
  an MCU (no secure element), and the verifier in Kishu is thousands of BLAKE3 Merkle-path
  compressions plus the PIOP checks, dearer than leanSPHINCS's ~300. In Kishu an arithmetic
  hash buys nothing either (Poseidon over q64 ≈ 17.7k digits a permutation against BLAKE3's
  15.1k a compression). Not a third method for Zoodles; at most a hash-only alternative to the
  Kishu leaf for the Ironwood SoK^qsk with existing keys. Not priced.

FINDING, to decide: the model's Zoodles spend action step counts one BLAKE3 compression, "the
payment key is the hash of the authorizing key". With the preimage method as the pages now
describe it, qk committed in pk and qk = H^qk(qsk) proved, the step derives H^qk and opens pk:
two compressions, so a preimage spend is ~15k digits more (65k, not 50k), and the leanSPHINCS
variant's pk commits the signature's public key (one compression plus the verifier). The actions
per step would be 1 / 6 / 25 at ranks 17 / 19 / 21 (was 28 at 21). `ZOODLES_NODES` would need
the authorization method as a parameter.

QUEUED by the user this session: (1) leanSPHINCS with BLAKE3 as an application beside BLAKE2s and
Keccak (the user: if Ethereum goes with Keccak there is no point in BLAKE2s; expected ~7/10 of
the BLAKE2s cost, the same 298 calls); (2) a section 1.3.1 "Kishu's Arithmetization" with a
rough cost model and the differences from Ragu, after everything else in flight.

NEXT: the Zoodles statements page (the user's earlier request), the leanSPHINCS-with-BLAKE3
application, the SpendAction compression decision, Kishu's Arithmetization, then the online
measure, the Tachyon → Zoodles application, and the queue as before.

STATE: branch book-reorganization at this entry's commit, 27 commits beyond main, history
rewritten since PR #5's pushed tip 9e3bce6; the book builds, 819 links check.

## 2026-11-24 02:23 UTC: leanSPHINCS with BLAKE3, Kishu's Arithmetization, pool accounting as a bundle

Still PR #5 (book-reorganization, a draft, history rewritten; the push is a force-push).

- **leanSPHINCS with BLAKE3** (the user: if Ethereum goes with Keccak there is no point in BLAKE2s,
  so the choice is Keccak or BLAKE3). `LEANSPHINCS_VERIFY` has the three hashes in increasing
  order of cost, BLAKE3 at the same 298 calls as BLAKE2s (same block and output sizes), and the
  applications follow: `leansphincs_{blake3,blake2s,keccak}`, and the Zoodles transactions, with
  and without Merkle paths, as `zoodles_leansphincs_{hash}` and `zoodles_merkle_leansphincs_{hash}`
  (`ZOODLES_AUTHS` lists them; `leansphincs_hash(auth)` picks the hash). The pages quote the BLAKE3
  variant: the verifier 4.53M digits, 71% of BLAKE2s's (claim `leansphincs_blake3_cheaper`), 0.234 s
  zk at rank 21; the Zoodles BLAKE3 signature transaction 9.42M digits, 0.363 s zk at rank 21 in 5
  steps, a spend 4.58M digits; the preimage transaction stays under a quarter of it (claim holds at
  0.0824 against 0.363/4). The device's BLAKE3 grind is unmeasured in Wam26's benchmark; the pages
  say it should be no slower than BLAKE2s (seven rounds to ten).
- **Kishu's Arithmetization** (`kishu-arithmetization.md`, section 1.3.1 under Kishu, a PROSE_FILE;
  `NOTE_CHAPTERS["kishu-arithmetization"]`, and `data-section` may now be a heading id with its
  `#`). The frontier page's Kishu section lost its paragraphs on digits and constraints, the two
  routes, the merge, and the recovery circuit to it, keeping a summary, the costs at rank 17, and
  the status; the page adds a unit-cost table and the differences from Ragu, read from Ragu's own
  arithmetization chapter (four wires a gate, a_i b_i = c_i and c_i d_i = 0, 4n linear constraints,
  one structured trace polynomial of degree < 4n, a revdot identity; a rank-r step is 2^r
  coefficients = 2^(r-2) gates). The Kishu page lists its three subpages; the Zoodles page points at
  the cost model from its packing paragraph.
- **Pool accounting** is stated for the Zoodles bundle (e.g. in a ZIP 248 transaction [ZIP-248]
  cited): it reveals the Ironwood and Tachyon spend totals and the Zoodles balance; the fee check
  is ZIP 248's per-asset balance, not the bundle's, so the "three sum to the fee" sentence went.
  The Zoodles opening is the user's: a post-quantum shielded protocol based on Tachyon with its own
  pool, Kishu as its proof system, a follow-on to Tachyon.
- **The Ragu commitments chapter** names the frontier's measures as they are (proof bytes plus two
  of eight; the frontier on bytes, the two measures, and three requirements) and Kishu among the
  candidates.
- The book builds, 823 links check; the headless Firefox checks are in `work/firefox-*-kishu.log`.

NEXT: the Zoodles statements page; the SpendAction compression decision (the model counts one
BLAKE3 compression where the preimage method needs H^qk and the pk opening); the online measure;
the Tachyon → Zoodles application; the queue as before.

STATE: branch book-reorganization at this entry's commit, 31 commits beyond main; the book builds,
823 links check.

Later in the same session:

- **Kishu's Arithmetization opens at the PCD level** (the user: cart before the horse; describe it as
  it appears to circuit writers, assuming no familiarity with BitZ or Akita; "merge" and
  "accumulation" are too low-level there): a section "Kishu as a Proof-Carrying-Data scheme" on
  nodes, headers, the witness as bits, constraints as polynomial relations among words with
  integer semantics below q/2, the unit costs, what is free; then "What Kishu is made of" defines
  Akita and BitZ and places accumulation beneath the node interface. Terms: a NODE is a vertex of
  the PCD graph (a Tachyon circuit), a STEP the accumulation scheme's unit, which packs several
  nodes. Ragu's book calls the application circuit "a PCD step" and Tachyon's book names its
  circuits steps, so their "step" is our node; in Ragu the two coincide, one circuit a step.
- **Faerie gold is open for Zoodles** (the user, correcting the chat answer above): Tachyon's
  wallet-side detection does not survive a roadblock, since a sender can send two notes with the
  same ψ and the wallet cannot tell the payment from the roadblock, so spendability cannot be
  established at receipt; this is why Sprout, Sapling, and Orchard derive ρ uniquely (the Zerocash
  authors had suggested the wallet check and the user argued it did not work). Tachyon has no
  incoming viewing keys, so note secrecy might be assumed against everyone but the sender, but the
  spendability definition would still have to allow all but one note from a sender to be rejected.
  Zoodles needs a unique ρ per output; the statements page is to settle how (Orchard's pairing of
  a spend with each output, or another per-transaction unique value). A Status bullet says so.
- **use_qsk**: the priced recovery circuit takes either value (ZIP 2005's cost section: three
  BLAKE2b compressions multiplexed between the two paths); the Ironwood recovery and
  hardware-wallet pages said the false path was not considered, which was about their device
  analysis only, and now say so.

After the push (ced08c7): the SpendAction compression question is settled by the user: a Zoodles
spend proves knowledge of (nk, qk) opening pk = H(nk, qk) AND knowledge of qsk with qk = H^qk(qsk),
two BLAKE3 compressions; the model's preimage variant now counts both (`zoodles_node_cost`,
`zoodles_node_piop`, the Merkle variant likewise), so a preimage spend is 65,533 digits, the
two-by-two transaction 343,000, and 25 actions fit at rank 21 (was 28); the zk time is 0.0825 s,
unchanged in effect. The signature variant opens the payment key once. Tachyon's pk is a Poseidon
commitment over Pallas, which the Tachyon recovery spend in Kishu must open by limbs or
fingerprint; said on the Recovery from Tachyon page. Linked citations now keep their brackets on
every note (`[\[KEY\]](#ref-key)`). The hardware wallet is orthogonal to the pool a spend is from.

The user is not sure the hash that produces pk is needed; Zoodles mirrors Tachyon as closely as
possible with the minimal change for the same quantum recoverability, and this may be optimized
later. A Status bullet on the Zoodles page records it.

Two design questions from the user, for the statements page:

- **Orchard-style actions.** Given two tachygrams per Tachyon action anyway, why not actions of a
  spend and an output, either a dummy, as Orchard's? Tachyon's book (revisit.md, "two
  tachygrams"): a spend publishes its current and next epoch's nullifiers for the race at the
  epoch boundary, and an output publishes a dummy tachygram beside its commitment so that every
  action carries two and the spend/output split does not leak; it does not consider the pairing.
  A paired action would publish three tachygrams (two nullifiers and a commitment), also uniform:
  one fewer per spend–output pair, no padding tachygram, and a unique ρ for every output from the
  action's spend nullifier, which answers Faerie gold as Orchard does. Against it: a dummy spend
  needs the spendability proof to be skippable, as Orchard's value-0 rule does; unbalanced
  transactions pay three tachygrams an action where Tachyon pays two; and the node's circuit
  doubles, which matters for Ragu's rank-13 steps and not for Kishu's packing.
- **ak and nk.** Why separate keys? The user cannot recall why Orchard did not use ak as nk;
  Sapling wanted a proof authorizing key (ak, nsk), and Orchard may have kept the shape by inertia.
  For Zoodles the constraint is that the nullifier key must stay hidden from senders, who know
  the address and ψ, or a sender could watch for the note's spend; that is what the hash
  producing pk does, so the hash is needed unless the address carries nk in the clear.

The user's follow-up: Zoodles could have the chain qsk -> qk -> pk and use qk as the nullifier key,
dropping nk; the two compressions stay (H^qk and the pk hash), the host holds qk for scanning and
cannot spend, and a sender sees only pk. The Status bullet on the key chain says so.

On ak and nk in Orchard, the user sees three plausible reasons they were not unified: (a) it did
not occur to the designers; (b) key hygiene, since using a public key as a PRF key is a little
janky (Sapling uses a point representation as one, but not one that is also a public key, other
than to separate it from nsk); (c) no significant circuit saving. The user rules out (c), since
Commit^ivk is Sinsemilla and pays for the extra input bits; (a) or (b) remain. For Zoodles (b) does
not apply to qk as the nullifier key: qk is a hash output, not a public key in the discrete-log
sense, and ZIP 2005 already uses it as a PRF key, in H^rivk_ext_qk.
(The user: the rivk precedent is for the hygiene point only; Zoodles has no rivk, "and good
riddance".)

TODO (the user): work out the details of key derivation for leanSPHINCS: how the signature's key
pair is derived from the wallet's seed or quantum spending key, how its public key is committed in
the Zoodles payment key and in a recovery arm, and what a FROST group does with it.

The user pulled the Tachyon and Ragu checkouts (2026-11-24): Tachyon main is d1f5ffb (2026-11-23),
15 commits past the 73031f7 the study read, among them "feat: use real proofs" (267a566: the
mock `ragu` dependency replaced by `ragu_pcd` with the accelerated prover; the `relations` module
gone, steps checking polynomial identities inline; FixedBase reads 254 bits), "hold rcm nonzero
wherever a note commitment is derived" (a36788b, #324), the QR and pool refactors, and a parameters
appendix in the book. Ragu main is 7914b3b8, 315 commits past 8109a41c. So keep/tachyon-statements.md
and the measured gate counts (TACHYON_STEPS) describe the old revision; re-read the step circuits
before the Zoodles statements page, and re-measure the counts when Ragu steps 2–4 come up. Every
tachyon.z.cash link the pages cite resolves (payment-key, pq, pq-rerand, team, the Ragu chapter).

Kishu's Arithmetization was reworked with the user sentence by sentence (the definition is the
part a misreading would poison, so it got the time): "Kishu as a Proof-Carrying-Data scheme"
(nodes, headers, the node/step distinction); "The arithmetization" (q a fixed prime, 2^64 − 59 for
the modelled parameters; column vectors, ⟨x, y⟩ = xᵀy by the `\innerprod` macro in
book/macros.txt with a −0.8mu kern; matrices r × c take F_q^c to F_q^r; a circuit with m
constraints, the public inputs padded with zeros to the instance vector v ∈ F_q^m, the witness
w ∈ {0,1}^N; per constraint j, sparse A_j, B_j ∈ F_q^{t_j × N} and a row vector c_j ∈ F_q^{1×N};
⟨A_j w, B_j w⟩ + c_j w = v_j in F_q; a prose gloss; the constant term wlog through an input fixed
to 1; booleanity enforced for the whole witness at once); "Relation to R1CS" (a generalization with
several products a constraint, boolean constraints implicit), "Relation to CCS" (STW23's
definition, read row by row at degree two; z = (w, 1, x) against bits and the right-hand side;
degree two here), "Relation to Ragu" (Bootle et al.'s constraint system over Pallas with a fourth
wire; bits, F_q, free constraint shape; instance values in both); "Writing circuits" (the costs,
words, integer semantics, other prime fields expensive but not prohibitively so, gadget costs,
steps, zero knowledge, no lookups). Lowercase "boolean" as an adjective; "Booleanity" left as the
study spells it. The user: some redundancy remains, left for now.

The user's observation (2026-11-24): most optimization techniques for bignum arithmetic on native
limbs apply in Kishu's arithmetization too. Assessment: yes, since a limb is a word below q/2 with
free range checks, so lazy carry propagation, redundant (non-canonical) limb representations,
Karatsuba, and quotient-witness reductions (Barrett, Montgomery, Solinas-style for Pasta's primes)
all translate; but the cost structure differs from a CPU's: a product term is 9.8 word
multiplications where a committed bit is about 11, so the committed intermediate bits (carries,
quotients, products' outputs) dominate, and the techniques worth most are those that cut committed
bits, not multiplications. The limb route is schoolbook over 29-bit limbs with 34-bit carries, 17
constraints of up to nine products; the fingerprint route avoids limbs altogether.

## 2026-11-24 17:37 UTC: the arithmetization page reviewed sentence by sentence; relations to CCS, UCS, Ragu

PR #5 (book-reorganization, draft): the user force-pushed through 715f07a; the commits after it are
this session's review of `kishu-arithmetization.md` with the user, each sentence settled in chat
before it was written (the user: a misconception at the definition sends the reader down wrong
paths; reading is repeatedly asking "do I already understand this?"; an explicit sum is a math
smell; the same notation should mean the same thing; ask whether each unit can be set down).

- **The arithmetization**, as it stands: q a fixed prime (2^64 − 59 modelled); ⟨x, y⟩ = xᵀy for
  column vectors (`\innerprod` macro in book/macros.txt, −0.8mu kern); matrices r × c take a
  column vector in F_q^c to F_q^r; a circuit with m constraints, the public inputs padded with
  zeros to v ∈ F_q^m, a witness w ∈ {0,1}^N; per constraint index j, sparse A_j, B_j ∈
  F_q^{t_j × N} and a row vector c_j ∈ F_q^{1×N}; the equality in F_q ⟨A_j w, B_j w⟩ + c_j w = v_j;
  a prose gloss; the constant term wlog through an input fixed to 1 and a bit constrained to it;
  booleanity enforced for the whole witness at once.
- **Relations**: to R1CS (a generalization with several products a constraint; boolean constraints
  implicit); to CCS [STW23] (keep/2023-552.pdf: Σ c_i ∘_{j∈S_i} M_j z = 0 over z = (w, 1, x), read
  row by row at degree two; varying t_j = zero-row padding; z against bits and the right-hand side;
  degree two here); to Universal Constraint Systems [AGK+26] (Zinc+'s, over polynomial rings;
  over the integers Zinc's [GWHD25], CCS on bounded integers with lifted moduli, keep/2025-316.pdf;
  proved by projection to a random prime field, which is what makes them universal; BitZ [BGK+26]
  proves integer polynomial constraints the same way; Albert Garreta is an author of all three;
  Kishu keeps the shape and the bits but evaluates in F_q, its fingerprint route being Zinc's
  method and its limb route a range argument); to Ragu (Bootle et al.'s constraint system
  [BCC+16] over Pallas with a fourth wire; bits, F_q, free constraint shape; instance values in
  both). The closing "Differences from Ragu" refers back for the arithmetization's own.
- **Writing circuits**: what the writer pays (per bit, per product, a little per nonzero
  coefficient; degree two by the model's choice); words of ℓ < 64 canonical bits, bit vectors and
  F_q elements (non-canonically) represented directly, range checks free; integer semantics
  whenever both sides lie in a range no larger than q ([0, u] + [0, v] safe for u + v < q), not a
  q/2 bound; a word multiplication one product term; arithmetic in another prime field a relation
  with a committed quotient, expensive but not prohibitively so, since R1CS pays mostly for the
  boolean constraints that Kishu's bits do not need; gadget costs; steps; zero knowledge asks
  nothing of the writer (the binding clause was removed: binding is soundness, not zk); no lookups.
- "Kishu is an arithmetization in BitZ's style", not BitZ's (frontier page lede too); "What
  Kishu is made of" in one-sentence and short paragraphs. Lowercase "boolean" as an adjective;
  "Booleanity" left as the study spells it (a sweep would touch claims; ask before doing it).
- Ragu's published book has the arithmetization chapter at protocol/construction/, not the
  checkout's protocol/local/; the page links the former. Tachyon main d1f5ffb (real proofs) and
  Ragu main 7914b3b8 are pulled; keep/tachyon-statements.md and TACHYON_STEPS predate them.
- The user's bignum observation and its assessment are in the entry above.

NEXT: the Zoodles statements page (unique ρ for Faerie gold; Orchard-style actions; the key chain
qsk → qk → pk with qk as nullifier key; leanSPHINCS key derivation; the preimage spend's two
compressions, already in the model); re-read Tachyon's step circuits at d1f5ffb first; then the
online measure, the Tachyon → Zoodles application, and the queue as before. The user: some
redundancy remains on the arithmetization page, left for now; KaTeX kerning elsewhere deferred.

STATE: branch book-reorganization at this entry's commit, pushed through 715f07a; the book builds,
822 links check.

NEXT, first (the user, 2026-11-24): investigate whether one bit per digit is the optimal choice for
Kishu, or whether the commitment cost improves by keeping closer to Akita, whose digits are
balanced base-8 digits of a few bits (the paper's "Committing through small digits",
work/akita.txt). The questions: what the Booleanity check would become for digits of several bits
(a range check per digit, higher degree or a decomposition), how the digit count, the constraint
terms, and the Ajtai rate per digit trade off, and what the hash-heavy circuits lose if XOR stops
being one term over bits.

## 2026-11-25 05:49 UTC: every other XOR, tribits, the shared step; PR #5 merged

PR #5 was merged at 8a18caa (merge commit d4ce262). The branch `circuit-improvements` carries
the next PR, five commits on top of main, with the book built and 823 links checking:

- **Every other XOR word committed** (4a034d1). A value needs committing only where it is a
  factor; an XOR output consumed by an adder stays the expressions x + y − 2xy, and of each
  chain of two XORs the second's word is committed and certified against both XORs' inputs at
  two products a bit. BLAKE3 11,216 digits (15,072), 11,120 terms (7,904); BLAKE2s 15,968;
  BLAKE2b in halves 38,272; Keccak-f 92,160 (153,600). The three-addend carries are two bits.
  The Sinsemilla chunk commits the 52 subset products within each half of its ten bits; the
  961 cross products are terms of the two coordinate constraints, with field-constant
  coefficients. Prover work on BLAKE3 −14% plain, −20% zk. The frontier page's lede says which
  commit of the model its figures come from (`<!--model-commit-->`, filled at generation).
- **Tribits for integer-word data** (2231d86). Bits where the circuit needs bits as factors (the
  hashes); tribits, Akita's balanced base-8 digits, for limbs, quotients, carries, claim-field
  values, amounts, hash inputs, with a dibit or a bit for the remainder if needed; the digit
  bound 4 for Kishu (the matrix stays rank 1 unmasked, rank 2 masked; tribits reach degree
  1,024 at floor 147 and 2^25). The range check with Akita's paired predicate is b/2 products
  a digit (b even): one a bit (the Booleanity charge), two a dibit, four a tribit; the products
  beyond one a digit are a fourth PIOP count (piop_sum pads; piop_range_word_mults). A Pasta
  multiplication 374 digits by limbs (1,088), 170 by fingerprint (510); an F_q value 22 digits.
  Recovery 6.1M digits by limbs (17M). Poseidon over F_q now commits 54% of BLAKE3's digits per
  absorbed byte and its merge is cheaper per 64 bytes. The device statement's vector is priced
  at its exact ℓ2 norm with mask elements in the widest digits that keep the matrix at the
  sweep's 1,024 rows: balanced dibits (33 a value) at floor 147, tribits at 128; 19,700 digits,
  response 54 kbytes (50 at 128). BitZ keeps bits (RANGE_CHECK_BITS, BITZ_CLAIM_MULT_BITS).
- **The dibit identities** (the user's): x ⊕ y = x + y + 2xy mod 4; x² mod 4 = x₀; (x² − x) mod 4
  = 2x₁. In F_q each "mod 4" is a committed quotient digit (the −2xy form keeps it a dibit),
  AND = xy − 2c′ follows, AND is not a Z₄ polynomial (mixed second difference 2), XOR has no
  degree-two form mod 8 (checked by enumeration). A dibit XOR's quotient is pinned only by
  committing the reduced result, so dibits cannot leave every other XOR uncommitted; dibits
  "almost everywhere" with bits around the rotation by 7 is 212 digits a G against 196 for bits.
- **The arithmetization page** (67672ab): the witness is small integers in three alphabets fixed
  per position; Writing circuits says which width a value takes and what the range check costs;
  the per-value comparison with a Pedersen coefficient (85 tribits, 935 word multiplications
  against 5,600) and "Kishu is not specialized to Pasta", from the PR review.
- **Review comments and the QR channel** (2b76292): the soundness note's obligations (B2 the
  range check, B4 the fingerprint route's random primes, the limb route circuit-level, Lemma B3
  to be redone for tribits); the Tachyon page's opening as suggested; the QR section now takes
  Keystone's firmware rate (200-byte fragments at 5 fps, 1 kbyte/s): 54 s lossless for the
  response, two to three times with losses; 14 s at 800 bytes a fragment, 5.2 s at the
  version-40 ceiling, reliability depending on the screen, the light and the camera; the device
  holds the mask with the response written over it, beside a 2.9-kbyte witness.
- **The shared step** (ffa2a4c): a Kishu step is the least circuits that hold the merge, the
  step's transcript digits (about 220k at rank 18: twenty BLAKE3 compressions) and one circuit
  for the application (STEP_HEADROOM 1.0), the application's nodes filling the slack too. The
  application's digits are charged exactly (unit_cost); the fold's sum-checks and the mask run
  over the whole step, which now includes the application's digits and the step's transcript
  (before: the merge's circuits alone, an undercount). A per-application slot search was tried
  and reverted: it made the per-step axes inconsistent (a rank-17 row's transaction used a
  34-circuit slot while its bytes and memory were at 12). Keccak zk 0.917 s (1.03), BLAKE3
  leanSPHINCS 0.173 (0.183); recovery zk 0.220 (0.205), Zoodles preimage zk 0.0506 (0.0418).

Findings to weigh (the user asked for such notes): BitZ's rows are priced per committed bit,
so they take the every-other saving without paying the extra products; the merge's transcript
words' own digits are not counted, only their canonicity checks and hashing; Tachyon's
bit-level gates stay bits (its comparisons would be tribits); a fingerprint row at a low rank
has no capacity for an application with multiplications (its transaction is left blank); the
Akita Goldilocks variant with Poseidon beats Kishu's BLAKE3 variant on the device statement
(83.7M against 86.3M word multiplications, plain), as it did before today (109M), the merge
being nearly the whole transaction; the step's transcript hashing is a fixed ~220k digits a
step. The mask width: the measure's optimum is the grid's top at every sampler rate; nine
slices now stop at α ≈ 54 at the recovery's accumulator, ten reach 256; at the page's sampler
α = 48 is within 9.9% of the least, 64 within 7.1%, 128 within 3.1% (Karney's sampler does not
matter, the user). The user asks whether a fixed α is sufficient at all: a per-row width needs
the slices' cost priced (the aggregator's first fold, the response's bytes, the peak memory).

NEXT: the user's decision on α and on a per-row width; then the queue: the online transaction
measure beside the transaction prover; the Zoodles statements page (unique ρ for Faerie gold;
Orchard-style actions; the key chain qsk → qk → pk; leanSPHINCS key derivation); the Tachyon →
Zoodles application; a diff view between model versions on the page (the user: a window on the
old version is hard to keep track of); a lightweight structural check or type system for
constraint programs so that values cannot be left without their intended constraints under
optimizations such as these, with "locally equivalent on all inputs" statements short of full
verification (the user, 2026-11-24); Tachyon's comparisons as tribits; the merge's transcript
words' digits.

STATE: branch circuit-improvements at this entry's commit, five commits past main d4ce262,
unpushed; the book builds, 823 links check.
