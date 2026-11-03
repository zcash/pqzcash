//! Minimal scalar SIS rows for a Euclidean collision bound at a Pasta modulus.
//!
//! For each length bound (given as log2), binary-search the smallest number of
//! scalar SIS rows `n` such that Akita's Euclidean estimator (ADPS16 quantum)
//! reports at least `target` bits. Reports the same for Akita's q64 and q128
//! families so that the "bits of commitment are independent of q" claim can be
//! read off directly.

use akita_sis_estimator::{
    akita_q128, akita_q64, estimate, Bound, CostValue, EstimateConfig, SisNorm, SisParameters,
};
use num_bigint::BigUint;
use std::env;

fn pallas_base_field() -> BigUint {
    // p = 2^254 + 45560315531419706090280762371685220353 (Pallas base field, Vesta scalar field).
    BigUint::parse_bytes(
        b"40000000000000000000000000000000224698fc094cf91b992d30ed00000001",
        16,
    )
    .expect("hex literal")
}

fn log2_biguint(q: &BigUint) -> f64 {
    let bits = q.bits();
    let top = if bits > 64 { q >> (bits - 64) } else { q.clone() };
    let top: u64 = top.try_into().expect("fits");
    (top as f64).log2() + (bits.saturating_sub(64)) as f64
}

struct Cell {
    bits: f64,
    beta: Option<u32>,
    dim: u64,
}

/// Cheapest attack over the estimator's own dimension choice and a ladder of
/// explicit lattice dimensions. The estimator reports infinity when the BKZ
/// block it needs exceeds the lattice dimension it picked, which at tiny row
/// counts hides a trivial attack in a larger sublattice; the ladder removes
/// that artefact. An all-infinite result means the bound sits below the
/// expected shortest vector, so no solution is expected.
fn cost(n: u32, q: &BigUint, m: u64, log2_bound: f64) -> Cell {
    let base = EstimateConfig::akita_euclidean_table();
    let mut dims: Vec<Option<u64>> = vec![None];
    let mut d = 50u64;
    while d <= m.min(1 << 16) {
        dims.push(Some(d));
        d *= 2;
    }
    let mut best = Cell {
        bits: f64::INFINITY,
        beta: None,
        dim: 0,
    };
    for dim in dims {
        let params = SisParameters::try_new(
            n,
            q.clone(),
            Some(m),
            Bound::Float(2f64.powf(log2_bound)),
            SisNorm::Euclidean,
        )
        .expect("valid SIS parameters");
        let config = EstimateConfig {
            lattice_dimension: dim,
            ..base
        };
        let cost = estimate(&params, &config).expect("estimate");
        let bits = match cost.rop {
            CostValue::Finite(c) | CostValue::ProvenAboveTarget(c) => c.log2,
            CostValue::Infinity => f64::INFINITY,
        };
        if bits < best.bits {
            best = Cell {
                bits,
                beta: cost.beta,
                dim: cost.d,
            };
        }
    }
    best
}

fn min_rows(q: &BigUint, m: u64, log2_bound: f64, target: f64) -> (u32, Cell) {
    let mut hi = 1u32;
    while cost(hi, q, m, log2_bound).bits < target {
        hi *= 2;
        assert!(hi < (1 << 24), "no secure row count found");
    }
    let mut lo = 1u32;
    while lo < hi {
        let mid = (lo + hi) / 2;
        if cost(mid, q, m, log2_bound).bits >= target {
            hi = mid;
        } else {
            lo = mid + 1;
        }
    }
    (lo, cost(lo, q, m, log2_bound))
}

fn main() {
    let args: Vec<String> = env::args().skip(1).collect();
    let target: f64 = args.first().map_or(128.0, |s| s.parse().expect("target bits"));
    let m: u64 = args.get(1).map_or(1 << 22, |s| s.parse().expect("columns"));
    let bounds: Vec<f64> = if args.len() > 2 {
        args[2..].iter().map(|s| s.parse().expect("log2 bound")).collect()
    } else {
        vec![20.0, 24.0, 27.0, 32.0, 36.0, 41.6, 44.0, 48.0]
    };

    let moduli = [
        ("pallas", pallas_base_field()),
        ("q64", akita_q64()),
        ("q128", akita_q128()),
    ];
    println!("target_bits={target} columns_m={m}");
    println!("modulus,log2_q,log2_bound,min_rows_n,commit_bits,commit_bytes,cost_bits,bkz_beta,lattice_dim");
    for (label, q) in &moduli {
        let log2_q = log2_biguint(q);
        for &b in &bounds {
            let (n, cell) = min_rows(q, m, b, target);
            let commit_bits = n as f64 * log2_q;
            println!(
                "{label},{log2_q:.3},{b},{n},{commit_bits:.0},{:.0},{:.2},{},{}",
                commit_bits / 8.0,
                cell.bits,
                cell.beta.map_or(String::new(), |v| v.to_string()),
                cell.dim
            );
        }
    }
}
