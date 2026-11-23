# Kishu

Kishu is the draft lattice route in the comparison: Ragu's proof-carrying-data arrangement and
split accumulation, arithmetization ideas from [BitZ](https://eprint.iacr.org/2026/2141), and
[Akita](https://eprint.iacr.org/2026/1983) as the polynomial commitment scheme. Each wire is
committed as its bits under Akita's 64-bit modulus, the constraints and the Booleanity check
are sum-checks over that field's quadratic extension, and Pasta values enter as 32-bit limbs or
through a fingerprint rather than as claims in the Pasta field. The name follows the naming
convention of Japanese dog breeds used by Akita and its predecessor Hachi, with a nod to the
"u" from Ragu.

Kishu has not been implemented. The frontier page's [Kishu section](pcs-frontier.md#kishu)
holds its performance and security modelling beside the competing schemes', but many details
remain to be filled in.

The idea of combining Akita and BitZ came from their designers. We would particularly like to
thank Quang Dao (Akita), Albert Garreta (BitZ), and Tal Derei (Tachyon Project), for fruitful
discussions with Daira-Emma Hopwood at the Cambridge PQC workshop. The performance and security
modelling, the suggestion to use them in Zcash, and the name Kishu came from Daira-Emma. Ulrich
Haböck made suggestions on performance modelling that influenced the design.

The two pages here are the study's longer write-ups on it.
[Zero Knowledge for a Lattice Accumulation Step](kishu/zk-fiat-shamir-with-aborts.md) shows how
the user's fold of an Akita accumulator is made zero-knowledge by rejection sampling, the masking
fold that Kishu's zero-knowledge rows pay for.
[Kishu's Soundness Obligations](kishu/kishu-soundness.md) states what has to be proved for
Kishu: Akita's own knowledge soundness at its 64-bit profile, the Booleanity check, and a limb
lemma.
