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
