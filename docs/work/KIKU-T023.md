---
id: KIKU-T023
type: task
title: Run bounded MTEX density validation
status: ready
parent: KIKU-F003
created: 2026-07-13
priority: P1
tags: [subprocess, timeout, heartbeat, mtex, tdd]
evidence:
  - ../superpowers/plans/2026-07-13-spherical-intensity-and-mtex-density-bridge.md
---

# KIKU-T023: Run bounded MTEX density validation

## Description

Discover the explicit MATLAB/MTEX runtime and run one observable subprocess
with immutable wall-clock limits, retained diagnostics, and validated outputs.

## Acceptance Criteria

- [ ] Synthetic process tests prove heartbeat capture, timeout, termination, and retained logs in under one second.
- [ ] Runtime discovery validates the executable, `startup_mtex.m`, and exact `mtex-6.1.1` version file.
- [ ] One explicitly enabled smoke run passes in at most `300` seconds without retry or timeout widening.
