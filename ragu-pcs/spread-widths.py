"""Spread-table widths for lookups emulated in Ragu's gates.

For a spread table of width w (entries for dense values below 2^w, with a tag per width class
so that narrower pieces share the table), a word is cut into pieces of at most w bits with a
boundary at the rotation amount that the word's next use needs, so the rotation is a free
re-ordering. Each piece costs one lookup for a range check or spread form and two for an XOR
(the even and odd parts of the spread sum). A lookup is L gates: 1 over Pasta, where one
base-field challenge suffices, 3 over Goldilocks, where three are needed. A step circuit that
uses the table pays 2 L gates per table entry and one challenge hash.

Prints, per width, the pieces per 64-bit and 32-bit word, the table's entries and gates, and
the effective gates per BLAKE2b and BLAKE3 compression and per emulated Pallas multiplication
at ranks 13 to 16, with the per-step overhead amortised over the step.

Run: python spread-widths.py
"""

BLAKE2B_ROTATIONS = (32, 24, 16, 63)
BLAKE3_ROTATIONS = (16, 12, 8, 7)
STEP_GATES = {13: 2048, 14: 4096, 15: 8192, 16: 16384}
CHALLENGE_HASH = {"Pasta": 288, "Goldilocks": 470}
L = {"Pasta": 1, "Goldilocks": 3}
LIMB_BITS, CARRY_BITS, LIMBS, COLUMNS, PRODUCTS = 29, 34, 9, 17, 81


def pieces_of(length, w):
    """The widths of the pieces that a `length`-bit span cuts into at width w."""
    full, rest = divmod(length, w)
    return [w] * full + ([rest] if rest else [])


def word_pieces(n, r, w):
    """A word of n bits cut at the rotation amount r."""
    return pieces_of(r % n, w) + pieces_of(n - r % n, w) if r % n else pieces_of(n, w)


def hash_cost(n, rotations, w, l):
    """Gates per compression for a BLAKE-style function of 32- or 64-bit words: per G, one
    addition and one XOR per rotation (the addition's result is cut as the XOR's rotation
    needs), 96 G for BLAKE2b and 56 for BLAKE3, plus the output XORs; and the width classes
    the table must hold."""
    g_rounds = 96 if n == 64 else 56
    gates, widths = 0, set()
    for r in rotations:
        p = word_pieces(n, r, w)
        widths |= set(p)
        gates += (len(p) + 1) * l + 2 * len(p) * l  # the addition's pieces and carry, the XOR's two lookups per piece
    plain = pieces_of(n, w)
    widths |= set(plain)
    gates = gates * g_rounds + 8 * 2 * len(plain) * l  # the output XORs
    return gates, widths


def mult_cost(w, l):
    """Gates per emulated Pallas multiplication: the limb products, the carries' and the two
    operands' range checks as tagged pieces; and the width classes."""
    limb, carry = pieces_of(LIMB_BITS, w), pieces_of(CARRY_BITS, w)
    gates = PRODUCTS + COLUMNS * len(carry) * l + 2 * LIMBS * len(limb) * l
    return gates, set(limb) | set(carry)


def table_gates(widths, l):
    return 2 * sum(2 ** k for k in widths) * l


def effective(gates, overhead, step):
    """The gates a step's share of `gates` costs once the per-step overhead is paid."""
    if overhead >= step:
        return None
    return gates * step / (step - overhead)


def main():
    for field in ("Pasta", "Goldilocks"):
        l = L[field]
        print(f"\n== {field}: L = {l} gates per lookup")
        print(f"{'w':>2} {'p64':>4} {'p32':>4} {'entries':>7} {'table':>7} {'b2b':>7} {'b3':>6} {'mult':>5} |"
              + "".join(f" {'r' + str(r) + ' b2b':>9} {'mult':>6}" for r in STEP_GATES))
        for w in (4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 16):
            b2b, widths = hash_cost(64, BLAKE2B_ROTATIONS, w, l)
            b3, widths3 = hash_cost(32, BLAKE3_ROTATIONS, w, l)
            mult, widthsm = mult_cost(w, l)
            all_widths = widths | widths3 | (widthsm if field == "Goldilocks" else set())
            table = table_gates(all_widths, l)
            p64 = max(len(word_pieces(64, r, w)) for r in BLAKE2B_ROTATIONS)
            p32 = max(len(word_pieces(32, r, w)) for r in BLAKE3_ROTATIONS)
            entries = sum(2 ** k for k in all_widths)
            row = f"{w:2d} {p64:4d} {p32:4d} {entries:7,d} {table:7,d} {b2b:7,d} {b3:6,d} {mult:5,d} |"
            for step in STEP_GATES.values():
                overhead = table + CHALLENGE_HASH[field]
                e_b2b = effective(b2b, overhead, step)
                e_mult = effective(mult, overhead, step)
                row += f" {e_b2b:9,.0f} {e_mult:6,.0f}" if e_b2b else f" {'no fit':>9} {'':>6}"
            print(row)
    print("\nwithout lookups: BLAKE2b 51,600; BLAKE3 14,900; emulated multiplication 1,100 (bits)")


if __name__ == "__main__":
    main()
