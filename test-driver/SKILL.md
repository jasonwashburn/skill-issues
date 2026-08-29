---
name: test-driver
description: Use when writing, modifying, or reviewing tests directly required by feature work, bug fixes, production refactoring, or other normal development. Guides the smallest useful behavioral coverage; not for protection-preserving suite maintenance or pruning existing tests.
---

# Test Driver

Add the smallest clear test protection that the change needs. Treat tests as
maintained code, not as proof of effort. Prefer explicit behavior and ordinary
repository patterns over new helpers, frameworks, or exhaustive case lists.

## Understand the Change

Before changing tests:

- Inspect the affected behavior, nearby tests, test commands, and repository
  conventions.
- State what behavior or contract is intended to change, remain unchanged, or
  be restored.
- Check whether an existing test already protects it.
- Identify the realistic failure the proposed test should detect.

Before running tests, inspect environment gates and whether they use
credentials, external services, persistent resources, or billable
infrastructure. Run them only when safe and authorized.

A test should protect a distinct behavior, boundary, risk, configuration, or
known failure. Do not add one merely for a method, branch, line, or coverage
percentage. No new test is a valid outcome when existing tests provide the
needed protection or the change has no meaningful behavioral effect.

## Test Stable Behavior

- Exercise the narrowest stable boundary that provides useful confidence.
- Assert relevant outputs, state, errors, or externally meaningful effects.
- Verify interactions only when the interaction itself is part of the contract.
- Avoid private structure, exact call order, incidental formatting, unstable
  metadata, or complete snapshots unless they are intentionally contractual.
- Prefer a few representative cases with distinct meaning over speculative
  combinations.
- Keep important setup, inputs, and expectations visible. Extract a helper only
  when it makes the behavior easier to understand.
- Some test duplication is better than an abstraction that hides intent.

Use real collaborators when they are fast and deterministic. Introduce a stub,
fake, or mock when it gives necessary control, failure injection, isolation, or
observation. Do not recreate production logic in a test double or in the code
that calculates an expected value.

## Treat Existing Failures as Evidence

When production work causes an existing test to fail, classify the failure
before editing either side:

- The implementation broke behavior that should remain stable.
- The intended contract changed and the old expectation is no longer correct.
- The test depends on an incidental implementation detail.
- The test was already invalid or obsolete.
- The failure is environmental or nondeterministic.

Do not change an expected value, mock, snapshot, skip, or retry merely because
the new implementation fails the old test. A refactor should normally preserve
behavioral assertions, although non-contractual setup may reasonably change.

For a bug fix, add a regression test that demonstrates the defect before the
fix when practical. Preserve an existing characterization test until the
captured behavior has been classified as required, erroneous, or safely
replaced.

## Verify and Stop

- When safe and practical, run the narrowest relevant test first, then broader
  checks justified by the change and repository practice.
- Confirm a new test fails for the intended reason when practical, not because
  setup is broken.
- Keep tests deterministic and failures easy to interpret.
- Report the behavior protected and any material verification not run.
- Do not expand into unrelated cleanup, test infrastructure, or documentation.

Read `references/test-design.md` only when test boundaries, doubles, case
selection, snapshots, characterization, or a disputed test change need deeper
reasoning.
