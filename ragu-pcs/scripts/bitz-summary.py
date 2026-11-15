"""Summarize the RESULT lines of a BitZ sweep: python bitz-summary.py RESULTS [RESULTS ...].

The same table as the overnight run's summary.txt: profile, log2 bits, threads, commit and
prove ms (grand product and Ligerito parts), verify ms, proof bytes (non-Ligerito, Ligerito).
"""
import re
import sys

print(f"{'profile':12} {'n':>2} {'thr':>3} {'commit':>7} {'prove':>8} {'gp':>7} {'lig':>7} "
      f"{'verify':>6} {'proof':>8} {'nonlig':>7} {'lig_B':>7}")
for path in sys.argv[1:]:
    for line in open(path):
        if not line.startswith("RESULT"):
            continue
        r = dict(re.findall(r"(\w+)=(\S+)", line))
        print(f"{r['lig']:12} {r['n']:>2} {r['threads']:>3} {float(r['commit_ms']):7.1f} "
              f"{float(r['prove_ms']):8.1f} {float(r['prove_gp_ms']):7.1f} "
              f"{float(r['prove_lig_ms']):7.1f} {float(r['verify_ms']):6.2f} "
              f"{int(r['proof_bytes']):8,} {int(r['proof_nonlig_bytes']):7,} "
              f"{int(r['proof_lig_bytes']):7,}")
