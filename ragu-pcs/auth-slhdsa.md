# SLH-DSA at NIST Level 3

This page is for illustration only. Zoodles does not adopt SLH-DSA, and nothing here proposes it.
The page shows what a spend authorization at NIST's 192-bit level would cost inside a proof, since
a signature scheme at that level compounds its cost with the proof system's. The [frontier
page](pareto-template.html#level-3) has the matching illustration for the proof system itself.

## The signature

SLH-DSA [\[FIPS205\]](#ref-fips205) is the standardized form of SPHINCS+, a stateless hash-based
signature. It would authorize a spend exactly as [leanSPHINCS](auth-leansphincs.md) does: the
signature is made outside the proof over the same [transaction
digest](auth-leansphincs.md#the-message), and is verified inside the spend's step. The parameter
set considered is SLH-DSA-SHAKE-192s, which the standard places in security category 3. Its hash is
SHAKE256, so its verifier in the circuit is Keccak permutations.

## Why the small-signature parameter set

The standard has two parameter sets at the level, 192s and 192f. The second signs faster, which a
proof does not benefit from, and costs its verifier more. A verifier recomputes one WOTS+ public key
for each layer of the hypertree: <!--fig:slhdsa_192_chains-->51<!--/fig--> chains, at half of
their <!--fig:slhdsa_192_chain_steps-->15<!--/fig--> steps expected, and the key's
compression. <!--claim:slhdsa_192s_cheaper_to_verify:cd2bff-->SLH-DSA-SHAKE-192f
has <!--fig:slhdsa_192f_layers-->22<!--/fig--> layers where SLH-DSA-SHAKE-192s
has <!--fig:slhdsa_192s_layers-->7<!--/fig-->. So 192s takes an
expected <!--fig:slhdsa_192s_perms-->3,070<!--/fig--> Keccak permutations to verify, for a signature
of <!--fig:slhdsa_192s_sig_bytes-->16,224<!--/fig--> bytes. 192f
takes <!--fig:slhdsa_192f_perms-->9,006<!--/fig-->
permutations, <!--fig:slhdsa_192f_over_s_perms-->2.9<!--/fig--> times as many, for a signature
of <!--fig:slhdsa_192f_sig_bytes-->35,664<!--/fig--> bytes. Either is far more than leanSPHINCS:
192s takes <!--fig:slhdsa_192s_over_leansphincs-->12<!--/fig--> times its permutations.<!--/claim-->
So 192s is the set considered.

The counts follow from the standard's parameters. Each call of the hash absorbs the public seed, a
32-byte address, and its input, which is one permutation for a chain step or a tree node. The
verifier's count is an expectation, since the chains' lengths depend on the message digest.

## The cost in the circuit

A Zoodles transaction of two spends by SLH-DSA-SHAKE-192s and two outputs
is <!--fig:app_zoodles_slhdsa192s_kishu-->283 million<!--/fig--> of Kishu's digits. At the frontier
page's default floor, with zero knowledge and a BLAKE3 transcript, Kishu proves it
in <!--fig:sigtx_slhdsa_147_s-->8.20<!--/fig--> s on one core,
in <!--fig:sigtx_slhdsa_147_steps-->7<!--/fig--> steps of a step
of <!--fig:sigtx_slhdsa_147_rank-->$1.25 \times 2^{25}$<!--/fig--> digits. The same transaction with
leanSPHINCS over BLAKE3 takes <!--fig:sigtx_leansphincs_147_s-->0.110<!--/fig--> s. The frontier
page's transaction list has the SLH-DSA transaction, so that its cost can be seen under any family
and floor.

## With the proof system at NIST Level 3

The frontier page's "165 quantum bits (ADPS16 core-SVP), unreviewed ⚠️" option
raises the security floor for the proof system, also to approximately NIST Level 3. It offers
SHA3-384 for its transcript as an alternative to BLAKE3. The table gives Kishu's prover time for the
transaction of two spends and two outputs with zero knowledge, in seconds on one core, under each
signature and each setting of the proof system. The factor in brackets is against the first cell:
leanSPHINCS over BLAKE3, with Kishu at 147 bits and a BLAKE3 transcript.

| Kishu | leanSPHINCS over BLAKE3 | SLH-DSA-SHAKE-192s |
|---|---|---|
| 147 bits, BLAKE3 transcript | <!--fig:sigtx_leansphincs_147_s-->0.110<!--/fig--> s (×<!--fig:sigtx_leansphincs_147_x-->1.0<!--/fig-->) | <!--fig:sigtx_slhdsa_147_s-->8.20<!--/fig--> s (×<!--fig:sigtx_slhdsa_147_x-->74<!--/fig-->) |
| Level 3, BLAKE3 transcript | <!--fig:sigtx_leansphincs_level3_blake3_s-->0.128<!--/fig--> s (×<!--fig:sigtx_leansphincs_level3_blake3_x-->1.2<!--/fig-->) | <!--fig:sigtx_slhdsa_level3_blake3_s-->11.2<!--/fig--> s (×<!--fig:sigtx_slhdsa_level3_blake3_x-->100<!--/fig-->) |
| Level 3, SHA3-384 transcript | <!--fig:sigtx_leansphincs_level3_sha3_384_s-->0.276<!--/fig--> s (×<!--fig:sigtx_leansphincs_level3_sha3_384_x-->2.5<!--/fig-->) | <!--fig:sigtx_slhdsa_level3_sha3_384_s-->13.5<!--/fig--> s (×<!--fig:sigtx_slhdsa_level3_sha3_384_x-->120<!--/fig-->) |

In the table, <!--claim:sigtx_each_change_dearer:a49e80-->each change makes the transaction dearer
whatever the other two are: down a column the proof system's level and then its transcript hash, and
across a row the signature.<!--/claim--> The signature is by far the largest of the three, since the
transaction's digits are almost all the two verifiers'.

## References

- <a id="ref-fips205"></a>[FIPS205] NIST. Stateless Hash-Based Digital Signature Standard. FIPS 205,
  August 2024. <https://nvlpubs.nist.gov/nistpubs/fips/nist.fips.205.pdf>. Table 2 for the parameter
  sets and their security categories.
