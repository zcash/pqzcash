# Akita proof sizes at a Pasta modulus: what can be computed now, and how

Written 2026-10-13. Companion to [Zero knowledge for a lattice accumulation
step](zk-fiat-shamir-with-aborts.md), the zk note below. The question: what would an Akita opening
proof cost if the base field were the Pallas base field (255 bits), as Tachyon and the Ironwood
recovery circuit want, and what about Goldilocks. Akita's planner cannot plan a schedule for a
modulus that it does not know, so this note does two things. It re-prices every shipped schedule at
the other field's widths with Akita's own byte formula. And it generates the SIS width tables that a
real Pasta profile would need. The remaining work for a real profile is listed at the end.

## 1. What was built

All code is a patch,
[`scripts/patches/akita/0001-Pallas-and-Goldilocks-moduli-width-re-pricing.patch`](scripts/patches/akita/0001-Pallas-and-Goldilocks-moduli-width-re-pricing.patch),
on `LayerZero-Labs/akita` at commit 60b82bc30f4f8f1130ccd71fe10b0b9bed909ab9 (2026-10-09, Apache-2.0
or MIT); [`scripts/akita-checkout.sh`](scripts/akita-checkout.sh) clones that revision and applies
it (the [Regenerating the study's numbers](REGENERATING.md) page). The diff is small and
self-contained:

- `akita-sis-estimator`: two estimator-only moduli, `pallas` (the Pallas base field) and
  `goldilocks` ($2^{64} - 2^{32} + 1$), selectable in every example by name. They do not have any
  params profile, so the table generators emit CSV for them and the $\ell_\infty$ generator gives
  them the canonical role cells of the checked-in profiles as explicit origins. A small example,
  `pasta_rank`, binary-searches the least row count for a Euclidean bound at each modulus.
- `akita-params`: `NonterminalLevelLayout::with_field_widths`, which re-prices a level's atoms at
  other base-field and challenge-field widths without changing their counts.
- `akita-schedules`: `expanded_schedule_proof_breakdown`, which splits a schedule's proof estimate
  into non-terminal payloads, offloaded setup sum-checks, the terminal extension-opening reduction,
  the terminal response, and grinding nonces, at the schedule's own widths or at a
  `FieldWidthOverride`. With no override its total equals the planner's own estimate, and the
  example checks that on every row.
- `akita-schedules` and `akita-planner`: a process-wide pricing width override,
  `set_pricing_width_override`, consulted by every byte estimate that the planner derives from a
  policy, and read by the artifact generator from `AKITA_PRICING_WIDTHS`. With it set, the planner
  selects schedules by their cost at the override widths
  ([§3.1](#31-letting-the-planner-re-plan-at-pasta-widths)).
- `akita-planner`: the example `catalog_reprice`, which loads every shipped schedule artifact, or
  those in a directory given by `--artifacts`, and prints the breakdown three times. Once at the
  schedule's own modulus, once at Pallas widths (255-bit base and challenge field, no extension),
  and once at Goldilocks widths (64-bit base field, degree-2 challenge extension, as the fp64
  presets use).
- [`scripts/akita-pasta-estimates.sh`](scripts/akita-pasta-estimates.sh): builds, runs the
  re-pricing and the rank ladder, then generates the full Euclidean and $\ell_\infty$ width tables
  for both new moduli as CSV, one log per step and a summary with timings. The tables and TSVs it
  writes are tracked under [`estimates/`](estimates/).

Reproduce the re-pricing alone, in the patched clone, with:

```
RUSTUP_TOOLCHAIN=1.96.0 cargo run --release -p akita-planner --features catalog-gen --example catalog_reprice
```

## 2. What re-pricing means

The planner's proof estimate is a byte formula over a schedule's geometry
(`crates/akita-params/src/proof_size.rs` and `crates/akita-schedules/src/runtime.rs`). Per
non-terminal level it sums opening payloads and compressed images in base-field atoms, the
range-tree, norm, and fused sum-checks in challenge-field atoms, and the next level's compressed
payload. The terminal adds the clear partials in base-field atoms and the digit-valued folded
response at a variable width, and grinding nonces are priced separately.

Re-pricing keeps everything about the schedule fixed: fold levels, witness lengths, digit bases,
sum-check shapes, terminal shape, nonces. It changes only the width of a base-field atom and of a
challenge-field atom, and the claim extension degree used for the extension-opening reduction. So it
prices "this schedule, serialized over that field". It is not the schedule that the planner would
choose for that field. Two effects go the other way:

- Pallas has 85 base-8 digits per coefficient against 43 for the 128-bit field, so a natively
  planned Pasta witness is longer at every level, which adds sum-check rounds and possibly a level.
  This pushes the real figure up.
- The planner would re-optimize levels, block counts, and the terminal shape for 32-byte atoms. This
  can push it down, and [§3.1](#31-letting-the-planner-re-plan-at-pasta-widths) measures it: about
  6%.

The first effect cannot be quantified without a Pasta profile, which is the remaining work of
[§6](#6-the-tail-and-decoupling-the-commitment-modulus). The re-pricing is the part of the answer
that follows from the byte formula alone.

## 3. Results

The fp128 presets do not use any challenge extension and have a claim extension degree of one, so
their geometry is the right template for a Pasta field, which would also use none. The fp32 and fp64
presets carry extension-opening partials that a Pasta schedule would not have, so their Pallas
columns overstate and are not quoted here.

Dense polynomials, fp128 template, bytes:

| coefficients | own modulus (128-bit) | at Pallas widths | ratio |
|---|---|---|---|
| $2^{14}$ | 65,074 | 107,426 | 1.65 |
| $2^{16}$ | 67,325 | 111,869 | 1.66 |
| $2^{24}$ | 70,995 | 119,059 | 1.68 |
| $2^{30}$ | 72,371 | 121,747 | 1.68 |

One-hot polynomials of $2^{12}$ to $2^{15}$ entries, two fold levels: 41,063 at the 128-bit modulus,
63,607 at Pallas widths.

Where the bytes go, dense $2^{14}$:

| component | 128-bit | Pallas widths |
|---|---|---|
| non-terminal payloads | 13,696 | 27,376 |
| terminal response | 50,919 | 79,591 |
| grinding nonces | 459 | 459 |

So the terminal response is most of every shipped proof, and most of the terminal is clear partials
in base-field atoms: about 1,800 of them, which is 28.7 kbytes at 16 bytes and 57.4 kbytes at 32.
The digit-valued folded response, about 22 kbytes, does not change with the field. The non-terminal
levels double because every sum-check message is a challenge-field element.

### 3.1 Letting the planner re-plan at Pasta widths

The second native-planning effect of [§2](#2-what-re-pricing-means) can be measured without a Pasta
profile. The planner selects schedules by their estimated bytes, and every byte estimate that it
derives from a policy passes through a handful of functions in `akita-schedules`. A process-wide
pricing override, set by `AKITA_PRICING_WIDTHS=255:255:1` on the artifact generator, makes those
functions price at Pasta widths while geometry, SIS sizing, digit bases, and validation stay the
fp128 policy's. The planner then chooses the schedule that is cheapest at 32-byte atoms. This was
run over all seventeen fp128 families, 79 rows at about five seconds a row. A no-override run first
confirmed that the generator reproduces the shipped catalog byte for byte.

| dense coefficients | shipped geometry at Pallas widths | re-planned at Pallas widths | saving |
|---|---|---|---|
| $2^{14}$ | 107,426 | 101,441 | 5.6% |
| $2^{16}$ | 111,869 | 105,719 | 5.5% |
| $2^{24}$ | 119,059 | 115,152 | 3.3% |
| $2^{30}$ | 121,747 | 119,520 | 1.8% |

The planner's move is one fold level fewer, not one more. At $2^{14}$ it goes from five levels to
four, which cuts the non-terminal payloads from 27.4 kbytes to 17.7 kbytes and accepts a terminal of
83.4 kbytes instead of 79.6 kbytes. With sum-check messages as wide as partials, a level of
sum-checks no longer pays for the partials it removes. Savings across the fp128 rows run from 1.3%
to 7.5%, and the small one-hot rows with two levels do not change at all. So re-planning takes back
about 6 kbytes of the 42, and a Ragu-sized opening stays around 100 to 106 kbytes on this
accounting.

The earlier estimate of 15 kbytes for the move to a 255-bit field accounted for the terminal
partials at a 64-bit base field and nothing else. From the 128-bit field, the partials alone add
28.7 kbytes, and the sum-checks add about the same again, so the same-geometry figure is about 42
kbytes above fp128, roughly 1.65 times. A Ragu-sized opening, $2^{14}$ to $2^{16}$ dense
coefficients, is therefore around 105 to 115 kbytes on this accounting, before the two
native-planning effects of [§2](#2-what-re-pricing-means).

Goldilocks does not need any new work for proof sizes. Re-pricing the fp64 rows at Goldilocks widths
reproduces the fp64 figures to the byte, because the widths and the extension degree are the same.
The SIS estimator gives the same ranks as the 64-bit representative at every bound tried, since the
two moduli differ by one part in $2^{32}$ in $\log_2 q$. What Goldilocks changes is runtime only:
its 2-adicity makes $X^d + 1$ split completely, the same challenge-set question that Pasta raises in
[§5.4 of the zk note](zk-fiat-shamir-with-aborts.md#54-other-costs).

## 4. SIS tables for the new moduli

The 2026-10-14 run of [`scripts/akita-pasta-estimates.sh`](scripts/akita-pasta-estimates.sh)
completed every step; its outputs are in [`estimates/`](estimates/) beside this note, with
[`summary.txt`](estimates/summary.txt) giving each step's status and duration. The Euclidean width
tables for both moduli, 16,800 rows, took under a second. The $\ell_\infty$ tables, 9,480 rows each
over the canonical role cells, took 2.4 hours for Pallas and 1.1 for Goldilocks. At Pallas 8,963 of
the 9,480 cells are secure up to the search cap, against 7,243 at Goldilocks, because a single ring
row at 255 bits already carries most of the bits that a cell needs. Three readings from the tables:

- Per $\ell_\infty$ cell, the least rank that is secure at any width carries about the same number
  of bits at both moduli, as [§5.2 of the zk
  note](zk-fiat-shamir-with-aborts.md#52-the-module-sis-bound) predicts, with Pallas coarser. At
  ring dimension 128 and coefficient bound 7, Pallas needs rank 1, 128 rows and 32.5K bits, where
  Goldilocks needs rank 4, 512 rows and 32.8K bits. At ring dimension 64 and the same bound, Pallas
  needs rank 2 (32.5K bits) where Goldilocks needs rank 7 (28.7K bits). The whole-row granularity
  costs Pallas 13% there, so a native Pasta profile would prefer the smaller ring dimensions.

- At a Euclidean collision bound of $2^{22}$ and ring dimension 64, one ring row at Pallas (64 rows,
  16,256 bits) secures widths up to 14 ring elements, and rank 2 secures any width. Goldilocks needs
  rank 3 at that bound. Same bits, as expected.
- For the $\ell_\infty$ bound 7 at ring dimension 64, rank 1 at Pallas secures any practical width,
  where Goldilocks rank 1 stops at width 1,380. Pallas commitments therefore come in coarser steps:
  one ring row is 2 kbytes at dimension 64, and the planner would pick smaller ring dimensions to
  get finer steps.

The same run also re-planned all seventeen fp128 families under the decoupled pricing of
[§6.3](#63-decoupling-the-commitment-modulus-from-the-claim-field): across the 79 rows the planner
improves 49 and leaves the rest, saving 0 to 1.7 kbytes per row and 0.7 kbytes on average. The
shipped schedules are already close to the planner's choice under that pricing, so the
[§6.3](#63-decoupling-the-commitment-modulus-from-the-claim-field) figures stand. The shipped
catalog's own security check passed as the last step.

## 5. What this does not tell us

- The native Pasta schedule's reaction to the doubled digit count, the first effect of
  [§2](#2-what-re-pricing-means). The planner's reaction to the atom widths is measured in
  [§3.1](#31-letting-the-planner-re-plan-at-pasta-widths) and is small, so my expectation is a
  modest increase over the re-planned figure.
- Verifier or prover time. The formula counts bytes only.
- The per-merge cost in Ragu, which the planner does not model;
  [§8](#8-conclusions-for-ragu-with-akita-as-a-split-accumulation-pcd-scheme) uses one of Akita's
  own fold levels as a proxy.

## 6. The tail, and decoupling the commitment modulus

### 6.1 What the terminal reveals

Akita's terminal is already LaBRADOR's folded tail (paper §8.2). The last committed fold binds, as
its outgoing message, the inner images $t_i = A_{\mathrm{term}}\, s_i$ of the terminal's $B$ witness
blocks. The terminal then reveals the partial evaluations $e_i$, grinds a nonce, and reveals the
folded response $z = \sum_i c_i s_i$. The verifier checks three relations directly:
$A_{\mathrm{term}}\, z = \sum_i c_i t_i$ in the ring, $\sum_i c_i e_i = a^{\top} G z$ for fold
consistency, and the trace relation that ties the $e_i$ to the claimed value. One block of $t$ and
of $e$ is recomputed from the others and checked against a digest. No outer commitment, range proof,
or relation sum-check is run.

So the clear message per block is $(n_A + 1)\, d_A$ field elements: $n_A d_A$ coordinates of $t_i$
and $d_A$ of $e_i$. In the shipped $2^{14}$ dense schedule that is 1,344 coordinates of $t$ against
448 of $e$ (seven blocks, rank 3, ring dimension 64), plus 16,384 digit-valued response coordinates
at about 1.4 bytes each. The inner images, not the partials, are three quarters of the clear field
elements. Folding them away means one more committed level, which the planner priced and rejected.
At Pasta a field element costs 32 bytes revealed, or about 85 three-bit digits carried, and folding
compresses those digits by only the block count. Revealing wins, which is why the planner stops
where it does.

### 6.2 Inner images are SIS-sized, not field-sized

The $t_i$ are commitment coordinates. Their size in bits is set by Module-SIS, and [§5.5 of the zk
note](zk-fiat-shamir-with-aborts.md#55-checking-the-ranks-with-akitas-estimator) showed that the
bits are independent of the modulus. A native Pasta plan therefore needs about half the rows at the
terminal for the same bound, and the $t$ bytes stay near their fp128 size instead of doubling. The
re-pricing of [§3](#3-results) doubled them. Pricing the inner images and the compressed payloads at
128 bits, with partials and sum-check messages at 255, approximates a native plan's $t$ without
changing the geometry:

| dense coefficients, shipped geometry | all atoms 32 B | $t$ at SIS size | 
|---|---|---|
| $2^{14}$ | 107,426 | 83,234 |
| $2^{16}$ | 111,869 | 87,421 |
| $2^{30}$ | 121,747 | 97,043 |

That is the better estimate for a plain Pasta profile: about 83 to 87 kbytes at Ragu sizes.
Re-planning under this pricing (`AKITA_PRICING_WIDTHS=255:255:1:128`) keeps the shipped geometry:
with inner images at their SIS size, the fp128 schedules are already the planner's choice.

### 6.3 Decoupling the commitment modulus from the claim field

The same observation goes further. Nothing in the commitments needs the modulus to be the claim
field. Binding needs Module-SIS modulo some $q_c$, and the ring relations modulo $q_c$ can be
checked over $\mathbb{F}_p$ with an explicit quotient. The identity $A z - \sum_i c_i t_i = q_c\, k$
holds over the integers, with $\lvert k \rvert$ around $2^{31}$ for Ragu-sized witnesses. An
$\mathbb{F}_p$ identity among integers of size $2^{86}$ cannot wrap, so checking it modulo $p$
checks it over the integers. The quotient $k$ joins the witness as eleven base-8 digits per relation
coordinate, a few thousand digits per level, in the same range check as everything else. Akita
already carries quotient witnesses for the reduction modulo $X^d + 1$, so this is the same kind of
object.

With $q_c = 2^{64} - 59$, Akita's own 64-bit modulus:

- inner images are revealed at 8 bytes and carried as 22 digits plus the quotient, instead of 32
  bytes and 85 digits;
- compressed images, outer commitments, and compression chains are the shipped 64-bit objects, with
  the shipped SIS tables, compression plans, ring dimensions, and challenge families, which also
  removes the fully-splitting-ring question for the challenge sets;
- partials, sum-check messages, and claim values stay at 32 bytes, since they are $\mathbb{F}_p$
  values;
- the response $z$ is unchanged;
- the merge circuit absorbs 64-bit commitment coordinates, three to a Pasta element.

Priced with partials and sum-checks at 255 bits and commitment coordinates at 64, on the shipped
geometry and after re-planning under that pricing (`AKITA_PRICING_WIDTHS=255:255:1:64`, which also
routes the commitment width into the planner's terminal pricing):

| dense coefficients | fp128 | decoupled, shipped geometry | decoupled, re-planned |
|---|---|---|---|
| $2^{14}$ | 65,074 | 71,138 | 70,725 |
| $2^{16}$ | 67,325 | 75,197 | 74,210 |
| $2^{24}$ | 70,995 | 82,003 | 80,257 |
| $2^{30}$ | 72,371 | 84,691 | 84,277 |

One-hot polynomials of $2^{12}$ to $2^{15}$ entries come to 40,375 bytes, slightly below their fp128
figure, because their proof is almost entirely inner images and response. The remaining gap to fp128
on dense polynomials is the sum-check messages and the partials, which cannot be narrowed without
leaving $\mathbb{F}_p$. The re-pricing still keeps the fp128 digit counts for $t$. A native plan
would carry 33 digits per $t$ coordinate instead of 85, which shrinks the recursive witness by
roughly a sixth per level and lets the planner fold deeper.

This is a protocol change, not a parameter: the relation rows gain the quotient terms, and the
knowledge-soundness proof has to be redone with the no-wrap step. LaBinius (ePrint 2026/2103) is an
implemented lattice commitment built on exactly this decoupling, a composite NTT-friendly commitment
modulus under claims in another field, with an extraction that avoids reduction modulo the
commitment modulus by working over the number field; its claim field is binary rather than Pasta,
but its soundness argument is the one to adapt. But it is a far smaller change than a 255-bit
profile, since every lattice object reuses the 64-bit profile, and it keeps Tachyon's circuits on
Pasta. It gets most of what the consensus-layer two-field split would get, without the second proof
system.

### 6.4 What a tail redesign would still have to beat

Within this structure the only tail quantities are $t$, $e$, and $z$. Decoupling makes $t$ cheap.
The partials cost $d_A$ claim-field elements per block, so a smaller terminal ring dimension cuts
them directly, at the cost of a larger challenge-coefficient range for the same soundness. The
response is digit-valued already. A LaBRADOR-style change that commits to the partials and folds
once more would trade $d_A \cdot 32$ bytes per block for the partials' digits folded into the
response, plus a range check. At 85 digits per partial coordinate that trade does not pay. A
genuinely smaller tail at a 255-bit claim field would need a way to reveal the block evaluations in
fewer than $d_A$ coordinates, which is a question about the opening representation rather than about
folding.

## 7. What a real Pasta profile needs

In order of effort, from the survey of the code:

1. A modulus profile in `akita-params`. `SisModulusProfileId::modulus()` returns `u128`, and
   `field_bits()` is derived from it, so a 255-bit modulus needs the representation widened first.
   That touches about fifteen call sites, among them the trivial collision bound in
   `sis/coverage.rs`, the physical-$\ell_2$ norm route, the challenge-field order used by transcript
   grinding, and the NTT cache. The enum itself is matched in about fifty non-test files across the
   workspace, most of them one-line arms.
2. Generated tables: the CSVs in [`estimates/`](estimates/), converted to the `rust-split` module
   format that `generated_sis_table` and `generated_l2_sis_table` consume, plus the table digests.
3. Compression chain plans for 32-byte coefficients: ring dimensions 8 and 4 for the two maps, so
   that an 8192-byte image compresses to 256 bytes and then 128, matching the pattern 64/32, 32/16,
   16/8 of the shipped profiles.
4. A preset in `akita-config`, modeled on `proof_optimized/fp128.rs`, with the base field as its own
   challenge field, a 255-bit field type for the offline path, and ring-challenge configurations for
   each ring dimension. The challenge families and their operator-norm certificates have to be
   redone for a fully splitting prime.
5. Response-model calibration for the optimized later-fold schedules needs an implementation to
   measure; the rigorous bounds of the paper's Appendix G do not, and give an upper bound.

With 1 to 4 done, `gen_schedule_artifacts` plans the schedule and the same breakdown function prices
it exactly.

## 8. Conclusions for Ragu with Akita as a split-accumulation PCD scheme

Take Ragu with Akita in place of Pedersen and IPA as a split-accumulation PCD scheme, with zero
knowledge as an option provided by folding with a random claim ([the zk
note](zk-fiat-shamir-with-aborts.md)). The scheme has four kinds of object, and the figures above
price each of them. Ragu's circuits are about $2^{12}$ gates with committed vectors of $2^{14}$
coefficients over Pasta, and every figure here is flat from that size upward, so the application's
circuit size is not where the cost comes from.

**Accumulator instance.** Today's compressed instance, counted from Ragu's structs at the checked-in
production rank, lists 50 native and 45 nested commitment components. With the registry and
accumulator points on each side that is 100 points of 32 bytes, plus 19 scalars and the two headers:
3,812 bytes plus 64 per header element. Of the 95 components, 54 are endoscaling steps and 4 are
challenge binders, which exist only because of the curve cycle, and several more are the bridge and
nested stages. A lattice instance does not have any of those. It would list on the order of 15 to 20
commitments, compressed to 128 bytes each, about 2.5 kbytes, plus the folded claims and the final
claims of the range and norm obligations. With the zero-knowledge option there is one more claim
group.

**Accumulation proof, one per fold.** Akita's planner does not model Ragu's accumulation step, but
one of Akita's own non-terminal levels is a fair proxy, since it sends the same kinds of object:
compressed commitments and the sum-check transcripts of the range and norm checks. In the re-planned
$2^{14}$ schedule a level costs about 4.4 kbytes at Pasta widths, so a fold's messages are about 5
kbytes on top of the instance. Today's edge carries the step's instance, about 4 kbytes, and no
sum-checks. So the per-edge succinct material goes from about 4 kbytes to about 7.5 kbytes, and it
is also what each merge circuit absorbs into its transcript.

**Accumulator witness.** The digit vector that the holder of an accumulator keeps and passes to
whoever folds it next: $N \approx 2^{22}$ digits, about 1.5 Mbytes, for the unmasked vectors. With
the zero-knowledge option the first fold masks the witness by rejection sampling, which makes it
about 9 times longer, 14 Mbytes, and raises the Module-SIS rank of the accumulation matrix, under
which every accumulator is committed, by about 2.4 times ([§5 of the zk
note](zk-fiat-shamir-with-aborts.md#5-costs)). This is the one cost that the zero-knowledge option
changes materially, and it is paid between provers, not in any proof. The length belongs to the
masked accumulator alone: the aggregator's first fold on it returns to $N$ digits, so the
accumulators above the zero-knowledge layer are the unmasked size, and the rank is what every fold
pays, in the prover's commitment work; Akita's internal levels and terminal keep their own bounds,
so the decider's opening is nearly unchanged.

**Decider proof.** The Akita opening of the final accumulator, which is what Ragu's compression
produces for a third party. At $2^{14}$ to $2^{16}$ coefficients:

| commitment modulus | opening proof |
|---|---|
| 128-bit field, or Goldilocks for both field and commitments | 65 to 67 kbytes |
| Pasta claims, 64-bit commitments ([§6.3](#63-decoupling-the-commitment-modulus-from-the-claim-field)) | 71 to 74 kbytes |
| Pasta for everything ([§6.2](#62-inner-images-are-sis-sized-not-field-sized)) | 83 to 87 kbytes |

Today's compressed proof, counted from the structs at rank 13,
is <!--fig:pedersen_checked_in_h0_bytes-->7,652<!--/fig--> bytes plus 64 per header
element, <!--fig:pedersen_checked_in_bytes-->7,908<!--/fig--> with a header of four elements. That
is the instance above, with the six online openings and two online polynomial commitments that
[§8.1](#81-measured-pedersen-ipa-size-the-group-dependence-and-prover-commitment-work-in-word-multiplications)
describes, and on each curve a revdot reduction of 4 points and 9 scalars, a batch of 1 point and 11
scalars, and an IPA of 13 rounds, 1,696 bytes per
curve. <!--claim:rank14_adds_128_bytes:103069-->Rank 14 adds 128 bytes.<!--/claim--> The model is
[`ragu-size-model.py`](ragu-size-model.py) beside this note. An independent estimate for a $2^{12}$
configuration with the endoscaling steps rebalanced gives about 5.9 kbytes. Before the online
polynomials, the model gave exactly 5,892 bytes at rank 14 with sixteen endoscalings per step on
both sides, one binder, and a two-element header, so that is presumably the configuration found; it
is <!--fig:pedersen_rank14_E16_b1_bytes-->6,372<!--/fig--> bytes now. The extra rank costs 128
bytes, one IPA round per curve. Going from four to eight endoscalings per step removes 37 committed
components, 1,184 bytes, and the doubled circuit is what makes room for them; the step from eight to
sixteen saves a further 320 bytes, and a third doubling of the circuit would cost another 128 bytes
for less than that. Its floor at rank 14 is about 6.2 kbytes, because 4.6 kbytes is independent of
every parameter: the 19 instance scalars, the online openings and commitments, both curves'
reduction and batch messages, and both IPAs. Below 5.5 kbytes needs changes to the compression
protocol itself, such as fewer opened polynomials, rather than parameter choices. The model also
prices the circuit budget (`python ragu-size-model.py budget`), from the internal circuits' gate
counts pinned in Ragu's tests: a rank-14 circuit holds eight endoscalings beside a step's overhead,
not sixteen, and the <!--fig:challenges_bound-->8<!--/fig--> challenges
need <!--fig:min_binders_14-->2<!--/fig--> binders there, so
the <!--fig:pedersen_rank14_E16_b1_bytes-->6,372<!--/fig-->-byte configuration does not
fit. <!--claim:smallest_pedersen_proofs:3bb44a-->The smallest proof that fits
is <!--fig:pedersen_least14_bytes-->6,468<!--/fig--> bytes at rank 14, with
the <!--fig:fixed_native_count-->6<!--/fig--> fixed native circuits packed
into <!--fig:packed_native_14-->3<!--/fig--> and the <!--fig:fixed_nested_count-->3<!--/fig-->
nested into <!--fig:packed_nested_14-->1<!--/fig-->,
or <!--fig:pedersen_least15_bytes-->6,244<!--/fig--> bytes at rank 15
with <!--fig:pedersen_least15_E-->16<!--/fig--> endoscalings per step, one binder, and the fixed
circuits packed into <!--fig:packed_native_15-->2<!--/fig-->
and <!--fig:packed_nested_15-->1<!--/fig-->.<!--/claim--> <!--claim:rank16_no_bytes_gain:c28b8e-->Rank
16 gains nothing further.<!--/claim--> Fewer components is also less prover commitment work: rank 14
packed needs fewer word multiplications than today's rank 13 as well as fewer bytes. Ragu's several
committed vectors open in one Akita batch at no visible cost: the catalog prices two polynomials of
$2^{15}$ within two bytes of one of $2^{16}$, and a separately committed group adds 0.6 to 2 kbytes.
The opening grows by about 0.4 kbytes per doubling of the final witness length, so the masked
witness of the zero-knowledge option adds a few kilobytes. A compressed lattice PCD proof is the
opening plus the 2.5 kbytes instance: 68 to 90 kbytes, or 9 to 11 times today's.

**Reading the table.** The decider proof is 9 to 11 times today's, and the field width moves it by a
quarter at most. The per-edge material is about twice today's. So the decoupled commitment modulus
of [§6.3](#63-decoupling-the-commitment-modulus-from-the-claim-field) matters more for the per-edge
objects, where it halves the width of every commitment coordinate that the merge circuit absorbs,
than for the decider, where it saves 12 kbytes. How often each object is produced is the
application's business.

### 8.1 Measured Pedersen-IPA size, the group dependence, and prover commitment work in word multiplications

**Measured.** Ragu's wire format (`crates/ragu_pcd/src/wire/`, since its PR #875) encodes a
compressed proof field by field at fixed widths behind a 28-byte versioned envelope, and
`CompressedProof::encoded_len::<R, HEADER_SIZE>()` gives the exact length from the rank, the header
size and the profile's component counts. At tachyon-zcash/ragu 8109a41c (2026-11-13) it
gives <!--fig:pedersen_checked_in_wire_bytes-->7,936<!--/fig--> bytes at rank 13 with a four-element
header, so <!--fig:pedersen_checked_in_bytes-->7,908<!--/fig--> of payload,
and <!--fig:pedersen_checked_in_h2_wire_bytes-->7,808<!--/fig--> with a two-element
header. <!--claim:rank14_adds_128_bytes:103069-->Rank 14 adds 128 bytes, one IPA round per curve, so
rank 14 with two header elements and rank 13 with four have the same length.<!--/claim--> The
payload is 448 bytes more than the 7,460 counted from the structs at the fork of 2026-10-04, because
every proof now carries two online polynomials. Those are their two commitments and the six
openings, a point and a value for each slot of the left, right and output proofs. The component
counts are otherwise unchanged, 50 native and 45 nested commitments.

Online polynomials are Ragu's polynomial oracles. A step's application circuit can open each of the
six slots once at the challenge $\zeta$, drawn after the polynomials and the staged values are
committed, and so prove an identity between committed polynomials by Schwartz–Zippel without their
coefficients entering the circuit. Tachyon uses them for its tachygram set polynomials, whose roots
are the set's members: a step proves that its output accumulator is the product of its children's,
or of its input's and the factors $X - t$ for the tachygrams it adds, with one opening per operand.
Every step pays for all six openings whether its headers use them or not, and so does every
compressed proof.

**Groups.** The planner was run for one final group of $2^{14}$ plus $K$ separately committed groups
of $2^{14}$ under the decoupled pricing ([`estimates/`](estimates/) does not include them; the
re-plan scripts under [`scripts/`](scripts/) reproduce them). Opening bytes at Pasta claims with
64-bit commitments: $K = 0$: 70,725; 1: 74,212; 2: 75,562; 4: 76,804; 8: 77,445; 12: 78,580. The
first extra group costs 3.5 kbytes, each further one about 0.4 kbytes. At Pasta for everything the
first extra group costs 14 kbytes, because every partial is a 32-byte atom. So how Ragu's stage
polynomials are grouped is the one Ragu parameter that reaches into Akita, and it matters little
under decoupling.

**Prover commitment work.** Comparing Pedersen and Ajtai commitment work in native 64-bit word
multiplications per coefficient, dense polynomials assumed:

| commitment | per coefficient | basis |
|---|---|---|
| Pedersen over Pasta, rank 14 | <!--fig:pedersen_per_coeff_14-->5,200<!--/fig--> | Ragu's fuse measured at rank 13, 1.46 s on one core for 96 commitments of $2^{13}$ coefficients, scaled by Pippenger's 255/rank mixed additions per coefficient |
| Ajtai, Pasta modulus | <!--fig:ajtai_per_coeff_pasta-->15,000<!--/fig--> | 85 digits, rows/64 + 3 multiplications per digit by NTT, 32 word multiplications each |
| Ajtai, 128-bit field | <!--fig:ajtai_per_coeff_fp128-->1,900<!--/fig--> | 43 digits, 8 word multiplications each |
| Ajtai, Pasta claims with 64-bit commitments | <!--fig:ajtai_per_coeff_pasta_q64-->940<!--/fig--> | 85 digits, 2 word multiplications each |
| Ajtai, Goldilocks | <!--fig:ajtai_per_coeff_goldilocks-->180<!--/fig--> | 22 digits, 1.5 word multiplications each |

So at a 255-bit commitment modulus the Ajtai prover does more wide multiplications per coefficient
than Pedersen, because the digit count outweighs the per-point cost. The decoupled modulus is what
makes the lattice prover cheaper: about seven times fewer word multiplications per coefficient. And
the step commits its circuits as one batch beside five stages, instead of about 100 separate
polynomials. Folding and sum-check work is not in these figures; the page's accumulation prover
measure adds the fold's two sum-checks over the accumulator, at about five field multiplications per
digit a pass, to the merge's commitments. The model and the interactive page are
[`pareto-model.py`](pareto-model.py), [`pareto-template.html`](pareto-template.html), and
`pareto.html` beside this note. The page plots bytes against two measures chosen from the same
seven, the accumulation prover and a whole transaction's prover by default, or the step's prover
alone, merge gates, absorbed atoms, the decider's verification, or the accumulator's memory, for
every configuration of every family, with the hashes in circuits selectable between BLAKE3 which is
the default, and Poseidon 1.1. It marks the frontier of each class, with native or relation Pasta
arithmetic as a requirement in the dominance test, and its Knobs and Circuit budget sections state
every assumption behind the numbers.


**Circuit budget and rank.** The gate counts of the internal circuits, pinned in Ragu's tests at
rank 13, bound the parameters at each rank. A rank-13 circuit
of <!--fig:budget_gates_13-->2,048<!--/fig--> gates holds <!--fig:endoscalings_13-->4<!--/fig-->
endoscalings per step and binds <!--fig:challenges_per_binder_13-->2<!--/fig--> challenges per
binder. Rank 14 holds <!--fig:endoscalings_14-->8<!--/fig-->
and <!--fig:challenges_per_binder_14-->5<!--/fig-->; rank 15
holds <!--fig:endoscalings_15-->17<!--/fig--> and
all <!--fig:challenges_per_binder_15-->8<!--/fig-->, so one binder; rank 16
holds <!--fig:endoscalings_16-->35<!--/fig-->. Under Pedersen-IPA this makes the merge the main
consumer of the rank. Every endoscaling step and binder is its own commitment, so a larger circuit
removes components faster than the IPA adds its 128 bytes per
rank. <!--claim:smallest_pedersen_proofs:3bb44a-->The smallest proof that fits
is <!--fig:pedersen_least14_bytes-->6,468<!--/fig--> bytes at rank 14 with the fixed circuits
merged, or <!--fig:pedersen_least15_bytes-->6,244<!--/fig--> bytes at rank 15,
against <!--fig:pedersen_checked_in_h2_bytes-->7,780<!--/fig--> today, all with two-element
headers.<!--/claim--> Rank 14 also needs fewer word multiplications than today. The application and
the merge therefore compete for the rank. Under Akita the merge verifier is spread over as many step
circuits of the rank's size as it needs, and their witnesses open as one batch. Its commitments are
therefore nearly flat in rank, while the fold's sum-checks over the accumulator, K groups of 2^rank
coefficients, grow with it; the page's accumulation prover measure counts both. From rank 13 to 16
the per-circuit evaluation claims save about 160 bytes and a dozen absorbed atoms, against a few
percent of prover commitment work spent padding the last circuit. The rank then follows the largest
application step. The limits are the padding of every polynomial to $2^{\text{rank}}$ coefficients,
the opening's growth of 0.5 to 2 kbytes per doubling of the batched witness, and the prover's memory
per circuit. The Pareto page shows all of this per configuration, and marks each one as needing
parameter changes only, code changes within the protocol, or design changes.

**Hash-based comparison.** The Pareto page also prices WHIR (ePrint 2024/1586) with ARC accumulation
(ePrint 2024/1731) over Pasta's own field, which is FFT friendly. The proof sizes come from WHIR's
reference implementation at the batched witness size over a 256-bit field, at 128 bits of security
in the proven Johnson regime. The conjectured sizes rest on capacity conjectures that were refuted
over large fields in late 2025 (ePrint 2025/2046; ePrint 2026/1367 §5.4), so they do not apply. What
has been proved beyond the Johnson bound since, for Reed–Solomon codes in fields of large
characteristic (ePrint 2026/2056), is not used: the query counts stay those of the Johnson bound.
The measured proofs
are <!--fig:whir_sweep_1_2_kb-->250 kbytes<!--/fig-->, <!--fig:whir_sweep_1_4_kb-->158 kbytes<!--/fig-->
and <!--fig:whir_sweep_1_8_kb-->126 kbytes<!--/fig--> at rates 1/2, 1/4 and 1/8,
with <!--fig:whir_sweep_1_2_khashes-->2.7k<!--/fig-->, <!--fig:whir_sweep_1_4_khashes-->2.0k<!--/fig-->
and <!--fig:whir_sweep_1_8_khashes-->1.7k<!--/fig--> verifier hashes. A hash commitment is not
homomorphic, so split accumulation does not apply. ARC's verifier checks $2\lambda/\log_2(1/\rho)$
Merkle openings per
input, <!--fig:arc_openings_1_2-->256<!--/fig-->, <!--fig:arc_openings_1_4-->128<!--/fig-->
and <!--fig:arc_openings_1_8-->86<!--/fig--> at those rates, each a path through the accumulator's
tree. At one Poseidon permutation per node that makes a merge
of <!--fig:whir13_rates_gates_min-->1.3<!--/fig-->
to <!--fig:whir13_rates_gates_max-->3.7<!--/fig--> million
gates, <!--fig:whir13_over_akita_poseidon-->50<!--/fig--> times Akita's estimate
and <!--fig:whir13_over_today_min-->10<!--/fig--> to <!--fig:whir13_over_today_max-->30<!--/fig-->
times today's. Ragu's step circuits hold 2,048 gates each at rank 13, so that merge verifier has to
be spread over hundreds of them. Committing their witnesses in Poseidon Merkle trees then costs
about a hundred times Pedersen-IPA's prover commitment work. WARP (ePrint 2025/753) has the same
opening count for Reed–Solomon codes; its linear-time prover needs linear-time codes and does not
help, since hashing rather than encoding is the cost. Basefold is subsumed by WHIR over Reed–Solomon
codes, and Zook (ePrint 2026/391) makes zero knowledge free at the IOP
level. <!--claim:whir_gold_sixth_off:4b4110-->Moving everything to Goldilocks, with the claims in
its cubic extension, cuts the prover by about <!--fig:whir_gold_prover_cut-->5<!--/fig--> times and
the proof by a sixth, to <!--fig:whir_gold13_kb_min-->315 kbytes<!--/fig-->
to <!--fig:whir_gold13_kb_max-->787 kbytes<!--/fig--> at rank 13.<!--/claim--> It grows the merge,
because a Goldilocks Poseidon costs more gates per node. A hybrid with a Pasta witness committed as
four 64-bit limbs gains nothing, unlike Akita's decoupled commitment modulus. The Pasta merge
circuit forces Pasta's hash on the trees, and four limbs per coefficient is more hashing, not less.
So the hash-based route is dominated by Akita on every measure here. What it offers is a native
Pasta field and a mature deployment base. To compete it would need a design with far larger step
circuits and a cheaper hash. The binary-field systems of 2026, Flock (arXiv 2607.27491) and
Binius64, show what that design looks like. They are Boolean circuits over $\mathbb{F}_2$ with
claims in $\mathbb{F}_{2^{128}}$. Flock proves 82,000 BLAKE3 compressions per second on one core,
with proofs of 205 to 395 kbytes at 100 bits. At that rate the Merkle hashes of an ARC merge are
about 44 ms of proving, against 276 ms per node today. The price falls on the application: Pasta
arithmetic, which the Ironwood recovery circuit is made of, then pays the embedding and simulation
overhead that the small-field survey (ePrint 2026/1371, §5) describes. The Pareto page prices the
binary-field route in its own terms, with FRI-Binius's measured commitment proofs at the merge's
witness size and Flock's measured throughput as prover time. At rate 1/8 it comes
to <!--fig:f2_1_8_kb-->240 kbytes<!--/fig--> and the time
of <!--fig:f2_1_8_prover-->1.0e9<!--/fig--> word multiplications per
merge. <!--claim:gold_poseidon_dominates_f2_rate8:1c108b-->Akita over Goldilocks with Poseidon still
dominates it on both, at <!--fig:goldilocks_16_poseidon_kb-->73 kbytes<!--/fig-->
and <!--fig:goldilocks_16_poseidon_prover-->2.4e7<!--/fig-->.<!--/claim--> The merge's Boolean size,
about <!--fig:f2_1_8_gates-->67<!--/fig--> million AND gates, is not comparable with Pasta gates.
LaBinius (ePrint 2026/2103) is a lattice scheme over a binary claim field. It reaches proofs under
103 kbytes with LaBRADOR compression and a prover within twice the hash-based ones, and
[§6.3](#63-decoupling-the-commitment-modulus-from-the-claim-field) says why it matters here.

**Each scheme's own recursion, and BitZ.** At Quang Dao's suggestion the page also prices every
hash-based scheme with full recursion in place of ARC: the merge circuit verifies its two input
proofs, each step emits a full proof, and the decider verifies one. The two rows of a scheme differ
only in the accumulation. For WHIR the recursion is about a wash at rate 1/8: the verifier's 2,600
hashes per input match ARC's 86 openings through 26 levels. At rate 1/2 it saves a fifth of the
merge and half of the prover, since the verifier's queries fall with the rate while ARC's openings
grow with it. <!--claim:fri_rec_twice_arc:e53a1e-->FRI's verifier has twice WHIR's hashes, so its
recursion costs about twice ARC.<!--/claim--> Ligerito's verifier, which Flock and BitZ use, opens
491 columns over its five levels at 100 bits, against ARC's 86 openings at rate 1/8. So its
recursion is two to seven times ARC's hashing, and ARC is the better accumulation for those two.
BitZ (ePrint 2026/2141) is a hash-based commitment for multilinears over any finitely generated
ring. The witness is bit-decomposed and committed packed over $\mathbb{F}_{2^{128}}$ with Flock's
Ligerito. A claim over a ring $R$ is lifted to the integers, through a random prime where $R$ is
large, and proved in the exponent of $\mathbb{F}_{2^{128}}$ by batched GKR grand products, at a cost
per committed bit that does not depend on $R$. With the Universal Constraint Systems of Zinc+
(ePrint 2026/855) the application's Pasta arithmetic is integer relations, integer witnesses with
ideal membership modulo $p$. So the recovery circuit stays Pasta arithmetic at 510 committed bits
per gate (a 255-bit value and its quotient). The merge is a hybrid circuit: its hashing is Boolean,
and its GKR and PIOP verifiers are native over the binary extension and the projection field. Its
costs are measured with the paper's own benchmark, on one thread of this machine. At 128 bits the
implementation works in the unique-decoding regime with fold grinding, where a query is worth under
one bit. Rate 1/8 is its proof-size minimum there: the stand-alone proof at $2^{25}$ bits
is <!--fig:bitz_udr_25_r1_kb-->304 kbytes<!--/fig--> at rate 1/2
and <!--fig:bitz_udr_25_r3_kb-->257 kbytes<!--/fig--> at 1/8, and lower rates only deepen the Merkle
paths. At the Johnson bound the implementation certifies only 118 bits, its level-0 binding in a
128-bit field. BEEP (ePrint 2026/2930) is the analysis that reaches 128 bits there, with several
out-of-domain samples before each fold. No implementation of it exists; the frontier page derives
rows from it, at the 128-bit floor, where the stand-alone proof
is <!--fig:bitz_beep_25_r3_kb-->150 kbytes<!--/fig--> at rate 1/8
and <!--fig:bitz_beep_25_r6_kb-->126 kbytes<!--/fig--> at 1/64. The figures below are the certified
ones. With its hybrid SNARK's PIOPs added, BitZ with ARC at rank 13 and rate 1/8 comes
to <!--fig:bitz13_kb-->538 kbytes<!--/fig-->, <!--fig:bitz13_prover-->1.1e9<!--/fig--> word
multiplications, a <!--fig:bitz13_merge_bits-->67 million<!--/fig--> bit merge and
a <!--fig:bitz13_decider_ms-->9.74<!--/fig--> ms
decider. <!--claim:bitz_gkr_four_fifths:84887d-->Its prover is mostly the grand-product
GKR, <!--fig:bitz_gkr_25_ms-->97<!--/fig--> of <!--fig:bitz_prover_25_ms-->122<!--/fig--> ms at
$2^{25}$ bits and rate 1/2 on one thread; as Quang Dao puts it, the prover with grand-product GKR is
just really
expensive.<!--/claim--> <!--claim:bitz_unbeaten_among_hash_pasta,kishu_beats_bitz13:8c7f84-->It is
on the frontier, because its Pasta arithmetic is one relation per multiplication and no other
hash-based family's row with native or relation Pasta arithmetic has both a smaller proof and a
cheaper prover; Kishu, described below, beats it on both.<!--/claim--> Akita's Pasta variants beat
it on proof size, and its merge is a Boolean witness of the $\mathbb{F}_2$ family's size. BitZ does
not support zero knowledge yet. Quang Dao notes that BitZ's arithmetization might in future be
combined with a lattice backend such as Akita, which would keep its free range checks and claims
over any ring while replacing the hash-based commitment. An internal research draft of September
2026 (provisional) supplies the piece that needs: Booleanity of a committed bit table certified over
the lattice's prime field by one quadratic identity plus an integer norm bound from a structured
random projection, so that the exponent-lift GKR, <!--fig:bitz_gkr_share_pct-->80<!--/fig-->% of
BitZ's prover, is not needed. Its single-threaded reduction at $2^{27}$ bits over $2^{64} - 59$
takes <!--fig:bool_projection_prover_ms-->113<!--/fig--> ms to prove
against <!--fig:bool_sumcheck_prover_ms-->438<!--/fig--> ms for the optimized conventional
Booleanity sumcheck, with verifiers of <!--fig:bool_projection_verify_ms-->0.85<!--/fig-->
and <!--fig:bool_sumcheck_verify_ms-->0.023<!--/fig--> ms. The page prices it
at <!--fig:value_digits-->85<!--/fig--> digits per Pasta value over Akita's 64-bit modulus, bits
where the circuit needs bits and tribits, digits of three bits, for integer words. Its claims are in
that modulus's field, and a Pasta value is recomposed from 32-bit limbs proved as linear claims in
the same sum-check, so it does not use the decoupled commitment. Its merge is Akita's, costed in
digits: a committed bit is one digit, and its arithmetic is native over the 64-bit field and its
quadratic extension, each product's output committed as
tribits, <!--fig:e_mult_digits-->44<!--/fig--> digits. In a step of $2^{21}$ digits with BLAKE3 it
comes to a proof of <!--fig:kishu21_blake3_kb-->74 kbytes<!--/fig-->, a merge prover
of <!--fig:kishu21_blake3_prover-->3.0e7<!--/fig--> word multiplications for the merge's
commitments, and a merge of <!--fig:kishu21_blake3_digits-->1.2 million<!--/fig--> digits in the
sum-check form; with
Poseidon <!--fig:kishu21_poseidon_kb-->74 kbytes<!--/fig-->, <!--fig:kishu21_poseidon_prover-->1.8e7<!--/fig-->
and <!--fig:kishu21_poseidon_digits-->0.72 million<!--/fig--> digits. The projection form's verifier
scans <!--fig:bool_projection_scan-->3.1 million<!--/fig--> public coefficients, which recursion
cannot afford. So against BitZ at rank 17 its proof is <!--fig:kishu_vs_bitz_bytes-->7.3<!--/fig-->
times smaller and its merge prover <!--fig:kishu_vs_bitz_prover_min-->38<!--/fig-->
to <!--fig:kishu_vs_bitz_prover_max-->64<!--/fig-->
times. <!--claim:kishu_blake3_dominates_q64:c39183-->Against the 64-bit Akita variant, which commits
every wire of a hash gate as a 255-bit value, its merge prover under BLAKE3
is <!--fig:kishu_vs_q64_blake3_prover-->190<!--/fig--> times smaller, so under conventional hashes
it dominates that variant on every measure but the merge's count, whose units differ.<!--/claim-->
Quang Dao thinks the prover is likely overestimated here: the commitment rows are sized by the loose
security analysis, with its grinding, and a tighter analysis would cut them, so the figure is an
upper bound. The page's measures are the recursion's, the step's commitments, the accumulator's
opening and the merge circuit, which every design pays and which can be estimated, whereas which
application circuit to benchmark is hard to agree on, since it depends on the application; so the
application enters only through the rank. The recovery circuit itself is hash-heavy: its expensive
parts are seven BLAKE2b-512 compressions by ZIP 2005's cost section, beside two Sinsemilla
commitments, two full-width Pallas scalar multiplications, a Merkle path, and a BLAKE3 compression
in the quantum-key signature. In Kishu a Boolean hash costs one bit per wire, and the integer
arithmetic simulates $\mathbb{F}_p$ without a bit decomposition per operation, with range checks
free. Costed component by component in this arithmetization, the recovery circuit
is <!--fig:app_recovery_kishu_limbs-->6.1 million<!--/fig--> digits by the limb route
or <!--fig:app_recovery_kishu_fingerprint-->3.2 million<!--/fig--> by the fingerprint route, since a
Pasta multiplication cannot be checked modulo one fixed field alone, so either its limbs' carries
are committed or BitZ's random-prime fingerprint runs in three instances whose column sums are
committed per step, against <!--fig:app_recovery_pasta_poseidon-->570,000<!--/fig--> Pasta gates,
which the page's transaction measure uses.

**What is not modeled.** Verifier and prover time, which the byte formula does not touch. The
accumulation step's exact message count, for which the fold-level proxy stands in. And of the two
native-planning effects of [§2](#2-what-re-pricing-means), the planner's own reaction is measured
([§3.1](#31-letting-the-planner-re-plan-at-pasta-widths),
[§6.3](#63-decoupling-the-commitment-modulus-from-the-claim-field)) and the doubled digit count is
not.

## 9. How much to trust the Module-SIS parameters

Akita's advantage over the hash-based route rests on Module-SIS, where that route rests on a random
oracle alone and Pedersen-IPA on the discrete logarithm. This section states what the parameters
assume and where the uncertainty sits.

**The sizing rule.** Every matrix in Akita's catalog is sized so that the cheapest known attack on
its Module-SIS instance costs at least $2^{128}$ operations under the quantum core-SVP model of
[ADPS16]. That model charges $2^{0.265\beta}$ for lattice reduction with BKZ block size $\beta$ and
ignores the polynomial factors. The block size that reaches a given root Hermite factor is taken
from the BKZ 2.0 analysis of [CN11]. Every instance in the catalog lands at block size 484 to 486,
in lattices of dimension 2,000 to 4,800. The catalog's own security check reports 128.26 bits on
each. A cross-check with the maintained lattice estimator [LE] agrees on the ranks ([§5.5 of the zk
note](zk-fiat-shamir-with-aborts.md#55-checking-the-ranks-with-akitas-estimator)). The estimator is
maintained; the paper that introduced it, [APS15], is not, and its authors say so in a 2019 note.
The estimator costs BKZ as 8·n calls to an SVP oracle of the block size, with sieving per [BDGL16]
classically and per [LMvdP15] and [Laa16] quantumly. It follows [ADPS16] for the primal attack, as
[AGVW17] established, and leaves out the dimensions for free of [Duc18] and [ADH+19]. The same block
size under other models:

| Cost model | Bits at $\beta = 485$ | Source |
|---|---|---|
| classical sieving, $2^{0.292\beta}$ | 142 | [BDGL16] |
| quantum sieving, $2^{0.265\beta}$, the floor used | 128 | [Laa16], as adopted in [ADPS16] |
| "paranoid" lower bound, $2^{0.2075\beta}$ | 101 | [ADPS16] |

For calibration, ML-DSA [FIPS204], the standardized Dilithium, sizes its SIS instances at block
sizes of about 423, 638 and 909 for its three security levels [Dil21]. These parameters therefore
sit between its levels 2 and 3 on the same model.

**Where the uncertainty sits.** Three places, in decreasing order of concern.

- *Proof-level slack, not the assumption.* Lattice schemes have slipped before by sizing for honest
  norms rather than the extractor's. Akita sizes for the extractor's collision bound, which is why
  the masked variant needs 340 scalar rows against 143 on the zk note's [Euclidean
  route](zk-fiat-shamir-with-aborts.md#55-checking-the-ranks-with-akitas-estimator), and rank 2
  against rank 1 at the 64-bit modulus on the $\ell_\infty$ route [the frontier
  page](pareto-template.html#security-floor) takes. But the knowledge-soundness proof in the quantum
  random-oracle model is still in progress. And the decoupled commitment modulus of
  [§6.3](#63-decoupling-the-commitment-modulus-from-the-claim-field) has no soundness argument yet
  beyond the LaBinius analogue. A gap of that kind moves parameters by a lot, not by twenty bits.
- *The instantiation is unusual.* Ring dimension 64 with 128-bit or 255-bit moduli, compression
  rings of dimension 8 and 4, and norm bounds up to $2^{48}$ are far from the regime of the
  standardized schemes. No attack exploits module structure beyond constant factors. Module-SIS has
  a worst-case reduction [LS15], and the quantum attacks on ideal lattices [CDW17] need principal
  ideals, which modules of rank 64 and more do not present. But there is less cryptanalytic
  attention on this corner, and the $\ell_\infty$ bounds take their own estimator route
  ([§4](#4-sis-tables-for-the-new-moduli)).
- *The cost model.* Core-SVP is already a lower-bound style model. Refinements since 2016, such as
  the dimensions for free of [Duc18], have moved concrete estimates by ten to twenty bits either
  way. The disputed dual-attack improvements of [MATZOV22], reassessed in [DP23], concern LWE rather
  than SIS, which is attacked through the primal route. A 128-bit quantum floor is 142 classical
  bits, and the paranoid model still gives 101.

**Against the other assumptions.** The hash-based route's assumption is weaker in the good sense: a
random oracle and collision resistance only. Its soundness risk is concentrated in the proximity-gap
conjectures, which is exactly where the 2025 refutations landed
([§8.1](#81-measured-pedersen-ipa-size-the-group-dependence-and-prover-commitment-work-in-word-multiplications)).
So every hash-based row takes its query counts from the proven Johnson regime. Pedersen-IPA rests on
the discrete logarithm on Pasta, about 126 classical bits and nothing against a quantum adversary.
So the fair statement is that Akita dominates on efficiency while adding one assumption whose
concrete hardness is estimated rather than proven. That assumption has SIS studied since [Ajt96],
Module-SIS since [LS15], and standardization behind it.

**A margin.** [The frontier page's](pareto-template.html#security-floor) higher floor is 147 quantum
bits, which moves the block size from 484 to about 556. It was to be 150. The width tables were
generated at 150 bits first ([`scripts/akita-150-tables.sh`](scripts/akita-150-tables.sh); those
tables are not kept under [`estimates/`](estimates/)). There the Euclidean rank ladder alone needs
12 percent more rows (the `pasta_rank` example under the 150-bit policy), and the coefficient-L∞
tables, which size the catalog's matrices, move
more. <!--claim:shrink_q32_least,shrink_36fold_large_dims:117006-->Where the 147-bit floor binds,
the median shrink of the maximum secure width, over the cells where neither width is at the
estimator's search cap and the width falls, is a factor of <!--fig:shrink_small_min-->2<!--/fig-->
to <!--fig:shrink_small_max-->3<!--/fig--> at ring dimensions up to
32, <!--fig:shrink_64_min-->4<!--/fig--> to <!--fig:shrink_64_max-->10<!--/fig--> at
64, <!--fig:shrink_mid_min-->4<!--/fig--> to <!--fig:shrink_mid_max-->13<!--/fig--> at 128 and 256,
and <!--fig:shrink_large_min-->6<!--/fig--> to <!--fig:shrink_large_max-->15<!--/fig--> at 512 and
above, the 32-bit modulus at the low end of each range.<!--/claim--> The exception is the largest
dimension of each table, where it is about 60. The q64 and Goldilocks tables each have 83 small
cells with no secure width at all. But a re-plan at 150 bits cannot run. Akita's compression chain
is built from rank-one maps, and at the catalog's geometry its first map, at ring dimension 16 and
width 4,096, certifies at 147.3 bits; the 150-bit cell allows width 3,806. Raising the maps to rank
two, or splitting them, would double the compressed images at every level. So the floor is 147 bits,
the most the rank-one maps allow. At that floor Akita's catalog is re-planned by its own planner, in
a checkout whose single policy, runtime width tables and compression cells are retargeted to 147
bits (2026-11-12). The page's openings there are therefore planned rather than scaled. The planner
does not give the prover's rows term or the verifier's inner-image share. For those the page's model
takes the 115 weakest Module-SIS instances in the shipped catalog's security report
([`estimates/catalog-security.tsv`](estimates/catalog-security.tsv)) and, for each, the smallest
module rank that covers the instance's width at both floors. With the catalog's own mix of moduli
the ranks sum to <!--fig:rank_sum_own_128-->121<!--/fig--> at 128 bits and
to <!--fig:rank_sum_own_147-->150<!--/fig--> at 147 bits, a factor
of <!--fig:rank_scale_own-->1.24<!--/fig-->, with <!--fig:rank_moves_own-->29<!--/fig--> instances
moving up a rank; at 150 bits the sum was 154, a factor of 1.27. Over a 64-bit modulus, where the
ranks are higher to begin with, the sums are 185 and 211, a factor of 1.14, with 26 moving; at 150
bits 215, a factor of 1.16. The q64 and Goldilocks tables are identical for these cells. Over Pallas
the instances sit at the width cap at both floors but one: the sums
are <!--fig:rank_sum_pallas_128-->117<!--/fig--> and <!--fig:rank_sum_pallas_147-->118<!--/fig-->, a
factor of <!--fig:rank_scale_pallas-->1.01<!--/fig-->. WHIR's proofs, measured with the reference
implementation over both fields, are <!--fig:whir_scale_147_pct-->16<!--/fig--> percent larger at
147 bits than at 128 and its verifier's hashes <!--fig:whir_hashes_147_pct-->12<!--/fig--> percent
more, through λ alone; ARC's openings grow by <!--fig:arc_floor_pct-->15<!--/fig--> percent.
Pedersen-IPA over Pasta rests on the discrete logarithm in a group of order near $2^{254}$: about
126 classical bits by Pollard rho, and nothing against a quantum adversary. The page shows it at the
128-bit floor as the conventional pre-quantum baseline. It drops out at 147 bits, which it does not
reach even classically.

**References.**

- [ADH+19] Martin R. Albrecht, Léo Ducas, Gottfried Herold, Elena Kirshanova, Eamonn W.
  Postlethwaite, Marc Stevens. The general sieve kernel and new records in lattice reduction.
  EUROCRYPT 2019. <https://eprint.iacr.org/2019/089>
- [ADPS16] Erdem Alkim, Léo Ducas, Thomas Pöppelmann, Peter Schwabe. Post-quantum key exchange: a
  new hope. USENIX Security 2016. <https://eprint.iacr.org/2015/1092>
- [AGVW17] Martin R. Albrecht, Florian Göpfert, Fernando Virdia, Thomas Wunderer. Revisiting the
  expected cost of solving uSVP and applications to LWE. ASIACRYPT
  2017. <https://eprint.iacr.org/2017/815>
- [Ajt96] Miklós Ajtai. Generating hard instances of lattice problems. STOC
  1996. <https://doi.org/10.1145/237814.237838>
- [APS15] Martin R. Albrecht, Rachel Player, Sam Scott. On the concrete hardness of Learning with
  Errors. J. Math. Cryptol. 9(3), 2015. <https://eprint.iacr.org/2015/046>. Marked outdated by its
  authors in 2019; see [LE] and [Pla18].
- [BDGL16] Anja Becker, Léo Ducas, Nicolas Gama, Thijs Laarhoven. New directions in nearest neighbor
  searching with applications to lattice sieving. SODA 2016. <https://eprint.iacr.org/2015/1128>
- [CDW17] Ronald Cramer, Léo Ducas, Benjamin Wesolowski. Short Stickelberger class relations and
  application to Ideal-SVP. EUROCRYPT 2017. <https://eprint.iacr.org/2016/885>
- [CN11] Yuanmi Chen, Phong Q. Nguyen. BKZ 2.0: better lattice security estimates. ASIACRYPT
  2011. <https://doi.org/10.1007/978-3-642-25385-0_1>
- [Dil21] Léo Ducas, Eike Kiltz, Tancrède Lepoint, Vadim Lyubashevsky, Peter Schwabe, Gregor Seiler,
  Damien Stehlé. CRYSTALS-Dilithium: algorithm specifications and supporting documentation, version
  3.1, 2021. <https://pq-crystals.org/dilithium/data/dilithium-specification-round3-20210208.pdf>
- [DP23] Léo Ducas, Ludo Pulles. Does the dual-sieve attack on Learning with Errors even work?
  CRYPTO 2023. <https://eprint.iacr.org/2023/302>
- [Duc18] Léo Ducas. Shortest vector from lattice sieving: a few dimensions for free. EUROCRYPT
  2018. <https://eprint.iacr.org/2017/999>
- [FIPS204] NIST. Module-Lattice-Based Digital Signature Standard. FIPS 204,
  2024. <https://doi.org/10.6028/NIST.FIPS.204>
- [Laa16] Thijs Laarhoven. Search problems in cryptography: from fingerprinting to lattice sieving.
  PhD thesis, Eindhoven University of Technology, 2016.
- [LE] Martin R. Albrecht et al. The lattice estimator. <https://github.com/malb/lattice-estimator>.
  Its SIS module is what the cross-check in [§5.5 of the zk
  note](zk-fiat-shamir-with-aborts.md#55-checking-the-ranks-with-akitas-estimator) used.
- [LMvdP15] Thijs Laarhoven, Michele Mosca, Joop van de Pol. Finding shortest lattice vectors faster
  using quantum search. Des. Codes Cryptogr. 77, 2015. <https://eprint.iacr.org/2014/907>
- [LS15] Adeline Langlois, Damien Stehlé. Worst-case to average-case reductions for module lattices.
  Des. Codes Cryptogr. 75(3), 2015. <https://eprint.iacr.org/2012/090>
- [MATZOV22] MATZOV. Report on the security of LWE: improved dual lattice attack. Zenodo, 2022.
- [Pla18] Rachel Player. Parameter selection in lattice-based cryptography. PhD thesis, Royal
  Holloway, University of London, 2018.
