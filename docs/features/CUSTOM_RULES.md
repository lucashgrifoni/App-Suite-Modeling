# Custom rules — organisation heuristics without forking the engine

Every organisation has threat-modelling rules the generic engine cannot know: an internal
standard, a control your platform team mandates, a lesson from an incident. Custom rules let
you add those as **data**, alongside the engine, in your own repository.

```bash
otm analyze threat-model.otm.yaml --rules org-rules.yaml
```

The flag is additive and opt-in. Without it nothing changes; with it, your rules run **after**
the engine and add threats to the same result, the same JSON, the same SARIF, and the same
CI gate.

---

## Rules are data, not code

There is no expression language, no regex, no callbacks, and nothing is executed. A rule
declares what to look for and what threat to raise. The file is parsed with `safe_load`, size
capped, and fully validated before a single rule touches the engine.

That is the whole sandbox, and it is a deliberate ceiling: the worst a hostile rules file can
do is describe threats nobody cares about. It cannot read your filesystem, reach the network,
or change how the engine scores anything else.

## Format

```yaml
id: acme                              # slug: [a-z0-9][a-z0-9_-]*
name: "ACME platform rules"           # optional
description: "..."                    # optional

rules:
  - id: datastore_encryption
    title: "Datastore must use the approved encryption-at-rest standard"
    stride: information_disclosure    # the six STRIDE categories
    match:
      component:
        kind: datastore
    likelihood_delta: 0               # -2..+2, applied to a base of 3
    impact_delta: 1
    refs: ["ORG-SEC-012"]             # optional, free-form
    control_hint: "Platform-managed key hierarchy"   # optional
    description: "..."                # optional
```

### Matching, in full

* A rule matches **exactly one subject**: `component:` or `flow:`. Not both, not neither.
* Inside a match block, **every key must hold** — it is AND.
* A **scalar is equality**; a **list is "any of these"** — it is OR.
* An **unknown field name is an error**, not a criterion that is quietly ignored.

That last point matters more than it looks. A misspelled field would produce a rule that
never fires, and a rule that never fires is worse than no rule at all: the organisation
believes it is covered when it is not. So `suports_admin_operations` fails loudly, with the
list of valid fields.

### `null` is not `false`

A field nobody filled in is `null`, not `false`.

```yaml
match:
  flow:
    encrypted: false            # ONLY flows explicitly marked unencrypted
```

```yaml
match:
  flow:
    encrypted: [false, null]    # also the ones nobody has answered for
```

The second form is usually what you want. "We never wrote down whether this is encrypted" is
a finding, not an all-clear.

### What you can match on

**Components** — `kind`, `technology`, `technology_role`, `exposure_type`, `privilege_level`,
`responsibility`, `in_trust_boundary`, `asset_ids`, and the modelling booleans:
`handles_credentials`, `handles_sensitive_data`, `executes_code_or_commands`,
`serves_user_content`, `has_direct_datastore_access`, `supports_admin_operations`,
`supports_debug_features`.

**Flows** — `protocol`, `operation_type`, `semantic_class`, `data_types`, `from_component`,
`to_component`, `authenticated`, `auth_required`, `authorization_required`, `encrypted`,
`public_exposure`, `input_from_untrusted_source`, `stores_sensitive_data`,
`affects_privileged_state`, `supports_file_upload`, `supports_redirect`,
`supports_external_fetch`, plus the derived **`crosses_boundary`**.

`crosses_boundary` is computed by the engine from your trust boundaries; it is not a field you
write in the model. Ids, names, descriptions and free-form metadata are deliberately not
matchable — matching on a display name produces rules that break when someone renames a box.

Run `otm analyze --help` and see [`examples/custom-rules.example.yaml`](../../examples/custom-rules.example.yaml)
for a working file.

## How rules interact with the engine

**They are additive and are never suppressed.** This is the one place custom rules behave
differently from [industry packs](../../packages/industry-packs), and it is on purpose. The
engine already raises a generic `information_disclosure` on every datastore. Your rule about
the same datastore says something the generic finding does not — which control, whose
standard, which internal reference. Marking it a duplicate would delete exactly the
information somebody wrote the rule to carry.

Within a rule set, the same rule never fires twice on the same target. Two different rules on
one target are two different findings, and stay that way.

**Scoring** uses the same arithmetic as industry packs: `likelihood_delta` and `impact_delta`
are applied to a base of 3 and clamped to `[1,5]`, then multiplied out into the L×I score.

**Generated threats are namespaced** so a reader can tell them apart at a glance:

```
id:    custom_<ruleset-id>_<rule-id>_<target-id>
title: [rules:<ruleset-id>] <your title>
```

**Your `refs` are kept and labelled `custom`.** They appear alongside the CAPEC/CWE/ASVS
references the engine attaches, but under their own catalogue — because they are your labels,
not a verified mapping to a published standard. `framework_ref_counts_by_catalog` keeps them
separate for the same reason.

**`control_hint` appears only for rules that actually fired.** Suggesting a control for a
threat that was never raised tells the reader there is a problem where the engine found none.

## In CI

Rules flow into everything downstream, including the drift gate — so a pull request that
introduces a component violating an organisation rule can fail the build:

```yaml
- uses: lucashgrifoni/App-Suite-Modeling@v7.9.0
  with:
    model: threat-model.otm.yaml
    baseline: baseline/threat-model.otm.yaml
    fail-on: high
```

The composite action does not yet expose `--rules` directly; run `otm analyze --rules` as a
step, or pin the CLI and call it. See [CI_AND_SECURITY_EVIDENCE.md](../CI_AND_SECURITY_EVIDENCE.md) §8.

## Limits, stated plainly

* **One subject per rule.** A rule cannot say "a component that executes commands *and* has an
  untrusted inbound flow". Cross-entity matching is not in this version.
* **No asset matching yet.** `data_classification`, `business_criticality` and
  `regulatory_relevance` are modelled but not yet matchable. Planned, additively.
* **Equality only.** No ranges, no negation, no substring matching. If you need "any privilege
  level except `low`", enumerate the ones you mean.
* **Rules do not change existing scores.** They add threats; they cannot re-score or suppress
  what the engine found. Use `risk_tuning` in an industry pack for that.
* **A rule is a heuristic, not a proof.** Same caveat as the rest of the engine: it flags
  things worth a human looking at, and a clean run is not a statement that the system is
  secure.
