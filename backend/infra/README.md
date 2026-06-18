# infra/ — optional AWS deployment notes (v2, NOT required to run)

The CLEAR MVP runs entirely locally (SQLite + in-process inference). This folder
exists only to show how the same logical data flow maps onto AWS for a later
production iteration. **None of this is needed to run, train, or demo the app.**

## Logical flow (identical locally and on AWS)

```

ingest -> validate -> idempotency -> store -> infer -> output-validate -> serve

```

| Local MVP component        | AWS v2 equivalent (optional)                     |
| -------------------------- | ------------------------------------------------ |
| `ingestion.ingest_one`     | API Gateway + Lambda (validation + idempotency)  |
| idempotency on `event_id`  | DynamoDB conditional put / SQS dedupe id         |
| `dead_letter` table        | SQS dead-letter queue                            |
| SQLite `clear.db`          | RDS Postgres / DynamoDB + S3 data lake           |
| `models/*` joblib files    | S3 model artifacts + SageMaker endpoints         |
| `train.py` / `retrain.py`  | SageMaker training + Step Functions pipeline     |
| shadow/canary/promote      | SageMaker endpoint variants + traffic shifting   |
| `corridor_risk` cache      | ElastiCache / DynamoDB TTL table                 |
| `hotspot.run_batch`        | scheduled ECS / Batch job (EventBridge cron)     |
| operator/citizen tokens    | Cognito user pools + scopes                      |

## Guardrails that must survive the port to AWS

- Dispatch stays decision-support only: no autonomous signal actuation; every
  recommendation needs an explicit operator-approval event.
- Clearance stays a censored-survival interval (median + P10-P90); never a
  point ETA imputed from missing resolutions.
- SLA% is always computed over the resolved subset and labeled as such.
- Secrets come only from the environment (Secrets Manager / SSM on AWS).

## Not included on purpose

No Terraform/CDK is shipped in the MVP to keep it runnable with zero cloud
setup. When v2 begins, add `infra/terraform/` or `infra/cdk/` here and wire the
table above; the application code does not change.
