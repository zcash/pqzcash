# CAPSS

A third authorization method, which Zoodles does not adopt, is a SNARK-friendly post-quantum
signature: one whose verification is cheap inside a proof because its hashing is a permutation that
is cheap in the proof system at hand, rather than a bit-oriented hash. CAPSS [\[FR25\]](#ref-fr25)
is a framework for such signatures, and the one [suggested by Tachyon's
book](https://tachyon.z.cash/book/revisit.html#pq-rerand). The signature is a zero-knowledge proof
of knowledge of a preimage under a one-way function built by truncating the permutation, made with
SmallWood [\[FR25a\]](#ref-fr25a), a hash-based argument whose Merkle trees and transcript hashing
use the same permutation. Its security rests on that permutation alone, modelled as ideal, plus the
random-oracle heuristic for the sponge. The paper instantiates it with Anemoi, Griffin, Poseidon,
and Rescue-Prime, but the framework takes any permutation; which one is a question for the proof
system that verifies the signature.

## The paper's figures

Over a 256-bit field at 128 bits, the paper's instances are
between <!--fig:capss_short_bytes_min-->9,504<!--/fig-->
and <!--fig:capss_fast_bytes_max-->25,824<!--/fig--> bytes, with verification
between <!--fig:capss_r1cs_min-->20,717<!--/fig--> and <!--fig:capss_r1cs_max-->71,145<!--/fig-->
rank-1 constraints. Its headline instances are
Anemoi's, <!--fig:capss_anemoi_default_bytes-->12,640<!--/fig--> bytes
and <!--fig:capss_anemoi_default_r1cs-->23,484<!--/fig--> constraints at the default trade-off, with
verification calling the permutation about <!--fig:capss_verify_calls-->173<!--/fig--> times and
signing about <!--fig:capss_sign_calls-->13,900<!--/fig-->. Over the 64-bit Goldilocks field, which
is Kishu's size, the implemented Anemoi instance signs
in <!--fig:capss_goldilocks_sign_ms-->101<!--/fig--> ms and verifies
in <!--fig:capss_goldilocks_verify_ms-->1.4<!--/fig--> ms on a desktop core
at <!--fig:capss_goldilocks_bytes-->9,715<!--/fig--> bytes,
against <!--fig:capss_bn254_sign_ms-->2,460<!--/fig--> ms of signing over a 254-bit field. The paper
estimates the 64-bit verifier at <!--fig:capss_goldilocks_r1cs_min-->80,000<!--/fig-->
to <!--fig:capss_goldilocks_r1cs_max-->100,000<!--/fig--> constraints,
about <!--fig:capss_field_factor-->4<!--/fig--> times the 256-bit field's, since the smaller field
needs more repetitions for the same soundness.

Anemoi is not the permutation to use. The algebraic FreeLunch attacks [\[BBL+24\]](#ref-bbl24) and
the Gröbner-basis cryptanalysis of Anemoi that followed [\[CR25\]](#ref-cr25) have cut its margin,
and Griffin's and Rescue-Prime's with it, below the 128 bits the paper's parameters claim. The paper
says so and keeps its parameters for comparability. Its Poseidon instances, which the attacks do not
reach, are the conservative ones: <!--fig:capss_poseidon_default_bytes-->19,616<!--/fig--> bytes
and <!--fig:capss_poseidon_default_r1cs-->46,567<!--/fig--> constraints at the default trade-off,
with verification calling the permutation about <!--fig:capss_poseidon_verify_calls-->143<!--/fig-->
times at three widths and signing about <!--fig:capss_poseidon_sign_calls-->10,000<!--/fig-->.

## An instance for Kishu

A SNARK-friendly signature's advantage is in a prime-field arithmetization: there a CAPSS verifier
is tens of thousands of multiplication gates, where a leanSPHINCS
verifier's <!--fig:leansphincs_blake3_calls-->298<!--/fig--> BLAKE3 or BLAKE2s compressions are
millions. Kishu commits bits, which is what suits BLAKE2s to it, and a field wire costs
it <!--fig:q64_digits-->22<!--/fig--> digits, so the comparison has to be made in Kishu's own units.
The permutation that is cheap in Kishu is Poseidon over its 64-bit field, which the model already
prices at <!--fig:q64_poseidon_mults-->276<!--/fig--> multiplications a permutation, each a
committed wire. Taking the paper's Poseidon call counts and its factor
of <!--fig:capss_field_factor-->4<!--/fig--> for the 64-bit field, a verifier is
about <!--fig:capss_kishu_poseidon_digits_est-->3.47 million<!--/fig--> digits,
against <!--fig:app_leansphincs_blake3_kishu-->3.35 million<!--/fig--> for leanSPHINCS with BLAKE3
and <!--fig:app_leansphincs_blake2s_kishu-->4.72 million<!--/fig--> with BLAKE2s. The paper's own
constraint estimate for the 64-bit field, at one wire a constraint,
gives <!--fig:capss_kishu_digits_est-->2.2 million<!--/fig-->. So in Kishu the two are within a
factor of two or so of each other, and nothing like the order of magnitude a prime-field circuit
sees. These are estimates from the paper's counts at the model's per-permutation cost, not a row of
the frontier page. A row would count the verifier's calls at each width and add the field arithmetic
of the PACS checks.

Signing is a SmallWood proof, about <!--fig:capss_kishu_poseidon_sign_calls-->40,000<!--/fig-->
permutations over the 64-bit field with Merkle trees of 2^10 to 2^14 leaves. At the page's assumed
rate for an MCU-class device that is about <!--fig:capss_device_sign_s_est-->1.1<!--/fig--> s, and a
few times that on a secure element. So a device can sign with it, where it could not make a Kishu
leaf. The trees' memory, 2^12 leaves of 32 bytes, is a secure element's whole budget. The signature,
about 20 kbytes, fits a QR channel at four or five times leanSPHINCS's scanning time.

## Against the other two methods

- **In the circuit.** Parity with leanSPHINCS within a factor of two or so, on the estimates above,
  rather than a gain.
- **On the device.** Seconds of signing at the MCU rate and tens of kilobytes of memory, against
  hashing alone and under a second of grinding for leanSPHINCS; still feasible, which a Kishu leaf
  is not.
- **The assumption.** The hash preimage and leanSPHINCS rest on a bit-oriented hash. CAPSS rests on
  an arithmetization-oriented permutation, the class whose margins the algebraic attacks have cut
  and which the frontier page excludes from its default hash policy for future-proofing. Poseidon is
  the member with the most scrutiny, and a signature key can be rotated where a long-lived
  commitment cannot, which makes the policy's case weaker here than for storage.
- **Ethereum.** Ethereum's post-quantum signature is leanSPHINCS, so the compatibility the second
  method may offer is not on this route.

So CAPSS is the method for a prime-field proof system, and for Kishu it is a second signature route
with a different assumption and no clear gain over leanSPHINCS. It is not priced as a row; a row
would be a day's work if the comparison needed settling.

## References

- <a id="ref-fr25"></a>[FR25] Thibauld Feneuil, Matthieu Rivain. CAPSS: A Framework for
  SNARK-Friendly Post-Quantum Signatures. 2025. <https://eprint.iacr.org/2025/061>. Tables 2, 3, and
  6 for the figures above.
- <a id="ref-fr25a"></a>[FR25a] Thibauld Feneuil, Matthieu Rivain. SmallWood: Hash-Based Polynomial
  Commitments and Zero-Knowledge Arguments for Relatively Small Instances.
  2025. <https://eprint.iacr.org/2025/1085>
- <a id="ref-bbl24"></a>[BBL+24] Augustin Bariant, Aurélien Boeuf, Axel Lemoine, Irati Manterola
  Ayala, Morten Øygarden, Léo Perrin, Håvard Raddum. The Algebraic FreeLunch: Efficient Gröbner
  Basis Attacks Against Arithmetization-Oriented Primitives. CRYPTO 2024.
- <a id="ref-cr25"></a>[CR25] Luca Campa, Arnab Roy. Gröbner Basis Cryptanalysis of Anemoi.
  2025. <https://eprint.iacr.org/2025/814>
