#!/usr/bin/env python
"""Key generation of the pruned leanSPHINCS key in compressions, for the hardware-wallets note's
table (LEANSPHINCS_KEYGEN_COMPRESSIONS in the model), from sphincs.art's own cost script: for
each hash, the compressions of generating a key that keeps a subtree of height b in a tree of
height 26, beside the hash calls 226 * 2^b + 2 (26 - b) that its Lean development proves. A hash
call is not always one compression: a one-time leaf hashes its 64 chain ends in several.

Usage: python scripts/leansphincs-keygen.py SPHINCS_ART_CHECKOUT
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(sys.argv[1]) / "scripts"))
import scheme  # noqa: E402  (sphincs.art's scripts/scheme.py)

HEIGHT = 26
for H in scheme.HASHES:
    costs = scheme.Costs(H, None, scheme.COORDS)
    print(
        f"{H.name}: {costs.attempt} compression a grinding attempt, {costs.verify(HEIGHT, 'pruned')} a verification"
    )
    for b in (12, 14, 20, 26):
        calls = 226 * 2**b + 2 * (HEIGHT - b)
        print(
            f"  b = {b}: {round(costs.keygen(HEIGHT, 'pruned', b)):,} compressions, {calls:,} hash calls"
        )
