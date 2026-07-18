# Task 2 report: phase-neutral reflector evidence and strict recipes

## Changed files

- `src/kikuchi_lab/reflectors/__init__.py`: public reflector-contract exports.
- `src/kikuchi_lab/reflectors/contracts.py`: frozen `ReflectorMember` and
  `ReflectorCatalog` contracts, validation, owned immutable little-endian
  `float64` normals, and content-derived identities.
- `src/kikuchi_lab/reflectors/recipe.py`: frozen `ReflectorRecipe` and strict,
  closed-schema YAML loader.
- `recipes/reflectors/ice-ih-catalog.yml`: tracked Ice Ih selection recipe.
- `tests/unit/test_reflector_contracts.py`: member and catalog contract tests.
- `tests/unit/test_reflector_recipe.py`: tracked recipe and rejection tests.

## Red

Command:

```console
uv run pytest tests/unit/test_reflector_contracts.py tests/unit/test_reflector_recipe.py -q
```

Output: failed during collection exactly as expected with
`ModuleNotFoundError: No module named 'kikuchi_lab.reflectors'` for both new
test modules (`2 errors in 0.10s`).

## Green

Command:

```console
uv run pytest tests/unit/test_reflector_contracts.py tests/unit/test_reflector_recipe.py -q && uv run ruff check src/kikuchi_lab/reflectors tests/unit/test_reflector_contracts.py tests/unit/test_reflector_recipe.py
```

Output:

```text
..........                                                               [100%]
10 passed in 0.09s
All checks passed!
```

`git diff --check` also completed cleanly before commit.

## Commit

`9cbee027eb142d5e833bc8ad1374577dbc9b48ce`
(`feat: define reflector evidence contracts`)

## Self-review

- The member normal is copied into an owned, read-only `<f8` array before the
  identity is created; callers cannot mutate it through either the input array
  or the public field.
- Member, catalog, and recipe identities are canonical-content-derived. The
  loader's local input path is never included; the recipe records only its
  explicit project-relative source reference.
- The loader has a closed key set and rejects absolute/traversing source paths,
  nonpositive physical values, a non-approved Ice threshold, wrong tie policy,
  and a cohort count other than four.
- No adapter, catalog-building, bundle, kinematical, mesh, or globe behavior
  was added.

## Concerns

No blocking concerns. `ReflectorCatalog.selection` is deliberately a frozen
plain mapping because this task specifies it without a further schema; later
selection/cohort work can populate that contract without introducing
upstream-library objects or local filesystem paths.

---

## Review-fix follow-up

### Fixed findings

- `ReflectorMember.normal_crystal` is now rebuilt over immutable `bytes` after
  validation, rather than relying only on NumPy's reversible read-only flag.
  A caller's `setflags(write=True)` attempt now raises `ValueError`; the
  regression test also confirms both the vector and its content-derived member
  identity remain unchanged.
- Recipe loading now uses a `yaml.SafeLoader` subclass with a mapping
  constructor that detects a repeated key before closed-schema or value
  validation. This rejects duplicate `schema_version`, duplicate
  `eligibility_min_weight`, and duplicates in any YAML mapping loaded by the
  strict recipe loader.
- Recipe scalar checks now use exact built-in scalar types: `schema_version`
  and `cohort_count` require non-bool `int`; energy, spacing, and eligibility
  threshold require non-bool built-in `int` or `float`. Quoted numeric YAML
  scalars, floating integer fields, and booleans are rejected.

### Regression evidence

The new tests were run before the implementation change and failed for the
reviewed gaps: writable-flag re-enablement succeeded, duplicate YAML keys were
accepted or reached later validation, and `1.0` / `4.0` values for integer
fields plus a quoted threshold were coerced or accepted.

Final verification:

```console
uv run pytest tests/unit/test_reflector_contracts.py tests/unit/test_reflector_recipe.py -q
.........................                                                [100%]
25 passed in 0.10s

uv run ruff check src/kikuchi_lab/reflectors tests/unit/test_reflector_contracts.py tests/unit/test_reflector_recipe.py
All checks passed!
```

`git diff --check` completed cleanly. Self-review confirmed the immutable
normal has a `bytes` backing buffer, the duplicate-key check runs in the safe
loader before `ReflectorRecipe`, and scalar validation does not rely on Python
numeric coercion.
