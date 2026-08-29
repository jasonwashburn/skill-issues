# Test Removal Reference

Use this reference to distinguish test-suite waste from independent protection.
Test deletion is a judgment under uncertainty, not a mathematical proof.

## Marginal Protection

A test earns its place through the protection it adds beyond retained tests.
Compare candidates across several dimensions:

| Dimension | Questions |
| --- | --- |
| Behavior | Does it assert a distinct outcome, invariant, error, or state transition? |
| Contract | Does a caller, consumer, protocol, or public promise depend on it? |
| Input | Does it represent a meaningful boundary, equivalence class, or adversarial case? |
| Environment | Does it cover a supported platform, version, locale, configuration, or dependency? |
| Boundary | Does it exercise real wiring or integration absent from narrower tests? |
| Risk | Does it protect security, money, data, compatibility, recovery, or concurrency? |
| History | Did it capture an escaped defect or surprising behavior that remains relevant? |
| Diagnosis | Does it locate failures that broader retained tests would obscure? |
| Independence | Could it catch an error in a shared fake, fixture, helper, or oracle? |

No single dimension or metric decides the result. The relevant question is
whether the protection is meaningful enough to justify its ongoing cost.

## Candidate Signals

High-confidence candidates commonly include:

- identical setup, input, boundary, assertion, environment, and purpose;
- no assertion or an assertion that cannot fail meaningfully;
- permanently unreachable test code;
- behavior deliberately removed from the supported contract;
- an incidental call sequence, private representation, ordering, or formatting
  rule that no consumer relies on;
- generated cases duplicated accidentally rather than representing intentional
  input coverage.

Signals that require investigation include:

- slow or flaky execution;
- elaborate setup or many mocks;
- broad snapshots;
- frequent changes during refactors;
- cases covering the same lines or branches;
- a lower-level test and a broader test of similar behavior;
- a test that has never recorded a failure.

These may indicate a valuable test expressed badly. Prefer replacement or
relaxation when the underlying protection matters.

## Restrictive Assertions

An assertion is overly restrictive when it rejects implementations permitted
by the intended contract. Common examples include exact internal call order,
incidental collection order, unstable timestamps or identifiers, complete
object equality when only part is promised, and snapshots containing unrelated
details.

Before relaxing one, establish what consumers actually rely on. Exact order,
format, timing, and interactions are sometimes the contract. Replace the
assertion with the narrowest statement that still detects a meaningful breach.

## Evidence

Useful evidence can include:

- reading the assertion and relevant production boundary;
- comparing inputs, outcomes, configurations, and test levels;
- checking names, comments, issue references, blame, and commit history;
- deliberately perturbing the protected behavior to see which tests detect it;
- per-test coverage or mutation results when existing tooling makes them cheap.

A passing suite after removal shows compatibility with the retained tests, not
absence of lost protection. Coverage shows execution, not assertion quality.
Mutation testing samples selected synthetic faults and does not cover every
real defect, contract, configuration, or environment.

Require stronger evidence for high-impact behavior, compatibility promises,
rare failures, and tests crossing boundaries that are difficult to reproduce.
When uncertainty remains material, recommend investigation or retention.

## Audit and Removal

Keep the audit separate from deletion. This prevents the desire to simplify the
suite from silently deciding what the product should promise.

After approval, preserve normal version-control reversibility, apply small
batches, and verify the scope affected by the removed evidence. A controlled
removal followed by relevant test runs can now provide additional evidence. If
a candidate is replaced, make the retained intent obvious in the new test's
name and assertion.

## Selected Sources

- Martin Fowler, *Test Coverage*:
  https://martinfowler.com/bliki/TestCoverage.html
- Inozemtseva and Holmes, *Coverage Is Not Strongly Correlated with Test Suite
  Effectiveness*: https://doi.org/10.1145/2568225.2568271
- Harrold, Gupta, and Soffa, *A Methodology for Controlling the Size of a Test
  Suite*: https://doi.org/10.1145/152388.152391
- Wong et al., *Effect of Test Set Minimization on Fault Detection
  Effectiveness*: https://doi.org/10.1145/225014.225018
- Petrovic et al., *Practical Mutation Testing at Scale: A View from Google*:
  https://doi.org/10.1109/TSE.2021.3107634
- Gerard Meszaros, *Test Smells*:
  http://xunitpatterns.com/Test%20Smells.html
