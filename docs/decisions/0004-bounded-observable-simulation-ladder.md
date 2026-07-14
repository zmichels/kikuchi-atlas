# ADR 0004: Replace Opaque Production Solves with a Bounded Simulation Ladder

- Status: Accepted
- Date: 2026-07-13
- Work item: [KIKU-T011](../work/KIKU-T011.md)
- Superseded execution: `forsterite-production-master` single-shot attempt
- Active experiment: [forsterite-resolution-501.yml](../../recipes/benchmarks/forsterite-resolution-501.yml)

## Context

The first M2 production attempt combined a 501 x 501 Lambert raster, `dmin =
0.05 nm`, Smith rank 20, and up to twenty 1 keV energy bins. It was interrupted
after at least 5 h 29 min without completing its first bin or publishing an
artifact. The transactional bundle correctly removed the incomplete staging
tree, but verbosity zero and the lack of a durable progress journal made a very
large finite solve look indistinguishable from a stalled process.

Runtime diagnosis found active Metal command submission and completion, GPU
utilization near 99%, no Metal recovery, and finite loops. Exact CPU-only
preflight counts explain the elapsed time:

| Control | Proof | Attempted production | Ratio |
| --- | ---: | ---: | ---: |
| Fundamental-sector directions | 17,003 | 63,701 | 3.746 |
| Reflections | 2,361 | 9,773 | 4.139 |
| Smith rank | 8 | 20 | 2.500 |
| Maximum energy bins | 1 | 20 | 20.000 |

The first-order per-bin proxy `n_k * n_reflections * rank` is 38.77 times the
proof. Scaling the measured 532.774 s proof gives about 5.74 h for one
production bin, closely matching the interrupted run. Relative-image stopping
cannot occur before two active bins, so the plausible lower bound was about
11.5 h and the twenty-bin upper estimate about 115 h.

## Decision

Production-source development proceeds as a sequence of one-variable,
one-energy-bin benchmark rungs. Every rung must:

1. pass CPU-only planning before a GPU device is created;
2. report exact grid, direction, reflection, chunk, rank, and maximum-bin
   bounds;
3. set ebsdsim verbosity 2 and write a persistent progress journal outside the
   transactional bundle;
4. publish only a complete atomic bundle; and
5. receive diagnostic or visual review before the next expensive control is
   promoted.

The initial rung changes only Lambert resolution from 257 x 257 to 501 x 501.
It deliberately retains the proof's `dmin = 0.08 nm`, rank 8, one 20 keV bin,
and Monte Carlo controls. Its exact plan is 63,701 directions, 2,361
reflections, and 7,963 chunks.

`kikuchi-lab simulate-master --plan-only` is the non-GPU planning interface.
The CLI refuses recipes with more than one possible energy bin unless the
caller supplies `--allow-multi-bin`. That opt-in does not imply resumability.

## Checkpoint and cancellation semantics

ebsdsim 0.1.8 does not expose a public resumable partial-bin or partial-run
artifact. The current scientifically honest checkpoint is therefore one
complete single-bin rung, not an invented partial master pattern. Failed or
interrupted runs retain their progress journal and remove their unpublished
staging bundle. Multi-bin checkpoint/resume requires an upstream ebsdsim
contract or an explicitly versioned companion implementation and remains
future work.

## Ladder state

| State | Experiment | Changed control | Promotion gate |
| --- | --- | --- | --- |
| accepted baseline | proof 257 | none | Existing proof and selected orientation |
| completed; review pending | resolution 501 | `halfw: 128 -> 250` | Runtime evidence complete; user visual review pending |
| proposed | reflection depth | `dmin: 0.08 -> 0.05 nm` | Resolution rung shows a supported visual/scientific need |
| proposed | solver rank | `rank: 8 -> 20` | Reflection-depth comparison justifies added dynamical cost |
| deferred | multi-energy integration | bin width and coverage | Public checkpoint/resume or explicit long-run approval |

## Consequences

- A slow run is distinguishable from a frozen run by durable chunk counters and
  rates.
- Expensive controls are evaluated for marginal benefit instead of multiplied
  blindly.
- The original production recipe remains a documented scientific target but is
  guarded against accidental launch.
- The current ladder checkpoints completed experiments; it does not claim
  resumability that the upstream engine cannot provide.
