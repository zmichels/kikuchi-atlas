# Reflector ridge/bands globe series

Accepted on 2026-07-18 and rebalanced on 2026-07-20 as a print-oriented series
of raised reflector-band globes. These products intentionally exclude the
intensity-relief globe path.

All listed STLs were validated by the repo mesh validator as watertight,
single-body, outward raised-ridge meshes.

| Phase | Source | Selected ridges | STL | SHA-256 |
| --- | --- | ---: | --- | --- |
| Ice Ih oxygen sublattice | COD-1572233 derivative | 15 | `local/ice-reflector-globes/reflector-ridge-globe-build-f07f822ff336b13e/ice-ih-reflector-ridges.stl` | `42a4b9dc7a779245a5f35cb5755988481ed1a689a84042427458049cbeb43a2d` |
| Quartz | COD-9000775 | 16 | `local/reflector-ridge-series/quartz/reflector-ridge-globe-build-5631d275ba61abb6/quartz-reflector-ridges.stl` | `87671bc4a47f7408fc947f656e07649c6b9b20ada0cb74fd8475127fdb31be52` |
| Forsterite | COD-9000319 | 17 | `local/reflector-ridge-series/forsterite/reflector-ridge-globe-build-1c2dad85f3d06ae1/forsterite-reflector-ridges.stl` | `a0bdfa05a42350558203323ec498c583326f8a5e615299f8af6847c20e346b61` |
| Titanite | COD-9000509 | 16 | `local/reflector-ridge-series/titanite/reflector-ridge-globe-build-a786a35bbb9f57db/titanite-reflector-ridges.stl` | `0b390ae8c733ecc36b41cc6a1f3d2a9371d160fff1940e00804df719eccba980` |
| Zircon | COD-9000685 | 15 | `local/reflector-ridge-series/zircon/reflector-ridge-globe-build-d050d0e211300849/zircon-reflector-ridges.stl` | `c293598686b1c7a8a615983ed66e097407b900a4cfa86f74a026963f296c429e` |
| Diamond | COD-2101499 derivative | 7 | `local/reflector-ridge-series/diamond/reflector-ridge-globe-build-368e3cf8d2cf2bbe/diamond-reflector-ridges.stl` | `c9071c18c5ed41414585ba592dc387d6d1b6625696963174e71ce8f6edb7c269` |

## Claim boundary

The Ice Ih product keeps the stricter previously accepted oxygen-sublattice
canonical-catalog authentication.

Quartz, titanite, zircon, and diamond use tracked COD CIF records with explicit
fallback `U_iso` values because their selected CIFs do not report
`_atom_site_U_iso_or_equiv`. These are deterministic printable reflector-band
designs, not refined EBSD intensity simulations.

The primary Atlas Titanite globe is rebuilt from its tracked room-temperature
`COD-9000509` source and retains 16 strong, integer-HKL reflector families.
Diamond retains its two intact cubic symmetry blocks (seven families) rather
than splitting tied members merely to make a denser globe.
