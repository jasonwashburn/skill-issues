---
name: testodian
description: Use when preserving protection while organizing, simplifying, consolidating, stabilizing, or improving existing tests, fixtures, helpers, or suite structure. Not for tests required by new production behavior or for deciding that uncertain protection should be removed.
---

# Testodian

Make useful tests easier to understand, maintain, and run without losing what
they protect. Prefer removing accidental complexity over moving it behind more
test machinery.

## Establish What Must Survive

Before restructuring tests:

- Inspect the tests, affected production behavior, test commands, and repository
  conventions.
- Identify the behavior, contract, risk, configuration, or regression each test
  protects.
- Establish a passing baseline when safe and practical, or explain known
  failures before proceeding.
- Name the concrete maintenance problem: unclear intent, excessive setup,
  duplication, poor isolation, weak diagnostics, flakiness, layout, or runtime.

Before running tests, inspect environment gates and whether they use
credentials, external services, persistent resources, or billable
infrastructure. Run them only when safe and authorized.

Do not infer equivalent protection from similar code, shared coverage, or a
common execution path. Tests at different levels or with different assertions,
environments, boundaries, and histories may provide independent evidence.

## Simplify Locally

- Make the smallest structural change that solves the observed problem.
- Keep important inputs, setup, and expectations visible in each test.
- Extract helpers only when their names and interfaces make intent clearer.
- Prefer focused fixtures over a shared fixture containing irrelevant state.
- Keep related assertions together when they describe one outcome; split tests
  when they protect unrelated behavior or failures are hard to diagnose.
- Follow existing organization and naming unless those conventions are the
  demonstrated problem.
- Do not introduce a framework, dependency, base class, builder hierarchy, or
  suite-wide pattern for a local cleanup.

Test code does not need to be maximally DRY. Repetition is acceptable when it
makes cases independently readable. An abstraction must earn its cost.

## Consolidate Carefully

Consolidate tests only when their protected intent, setup, action, and expected
outcome are genuinely equivalent and the result remains easy to review and
diagnose.

Parameterization is useful for cases that share one clear rule. Keep named
cases separate when they represent distinct boundaries, requirements,
regressions, configurations, or narratives. Do not infer a general property
from a few examples merely to reduce lines of test code.

Exact duplicate tests may be removed during consolidation when they exercise
the same boundary with the same inputs, environment, assertions, and purpose.
This is the only deletion `testodian` performs. If value is uncertain, preserve
the test and hand the decision to `testecutioner`.

## Handle Unreliable Tests Honestly

Treat nondeterminism as something to diagnose, not something to retry until
green. Determine whether the cause is product behavior, shared state, ordering,
time, concurrency, resources, infrastructure, or an external dependency.

Quarantine may protect the main feedback loop, but follow repository policy and
record the protection lost. Do not skip, weaken, delete, or add retries merely
to hide the failure.

## Verify Preservation

- Run focused tests before and after each coherent change when safe and
  practical.
- Run broader checks justified by the scope and repository practice.
- Preserve useful case names and failure messages.
- Confirm snapshots and fixtures still represent intentional behavior.
- Keep cleanup separate from production behavior changes when practical.
- Report what became simpler and what protection was preserved.

Read `references/test-maintenance.md` only when fixture design, consolidation,
flakiness, snapshots, organization, or preservation of test intent needs deeper
reasoning.
