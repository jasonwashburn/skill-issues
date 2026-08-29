# Test Design Reference

Use this reference when the right test is not obvious. These are decision aids,
not universal rules. Repository conventions and the risk of the behavior still
matter.

## Start With the Protection

Complete this sentence before adding a test:

> Without this test, a change could break ___ without the relevant suite
> detecting it.

A useful answer names observable behavior, a contract, an important boundary,
a supported configuration, a risk, or a failure that has occurred before. A
description of a method, branch, or line is not enough by itself.

Prioritize cases that represent:

- ordinary intended behavior;
- meaningful boundaries or equivalence classes;
- invalid input or failure behavior that callers rely on;
- state transitions and externally visible side effects;
- compatibility or integration assumptions;
- regressions that escaped earlier protection.

Do not enumerate every combination by default. Add another case when it can
detect a materially different defect or protect a distinct obligation.

## Choose the Boundary

Choose the least expensive boundary that can answer the testing question with
credible fidelity.

- Focused tests are useful for deterministic rules and precise diagnosis.
- Tests of cooperating components are useful when their wiring or shared
  behavior is the risk.
- Integration and contract tests are useful when serialization, persistence,
  configuration, protocols, or real dependency behavior is the risk.
- End-to-end tests are useful for selected journeys that cannot be established
  convincingly at narrower boundaries.

Language visibility does not define a testing boundary. Prefer stable seams,
but a meaningful internal abstraction may deserve direct tests when broader
tests would be obscure, costly, or combinatorial. Conversely, a public function
does not automatically need a dedicated test when consumers already protect
its behavior.

## Assertions and Representations

Assert the part of the result that expresses the behavior. Multiple assertions
are reasonable when together they describe one outcome.

Exact order, text, serialization, call count, or timing is appropriate only
when consumers depend on it. Otherwise, assert the meaningful property and
leave implementation choices free.

Snapshots and golden files are useful when the complete artifact is itself a
reviewable output, such as generated code, a protocol document, a migration, or
a user-visible rendering. Keep them focused, inspect their diffs, and never
accept an update solely because output changed.

## Doubles

Prefer a real collaborator when it is inexpensive, deterministic, and faithful.
Use a double deliberately:

- a stub supplies controlled input;
- a fake provides a lightweight working implementation;
- a mock observes an interaction that matters to the contract.

Double a boundary to control failure, time, randomness, cost, or unavailable
systems. Retain suitable integration evidence where correctness depends on the
real boundary. Avoid detailed interaction scripts that merely mirror current
production steps.

## Changes and Failures

Use the intent of the production change to interpret a failed test:

| Change | Normal response |
| --- | --- |
| Refactor | Preserve behavior; diagnose a regression or brittle setup/assertion. |
| New behavior | Add only the protection the new behavior needs. |
| Intentional behavior change | Revise tests that genuinely specify the old contract. |
| Bug fix | Reproduce the failure with a regression test when practical. |
| Legacy change | Characterize uncertain behavior, then decide what should remain contractual. |

Coverage can identify code that tests did not execute. It cannot establish that
executed behavior is asserted well. Mutation testing, property-based testing,
fuzzing, and metamorphic testing can provide useful evidence for suitable code,
but do not introduce them merely to satisfy a general methodology.

## Selected Sources

These sources inform the defaults above; they do not make them universal:

- Google, *Software Engineering at Google*, Unit Testing:
  https://abseil.io/resources/swe-book/html/ch12.html
- Google, *Software Engineering at Google*, Test Doubles:
  https://abseil.io/resources/swe-book/html/ch13.html
- Martin Fowler, *Mocks Aren't Stubs*:
  https://martinfowler.com/articles/mocksArentStubs.html
- Gerard Meszaros, *xUnit Test Patterns*:
  http://xunitpatterns.com/
- Michael Feathers, *Working Effectively with Legacy Code*:
  https://www.informit.com/store/working-effectively-with-legacy-code-9780131177055
- Inozemtseva and Holmes, *Coverage Is Not Strongly Correlated with Test Suite
  Effectiveness*: https://doi.org/10.1145/2568225.2568271
