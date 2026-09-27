# Architecture Evidence Model

All skills should use a shared evidence model when turning code, docs, runtime data, and assumptions into architecture artifacts.

## Node fields

```json
{
  "id": "service.order-api",
  "label": "Order API",
  "type": "service | module | database | queue | external-system | actor | capability | cloud-resource | decision | risk",
  "state": "current | target | deprecated | proposed | unknown",
  "owner": "team or person when known",
  "description": "short human-readable explanation",
  "sourceRefs": ["path/to/file.ts:10-80", "docs/adr-001.md"],
  "confidence": "high | medium | low | unknown"
}
```

## Edge fields

```json
{
  "id": "edge.order-api-to-payment",
  "from": "service.order-api",
  "to": "service.payment-provider",
  "type": "calls | reads | writes | publishes | subscribes | depends-on | deploys-to | owns | replaces | validates",
  "sync": "sync | async | batch | unknown",
  "protocol": "HTTP | gRPC | SQL | Kafka | S3 | file | in-process | unknown",
  "description": "what crosses this relationship",
  "sourceRefs": ["src/order/paymentClient.ts"],
  "confidence": "high | medium | low | unknown"
}
```

## Evidence types

- **code**: imports, handlers, clients, repositories, modules, annotations, tests.
- **contract**: OpenAPI, AsyncAPI, Protobuf, GraphQL schema, event schema.
- **config**: environment variables, service discovery, routing, feature flags, package manifests.
- **data**: database schema, migrations, SQL, ORM mapping, cache keys, lineage jobs.
- **runtime**: logs, traces, metrics, service registry, deployment inventory.
- **document**: README, ADR, design docs, runbooks, incident postmortems.
- **human-assumption**: explicitly marked assumption from interview, prompt, or architecture intent.

## Model metadata

Reference-only teaching models may use:

```json
{
  "metadata": {
    "sourceRefPolicy": "illustrative",
    "sourceRefPolicyReason": "Representative sourceRefs demonstrate evidence shape; paths are not expected to resolve in this repository."
  }
}
```

Use this only for examples under skill references. Real current-state or CI-validated architecture models should keep resolvable `sourceRefs` and validate with `--source-refs error --require-source-refs`.

## Validation rules

- Current-state nodes need at least one high or medium evidence source.
- Target-state nodes can exist without code evidence, but must be labeled as target/proposed.
- Runtime-only relationships should not be presented as static design unless confirmed.
- Inferred relationships must carry lower confidence and a validation task.
