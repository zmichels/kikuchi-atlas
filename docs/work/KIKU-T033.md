---
id: KIKU-T033
type: task
title: Build deterministic geodesic topology
status: ready
parent: KIKU-F005
created: '2026-07-17'
priority: P1
tags:
- relief
- topology
- icosphere
evidence:
- ../superpowers/plans/2026-07-17-spherical-intensity-relief-globe.md
---

# KIKU-T033: Build deterministic geodesic topology

## Description

Build a project-owned deterministic icosphere by fixed seed ordering and sorted
edge subdivision, preserving immutable directions, outward faces, and a stable
topology identity.

## Acceptance Criteria

- [ ] Subdivision counts follow `V=10*4^s+2` and `F=20*4^s`, including exactly `163842` vertices and `327680` triangles at subdivision `7`.
- [ ] Every direction is finite and unit length, every face is unique and outward, every edge has incidence two, and Euler characteristic is `2`.
- [ ] Repeated builds produce byte-identical arrays and topology IDs without relying on Trimesh generation or repair.
