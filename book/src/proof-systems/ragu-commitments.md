# Commitment Schemes for Ragu

This study prices Ragu as a proof-carrying-data scheme under each candidate commitment
scheme, on three measures. They are the compressed proof's bytes, the prover's work in word
multiplications, and the cost of recursion, measured either as the merge circuit's gates or
as the atoms that the merge absorbs. The candidates are:

- Ragu's Pedersen inner-product argument as deployed today, the pre-quantum baseline;
- Akita ([ePrint 2026/1983](https://eprint.iacr.org/2026/1983)), a lattice-based polynomial
  commitment scheme over Module-SIS, priced under five choices of field and commitment
  modulus, from its own 128-bit field to the Pasta base field;
- the hash-based schemes: WHIR over Pasta, over Goldilocks, and with Pasta claims in 64-bit
  limbs; a Plonky3-style FRI over Goldilocks; the Flock/Binius-style binary-field family,
  whose proof sizes come from FRI-Binius; and BitZ, which is Pasta-native through a binary
  field. Each is priced both under ARC accumulation and under its own recursion;
- and, as a draft, BitZ's bit-level arithmetization with Akita as the backend.

The hash-based rows' rate and grinding, the security floor, and zero knowledge are
selectable. For each class, pre-quantum and post-quantum, the comparison marks the frontier:
the configurations that nothing else in the class beats on all three measures at once.
Native support for the Pasta base field counts as a requirement rather than a cost, since
the Ironwood recovery circuit needs it.

No scheme has been selected. The comparison is an input to that choice, beside
implementation experience with each route.

[The PCS frontier](pcs-frontier.md) is the interactive comparison. The study's own material
is in the repository's [`ragu-pcs/`](../../../ragu-pcs/) directory. There,
[`pareto-model.py`](../../../ragu-pcs/pareto-model.py) generates the comparison from the
measurements under [`estimates/`](../../../ragu-pcs/estimates/) and the models beside it, and
[`WORKING-NOTES.md`](../../../ragu-pcs/WORKING-NOTES.md) is the running log of what was done
and what is open. [Regenerating the Study's Numbers](regenerating.md) says where each number
comes from and how to redo it. The two working
notes in this section are the study's longer write-ups. The first prices an Akita opening at
a Pasta modulus; the second shows how a lattice accumulation step can be made
zero-knowledge.
