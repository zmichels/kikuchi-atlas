# Adaptive Simulation and Evidence Budget

- Status: Incubating
- Boundary: a future cost-aware experiment planner, not a hidden policy inside
  a fixed baseline or a replacement for deterministic dictionary indexing

## Motivation

Some prospective work is expensive: dynamical simulations across phase,
energy, detector geometry, and orientation; local detector refinement; and
targeted acquired-data collection. A contextual multi-armed-bandit style
policy could eventually decide which *next* candidate family earns a limited
simulation or acquisition budget, using a declared reward such as reduction in
held-out ambiguity or calibrated geometry error. This is an adaptive
allocation problem, not a shortcut to scientific truth.

## Current evidence

- The Ni source-bound pack has a deliberately fixed recipe and seven-pattern
  Hough result ([KIKU-F028](../work/KIKU-F028.md)); it supplies no valid online
  reward loop and must remain deterministic for comparison.
- The Ice Ih virtual-camera work exposes named detector geometry candidates and
  coverage masks ([KIKU-F026](../work/KIKU-F026.md)), a possible future arm
  family once acquired observations and held-out truth exist.
- Simulation-work diagnostics already make computational effort visible, but
  do not yet model utility, uncertainty, or adaptive allocation.

## Dependencies

- A frozen baseline dictionary or simulation grid and a declared held-out
  observation set, so adaptive results can be compared without selection bias.
- A scientifically defensible reward: for example, held-out top-k ambiguity,
  calibrated geometry error, or explicit value of information—not a visually
  appealing result or an in-sample score alone.
- Logged arm definitions, context/features, exploration policy, random seed,
  allocation history, stopping rule, cost, and both adaptive and fixed-budget
  comparison results.
- A decision on whether contextual bandits, Bayesian optimization, or ordinary
  active learning best match the continuous orientation/geometry space.

## Unresolved questions

- What unit should be an arm: a phase, local orientation cell, detector model,
  preprocessing recipe, or acquisition setting?
- How should phase imbalance and rare-but-important ambiguity be weighted
  without allowing the policy to hide poor cases?
- Can a policy allocate local refinement effort while retaining a fair,
  reproducible global dictionary benchmark?

## Linked decisions and experiments

- [Open Kikuchi Reference Pack](open-reference-pack.md) provides the first
  acquired-data provenance boundary.
- [Detector and acquisition model](detector-acquisition-model.md) contains the
  geometry variables a later planner might allocate.
- [KIKU-F029](../work/KIKU-F029.md) releases the first lightweight source and
  checksum contract; it is a prerequisite, not an adaptive-policy experiment.

## Promotion trigger

Promote when two or more costly candidate families compete under a fixed
budget, a held-out reward and a fixed-grid baseline are retained, and an
adaptive allocation can be tested without changing the reference-pack claim
boundary.

## Present non-goals

- Randomizing the Ni v0.1 verification or baseline runner.
- Adapting per pattern and then presenting selected in-sample scores as a fair
  benchmark.
- Replacing canonical dictionaries, reproducible recipes, or detector
  calibration with an opaque learned policy.
- Deploying online detector control or data acquisition.
