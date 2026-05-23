# Monthly Cost by Classification - Implementation Guide

This guide explains the best ways to calculate and report monthly Azure cost by your classification model (`Workload-L1`, `Workload-L2`, `Workload-L3`, `Environment`).

## Goal

Track monthly spend by classification so you can answer:
- How much did we spend this month by `Workload-L1` (Infra/Data/Apps)?
- Which `Workload-L2` and `Workload-L3` categories are driving cost?
- How much of spend is still unclassified or missing tags?

---

## Recommended Approaches

## Approach 1 (Fastest): Azure Cost Management + Tag Dimensions

Use Azure Cost Management directly with your tags.

### When to use
- You need dashboards quickly.
- You want native Azure reporting without building a data pipeline.
- You can enforce tagging coverage.

### Steps
1. Ensure required tags are present on all taggable resources:
   - `Workload-L1`
   - `Workload-L2`
   - `Workload-L3`
   - `Environment`
2. In Azure Portal, open **Cost Management + Billing** for the target scope (subscription or management group).
3. Go to **Cost analysis**.
4. Set:
   - Date range: current month (or last month)
   - Granularity: Monthly
   - Metric: Actual cost (or Amortized cost)
5. Group by tag:
   - Start with `Workload-L1`
   - Drill down by `Workload-L2`, then `Workload-L3`
6. Add filters:
   - `Environment` = `prod`, `dev`, etc.
   - Include only subscriptions/resource groups you want.
7. Save views for:
   - Monthly total by L1
   - Monthly by L2
   - Monthly by L3
   - Untagged/empty tag values
8. Create budgets and alerts per tag (if scope supports it).

### Pros
- Very fast to start.
- Native Azure UI and governance alignment.
- No custom infra required.

### Cons
- Limited custom logic (for example complex reclassification rules).
- Tag quality directly impacts report quality.

---

## Approach 2 (Best Balance): Scheduled Cost Export + Classification Join (Recommended)

Export detailed cost data, then join it with your classification data for robust monthly reports.

### When to use
- You want reliable monthly reporting and trend analysis.
- You need custom KPIs (coverage, drift, unclassified spend, lineage).
- You want analytics in Power BI or Fabric.

### Architecture
1. Azure Cost Management **Exports** writes daily/monthly cost detail CSV/Parquet to Storage.
2. A data job (Python/ADF/Fabric) loads:
   - Cost export dataset
   - Classification dataset (Cosmos DB or API)
3. Join on `resourceId`.
4. Aggregate monthly cost by `Workload-L1/L2/L3`.
5. Publish to dashboard (Power BI/Fabric/SQL).

### Steps
1. Configure Cost Export:
   - Scope: subscription or management group
   - Frequency: daily
   - Dataset: cost details (actual or amortized)
   - Sink: Storage account container
2. Build `classification_snapshot` table from your app data:
   - Keys: `resource_id`, `subscription_id`
   - Tags: `Workload-L1`, `Workload-L2`, `Workload-L3`, `Environment`
   - Status fields: `pending`, `approved`, `applied`, `failed`
3. Build ETL job:
   - Parse export files
   - Normalize `resourceId` casing
   - Join cost rows with classification snapshot on `resourceId`
4. Create monthly fact table:
   - `month`
   - `subscription_id`
   - `resource_id`
   - `workload_l1`, `workload_l2`, `workload_l3`, `environment`
   - `cost`
5. Compute key metrics:
   - Monthly cost by L1/L2/L3
   - % classified spend
   - Untagged spend
   - Approved vs applied spend coverage
6. Visualize in Power BI/Fabric:
   - Trend by month
   - Drilldown from L1 -> L2 -> L3
   - Unclassified and missing-tag exceptions

### Pros
- Most practical long-term approach.
- Flexible and auditable.
- Works even when some resources cannot be tagged directly.

### Cons
- Requires a data pipeline and storage.

---

## Approach 3 (Enterprise): FinOps Data Mart with Governance

Create a governed cost data mart with policy enforcement and organizational reporting.

### When to use
- Multi-subscription/multi-team environments.
- Central FinOps and chargeback/showback requirements.
- Executive reporting and forecasting.

### Steps
1. Enforce tags with Azure Policy:
   - Require `Workload-L1/L2/L3` and `Environment` on create/update.
   - Optionally deny creation without required tags.
2. Ingest cost exports centrally across subscriptions.
3. Build a curated semantic model:
   - Cost fact table
   - Dimensions for hierarchy, subscription, team, environment
4. Implement governance metrics:
   - Tag compliance %
   - Untagged spend trend
   - Classification drift and orphaned resources
5. Deliver dashboards for:
   - Platform teams
   - Product teams
   - Finance leadership

### Pros
- Strong governance and standardization.
- Scales for enterprise FinOps.

### Cons
- Highest implementation effort.

---

## Recommended Path for Your Current Project

Given your existing classification/tagging workflow, implement in this order:

1. Start with **Approach 1** now for immediate visibility.
2. Move to **Approach 2** as your primary monthly reporting solution.
3. Add **Approach 3** controls if/when organizational scale requires it.

---

## Implementation Checklist

- [ ] Confirm all approved/applied resources receive `Workload-L1/L2/L3` tags.
- [ ] Add a recurring check for untagged or failed-tag resources.
- [ ] Create and save Cost Analysis views grouped by tags.
- [ ] Set up Cost Management Export (daily) to Storage.
- [ ] Build monthly aggregation pipeline by classification hierarchy.
- [ ] Publish dashboard with L1/L2/L3 drill-down and unclassified spend.
- [ ] Add budgets/alerts by `Workload-L1` and critical `Environment` values.

---

## Practical Notes and Caveats

1. Cost data latency is normal (typically not real-time).
2. Some charges may appear at subscription/shared level and not map to a specific resource ID; classify these under a shared bucket.
3. Keep tag keys exactly consistent (case and spelling).
4. Decide whether to report **Actual cost** or **Amortized cost** and keep it consistent across dashboards.

---

## Suggested Report Pages

1. Monthly Summary
   - Total cost
   - Classified spend %
   - Untagged spend %
2. L1 Breakdown
   - Infra vs Data vs Apps trend
3. L2/L3 Drilldown
   - Top categories and month-over-month change
4. Exceptions
   - Missing tags
   - Failed apply operations
   - High-cost unclassified resources
