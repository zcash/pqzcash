import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'work', 'akita-src', 'third_party', 'lattice-estimator'))
from estimator import SIS
from estimator.reduction import ADPS16
from sage.all import log, oo
p = 0x40000000000000000000000000000000224698fc094cf91b992d30ed00000001
print("log2_bound,n,bits,beta,d")
for (lb, n) in [(27, 142), (27, 143), (41.6, 339), (41.6, 340)]:
    params = SIS.Parameters(n=n, q=p, m=2**22, length_bound=2.0**lb, norm=2)
    c = SIS.lattice(params, red_cost_model=ADPS16(mode="quantum"))
    bits = "inf" if c["rop"] == oo else "%.2f" % float(log(c["rop"], 2))
    print(f"{lb},{n},{bits},{c.get('beta')},{c.get('d')}")
