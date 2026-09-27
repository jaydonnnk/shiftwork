# Architecture Contract

This reference defines shared rules for all architecture skills in this package.

## Core principles

- **Evidence first**: every important node, edge, risk, decision, or metric should trace back to code, configuration, runtime data, documentation, or an explicit assumption.
- **Separate view states**: never mix current-state, target-state, runtime observation, and conceptual design without labeling them.
- **One view, one question**: a diagram should answer a specific decision question. If the diagram answers multiple unrelated questions, split it.
- **Stable identity**: use stable IDs for nodes and edges so diagrams can be regenerated, diffed, and traced back to code.
- **Progressive disclosure**: start with a high-level map, then provide drill-down views for modules, data, deployment, risks, or changes.
- **Human-readable summary**: every architecture artifact should include a short explanation of purpose, audience, scope, assumptions, and next action.
- **Skill transparency**: name both the scenario skill that produced the architecture understanding and any foundation/format skill that shaped the diagram source, for example `flow-visualizer` + `graphviz` or `system-modeler` + `c4model`.

## View levels

Use these levels consistently:

- **L0 Business capability**: what the organization or product needs to do.
- **L1 System context**: people, external systems, and system boundary.
- **L2 Containers / services**: deployable or independently owned units.
- **L3 Components / modules**: internal building blocks inside a service or application.
- **L4 Code / symbols**: files, packages, classes, functions, handlers, schemas.
- **Runtime topology**: processes, pods, nodes, cloud resources, regions, networks, queues, storage.
- **Data topology**: data objects, owners, stores, flows, lineage, sensitivity, retention.

## Standard artifact shape

Prefer producing the following files when possible:

```text
<view-name>.md              # explanation, assumptions, reading order
<view-name>.dsl|dot|mmd|puml # diagram source
<view-name>.evidence.md     # supporting files, docs, traces, configs
<view-name>.summary.md      # summary, next action, and maintenance note
```

**File delivery rule**: diagram source files (`.dot`, `.dsl`, `.mmd`, `.puml`) MUST be written to disk as actual files, not inlined as code blocks in the chat response. Use the file creation tool to write the file, then reference the path in the response. Only show a short excerpt (<= 20 lines) inline if the user explicitly asks to see the content.

## Evidence and confidence

Use confidence labels:

- **high**: direct evidence from code, config, schema, API contract, IaC, runtime telemetry, or authoritative doc.
- **medium**: multiple partial signals agree, but no direct source confirms the relationship.
- **low**: inferred from naming, folder structure, conventions, or human assumption.
- **unknown**: intentionally shown as an unknown area to investigate.

## Diagram grounding

Diagrams must not make a claim look more certain than the supporting text.

Prefer maintainable architecture sources before lightweight Markdown-native diagrams:

- Structurizr DSL for system landscape, context, container, component, and reusable C4 views.
- Graphviz DOT for business flows, lifecycles, integration maps, dependency/impact maps, deployment/resource graphs, risk maps, data lineage, legacy maps, and dense relationships.
- Mermaid only when the user asks for Markdown-native output, the view is deliberately small, or the format is needed for a simple sequence/state sketch.

- If a node, actor, boundary, state, or flow step is inferred, label it `inferred` or `assumed` in the diagram.
- If the text says a workflow, permission boundary, tenant/workspace model, external integration, or state transition is unknown, the diagram must also show it as unknown or omit it from the confirmed path.
- Do not turn a scenario-critical unknown into a complete happy path just because a diagram would look cleaner.
- Prefer a confirmed partial path plus an `Unknown / validate next` branch over a fully drawn but unsupported process.
- Field, table, enum, counter, or relation existence confirms data shape, not the business action that uses it. If the mutation, job, callback, trigger, event handler, test, or process note is missing, split the confirmed structure from the inferred mechanism in both text and diagrams.
- UI/form/template/page-object evidence confirms interface affordances, payloads, routes, or tested UI steps, not backend effects. If the handler, mutation, model method, integration test, job, callback, or trace is missing, draw the UI submit step separately from the unknown persistence, delivery, or state transition.
- In diagrams, label UI-only nodes as `UI:`, `Form:`, `Route:`, or `Test step:` instead of using bare business-completion labels such as `Create Client`, `Send Invoice`, or `Record Payment`.
- Factory/fixture/seed evidence confirms example data shape, not production behavior. In text, phrase sample values as factory/fixture values, not runtime defaults. In diagrams, make `Factory:`, `Fixture:`, `Seed:`, or `Data shape:` the main node label, not a bare action label with the qualifier hidden in parentheses. Draw the production handler, lifecycle transition, or side effect as unknown unless directly evidenced, and use dashed/dotted edges from unknown handlers to factory-only structures.
- For Mermaid flowcharts, declare every node with a stable ID and readable label before using it in edges; avoid dangling edge endpoints, mismatched node IDs, and mismatched node-shape delimiters such as `{... ]`.

## Visual conventions

- Use different node shapes or labels for people, systems, services, modules, databases, queues, external systems, and infrastructure.
- Use edge labels for relationship type: calls, reads, writes, publishes, subscribes, deploys-to, owns, depends-on, secures, routes-to.
- Label boundaries explicitly: system boundary, team boundary, trust boundary, network boundary, data ownership boundary, deployment environment.
- Prefer multiple focused diagrams over one unreadable diagram.
- Keep generated diagrams text-based whenever maintainability matters.
- For Graphviz DOT intended for Qoder Canvas or `.dot` preview, prefer top-to-bottom `rankdir=TB` for dense relationship graphs. Use `rankdir=LR` only for short linear lineage, traffic-path, or service-path graphs with controlled width, because wide horizontal SVGs can start outside the useful viewport.
