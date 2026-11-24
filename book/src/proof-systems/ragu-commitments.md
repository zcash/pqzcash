# Commitment Schemes for Ragu

This study prices Ragu as a proof-carrying-data scheme under each candidate commitment
scheme, on the measures of [The PCS Frontier](pcs-frontier.md): the compressed proof's bytes,
and two more chosen from eight, among them the prover's work for one step's commitments, for
a fuse's accumulation, and for a whole transaction, the merge circuit's gates or the atoms it
absorbs, the decider's work, and the accumulator's and a fuse's peak memory. The candidates
are:

- Ragu's Pedersen inner-product argument as deployed today, the pre-quantum baseline;
- Akita ([ePrint 2026/1983](https://eprint.iacr.org/2026/1983)), a lattice-based polynomial
  commitment scheme over Module-SIS, priced under five choices of field and commitment
  modulus, from its own 128-bit field to the Pasta base field;
- the hash-based schemes: WHIR over Pasta, over Goldilocks, and with Pasta claims in 64-bit
  limbs; a Plonky3-style FRI over Goldilocks; the Flock/Binius-style binary-field family,
  whose proof sizes come from FRI-Binius; and BitZ, which is Pasta-native through a binary
  field. Each is priced both under ARC accumulation and under its own recursion;
- and [Kishu](kishu.md), BitZ's bit-level arithmetization with Akita as the backend, a draft.

The hash-based rows' rate and grinding, the security floor, zero knowledge, and the hashes
allowed in circuits are selectable. For each class, pre-quantum and post-quantum, the
comparison marks the frontier: the configurations that nothing else in the class dominates on
proof bytes, the two chosen measures, and three requirements. Native support for the Pasta
base field is one requirement, since the Ironwood recovery circuit needs it; the others are
the scheme's assumption and whether a row needs only parameter changes.

No scheme has been selected. The comparison is an input to that choice, beside
implementation experience with each route.

[The PCS frontier](pcs-frontier.md) is the interactive comparison. The study's own material
is in the repository's [`ragu-pcs/`](../../../ragu-pcs/) directory. There,
[`pareto-model.py`](../../../ragu-pcs/pareto-model.py) generates the comparison from the
measurements under [`estimates/`](../../../ragu-pcs/estimates/) and the models beside it, and
[`WORKING-NOTES.md`](../../../ragu-pcs/WORKING-NOTES.md) is the running log of what was done
and what is open. [Regenerating the Study's Numbers](regenerating.md) says where each number
comes from and how to redo it. The study's longer write-ups are in the [Kishu](kishu.md) and
[Other Schemes](other-schemes.md) sections: for Kishu, the zero-knowledge fold of a lattice
accumulation step and the soundness statements; for the others, an Akita opening priced at a
Pasta modulus and the soundness statement of the variant with Pasta claims.
