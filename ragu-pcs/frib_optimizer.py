#!/usr/bin/env python
# A port of Ulrich Haböck's frib_optimizer.sage, copyright (c) 2026 Ulrich Haböck, with
# extensions copyright 2026 Zcash Protocol Developers. Licensed under the MIT license or the
# Apache License, Version 2.0, at your option: the original with its author's agreement
# (2026-11-11), the extensions as the rest of this repository.
"""Python port of Ulrich Haböck's frib_optimizer.sage at revision 1187ef3c of
github.com/ulrich-haboeck/scripts (2026-11-12; the copy beside this file is his original of
2026-10-21): Sage's `^` is `**`, its log/ceil/floor/sqrt are math's, and there are three
extensions. `field_bits` (default 256) in `CAT_bits`, `max_list_size` and `optimize` is the
size of the field that the folding challenges are drawn from, which sets the agreement bound
and the opened values' size from the second round on. `first_bytes` in `optimize` (default:
that field's bytes) is the opened bytes per 256 witness bits in the first round, for a witness
packed into a smaller subfield of the challenge field: its first-round oracle has the same
bytes as a 256-bit packing's, so 32. `first_trees` in `optimize` (default 1) is the number of
separately committed oracles that the first round opens, each under its own Merkle root, for
a batched opening such as an accumulation decider's: the first round's opened values and
authentication paths are multiplied by it, and the schedule is optimised with that cost.
`list_bits` in `optimize` is optional; left out, the largest list that the agreement bound
admits at the security level is taken, as the original now does.

Changes in the original since the first port: the list size is automatic and the agreement
check counts the codeword's length in field elements (`w - 8 + rate_bits`) rather than in
bits; zero knowledge is a mask of the witness's size added in the first round, which doubles
that round's leaves and adds a hash-sized blinder to each (his revision ada1e779 had one
mask row per leaf, a slip he corrected at 1187ef3c when asked), and a schedule with no
reduction opens the mask beside the witness before revealing it, instead of the earlier
separate opening round; every proof carries the Galois orbit of the evaluation claim; and
the verifier's hash count is the pruned paths plus the opened leaves.

FRI-Binius proof size optimizer. Given initial witness size and rate, determines the folding parameters
achieving minimal proof size.
Assumes packing into L = GF(2**256) to accomodate list-decoding soundness. Hashes are 256 bits.

Run: sage frib_optimizer.sage
     sage frib_optimizer.sage --min-w 20 --max-w 26 --step 2
     sage frib_optimizer.sage --w 24 --rate-exp 5 --lambda-bits 124 --ell 15
"""

from __future__ import print_function
import argparse
import math
from functools import lru_cache
from math import ceil, floor, sqrt
def log(x, base=None):
    return math.log(x) if base is None else math.log(x, base)

FIELD_BYTES = 32  # the default; `optimize` sets it from `field_bits`
HASH_BYTES = 32


# log2 soundness error of linear CAT over GF(2**256)
def CAT_bits(n_bits, list_bits, field_bits=256):
    # word_len =  2**n_bits, list_size = 2**list_bits
    if list_bits == 0:
        # the BCIKS20 bound is good enough
        err = n_bits - field_bits
    else:
        # Simplified bound from BCHKS25.
        err = 5*list_bits - log(3,2.) + n_bits - field_bits
    return err

def max_list_size(n_bits, lambda_bits, field_bits=256):
    # 5*list_bits - log(3,2.) + n_bits - FIELD_BYTES*8 = - lambda_bits
    list_bits = max(
            floor((log(3,2.) - n_bits + field_bits - lambda_bits)/5),
            0
    )
    return list_bits


# determines number of queries for given security level
def queries(rate_bits, lambda_bits, list_size, grind_bits):
    rho = 2**(-rate_bits)
    if list_size == 1:
        # UDR agreement density
        alpha = (1 + rho)/2
    else:
        # Guruswami-Sudan multiplicity parameter
        m = max(ceil(sqrt(rho) * list_size - 1/2),3)
        alpha = (1 + 1/(2*m)) * 2**(-rate_bits/2.0)

    return ceil((grind_bits - lambda_bits)/log(alpha,2))

# let's keep function returns in cache. Helps performance.
@lru_cache(maxsize=None)
# Pr[a fixed subset of subset_size leaves receives no query], t samples
def empty_probability(M, subset_size, t):
    if subset_size >= M:
        return 0.0
    # t times in the complement:
    # Pr = (1 - subset_size/M)**t
    # Log form with log1p(x) = ln (1 + x) is stable for very large M and modest t.
    return math.exp(t * math.log1p( -float(subset_size)/M))


@lru_cache(maxsize=None)
# Expected number of hashes required for the authentication paths of `t` distinct uniform leaves
# in a Merkle tree of height `height`. Good proxie for optimal Merkle caps.
def expected_multiproof_hashes(height, t):
    M = 1 << height
    # For each level j = 0 .. height-1:
    # A node has a non-empty subtree, but it sibling node has empty subtree: With
    # Pr =  E(j) - E(2j)
    # a sibling hash is added. (The hash of the non-empty subtree is reconstructed.)
    # Now use linearity of expection, summing over all nodes in that level (there are M/2**j),
    # and over all levels
    avg_hashes = sum((M >> j) * (
        empty_probability(M, 1 << j, t) -
        empty_probability(M, 1 << (j+1), t)
    ) for j in range(height))
    return avg_hashes

# Proof size optimizer. zk uses a dense mask of the same size as the witness,
# which is added in the first round (as for the sumcheck intermediate steps, no explict commit of the random linear combination).
def optimize(w, rate_bits, lambda_bits, grind_bits,
            zk='true',
            optimize_for='compressed', list_bits=None, field_bits=256, first_bytes=None, first_trees=1):
    global FIELD_BYTES
    FIELD_BYTES = (field_bits + 7) // 8
    first = FIELD_BYTES if first_bytes is None else first_bytes
    if w < 8:
        raise ValueError('w must be at least 8')
    if optimize_for not in ('compressed', 'uncompressed'):
        raise ValueError('optimize_for must be compressed or uncompressed')

    # determine best possible list size for proximity testing
    if list_bits is None:
        list_bits = max_list_size(w-8+rate_bits, lambda_bits, field_bits)
    # sanity check.
    if CAT_bits(w - 8 + rate_bits,list_bits, field_bits) > -lambda_bits:
        raise ValueError('CAT error too large for given list size')

    t = queries(rate_bits, lambda_bits, 2**list_bits,grind_bits)

    # For witness log size `m` felts, finds out the reduction factor log `ell` for which
    #   current reduction step openings + solve (m - ell)
    # is minimal.
    # For zk='true', we ignore the small witness increase for securing its queried values (both IOP and PIOP).
    @lru_cache(maxsize=None)
    def solve(m,zk,top=True):
        # the element size: `first` in the first round, the challenge field's after it; the
        # first round opens `first_trees` oracles. The mask doubles the rows of each leaf
        # and the blinder adds a hash, per oracle.
        unit = first if top else FIELD_BYTES
        trees = first_trees if top else 1
        rows = 2 if zk == 'true' else 1
        blinder = HASH_BYTES if zk == 'true' else 0

        # reduction exponent ell=0, always terminates the protocol
        ell = 0
        h = m - ell + rate_bits

        if zk == 'true':
            # Batching step with mask of witness size, then reveal.
            # Includes Merkle leaf blinder of size HASH_BYTES
            b = rows * (1 << ell) * unit + blinder
            opened = b * t * trees
            uncompressed_auth = HASH_BYTES * t * h * trees
            compressed_auth = HASH_BYTES * expected_multiproof_hashes(h, t) * trees
            terminal_bytes = unit * trees * (1 << (m-ell))

            best = dict(
                compressed=opened + compressed_auth + terminal_bytes,
                uncompressed=opened + uncompressed_auth + terminal_bytes,
                rounds=[dict(
                            ell= ell,
                            zk= zk,
                            height=h,
                            opened_bytes=opened,
                            compressed_auth_bytes=compressed_auth,
                            uncompressed_auth_bytes=uncompressed_auth,
                            compressed=opened + compressed_auth,
                            uncompressed=opened + uncompressed_auth
                            )],
                terminal_elements=(1 << (m-ell))
            )
        else:
            # plain reveal, no proof of proximity samples.
            terminal_bytes = unit * trees * (1 << (m-ell))
            best = dict(
                    compressed= terminal_bytes,
                    uncompressed=terminal_bytes,
                    rounds=[],
                    terminal_elements=1 << (m-ell)
            )

        # over all non-trivial reduction exponents
        for ell in range(1, m+1):
            # treee height
            h = m - ell + rate_bits
            # leaf size, with the witness-size mask and the leaf blinder under zk
            b = rows * (1 << ell) * unit + blinder

            opened = b * t * trees
            uncompressed_auth = HASH_BYTES * t * h * trees
            compressed_auth = HASH_BYTES * expected_multiproof_hashes(h, t) * trees

            # recursive call
            child = solve(m - ell, zk='false', top=False)

            candidate = dict(
                compressed=opened + compressed_auth + child['compressed'],
                uncompressed=opened + uncompressed_auth + child['uncompressed'],
                rounds=[dict(ell= ell,
                            zk= zk,
                            height=h,
                            opened_bytes=opened,
                            compressed_auth_bytes=compressed_auth,
                            uncompressed_auth_bytes=uncompressed_auth,
                            compressed=opened + compressed_auth,
                            uncompressed=opened + uncompressed_auth
                            )] + child['rounds'],
                terminal_elements=child['terminal_elements']
            )
            if candidate[optimize_for] < best[optimize_for]:
                best = candidate

        return best

    out = solve(w - 8,zk,True).copy()

    # add Galois orbit of eval claim in GF(2^128) is contained in GF(2^128)
    overhead = (4*FIELD_BYTES)*(FIELD_BYTES/2)
    out['compressed'] = out['compressed'] + overhead
    out['uncompressed'] = out['uncompressed'] + overhead
    out.update(
        overhead=overhead
    )

    # add global parameters to output dict
    out.update(w=w,
        rate_bits=rate_bits,
        lambda_bits=lambda_bits,
        grind_bits=grind_bits,
        list_bits=list_bits,
        queries=t,
        zero_knowledge=zk,
        optimize_for=optimize_for
    )

    first_fold = 2**out['rounds'][0]['ell'] if out['rounds'] else 1
    # Model used in the explorer: packed witness + full first-round
    # encoded matrix + full binary Merkle tree (approx. 2 hashes per leaf).
    witness_bytes = 1 << (w - 3)
    encoded_bytes = witness_bytes * (1 << rate_bits)
    tree_bytes = 64 * (1 << (w - 8 + rate_bits)) // max(first_fold, 1)
    out['ram_bytes'] = witness_bytes + encoded_bytes + tree_bytes
    out['ram_breakdown'] = dict(witness=witness_bytes, encoded=encoded_bytes,
                                merkle_tree=tree_bytes)
    return out



# ============================================================
# auxilary formatting functions
# ============================================================ß

def fmt_kib(n):
    return '%.2f KiB' % (n / 1024.0)


def fmt_ram(n):
    return ('%.2f GiB' % (n / 2.0**30) if n >= 2**30
            else '%.2f MiB' % (n / 2.0**20))

def print_detail(result):
    print()
    print('Witness: 2^%d bits; Packed: 2^%d felts,  RS rate: 1/%d; queries: %d' %
          (result['w'],
           result['w']-8,
           1 << result['rate_bits'],
           result['queries'])
    )
    print('Optimization objective: %s' % result['optimize_for'])
    print()
    print('Galois openings: %s' % fmt_kib(result['overhead']))
    print('Folding schedule: %s' %
           (' x '.join(str(2**r['ell']) for r in result['rounds']) or 'direct reveal'))

    for i, round_info in enumerate(result['rounds'], 1):
        x = round_info
        if x['zk'] == 'true':
            print('  Round %d: 2^%d (+ 1) rows, 2^%d cols,    opened: %s,     auth: %s (%s),  tot: %s (%s)' %
                (i,
                x['ell'],
                x['height'],
                fmt_kib(x['opened_bytes']),
                fmt_kib(x['compressed_auth_bytes']),
                fmt_kib(x['uncompressed_auth_bytes']),
                fmt_kib(x['compressed']),
                fmt_kib(x['uncompressed'])
                )
            )
        else:
            print('  Round %d: 2^%d rows, 2^%d cols,    opened: %s,     auth: %s (%s),  tot: %s (%s)' %
                (i,
                x['ell'],
                x['height'],
                fmt_kib(x['opened_bytes']),
                fmt_kib(x['compressed_auth_bytes']),
                fmt_kib(x['uncompressed_auth_bytes']),
                fmt_kib(x['compressed']),
                fmt_kib(x['uncompressed'])
                )
            )


    print('  Terminal: %d elements, %s' % (result['terminal_elements'], fmt_kib(FIELD_BYTES*result['terminal_elements'])))

# ============================================================
# main
# ============================================================
def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--w', type=int, default=None,
        help='log2 of witness size'
    )
    p.add_argument('--min-w', type=int, default=20,
        help='min witness size for table mode'
    )
    p.add_argument('--max-w', type=int, default=26,
        help='max witness size for table mode'
    )
    p.add_argument('--step', type=int, default=1,
        help='step size for table mode'
    )
    p.add_argument('--rate', type=int, default=None,
        help='|log2| of the rate, i.e. 1 for rate 1/2 and 2 for rate 1/4'
    )
    p.add_argument('--sec', type=int, default=128,
        help='Security level in bits. Default 128.'
    )
    p.add_argument('--field-bits', type=int, default=256,
        help='bits of the challenge field; default 256'
    )
    p.add_argument('--grind', type=int, default=0,
        help='grinding bits, default 0'
    )
    p.add_argument('--zk', choices=['true','false'], default='false',
        help='zero knowledge'
    )
    p.add_argument('--optimize-for', choices=['compressed', 'uncompressed'],
        default='compressed',
        help='Compressed proofs are a good proxie for Merkle caps'
    )
    args = p.parse_args()

    rates = [args.rate] if args.rate is not None else [6, 5, 4, 3]
    ws = [args.w] if args.w is not None else range(args.min_w, args.max_w+1, args.step)

    print()
    print('Security: %d bits; Grinding: %d bits; zk: %s' %
        (args.sec, args.grind, args.zk)
    )
    print('Packing field: %d bits' % args.field_bits)
    print('%-10s %-8s %-12s %-10s %-16s %-16s %-14s %-8s %s' %
        ('Witness', 'Rate', 'list size', 'queries', 'Uncompressed', 'Compressed', 'Peak RAM', 'hashes', 'Folds')
    )
    for r in rates:
        for w in ws:
            result = optimize(w, r, args.sec, args.grind, zk=args.zk, optimize_for=args.optimize_for, field_bits=args.field_bits)
            # total number of hashes for the verifier
            hashes = ceil(
                (sum(x['compressed_auth_bytes'] for x in result['rounds']) + sum(x['opened_bytes'] for x in result['rounds'])) / HASH_BYTES
            )

            print('%-10s %-8s %-12s %-10s %-16s %-16s %-14s %-8s %s' %
                  ('2^%d' % w,
                   '1/%d' % (1 << r),
                   '2^%d' % result['list_bits'],
                   '%d' % result['queries'],
                   fmt_kib(result['uncompressed']),
                   fmt_kib(result['compressed']),
                   fmt_ram(result['ram_bytes']),
                   str(hashes),
                   ' x '.join(str(2**x['ell']) for x in result['rounds']) or '-'
                   )
                )
            if args.w is not None:
                print_detail(result)
        print()

if __name__ == '__main__':
    main()
