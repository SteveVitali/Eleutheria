# Provisional production rules vs shadow eligibility — P32.22

> The shadow gate is **computed, never applied**. Nothing was promoted,
> demoted, or certified; the PROVISIONAL production rules remain active.

## Active provisional production rules

- **camera-site auto-write tiers (decide_auto_write_tiers)** — `PROVISIONAL-active`
  - resolution/camera_sites* + resolution/eval_loop.py (`provisional=True`; auto-write floor 0.98 set against an LLM-bootstrapped gold set)
  - D-R6.1-EVAL (OPEN) — the thresholds are explicitly provisional and must not ossify; every resolved-sites surface carries the provisional-eval disclosure
- **historical point-gate (0.98 auto-write precision floor)** — `PROVISIONAL-active`
  - P28.1 measured first-pass floor; carried in the evaluator report labelled `history` — never new eligibility
  - D-R6.1-EVAL (OPEN)

## Shadow eligibility evaluator (eval-confidence/1)

- policy `eval-confidence/1`, mode `shadow`, applied `[]`
- eval units materialized: 0
- activation attempts refused: ['confidence policy activation refused — no_measured_decision, no_operational_release, policy_shadow_mode, zero_sample']
- installing the evaluator activates nothing — applied stays empty until the measured post-HUMAN-H5 P32.23 decision + an operational release scope

## Safety demotions scoped in this packet

- none — no safety demotion is scoped in this stage

no provisional production rule was replaced, weakened, or certified by this stage; no shadow result activated a gate; no safety demotion is scoped in this packet (an approved demotion, if any, is a separately recorded operational decision in the live packet)
