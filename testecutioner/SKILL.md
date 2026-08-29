---
name: testecutioner
description: Use ONLY when explicitly auditing, challenging, pruning, weakening, or removing existing tests whose protection may be unnecessary, obsolete, redundant, or overly restrictive. Produces an evidence-based audit before changes; not for production-change coverage or protection-preserving maintenance.
---

# Testecutioner

Find tests whose cost is no longer justified by distinct protection. Be
skeptical of waste and equally skeptical of easy deletion arguments.

This is an audit-first skill. Present recommendations and wait for the user's
approval before deleting, weakening, replacing, or consolidating any test, even
when a candidate appears obvious. An approved follow-up may apply changes in
small verified batches.

## Establish the Baseline

- Inspect the repository's test structure, commands, environment gates, and
  conventions.
- Run an appropriate baseline when safe and practical.
- Explain existing failures rather than treating them as deletion candidates.
- Choose a bounded audit scope; do not inventory the entire repository unless
  requested.

## Ask What Each Test Protects

For each candidate, ask:

> What distinct behavior, risk, configuration, contract, or known failure would
> become unprotected without this test?

Consider:

- the outcome and assertion, not only code executed;
- boundary values, errors, state transitions, and absence of side effects;
- supported platforms, versions, feature flags, and environments;
- unit, integration, contract, and end-to-end evidence at different boundaries;
- security, compatibility, data integrity, concurrency, and other high-impact
  risks;
- regression history and useful failure diagnosis;
- independence from shared fixtures, doubles, or test helpers.

Inspect history when the purpose, contract, or regression value is unclear or
the risk of removal is material. Do not require history work for an obvious,
low-risk duplicate.

## Classify Before Recommending

Recommend one of:

- **Remove:** no meaningful unique protection remains.
- **Replace or relax:** the behavior matters, but the current assertion or test
  boundary is unnecessarily restrictive, brittle, or expensive.
- **Consolidate:** equivalent protection can be expressed more clearly without
  losing case identity or diagnosis.
- **Retain:** the test provides distinct or prudent independent evidence.
- **Investigate:** intent or risk is too uncertain for a safe recommendation.

Strong removal candidates include exact duplicates, vacuous tests, tests for a
confirmed obsolete contract, unreachable tests, and assertions whose only
effect is to freeze an incidental implementation choice.

Slowness, flakiness, age, complexity, frequent maintenance, overlapping
coverage, similar code paths, or never having failed are reasons to investigate,
not reasons to delete by themselves. Coverage and mutation testing can provide
supporting evidence; neither proves semantic redundancy.

## Keep the Audit Useful

For each recommendation, report concisely:

- the test and location;
- what it currently protects;
- the proposed disposition and why;
- the retained or replacement protection;
- material uncertainty or risk.

Do not create an audit file, scorecard, matrix, or new tooling unless requested.
Keep candidate lists in the response and prioritize meaningful savings over a
large count of findings.

## Apply Approved Removals

After approval:

- Remove or replace candidates in small, reviewable batches.
- Avoid unrelated production changes and broad test reorganization.
- Run focused tests, then broader checks justified by the removed protection.
- When replacing a test, confirm the replacement detects the intended failure
  when practical.
- Report what protection was removed, what remains, and what was not verified.

Read `references/test-removal.md` before a nontrivial audit or when redundancy,
historical value, restrictive assertions, risk, or deletion evidence is
uncertain.
