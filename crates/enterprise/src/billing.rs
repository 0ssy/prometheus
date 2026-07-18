//! Usage metering and invoice generation.

use crate::tenant::Plan;
use crate::Result;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use tracing::info;
use uuid::Uuid;

/// A metered usage event.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UsageEvent {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub metric: UsageMetric,
    pub quantity: u64,
    pub at: DateTime<Utc>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum UsageMetric {
    ComputeMinutes,
    StorageGb,
    ApiCalls,
    InferenceTokens,
}

impl UsageMetric {
    pub fn unit_price(&self, plan: Plan) -> f64 {
        // per-unit price (USD) by plan tier
        let base = match self {
            UsageMetric::ComputeMinutes => 0.05,
            UsageMetric::StorageGb => 0.10,
            UsageMetric::ApiCalls => 0.001,
            UsageMetric::InferenceTokens => 0.00002,
        };
        match plan {
            Plan::Free => 0.0,
            Plan::Pro => base,
            Plan::Enterprise => base * 0.8,
        }
    }

    pub fn label(&self) -> &'static str {
        match self {
            UsageMetric::ComputeMinutes => "compute-minutes",
            UsageMetric::StorageGb => "storage-gb",
            UsageMetric::ApiCalls => "api-calls",
            UsageMetric::InferenceTokens => "inference-tokens",
        }
    }
}

/// A generated invoice line item.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InvoiceLine {
    pub metric: UsageMetric,
    pub quantity: u64,
    pub unit_price: f64,
    pub amount: f64,
}

/// A generated invoice for a tenant over a billing period.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Invoice {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub plan: Plan,
    pub lines: Vec<InvoiceLine>,
    pub total: f64,
    pub currency: String,
    pub issued_at: DateTime<Utc>,
}

/// Meters usage events and produces invoices.
#[derive(Debug, Clone, Default)]
pub struct BillingService {
    events: Arc<RwLock<Vec<UsageEvent>>>,
}

impl BillingService {
    pub fn new() -> Self {
        Self::default()
    }

    pub async fn record(&self, event: UsageEvent) {
        self.events.write().await.push(event);
    }

    pub async fn meter(
        &self,
        tenant_id: Uuid,
        metric: UsageMetric,
        quantity: u64,
    ) -> UsageEvent {
        let event = UsageEvent {
            id: Uuid::new_v4(),
            tenant_id,
            metric,
            quantity,
            at: Utc::now(),
        };
        self.record(event.clone()).await;
        event
    }

    /// Aggregate usage for a tenant into an invoice.
    pub async fn invoice(&self, tenant_id: Uuid, plan: Plan) -> Result<Invoice> {
        let events = self.events.read().await;
        let mut totals: HashMap<UsageMetric, u64> = HashMap::new();
        for e in events.iter().filter(|e| e.tenant_id == tenant_id) {
            *totals.entry(e.metric).or_insert(0) += e.quantity;
        }
        let mut lines = Vec::new();
        let mut total = 0.0f64;
        for (metric, quantity) in totals {
            let unit_price = metric.unit_price(plan);
            let amount = unit_price * quantity as f64;
            total += amount;
            lines.push(InvoiceLine {
                metric,
                quantity,
                unit_price,
                amount,
            });
        }
        let invoice = Invoice {
            id: Uuid::new_v4(),
            tenant_id,
            plan,
            lines,
            total: (total * 100.0).round() / 100.0,
            currency: "USD".into(),
            issued_at: Utc::now(),
        };
        info!(tenant = %tenant_id, total = invoice.total, "invoice generated");
        Ok(invoice)
    }

    pub async fn total_events(&self) -> usize {
        self.events.read().await.len()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::tenant::TenantManager;

    fn tid() -> Uuid {
        Uuid::new_v4()
    }

    #[tokio::test]
    async fn meter_and_invoice() {
        let billing = BillingService::new();
        let t = tid();
        billing.meter(t, UsageMetric::ComputeMinutes, 100).await;
        billing.meter(t, UsageMetric::ApiCalls, 1000).await;
        let inv = billing.invoice(t, Plan::Pro).await.unwrap();
        assert_eq!(inv.lines.len(), 2);
        assert!(inv.total > 0.0);
        assert_eq!(inv.currency, "USD");
    }

    #[tokio::test]
    async fn free_plan_zero_cost() {
        let billing = BillingService::new();
        let t = tid();
        billing.meter(t, UsageMetric::ComputeMinutes, 500).await;
        let inv = billing.invoice(t, Plan::Free).await.unwrap();
        assert_eq!(inv.total, 0.0);
    }

    #[tokio::test]
    async fn enterprise_discount() {
        let billing = BillingService::new();
        let t = tid();
        billing.meter(t, UsageMetric::ComputeMinutes, 100).await;
        let pro = billing.invoice(t, Plan::Pro).await.unwrap();
        let ent = billing.invoice(t, Plan::Enterprise).await.unwrap();
        assert!(ent.total <= pro.total + 1e-9);
    }

    #[tokio::test]
    async fn invoice_isolated_per_tenant() {
        let billing = BillingService::new();
        let a = tid();
        let b = tid();
        billing.meter(a, UsageMetric::ApiCalls, 100).await;
        billing.meter(b, UsageMetric::ApiCalls, 999).await;
        let inv_a = billing.invoice(a, Plan::Pro).await.unwrap();
        let inv_b = billing.invoice(b, Plan::Pro).await.unwrap();
        assert_ne!(inv_a.total, inv_b.total);
    }

    #[test]
    fn unit_price_tiers() {
        assert_eq!(UsageMetric::ApiCalls.unit_price(Plan::Free), 0.0);
        assert!(UsageMetric::ApiCalls.unit_price(Plan::Enterprise)
            < UsageMetric::ApiCalls.unit_price(Plan::Pro));
    }

    #[tokio::test]
    async fn integrates_with_tenant() {
        let tm = TenantManager::new();
        let tenant = tm.create_tenant("acme", Plan::Pro).await.unwrap();
        let billing = BillingService::new();
        billing.meter(tenant.id, UsageMetric::StorageGb, 10).await;
        let inv = billing.invoice(tenant.id, tenant.plan).await.unwrap();
        assert!(inv.total > 0.0);
    }
}
