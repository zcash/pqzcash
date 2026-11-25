# leanSPHINCS

The second authorization method is a stateless hash-based signature on a digest of the transaction,
made outside the proof and verified inside the host's transaction. The signature and the public key
are witnesses, which the zero-knowledge fold hides, so spends stay unlinkable and no re-randomized
signature is needed. The scheme is leanSPHINCS, the signature of post-quantum Ethereum
[\[EIP-8288\]](#ref-eip8288) [\[Lit26\]](#ref-lit26). A signature
is <!--fig:leansphincs_sig_bytes-->4,276<!--/fig--> bytes with [\[Wam26\]](#ref-wam26)'s pruned key
of lifetime $2^{30}$, the configuration priced
here, <!--fig:leansphincs_layered_sig_bytes-->6,332<!--/fig--> with its layered forest key,
and <!--fig:leansphincs_ethereum_bytes-->7,740<!--/fig--> with Ethereum's provisional set. Signing
is hashing alone. The pruned key adds <!--fig:leansphincs_grind-->16,384<!--/fig--> grinding digests
per signature, and its proved lifetime is <!--fig:leansphincs_lifetime-->126,900<!--/fig-->
signatures, one per transaction. The grind is the signer's, since it is keyed and the key cannot
leave the signer without revealing which leaves it kept; a full tree with a helper building and
storing it has no grind, which [Hardware wallets](hardware-wallets.md) takes up.

## The message

Since the signature is made outside the proof, its message has to bind the transaction's effecting
data. In Zoodles it is a BLAKE3 digest of them: each spend's two nullifiers, each output's
commitment, the change commitment, the fee, and the
epoch, <!--fig:zoodles_sighash_bytes-->235<!--/fig--> bytes
or <!--fig:zoodles_sighash_blake3-->4<!--/fig--> compressions. The digest is a PCD header value:
each spend verifies its signature over it, and the fee step recomputes it from the nullifiers and
commitments that its children's headers carry. The verification, not the digest, is the expensive
part of the method. In ZIP 2005's Recovery Statement [\[ZIP-2005\]](#ref-zip2005) the message is the
SigHash.

## The verifier in the circuit

The host proves the verifier inside its
transaction: <!--fig:leansphincs_blake3_calls-->298<!--/fig--> BLAKE3 or BLAKE2s compressions,
or <!--fig:leansphincs_keccak_calls-->262<!--/fig--> Keccak-f permutations, for the pruned key,
against <!--fig:leansphincs_layered_blake2s_calls-->462<!--/fig--> compressions
or <!--fig:leansphincs_layered_keccak_calls-->408<!--/fig--> permutations for the layered one
and <!--fig:leansphincs_ethereum_perms-->515<!--/fig--> permutations for Ethereum's. XOR is not free
in a digit arithmetization, so in Kishu a BLAKE3 compression
is <!--fig:blake3_bits-->11,000<!--/fig--> committed bits, a BLAKE2s
compression <!--fig:blake2s_bits-->15,800<!--/fig-->, and a Keccak-f
permutation <!--fig:keccak_bits-->92,200<!--/fig-->. <!--claim:leansphincs_blake3_cheaper:1c1db2-->The
verifier is therefore <!--fig:app_leansphincs_blake3_kishu-->3.38 million<!--/fig--> digits with
BLAKE3 and <!--fig:app_leansphincs_blake2s_kishu-->4.74 million<!--/fig--> with BLAKE2s, so BLAKE3's
is <!--fig:leansphincs_blake3_of_blake2s_pct-->71<!--/fig--> percent of BLAKE2s's, since its
compression has seven rounds to BLAKE2s's
ten.<!--/claim--> <!--claim:leansphincs_keccak_dearer:8d35d3-->With Keccak it
is <!--fig:app_leansphincs_keccak_kishu-->24.2 million<!--/fig-->, <!--fig:leansphincs_keccak_over_blake2s-->5.1<!--/fig-->
times BLAKE2s's, which is Ethereum's open hash question seen from the circuit.<!--/claim--> In a
Boolean circuit with XOR free the Keccak-to-BLAKE2s ratio
is <!--fig:leansphincs_keccak_over_blake2s_boolean-->3.3<!--/fig-->. With zero knowledge Kishu
proves the BLAKE3 verifier in <!--fig:tx_leansphincs_blake3_kishu_zk_s-->0.173<!--/fig--> s on one
M4 core at rank <!--fig:tx_leansphincs_blake3_kishu_zk_rank-->20<!--/fig-->, the BLAKE2s one
in <!--fig:tx_leansphincs_blake2s_kishu_zk_s-->0.222<!--/fig--> s at
rank <!--fig:tx_leansphincs_blake2s_kishu_zk_rank-->21<!--/fig-->, and the Keccak one
in <!--fig:tx_leansphincs_keccak_kishu_zk_s-->0.917<!--/fig--> s at
rank <!--fig:tx_leansphincs_keccak_kishu_zk_rank-->22<!--/fig-->,
beside <!--fig:tx_recovery_kishu_zk_s-->0.220<!--/fig--> s for the recovery circuit itself.
Ethereum's draft fixes Keccak-256 as the scheme's only primitive, and the circuit and the device
both argue against it. If Ethereum keeps Keccak, there is no compatibility to gain from BLAKE2s
either, and the choice is between Keccak and BLAKE3, Zoodles' own hash and the cheapest of the three
in the circuit. On the device BLAKE3's compression has fewer rounds than BLAKE2s's, though
[\[Wam26\]](#ref-wam26)'s benchmark did not measure it.

## References

- <a id="ref-eip8288"></a>[EIP-8288] Vitalik Buterin, Thomas Coratger. EIP-8288: in-mempool
  signature and proof aggregation. Draft, 2026. <https://eips.ethereum.org/EIPS/eip-8288>
- <a id="ref-lit26"></a>[Lit26] Ivan Litteri. Dependency frames for leanSPHINCS signatures. Draft
  EIP-8504, 2026. <https://github.com/ethereum/EIPs/pull/12672>
- <a id="ref-wam26"></a>[Wam26] Tom Wambsgans. leanSPHINCS: a hash-based stateless signature scheme
  for post-quantum Ethereum, with security proofs in Lean 4. 2026. <https://sphincs.art/>; the
  hardware-wallet benchmark at <https://github.com/TomWambsgans/hardware-wallet-benchmark>
- <a id="ref-zip2005"></a>[ZIP-2005] Daira-Emma Hopwood, Jack Grigg. ZIP 2005: Ironwood Quantum
  Recoverability. <https://zips.z.cash/zip-2005>
