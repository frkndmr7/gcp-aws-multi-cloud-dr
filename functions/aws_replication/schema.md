# Replication event v1

Create-only JSON envelope: `{"schema_version":1,"event_id":"stable-source-event-id","record":{"id":"short-code","original_url":"https://example.com/","origin_cloud":"gcp","created_at":"2026-01-01T00:00:00Z","version":1}}`.

The publisher must preserve the event ID and record fields on retry. Record ID is the DynamoDB partition key and Firestore document ID. A conditional create prevents overwrite; on collision a strongly consistent read accepts only an identical record, otherwise the message retries and reaches the DLQ. This does not deduplicate event IDs across different records. Version 1 is create-only; updates, deletes, promotion and ordering between versions require a separate design. No delivery guarantee exists until publisher and federation are implemented. Standard SQS is at-least-once and unordered. A failed record may be replayed; operators must monitor and remediate DLQ messages before retention expires. Lambda event source mapping is disabled by default.

The future GCP workload should use short-lived federated AWS credentials, with an independently verified issuer, audience and subject and an IAM role limited to `sqs:SendMessage` on the main queue. No credentials, trust policy or publisher access are provisioned by this module.
