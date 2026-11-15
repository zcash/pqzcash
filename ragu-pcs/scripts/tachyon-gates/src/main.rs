//! Gate and constraint counts of every Tachyon step at the production rank.
//!
//! Tachyon's steps implement the `Step` trait of ragu's API-level mock, so
//! they are counted through the mock's counting adapter, which synthesizes a
//! step as `ragu_pcd`'s adapter would: the application stage, the oracles,
//! the step's own circuit, the openings and the three padded headers.

use ragu::counting::step_synthesis_counts;
use ragu_circuits::polynomials::{ProductionRank, Rank as _};
use ragu_core::pasta::Pasta;
use tachyon::stamp::proof::{
    HEADER_SIZE, delegation, evidence, output, pool, qr, spend, spendable, stamp, summary,
};

/// The application stage's size: the largest `NUM_STAGED` any registered step
/// declares (`FeeFuse` stages five values).
const STAGE_SIZE: usize = 5;

macro_rules! count {
    ($($step:expr),* $(,)?) => {
        $(
            match step_synthesis_counts::<Pasta, _, HEADER_SIZE>($step, STAGE_SIZE) {
                Ok(counts) => println!(
                    "{:<32} {:>5} gates {:>6} constraints",
                    stringify!($step), counts.num_gates, counts.num_constraints
                ),
                Err(error) => println!("{:<32} error: {error:?}", stringify!($step)),
            }
        )*
    };
}

fn main() {
    println!(
        "budget at the production rank: {} gates, {} constraints; header {HEADER_SIZE}, stage {STAGE_SIZE}\n",
        ProductionRank::n(),
        ProductionRank::num_coeffs() - 1,
    );
    count!(
        delegation::NoteSeed,
        delegation::NullifierDerive,
        pool::UnspentFuse,
        pool::UnspentBind,
        spendable::SpendableInit,
        spendable::SpendableLift,
        output::OutputBind,
        stamp::OutputAction,
        spend::SpendBind,
        stamp::SpendAction,
        stamp::StampMerge,
        stamp::StampLift,
        delegation::NullifierFuse,
        summary::SummarySeed,
        summary::SummaryAdvance,
        qr::QrSummaryIntake,
        qr::QrIntakeMerge,
        qr::QrIntakeSplit,
        qr::QrSideDescend,
        qr::QrUnspentInit,
        qr::QrBucketSeal,
        qr::QrStampIntakeSeed,
        spendable::QrSpendableInit,
        qr::QrEmptyIntakeSeed,
        pool::UnspentLift,
        evidence::EvidenceTreePairFuse,
        evidence::EvidenceTreeFuse,
        evidence::EvidenceTreeCap,
        evidence::EvidenceTreeDescend,
        evidence::EvidenceTreeOpen,
        evidence::EvidenceTreeLeafPair,
        pool::AnchorSpanSeed,
        pool::AnchorSpanFuse,
        stamp::FeeFuse,
        stamp::ActionMerge,
        stamp::ActionLift,
        stamp::FeeSeed,
        stamp::StampUnmerge,
        qr::QrSideSelect,
    );
}
