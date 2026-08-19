# Provider Operations Reference

Use this reference for provider configuration, remote API behavior, secure
observability, import, tests, documentation, and release-facing changes. Follow
the repository's existing client and authentication contracts.

## Provider and Client Configuration

Decode provider configuration into Framework values and check diagnostics and
unknowns before resolving settings. Preserve the provider's documented
precedence among explicit configuration, environment variables, vendor files,
workload identity, and other sources; precedence is public behavior, not a
generic Go implementation detail.

Multi-part credentials sometimes need to come from one coherent source, while
independent non-secret settings can often resolve field by field. Follow the
API's authentication model rather than imposing a universal credential chain.
Test every supported source, incomplete configuration, and precedence boundary.

Provider `Configure` can receive unknown values. Choose behavior deliberately:

- Return an error if no provider operation can function without the value.
- Warn or defer client availability if some validation or operations can
  proceed, then diagnose use of an unavailable client at the operation boundary.
- Do not silently turn unknown into empty and authenticate through a lower
  precedence source as a different identity.

Construct and share provider-wide clients through `resp.ResourceData` and
`resp.DataSourceData`. Resource and data source `Configure` methods must return
safely for nil provider data, type-check non-nil data, and diagnose an
unexpected type as a provider implementation error. Guard CRUD against a nil
client rather than panicking.

Keep provider Configure repeat-safe. A remote identity check may improve error
messages but also adds network behavior during plan and can break offline or
deferred configuration. Retain the provider's existing policy unless the task
explicitly changes that contract.

## Sensitive Data and Error Safety

Sensitivity is a data-flow property, not only a schema flag. High-risk sources
include:

- Sensitive variables, schema attributes, credentials, certificates, and state.
- YAML, JSON, templates, scripts, and other secret-bearing documents.
- URLs with user information or secret query parameters.
- Authorization headers, cookies, and complete request headers.
- Request and response bodies, including API error responses.
- Parser, SDK, and transport errors that may echo inputs or responses.
- Generic formatting of errors, models, requests, or responses.

Do not write diagnostics like:

```go
resp.Diagnostics.AddError(
    "Unable to Parse Configuration",
    fmt.Sprintf("Invalid YAML %q: %s", document, err),
)
```

Both the document and parser error can disclose source text. Prefer an
attribute diagnostic built from known-safe text:

```go
resp.Diagnostics.AddAttributeError(
    path.Root("document"),
    "Invalid YAML Configuration",
    "The configured document could not be parsed as YAML. Check its syntax.",
)
```

Use an allowlist for diagnostic and log metadata. Operation names, status codes,
and correlation IDs can be useful, but verify that the target API does not put
secret material in an identifier. Before exposing `err.Error()`, establish that
every possible concrete error has sanitized text; otherwise map it to a safe
category and retain only proven-safe troubleshooting metadata.

Redacting `String` or `GoString` methods is defense in depth, not proof that a
value cannot leak through nested formatting, errors, serialization, or test
failures. Prefer never passing sensitive data to those paths.

Seed sentinel secrets into malformed inputs and fake API failures. Assert that
diagnostics, returned errors, captured logs, and test failure messages do not
contain them.

## Logging

Use `github.com/hashicorp/terraform-plugin-log/tflog` with the supplied context.
Do not log to stdout from provider operations.

Log narrowly selected structured fields. A credential source name, operation,
or safe resource type may be useful; complete models and payloads are not safe
merely because trace logging is enabled. Masking helpers are a final safeguard,
not permission to attach secrets to the logger.

## Context and Remote APIs

Pass the Framework context through clients, HTTP requests, pagination, polling,
retries, and waits. Derive bounded child contexts from it instead of replacing
it with `context.Background()`.

The Framework does not define a universal retry or pagination policy:

- Retry only classified transient failures.
- Respect operation idempotency and reconcile ambiguous create or update
  timeouts before repeating mutations.
- Bound attempts and elapsed time, add jitter, and honor safe server guidance.
- Do not retry validation, authorization, duplicate, or arbitrary client errors.
- Follow pagination until exhaustion and reject repeated or non-advancing
  cursors.
- Flatten remote collections into deterministic Terraform ordering and do not
  persist accidental partial collection results.

For asynchronous or eventually consistent APIs, use the repository's waiter
abstraction. Do not add an SDKv2 retry dependency solely because an external
example uses `retry.StateChangeConf`; first inspect pinned dependencies and
local patterns. Expose configurable operation timeouts when practitioners need
control.

For HTTP clients, check transport errors before dereferencing or closing the
response. Close successful response bodies, bound reads of error bodies, and do
not expose raw body content in diagnostics or logs.

## Import

Implement import only when the resource has stable lookup information. A simple
identifier can use `resource.ImportStatePassthroughID` when the schema actually
has that attribute. Composite identifiers require an unambiguous documented
format, validation, and explicit attribute writes.

Import should set only enough state for the following Read to hydrate the
resource. Verify import parity with `ImportStateVerify` or explicit state and
plan checks when supported by the pinned testing version. Ignore differences
only for values the remote API genuinely cannot recover, and document that
behavior.

When adopting modern resource identity support, verify its Framework, protocol,
Terraform, and OpenTofu requirements rather than treating it as a drop-in
replacement for string import IDs.

## Testing Existing Providers

Use focused unit tests for deterministic behavior:

- Schema `ValidateImplementation`.
- Framework-to-API conversions, especially null versus empty semantics.
- Validators, defaults, custom types, and plan modifiers.
- Import parsing, not-found and error classification, retries, and pagination.
- Direct historical-to-current state upgrades.
- Sensitive-data non-disclosure on failure paths.

Use `terraform-plugin-testing` acceptance tests for practitioner-visible
behavior. Match `ProtoV5ProviderFactories` or `ProtoV6ProviderFactories` to the
production server; do not test an extra protocol merely because the Framework
supports it.

Prefer the repository's established assertion style. On compatible testing
versions, typed `ConfigStateChecks` and `ConfigPlanChecks` can make state and
plan intent explicit. Do not introduce a broad testing migration just to use a
newer API in an otherwise focused change.

Applicable resource scenarios include:

- Minimal create followed by a no-op plan.
- In-place updates and replacement of immutable fields.
- Refresh after remote drift and external deletion.
- Import followed by authoritative Read and a no-op plan.
- Delete and already-absent deletion.
- Failure and partial-failure state behavior.

Centralized API lookup, existence, and disappearance helpers are valuable when
multiple resources, waiters, or tests share exactly the same not-found
semantics. Do not introduce them for a single call site without a concrete need.

Acceptance tests can create billable or persistent infrastructure. Respect the
repository's environment gate, dedicated-account policy, parallelism, cleanup,
and sweepers. Ask before using real credentials or remote infrastructure when
authorization is not already explicit.

## Documentation, Migration, and Releases

Schema descriptions are practitioner-facing and commonly feed
`terraform-plugin-docs`. Follow existing example and template conventions,
regenerate documentation after schema changes, and do not hand-edit generated
output instead of fixing its source.

For SDKv2-to-Framework migration, preserve existing configuration syntax,
blocks, identifiers, null/zero behavior, import behavior, and state. Baseline
acceptance behavior before migration and verify prior-version state produces an
empty plan after migration. Use muxing only when it matches the repository's
existing migration strategy and pinned versions.

Provider source addresses, schema and state compatibility, protocol metadata,
release archives, checksums, and signatures are public contracts. Do not replace
published artifacts. Terraform Registry and OpenTofu Registry are independent
distribution integrations; read `opentofu-compatibility.md` before changing
identity or publishing assumptions.

## Official References

- https://developer.hashicorp.com/terraform/plugin/framework/providers
- https://developer.hashicorp.com/terraform/plugin/framework/resources/configure
- https://developer.hashicorp.com/terraform/plugin/framework/data-sources/configure
- https://developer.hashicorp.com/terraform/plugin/log/writing
- https://developer.hashicorp.com/terraform/plugin/log/filtering
- https://developer.hashicorp.com/terraform/plugin/framework/resources/timeouts
- https://developer.hashicorp.com/terraform/plugin/framework/resources/import
- https://developer.hashicorp.com/terraform/plugin/framework/acctests
- https://developer.hashicorp.com/terraform/plugin/testing/acceptance-tests
- https://developer.hashicorp.com/terraform/plugin/testing/testing-patterns
- https://developer.hashicorp.com/terraform/tutorials/providers-plugin-framework/providers-plugin-framework-documentation-generation
- https://developer.hashicorp.com/terraform/registry/providers/publishing
