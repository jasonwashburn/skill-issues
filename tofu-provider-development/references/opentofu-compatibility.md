# OpenTofu and Terraform Compatibility Reference

Use this reference when a provider supports OpenTofu, Terraform, or both.
Provider implementation idioms generally come from the Plugin Framework and
provider protocol; cross-CLI concerns are Core features, protocol revisions,
source identity, installation, distribution, and behavioral testing.

## Separate the Compatibility Layers

Do not use “supports protocol v6” as a complete compatibility claim. Establish
four independent facts:

1. The protocol major served by the provider binary, normally v5 or v6.
2. The protocol revision and optional RPC features implemented or required by
   its Framework and protocol dependencies, represented according to each
   target registry's metadata contract.
3. The minimum CLI/Core version implementing every provider feature used.
4. The provider source address and distribution path used by each CLI.

A provider binary and CLI must negotiate a common protocol major, but a
successful handshake does not prove that Core understands every RPC or feature,
or that planning and lifecycle behavior is identical.

HashiCorp documents protocol v5 for Terraform 0.12+ and protocol v6 for
Terraform 1.0+. OpenTofu 1.6.0, its first release, contains clients and tagged
definitions for both protocol majors, including v6.4. OpenTofu's v1
compatibility promise explicitly protects protocol v5 throughout v1.x; it does
not make the same blanket promise for every later protocol revision or feature.

Use the target release's tagged protocol definitions and implementation when
the compatibility prose and source describe different baselines. Record the
evidence rather than generalizing beyond the tested versions.

## Build a Feature-Aware Support Matrix

Before adopting or reviewing a Framework capability, record:

- Provider, Go, Framework, and protocol dependency versions.
- Served protocol major, relevant protocol revision, and each registry's
  advertised protocol metadata.
- Minimum and tested Terraform CLI versions.
- Minimum and tested OpenTofu CLI versions.
- Core-dependent features used by the provider.
- Supported operating systems and architectures.
- Provider address and registry or mirror for each distribution path.

For each CLI family, test the declared minimum, each higher feature-specific
minimum that the provider relies on, and a representative current stable
release. Use behavioral acceptance or integration coverage; protocol
negotiation alone is insufficient.

Provider-defined functions illustrate the distinction. OpenTofu supports them
from 1.7.0 using protocol 5.5 or 6.5, while Terraform supports provider-defined
functions from 1.8. A provider serving protocol v5 can therefore use functions,
but not with a CLI that implements only earlier v5 revisions.

Functions, ephemeral resources, write-only arguments, actions, list resources,
identities, state stores, and other newer capabilities have independent
Framework, protocol-minor, and Core requirements. Verify the exact target
Terraform and OpenTofu releases before using them. Compilation proves only the
provider side is available.

## Provider Source Addresses Are Identity

A provider source address is:

```text
hostname/namespace/type
```

When the hostname is omitted, the defaults differ:

- Terraform uses `registry.terraform.io`.
- OpenTofu uses `registry.opentofu.org`.

Therefore `namespace/type` can resolve to different full identities in the two
CLIs. Use an explicit address where cross-registry identity would otherwise be
ambiguous.

Publishing the same binary under another hostname or namespace creates a
different provider identity. Existing modules and state do not automatically
treat it as the original provider. To distribute an existing identity through
another location, use a filesystem or network mirror rather than changing the
address.

Keep provider server options, user examples, tests, release automation, and
registry metadata coherent with the intended full address.

## Publishing Is Registry-Specific

Publishing to Terraform Registry does not publish to OpenTofu Registry, or the
reverse. Each registry or private distribution path has independent discovery,
metadata, checksum, signature, and platform requirements.

Terraform Registry documentation says Framework providers normally declare
`["6.0"]` in `terraform-registry-manifest.json`, unless explicitly serving
protocol v5. OpenTofu's registry protocol represents each supported major with
the highest supported minor, such as `"5.5"` or `"6.5"`. Follow the target
registry's contract; do not copy one registry's metadata mechanically into the
other.

Do not replace an already-published package. Registries, mirrors, and dependency
lock files depend on stable checksums.

## Compatibility Decision Procedure

When a change may affect compatibility:

1. Read the repository's current support policy and test matrix.
2. Identify the production server protocol and pinned Framework/protocol
   versions.
3. List every newly used Core-dependent capability.
4. Find each capability's minimum Terraform and OpenTofu versions separately.
5. Check source addresses and registry metadata for both distribution paths.
6. Run representative behavior against the claimed minimums and current
   releases, or state clearly which combinations remain unverified.
7. Update documentation, CI matrices, protocol metadata, and release policy
   together when the supported contract changes.

## Safe Claims

The skill may state:

- OpenTofu 1.6+ and Terraform can run compatible Plugin Framework protocol v5
  or v6 providers, subject to the provider's served major and feature needs.
- OpenTofu's v1 compatibility promise protects protocol v5, while v6 and newer
  minor features still require target-version verification.
- Terraform and OpenTofu behavior should be tested separately when both are in
  the support policy.
- Registry publication and source identity are separate from runtime protocol
  compatibility.

Avoid claims that:

- The Terraform Plugin Framework is officially supported or endorsed by the
  OpenTofu project.
- Every Framework provider or feature works with every release of either CLI.
- Protocol v6 is unsupported by OpenTofu.
- Protocol-major compatibility proves support for newer provider features.
- Publishing to one registry automatically publishes to the other.
- A shortened source address identifies the same origin in both CLIs.

## Official Sources

- https://developer.hashicorp.com/terraform/plugin/terraform-plugin-protocol
- https://developer.hashicorp.com/terraform/plugin/framework/provider-servers
- https://developer.hashicorp.com/terraform/plugin/framework/functions
- https://developer.hashicorp.com/terraform/language/providers/requirements
- https://developer.hashicorp.com/terraform/registry/providers/publishing
- https://opentofu.org/docs/language/v1-compatibility-promises/#provider-protocol-versions
- https://opentofu.org/docs/language/functions/#provider-defined-functions
- https://opentofu.org/docs/language/providers/requirements/
- https://opentofu.org/docs/internals/provider-registry-protocol/
- https://github.com/opentofu/opentofu/tree/v1.6.0/docs/plugin-protocol
- https://github.com/opentofu/opentofu/blob/v1.6.0/internal/plugin6/grpc_provider.go
