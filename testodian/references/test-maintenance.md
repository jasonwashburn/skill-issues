# Test Maintenance Reference

Use this reference to reason about a maintenance problem without turning it
into a suite rewrite.

## Preserve Meaning, Not Shape

Test maintenance can change names, layout, setup, fixtures, helpers, and
assertion form. It should preserve the ability to detect the failures the suite
intentionally protects.

Before changing structure, record for the affected tests:

- the behavior or contract;
- the meaningful input or state;
- the observable outcome or interaction;
- the environment or configuration;
- the test level and real boundaries crossed;
- any known regression history.

This need not become a document. A brief working understanding is enough for a
small change.

## Readability and Duplication

Optimize tests for the reader diagnosing a failure. A reader should be able to
see why the scenario matters and which values control it without following a
long chain of helpers.

Duplication is harmful when repeated changes drift or obscure a shared concept.
It is useful when it keeps examples complete and independent. Extract shared
code only when the resulting test says more clearly what matters.

A good helper:

- has one obvious purpose;
- uses explicit, meaningful inputs;
- hides irrelevant mechanics rather than important test data;
- produces failures attributable to the calling scenario.

Avoid helpers that contain assertions for unrelated callers, reproduce the
production algorithm, depend on invocation order, or grow a configuration API
larger than the behavior under test.

## Fixtures

Prefer the smallest fixture that makes the scenario realistic. Large shared
fixtures often create hidden dependencies and make tests fail when unrelated
data changes.

Use local setup when it is short and meaningful. Use factories or builders
when defaults remove noise while relevant differences remain explicit. Preserve
realistic integrity constraints; an unrealistically convenient fixture can
make tests pass for states production cannot reach.

## Consolidation

Source similarity is not behavioral equivalence. Before merging cases, compare:

- assertions and failure messages;
- boundary and error conditions;
- supported configurations and platforms;
- prior state and transition history;
- external systems or implementations exercised;
- historical defects represented by the case.

Parameterization should make one rule clearer. If each row requires extensive
conditional setup or a paragraph explaining why it exists, separate tests may
be easier to maintain.

## Flakiness and Runtime

First determine whether an unreliable test is exposing an unreliable product.
Control time, randomness, state, and scheduling only where the product contract
allows that control. Prefer waiting for conditions over arbitrary sleeps.

Slowness is a reason to profile and inspect a test, not proof that it lacks
value. Reduce irrelevant setup, use a narrower boundary when it answers the
same question, or move specialized checks according to repository policy. Keep
enough real integration evidence for the risks involved.

## Snapshots and Historical Tests

A focused snapshot can be a clear assertion when the artifact itself matters.
Keep it reviewable and ensure failures explain a meaningful change. Replace a
broad snapshot when a smaller assertion protects the same intent more clearly.

Historical regression tests are not automatically permanent or redundant.
Preserve them while the failure remains relevant and not clearly protected
elsewhere. Carry a useful name or short explanation forward when consolidating
the mechanics of a historical test.

## Selected Sources

- Google, *Software Engineering at Google*, Unit Testing:
  https://abseil.io/resources/swe-book/html/ch12.html
- Google Testing Blog, *Tests Too DRY? Make Them DAMP!*:
  https://testing.googleblog.com/2019/12/testing-on-toilet-tests-too-dry-make.html
- Gerard Meszaros, *Test Smells*:
  http://xunitpatterns.com/Test%20Smells.html
- Martin Fowler, *Eradicating Non-Determinism in Tests*:
  https://martinfowler.com/articles/nonDeterminism.html
- Luo et al., *An Empirical Analysis of Flaky Tests*:
  https://doi.org/10.1145/2635868.2635920
