//! Usage metering and invoice generation.
//!
//! Metered [`UsageRecord`]s are accumulated per tenant and exposed via a
//! [`Meter`]. The [`BillingSnapshot`] rolls usage up into an [`Invoice`]
//! against a rate card.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use thiserror::Error;
use tracing::debug;
use uuid::Uuid;

/// A billable metric.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum Metric {
    ComputeMinutes,
    StorageGbHours,
    ApiCalls,
    TunnelHours,
}

/// A single metered usage record attributed to a tenant.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UsageRecord {
    pub id: Uuid,
    pub tenant_id: crate::tenant::TenantId,
    pub metric: Metric,
    pub quantity: f64,
    pub timestamp: chrono::DateTime<chrono::Utc>,
}

impl UsageRecord {
    pub fn new(
        tenant_id: crate::tenant::TenantId,
        metric: Metric,
        quantity: f64,
        timestamp: chrono::DateTime<chrono::Utc>,
    ) -> Self {
        Self {
            id: Uuid::new_v4(),
            tenant_id,
            metric,
            quantity,
            timestamp,
        }
    }
}

/// Errors arising during billing operations.
#[derive(Debug, Error)]
pub enum BillingError {
    #[error("no rate configured for metric {0:?}")]
    NoRate(Metric),
    #[error("meter for tenant {0} not found")]
    MeterNotFound(String),
    #[error("serialization error: {0}")]
    Serialization(String),
}

/// A pricing rate card mapping metrics to cents-per-unit.
#[derive(Debug, Clone, Default)]
pub struct RateCard {
    rates: HashMap<Metric, u64>,
}

impl RateCard {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn set(&mut self, metric: Metric, cents_per_unit: u64) {
        self.rates.insert(metric, cents_per_unit);
    }

    pub fn rate(&self, metric: Metric) -> Option<u64> {
        self.rates.get(&metric).copied()
    }
}

/// Accumulates usage records and prices them against a rate card.
#[derive(Debug, Default)]
pub struct Meter {
    records: Vec<UsageRecord>,
    rates: RateCard,
}

impl Meter {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn with_rates(rates: RateCard) -> Self {
        Self {
            records: Vec::new(),
            rates,
        }
    }

    /// Record a usage event.
    pub fn record(&mut self, record: UsageRecord) {
        debug!(tenant = %record.tenant_id, metric = ?record.metric, qty = record.quantity, "usage recorded");
        self.records.push(record);
    }

    /// Total quantity of a metric recorded for a tenant within a window.
    pub fn total_for(
        &self,
        tenant_id: crate::tenant::TenantId,
        metric: Metric,
        start: chrono::DateTime<chrono::Utc>,
        end: chrono::DateTime<chrono::Utc>,
    ) -> f64 {
        self.records
            .iter()
            .filter(|r| {
                r.tenant_id == tenant_id
                    && r.metric == metric
                    && r.timestamp >= start
                    && r.timestamp < end
            })
            .map(|r| r.quantity)
            .sum()
    }

    fn price(&self, metric: Metric, quantity: f64) -> Result<u64, BillingError> {
        let cents = self
            .rates
            .rate(metric)
            .ok_or(BillingError::NoRate(metric))?;
        Ok((cents as f64 * quantity).round() as u64)
    }
}

/// A snapshot of a tenant's usage and invoices over a billing period.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BillingSnapshot {
    pub tenant_id: crate::tenant::TenantId,
    pub period_start: chrono::DateTime<chrono::Utc>,
    pub period_end: chrono::DateTime<chrono::Utc>,
    pub invoices: Vec<Invoice>,
    pub total_cents: u64,
}

/// A tenant invoice for a billing period.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Invoice {
    pub id: Uuid,
    pub tenant_id: crate::tenant::TenantId,
    pub period_start: chrono::DateTime<chrono::Utc>,
    pub period_end: chrono::DateTime<chrono::Utc>,
    pub lines: Vec<InvoiceLine>,
    pub total_cents: u64,
}

/// A single invoice line item.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InvoiceLine {
    pub metric: Metric,
    pub quantity: f64,
    pub cents: u64,
}

impl BillingSnapshot {
    /// Build a snapshot by generating one invoice spanning the period.
    pub fn build(
        meter: &Meter,
        tenant_id: crate::tenant::TenantId,
        period_start: chrono::DateTime<chrono::Utc>,
        period_end: chrono::DateTime<chrono::Utc>,
    ) -> Result<Self, BillingError> {
        let invoice = meter_invoice(meter, tenant_id, period_start, period_end)?;
        let total_cents = invoice.total_cents;
        Ok(Self {
            tenant_id,
            period_start,
            period_end,
            invoices: vec![invoice],
            total_cents,
        })
    }
}

/// Generate an invoice for a tenant over the given window.
pub fn meter_invoice(
    meter: &Meter,
    tenant_id: crate::tenant::TenantId,
    period_start: chrono::DateTime<chrono::Utc>,
    period_end: chrono::DateTime<chrono::Utc>,
) -> Result<Invoice, BillingError> {
    use Metric::*;
    let mut lines = Vec::new();
    for metric in [ComputeMinutes, StorageGbHours, ApiCalls, TunnelHours] {
        let qty = meter.total_for(tenant_id, metric, period_start, period_end);
        if qty > 0.0 {
            let cents = meter.price(metric, qty)?;
            lines.push(InvoiceLine {
                metric,
                quantity: qty,
                cents,
            });
        }
    }
    let total_cents = lines.iter().map(|l| l.cents).sum();
    Ok(Invoice {
        id: Uuid::new_v4(),
        tenant_id,
        period_start,
        period_end,
        lines,
        total_cents,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::Duration;

    fn window() -> (chrono::DateTime<chrono::Utc>, chrono::DateTime<chrono::Utc>) {
        let start = chrono::Utc::now() - Duration::days(30);
        (start, start + Duration::days(30))
    }

    fn rate_card() -> RateCard {
        let mut c = RateCard::new();
        c.set(Metric::ComputeMinutes, 2);
        c.set(Metric::ApiCalls, 1);
        c.set(Metric::StorageGbHours, 5);
        c.set(Metric::TunnelHours, 10);
        c
    }

    #[test]
    fn meter_and_total() {
        let mut m = Meter::with_rates(rate_card());
        let t = Uuid::new_v4();
        let now = chrono::Utc::now();
        m.record(UsageRecord::new(t, Metric::ApiCalls, 100.0, now));
        let (s, e) = window();
        assert_eq!(m.total_for(t, Metric::ApiCalls, s, e), 100.0);
        assert_eq!(m.total_for(t, Metric::ComputeMinutes, s, e), 0.0);
    }

    #[test]
    fn invoice_generation() {
        let mut m = Meter::with_rates(rate_card());
        let t = Uuid::new_v4();
        let now = chrono::Utc::now();
        m.record(UsageRecord::new(t, Metric::ApiCalls, 100.0, now));
        m.record(UsageRecord::new(t, Metric::ComputeMinutes, 50.0, now));
        let (s, e) = window();
        let inv = meter_invoice(&m, t, s, e).unwrap();
        // 100 * 1 + 50 * 2 = 200 cents
        assert_eq!(inv.total_cents, 200);
        assert_eq!(inv.lines.len(), 2);
    }

    #[test]
    fn invoice_window_filters_events() {
        let mut m = Meter::with_rates(rate_card());
        let t = Uuid::new_v4();
        let now = chrono::Utc::now();
        m.record(UsageRecord::new(t, Metric::ApiCalls, 10.0, now - Duration::days(60)));
        let (s, e) = window();
        let inv = meter_invoice(&m, t, s, e).unwrap();
        assert_eq!(inv.total_cents, 0);
    }

    #[test]
    fn missing_rate_errors() {
        let mut m = Meter::new();
        let t = Uuid::new_v4();
        let now = chrono::Utc::now();
        // Record usage for a metric that has no configured rate.
        m.record(UsageRecord::new(t, Metric::ApiCalls, 10.0, now));
        let (s, e) = window();
        assert!(matches!(
            meter_invoice(&m, t, s, e),
            Err(BillingError::NoRate(_))
        ));
    }

    #[test]
    fn snapshot_build() {
        let mut m = Meter::with_rates(rate_card());
        let t = Uuid::new_v4();
        let now = chrono::Utc::now();
        m.record(UsageRecord::new(t, Metric::ApiCalls, 1.0, now));
        let (s, e) = window();
        let snap = BillingSnapshot::build(&m, t, s, e).unwrap();
        assert_eq!(snap.invoices.len(), 1);
        assert!(snap.total_cents > 0);
    }
}
