# Spend authorization

A Zoodles spend is authorized in one of two ways, chosen per input and usually the same for all of a
transaction's inputs. The first is a hash preimage: knowledge of the secret behind the note's
payment key, proved inside the spend's own step. The second is a hash-based signature, leanSPHINCS,
made outside the proof and verified inside the host's transaction. Neither uses a curve. Both serve
a native Zoodles spend and a recovery spend of an Ironwood or a Tachyon note, whether or not the
spend is made from a hardware wallet. The [frontier page](pareto-template.html#transaction-prover)
prices both as applications of its transaction prover: the preimage statement as the device
statement, one BLAKE3 compression, and the leanSPHINCS verifier with BLAKE3, BLAKE2s, or Keccak.

Two methods are needed because signers differ. The hash preimage is what ZIP 2005 already specifies.
It is much the more efficient for a signer that creates the transaction itself, with no separation
between the device that holds the spending key and the one that builds the proof. The same holds for
a signer that is not constrained in outgoing bandwidth or memory. The check is a hash inside a step
it proves anyway. The leanSPHINCS signature is feasible on a wider range of devices, since signing
is hashing alone and the signature is a few kilobytes. So it reaches an airgapped wallet on a QR
channel or a secure element. It may also be compatible with Ethereum's post-quantum signature,
depending on the details of what Ethereum chooses. A third method, a signature whose verification is
built for the circuit, is analysed on the CAPSS page.

The pages of this section:

- [Hash preimage](auth-preimage.md): the statement, and why it has to be a signature of knowledge
  when it is made outside the transaction's own proof.
- [leanSPHINCS](auth-leansphincs.md): the signature, its pruned key, and its verifier's cost in the
  circuit.
- [CAPSS](auth-capss.md): a SNARK-friendly signature as a third method, analysed and not adopted:
  the method for a prime-field proof system, and for Kishu a second signature route with another
  assumption and no clear gain.
- [Recovery from Ironwood](recovery-ironwood.md): ZIP 2005's Recovery Statement, and how the two
  methods fit it.
- [Recovery from Tachyon](recovery-tachyon.md): Tachyon's key structure, what it lacks for recovery,
  and the migration transaction.
- [Hardware wallets](hardware-wallets.md): what a wallet proves on its own under either method, and
  at what cost.

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
