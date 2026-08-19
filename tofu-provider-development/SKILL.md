---
name: tofu-provider-development
description: Use when modifying, reviewing, debugging, or testing an existing Go provider for OpenTofu or Terraform built with the Terraform Plugin Framework, especially schemas, plan and state behavior, lifecycle methods, diagnostics, import, drift, and compatibility.
---

# OpenTofu Provider Development

Work within an existing Terraform Plugin Framework provider. Follow the
repository's architecture, naming, client, testing, documentation, and release
conventions. Apply this guidance where Terraform or OpenTofu configuration,
planning, state, lifecycle, protocol, or compatibility semantics differ from
ordinary Go development.

Do not scaffold or reorganize the provider unless the task requires it. Do not
silently upgrade dependencies, change protocol versions or source addresses,
or adopt a newer Core-dependent feature merely because the pinned Framework
version compiles it.

## Inspect Before Editing

Establish the local contract from:

- `go.mod` and `go.sum`: Framework, testing, logging, validators, timeouts,
  mux, SDKv2, and API client versions.
- Provider startup and `Metadata`: source address, served protocol, debug
  support, and version injection.
- Existing provider, resource, and data source models, constructors, interface
  assertions, client injection, conversions, diagnostics, and logging.
- Tests: CLI selection, protocol factories, environment gates, credentials,
  cleanup, and supported versions.
- Examples, generated documentation, state upgrades, compatibility policy, and
  release metadata affected by the change.

Prefer established repository abstractions over a theoretically cleaner
provider architecture. Preserve shipped configuration and persisted state
unless a deliberate breaking change or migration is part of the task.

## Read Only What the Task Needs

| Task | Reference |
| --- | --- |
| Schema, models, null or unknown values, CRUD, drift, plan modifiers, defaults, collections, state upgrades | `references/framework-core.md` |
| Provider configuration, API clients, sensitive data, logging, retries, import, testing, docs | `references/provider-operations.md` |
| Terraform/OpenTofu versions, protocols, feature gates, source addresses, registries, distribution | `references/opentofu-compatibility.md` |

Read a second reference only when the change crosses that boundary. Verify
exact APIs against the repository's pinned versions and official documentation.

## Preserve Provider Invariants

Treat the provider as an adapter among configuration, plan, prior state, and a
remote system, not as an ordinary Go CRUD service.

- Decode from the lifecycle-appropriate source: provider and data source
  configuration from `Config`, Create from `Plan`, Read and Delete from
  `State`, and Update from `Plan` plus prior `State` when needed.
- Append every returned diagnostic, check `resp.Diagnostics.HasError()` before
  using decoded data, and stop after unrecoverable errors.
- Use Framework values wherever null or unknown must survive. Do not treat
  null, unknown, omitted, empty, and zero as equivalent.
- Convert Framework models to API models deliberately. Do not serialize a
  Framework model directly unless null, unknown, computed, and wire semantics
  have all been designed.
- Keep Create and Update results consistent with the plan. Known and null
  planned values must remain semantically equal; only planned unknown values
  may resolve to different known or null values. State cannot contain unknowns.
- Make Read authoritative for remote values, but preserve state-only or
  configuration-only values the API cannot reconstruct. Remove state only for
  confirmed remote absence during Read.
- Treat confirmed absence during Delete as success. Do not write or explicitly
  remove state after a successful Delete; the Framework removes it.
- Do not remove state from Create or Update. Model immutable changes with
  replacement planning rather than failing an attempted update.
- Deliberately choose response state on partial failure. An error diagnostic
  does not prevent Terraform from persisting returned state; never rely on
  tainting as the recovery strategy.
- Keep list ordering deterministic, set identity stable, and nested block
  cardinality configuration-defined. Do not model API-created children by
  adding provider-generated blocks.
- Use defaults, validators, and plan modifiers only in their proper phases.
  Do not call remote APIs from validators or assume prior elements under lists
  and sets remain aligned.
- Pass the supplied `context.Context` through network calls, pagination,
  retries, polling, and waits. Bound long-running behavior and observe
  cancellation.

## Protect Sensitive Data

Framework `Sensitive` metadata controls display; it does not make decoded Go
values, state, errors, or logs safe. Treat credentials, sensitive attributes,
secret-bearing documents, request data, response bodies, headers, URLs, and
SDK errors as unsafe until specific content is proven safe.

Build diagnostics and structured `tflog` fields from allowlisted metadata.
Do not expose raw errors, payloads, complete models, or sensitive values merely
for troubleshooting. Read
`references/provider-operations.md#sensitive-data-and-error-safety` when a
change touches parsing, authentication, API errors, diagnostics, or logging.

## Match the Existing Lifecycle

Trace the affected schema, Framework model, API conversion, lifecycle method,
state write, documentation, and tests before editing. Do not mechanically call
Read after Create or Update: shared refresh logic is useful only when it
preserves planned/configuration-only values and handles eventual consistency.

Resource and data source `Configure` methods must tolerate nil provider data
during offline validation and diagnose unexpected non-nil types. Provider
configuration itself can contain unknown values; whether to defer, warn, or
error depends on what operations can function without the value.

Import writes only enough lookup state for the following Read. State upgraders
transform each historical version directly to the current schema, populate the
complete current state, and do not refresh the remote API.

## Verify Behavior, Not Just Go Code

Run focused unit tests first. Acceptance tests can create billable or persistent
infrastructure; inspect their gates and cleanup and do not use real credentials
without authorization.

For changed behavior, obtain evidence appropriate to the task:

- Schema implementation validation and null, unknown, conversion, validator,
  plan modifier, import parser, error classification, or state upgrader tests.
- Acceptance coverage for create, no-op plan, update or replacement, drift,
  remote deletion, import, and already-absent deletion where applicable.
- Typed `statecheck` or `plancheck` assertions when supported by the pinned
  `terraform-plugin-testing`; follow existing test style otherwise.
- Sentinel-secret tests proving diagnostics, errors, logs, and test output do
  not disclose sensitive values.
- Generated documentation, examples, import instructions, and release notes
  matching public behavior.
- Test factories matching the production protocol. When the provider claims
  Terraform and OpenTofu support, behavioral coverage for both claimed CLI
  families and relevant minimum versions.

## Final Review

Before finishing:

- Inspect every changed `Get`, `Set`, conversion, and diagnostics-returning
  call for append, error-check, and null/unknown handling.
- Verify Create and Update state against the plan, Read behavior for remote
  drift and absence, and Delete behavior for absence.
- Search changed diagnostics and logs for raw errors, identifiers, payloads,
  headers, URLs, and complete models that may disclose sensitive data.
- Verify collection ordering and identity, bounded remote operations, context
  propagation, import hydration, and direct historical-to-current upgrades.
- Confirm tests, generated docs, examples, protocol metadata, and claimed CLI
  compatibility match the implementation.
