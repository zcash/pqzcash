# Spend authorization

A Zoodles spend is authorized in one of two ways, chosen for each spending key and usually the same
for all of a transaction's inputs. The first is a hash preimage: knowledge of the secret behind the
note's payment key, proved inside the transaction's own proof. The second is a hash-based signature,
leanSPHINCS, made outside the proof and verified inside the host's transaction. Neither uses a
curve. Both serve a native Zoodles spend and a recovery spend of an Ironwood or a Tachyon note,
whether or not the spend is made from a hardware wallet. The [frontier
page](pareto-template.html#transaction-prover) prices both as applications of its transaction
prover: the preimage statement as the device statement, one BLAKE3 compression, and the leanSPHINCS
verifier with BLAKE3, BLAKE2s, or Keccak.

The pages of this section:

- [Hash preimage](auth-preimage.md): the statement, and why it has to be a signature of knowledge
  when it is made outside the transaction's own proof.
- [leanSPHINCS](auth-leansphincs.md): the signature, its pruned key, and its verifier's cost in the
  circuit.
- [CAPSS](auth-capss.md): a SNARK-friendly signature as a third method, analysed and not adopted:
  the method for a prime-field proof system, and for Kishu a second signature route with another
  assumption and no clear gain.
- [SLH-DSA at NIST Level 3](auth-slhdsa.md): for illustration only, what a signature at that
  level would cost inside the proof.
- [Recovery from Ironwood](recovery-ironwood.md): ZIP 2005's Recovery Statement, and how the two
  methods fit it.
- [Recovery from Tachyon](recovery-tachyon.md): Tachyon's key structure, what it lacks for recovery,
  and the migration transaction.
- [Hardware wallets](hardware-wallets.md): what a wallet proves on its own under either method, and
  at what cost.

## Choice of methods

Two methods are needed because signers differ. The hash preimage is what ZIP 2005 already specifies.
It is much the more efficient for a signer that creates the transaction itself, with no separation
between the device that holds the spending key and the one that builds the proof. The same holds for
a signer that is not constrained in outgoing bandwidth or memory. The check is a hash inside a step
it proves anyway. The leanSPHINCS signature is feasible on a wider range of devices, since signing
is hashing alone and the signature is a few kilobytes. So it reaches an airgapped wallet on a QR
channel or a secure element. It may also be compatible with Ethereum's post-quantum signature,
depending on the details of what Ethereum chooses. A third method, a signature whose verification is
built for the circuit, is analysed on the [CAPSS](auth-capss.md) page.

## Signing multiple inputs at once

An authorization is paid for once for each distinct spending key that a transaction spends from, not
once for each input note. The proof is zero-knowledge proof-carrying data, so one signature, or one
preimage check, can authorize every input note that has the same spending key, and nothing reveals
that those notes share a key. The authorization is a node of its own in the proof. It proves
knowledge of a leanSPHINCS signature $\sigma$ under a key $K$ of the transaction's digest $M$, or of
a quantum spending key $\mathsf{qsk}$ with $\mathsf{qk} = \mathsf{H^{qk}}(\mathsf{qsk})$, and every
spend from that key uses it. So the proof is a directed acyclic graph and not a tree, which is how
proof-carrying data is defined [\[CT10, Definition 3\]](#ref-ct10). Tachyon has no such sharing: it
signs each action outside the proof, under a key randomized for that action. The frontier page's
transactions of two inputs spend from <!--fig:zoodles_signing_keys-->one<!--/fig--> spending key.

A transaction's inputs may be authorized by several parties, each for some of them. So an
authorization node's header says which inputs it authorizes, and the transaction's root node checks
that every input is covered by some authorization node. Neither that check nor the control logic
that lets a step use a node twice is costed, because the cost is likely to be negligible.

Sharing has a hazard. An accumulator inside the proof that holds an authorization would authorize
whatever proof it were built into, so it must not be usable in another transaction if it leaks.
Zoodles prevents that by tying the proof's transcript to the transaction's digest, which makes every
authorization a [signature of knowledge](auth-preimage.md#the-signature-of-knowledge) on that
transaction. The wallet's leaf that a hardware wallet hands to its host needs the same thing. Kishu
cannot prevent the hazard in general, since it does not know which statements authorize anything.
What it can do is offer the signature of knowledge as a facility.

## Quantum recovery

The two recovery pages share one definition. A note is quantum-recoverable when its owner can spend
it, or move it to a post-quantum pool, after discrete logarithms fall, by a statement whose
soundness rests on hash and lattice assumptions alone. That asks four things of the note and of the
chain:

- the note commits to an owner key $\mathsf{qk} = \mathsf{H}(\mathsf{qsk})$ whose secret
  $\mathsf{qsk}$ is in no key used to view or to scan, so that such a key does not become a spending
  key when the curve's keys do;
- the commitment's opening and the derivation of the note's nullifier can be proved without discrete
  log, which means hash commitments, or commitments whose derivation is constrained so that a hash
  binds them;
- the note's membership in the chain's history and its nullifier's absence from it can be proved
  from a hash-based structure over the published commitments and nullifiers, built from public data
  where the chain's own structure is discrete-log-based;
- and the spend is authorized by one of the two methods above, with the message bound into the
  proof.

ZIP 2005 gives Ironwood-pool notes all four, with the quantum spending key and the Recovery
Statement. Tachyon's notes have the hash commitments and the hash-based nullifier by design and lack
the owner key, which the Tachyon page takes up.

## References

- <a id="ref-ct10"></a>[CT10] Alessandro Chiesa, Eran Tromer. Proof-Carrying Data and Hearsay
  Arguments from Signature Cards. Innovations in Computer Science (ICS)
  2010. <https://ic-people.epfl.ch/~achiesa/docs/CT10.pdf>
