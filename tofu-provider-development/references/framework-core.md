# Plugin Framework Core Reference

Use this reference when Terraform's data and lifecycle model changes an
implementation decision. Confirm exact interfaces and package APIs against the
repository's pinned Framework version.

## Configuration, Plan, and State

Terraform values carry information that ordinary Go values cannot always
represent:

- Null means absence, commonly an omitted optional attribute.
- Unknown means the graph will determine the value later.
- Known means a concrete value is available.

Use Framework types such as `types.String`, `types.List`, and `types.Object`
where null or unknown must survive. A Go primitive is reasonable only when the
schema and lifecycle guarantee a known, non-null value and doing so matches the
repository's convention.

Check `IsNull` and `IsUnknown` before reading a concrete value whenever either
is possible. Accessors such as `ValueString` return a zero value for null and
unknown; using that result without checking can turn omission or deferred data
into an explicit API update.

Keep Framework and API models separate. Convert deliberately so these cases do
not collapse:

- an omitted field versus an explicit empty string, false, zero, or empty list;
- a planned unknown versus a request value available only after apply;
- an API default versus a practitioner-configured value;
- a remote omission versus a value that exists only in configuration or state.

General lifecycle guarantees include:

- Required resource attributes are known and non-null during CRUD.
- Optional, non-computed resource attributes are known or null during CRUD.
- Provider configuration values can be unknown.
- Response state cannot contain unknown values.

## Schema Ownership

Each schema context has its own package, such as `provider/schema`,
`resource/schema`, and `datasource/schema`; do not interchange their types.
The Framework has no SDKv2-style implicit root `id`; expose a stable remote
identifier when it is part of the resource model, not merely to satisfy an old
SDK convention.

- `Required`: the practitioner supplies the value.
- `Optional`: omission is meaningful and normally represented as null.
- `Computed`: the provider or remote system owns the value.
- `Optional` plus `Computed`: the practitioner may configure the value;
  otherwise the provider or remote system supplies it.
- `Sensitive`: Terraform propagates display metadata. It does not encrypt state
  or protect a decoded value from diagnostics and logs.

Defaults are resource planning behavior, not generic schema values. On
Framework versions supporting the `Default` field:

- A default can be defined only on a resource attribute.
- The attribute must be `Computed`; a practitioner-overridable default normally
  uses `Optional: true, Computed: true`.
- The default becomes a planned value that Create and Update must preserve.
- Use a local deterministic default only when the provider can know it during
  planning. Keep server-selected defaults computed and persist the API result.

Protocol v6 supports nested attributes; protocol v5 does not. Prefer nested
attributes for new v6 schemas when their value semantics fit. Preserve nested
blocks when existing configuration syntax or protocol v5 compatibility
requires block semantics.

Nested blocks represent configuration cardinality. Provider logic cannot add
or remove blocks during planning or apply. Model API-created implicit children
with computed nested attributes or separate resources rather than inventing
additional blocks.

Collections also carry Terraform semantics:

- Lists are ordered; flatten remote collections deterministically.
- Sets are unordered, but element values determine identity. Do not include
  volatile computed fields in a shape whose changing value destabilizes set
  membership without understanding the consequences.
- Maps require stable keys and deterministic value conversion.
- Prior-state elements below lists and sets are not realigned for plan
  modifiers after elements move or disappear.

Validate schemas by invoking `Schema`, checking response diagnostics, and
calling `ValidateImplementation(ctx)`.

## Diagnostics and Failure State

Framework lifecycle methods report errors and warnings through response
diagnostics. Internal API clients and helpers should continue to return normal
Go `error` values and convert them at the Framework boundary.

For every operation returning diagnostics:

```go
resp.Diagnostics.Append(req.Plan.Get(ctx, &data)...)
if resp.Diagnostics.HasError() {
    return
}
```

- Append diagnostics; do not replace earlier diagnostics.
- Check the response diagnostics before using decoded data or continuing.
- Use attribute diagnostics when the problem belongs to a configuration path.
- Use logging, not diagnostics, for informational and debug output.
- Sanitize error text before exposing it; parser and API errors can quote
  sensitive inputs even when provider code did not format those inputs.

An error diagnostic does not prevent Terraform from persisting response state.
Do not rely on tainting. On failure, deliberately return prior state or state
that accurately records completed remote changes. Avoid constructing partial
state accidentally through incremental `SetAttribute` calls before an
operation's failure behavior is decided.

## Lifecycle Data and Results

| Operation | Decode from | Successful response |
| --- | --- | --- |
| Provider `Configure` | `req.Config` | Configured data or clients |
| Resource `Create` | `req.Plan` | Complete applied state |
| Resource `Read` | `req.State` | Complete refreshed state or removed state |
| Resource `Update` | `req.Plan`, often `req.State` | Complete updated state |
| Resource `Delete` | `req.State` | No error; Framework removes state |
| Data source `Read` | `req.Config` | Complete read-only state |

### Create and Update

Known and null planned values must remain semantically equal in the result.
Only planned unknown values may resolve to different known or null values. If
the API normalizes configured data, account for that during planning or with an
appropriate custom type rather than returning an inconsistent apply result.

Set complete state after successful remote work. Do not blindly call Read as a
shortcut: an eventually consistent API may not yet return the object, and a
read response may omit configuration-only values that must remain in state.
Shared flattening is useful only when it preserves the lifecycle contract.

Use the plan as the desired result in Update and prior state only for change
detection, lookup information, or values the plan intentionally cannot carry.
Follow the API contract: PATCH only changed fields when appropriate, but send a
complete PUT or revision token when the remote API requires it.

### Read

Read receives prior state, not configuration. Refresh every value the API can
authoritatively provide, while preserving values the API cannot reconstruct.
Confirmed remote absence calls `resp.State.RemoveResource(ctx)` and returns
without an error diagnostic. Other errors normally preserve prior state.

Avoid permanent drift from unstable serialization or ordering. Prefer a custom
Framework value type with semantic equality when normalization applies across
planning and refresh. For a narrow API inconsistency, preserving a prior
semantically equivalent representation in Read may be simpler.

### Delete

Treat confirmed absence as success. Do not set response state or call
`RemoveResource`; successful completion causes Framework state removal.

### Data Sources

Data source Read decodes configuration, performs a side-effect-free lookup,
maps all returned values, and sets complete state. Decide and document whether
a singular lookup treats zero or multiple matches as errors; follow existing
provider behavior rather than imposing a universal naming or matching rule.

## Validation and Planning

Use schema and configuration validators for deterministic offline rules.
Validators should normally defer when a needed value is null or unknown. Do
not make remote calls from validators.

Resource planning proceeds in this order on Framework versions with defaults:

1. Apply defaults to attributes with null configuration.
2. When state changes, mark unconfigured computed values unknown.
3. Run attribute plan modifiers.
4. Run resource-level plan modification.

Use `RequiresReplace` for immutable changes. Use `UseStateForUnknown` only when
an unconfigured computed value is genuinely stable across update; otherwise it
can conceal change. Plan modifiers run during create, update, and destroy and
must distinguish those operations when behavior differs.

## State Upgrades

Increment `schema.Schema.Version` only with an intentional persisted-state
migration. Every state upgrader key handles one historical version and must
transform it directly to the current schema; the Framework does not chain
intermediate upgraders or copy omitted values.

An upgrader must:

- Decode using the matching historical schema or raw type.
- Preserve meaning without calling the remote API.
- Populate every current attribute with a known or null value.
- Return diagnostics on unsafe conversion; Terraform retains prior state when
  the upgrade returns an error.
- Have regression coverage using the historical state shape.

## Official References

- https://developer.hashicorp.com/terraform/plugin/framework/handling-data/terraform-concepts
- https://developer.hashicorp.com/terraform/plugin/framework/handling-data/types
- https://developer.hashicorp.com/terraform/plugin/framework/handling-data/writing-state
- https://developer.hashicorp.com/terraform/plugin/framework/handling-data/types/custom
- https://developer.hashicorp.com/terraform/plugin/framework/handling-data/types/custom#semantic-equality
- https://developer.hashicorp.com/terraform/plugin/framework/diagnostics
- https://developer.hashicorp.com/terraform/plugin/framework/resources/create
- https://developer.hashicorp.com/terraform/plugin/framework/resources/read
- https://developer.hashicorp.com/terraform/plugin/framework/resources/update
- https://developer.hashicorp.com/terraform/plugin/framework/resources/delete
- https://developer.hashicorp.com/terraform/plugin/framework/resources/default
- https://developer.hashicorp.com/terraform/plugin/framework/resources/plan-modification
- https://developer.hashicorp.com/terraform/plugin/framework/resources/state-upgrade
