# Requested mineral phase expansion

Date reviewed: 2026-07-25

This intake resolves mineral-group language to exact structure records before
publication. A COD entry listed as a candidate is not yet an Atlas phase; it
must still pass checksum, site/occupancy, setting, thermal-factor, direct
reflector parity, and full product-build review.

## Existing requested coverage

| Requested mineral or group | Retained Atlas reference | Scope |
| --- | --- | --- |
| Quartz | `quartz` | Right-handed ambient alpha quartz |
| Plagioclase | `plagioclase-an52` | One An52 composition, not all plagioclase |
| Olivine | `forsterite` | Mg endmember, not the full olivine solid solution |
| Pyroxene | `diopside` | Ambient clinopyroxene reference |
| Mica | `muscovite-2m1` | One measured 2M1 natural composition |
| Calcite | `calcite` | New 295 K R-3c reference, COD 1547350 |
| Enstatite | `enstatite` | New 0 GPa MgSiO3 orthoenstatite reference, COD 9001593 |
| Pyrope | `pyrope` | New 298.15 K pure Mg garnet endmember, COD 9000435 |

No existing phase or product is replaced by this expansion.

## Located candidates for missing minerals

| Requested mineral | COD candidate | Exact candidate scope | Intake state |
| --- | --- | --- | --- |
| K-feldspar | [9000311](https://www.crystallography.net/cod/9000311.html) | Ordered orthoclase, KAlSi3O8, C2/m | Candidate; source omits Uiso and needs a declared fallback or derived-ADP decision |
| Augite | [1000035](https://www.crystallography.net/cod/1000035.html) | Measured multication augite, not an ideal endmember | Candidate; composition and missing-Uiso policy require review |
| Hornblende | [1530336](https://www.crystallography.net/cod/1530336.html) | One measured multication hornblende | Candidate; exact natural composition must remain in the display name and scope |
| Tremolite | [2108838](https://www.crystallography.net/cod/2108838.html) | 293 K refined tremolite-family composition, C2/m | Preferred candidate; explicit Uiso is present |
| Biotite | [1000038](https://www.crystallography.net/cod/1000038.html) | One 1M plutonic biotite composition | Candidate; source omits Uiso and “biotite” cannot be represented as a generic formula |
| Almandine | [1531283](https://www.crystallography.net/cod/1531283.html) | Fe3Al2Si3O12, Ia-3d | Preferred candidate; explicit Uiso is present |
| Grossular | [9000439](https://www.crystallography.net/cod/9000439.html) | Ca3Al2Si3O12 at 25 C, Ia-3d | Preferred candidate; explicit Uiso is present |
| Dolomite | [1200014](https://www.crystallography.net/cod/1200014.html) | CaMg(CO3)2, R-3 | Candidate; source omits Uiso |
| Magnetite | [2101535](https://www.crystallography.net/cod/2101535.html) | Cubic Fe3O4 above the Verwey transition | Candidate; temperature selection, origin choice, and missing-Uiso policy require review |
| Hematite | [2101167](https://www.crystallography.net/cod/2101167.html) | Alpha-Fe2O3, R-3c | Candidate; source omits Uiso |
| Chalcopyrite | [1010940](https://www.crystallography.net/cod/1010940.html) | Tetragonal CuFeS2, I-42d | Candidate; source omits Uiso |

## Promotion order

The next low-ambiguity source promotions should be grossular, almandine, and
tremolite because the located records combine an
explicit mineral/composition identity with reported isotropic-equivalent
thermal factors. Natural solid-solution labels (augite, hornblende, biotite)
need exact-composition display names. Records without Uiso remain blocked on a
documented fallback or defensible anisotropic-to-isotropic derivation; they
must not silently inherit another mineral's displacement parameters.

The Crystallography Open Database search and retrieval interfaces are the
source-discovery boundary. COD data are CC0, while the original structural-data
authors remain cited in each promoted `phases/<slug>/source.yml`.
