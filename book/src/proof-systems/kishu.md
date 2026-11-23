# Kishu

Kishu is the draft lattice route in the comparison: BitZ's bit-level arithmetization with Akita
as the commitment scheme. Each wire is committed as its bits under Akita's 64-bit modulus, the
constraints and the Booleanity check are sum-checks over that field's quadratic extension, and
Pasta values enter as 32-bit limbs or through a fingerprint rather than as claims in the Pasta
field. It is priced, with its applications, in the frontier page's
[Kishu section](pcs-frontier.md#kishu).

The two pages here are the study's longer write-ups on it.
[Zero Knowledge for a Lattice Accumulation Step](kishu/zk-fiat-shamir-with-aborts.md) shows how
the user's fold of an Akita accumulator is made zero-knowledge by rejection sampling, the masking
fold that Kishu's zero-knowledge rows pay for.
[Kishu's Soundness Obligations](kishu/kishu-soundness.md) states what has to be proved for
Kishu: Akita's own knowledge soundness at its 64-bit profile, the Booleanity check, and a limb
lemma.
