# rf-skill-eval report

**Runs:** 11 · **pass:** 6 · **fail:** 4 · **incomplete:** 1 · **skipped checks:** 2 · **reported cost:** $0.25

Pass rate = runs whose gate result is `pass` / runs attempted. Deltas are treatment − baseline over **outcome** checks only.

## Tasks

| Task | Skill | Tier | Arm | Runs | Pass rate | Outcome pass | Incomplete | Input tok | Output tok | Turns | Duration s | Cost $ | Flaky |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `adv-web-wrong-library` | rf-browser | adversarial (non-gating) | treatment | 1 | 0% | 0% | 0 | 1000 | 200 | 4.0 | 20.0 | 0.0200 | no |
| `adv-web-wrong-library` | rf-browser | adversarial (non-gating) | Δ T−B | | | unavailable | | unavailable | unavailable | unavailable | unavailable | unavailable | |
| `narrow-browser-login-01` | rf-browser | narrow | baseline | 3 | 33% | 33% | 0 | 1000 | 200 | 4.0 | 20.0 | 0.0200 | yes |
| `narrow-browser-login-01` | rf-browser | narrow | treatment | 3 | 100% | 100% | 0 | 1200 | 200 | 4.0 | 20.0 | 0.0300 | no |
| `narrow-browser-login-01` | rf-browser | narrow | Δ T−B | | | +67 pp | | +200 | +0 | +0.0 | +0.0 | +0.0100 | |
| `narrow-non-rf-control-01` | plugin | narrow | treatment | 1 | 100% | 100% | 0 | 1000 | 200 | 4.0 | 20.0 | 0.0200 | no |
| `narrow-non-rf-control-01` | plugin | narrow | Δ T−B | | | unavailable | | unavailable | unavailable | unavailable | unavailable | unavailable | |
| `narrow-selenium-login-01` | rf-selenium | narrow | treatment | 3 | 33% | 33% | 1 | 1000 | 200 | 4.0 | 20.0 | 0.0200 | yes |
| `narrow-selenium-login-01` | rf-selenium | narrow | Δ T−B | | | unavailable | | unavailable | unavailable | unavailable | unavailable | unavailable | |

## Skills

| Skill | Tasks | Treatment outcome pass | Baseline outcome pass | Δ outcome pass | Δ input tok | Δ turns | Δ cost $ |
|---|---|---|---|---|---|---|---|
| rf-browser | 2 | 50% | 33% | +67 pp | +200 | +0.0 | +0.0100 |
| rf-selenium | 1 | 33% | – | unavailable | unavailable | unavailable | unavailable |

## Skipped / errored checks

- `narrow-selenium-login-01` (2 skipped): lint_clean:tests/login.robot: skipped (robocop not installed)
- `narrow-selenium-login-01` (2 skipped): robot_pass:tests/login.robot: skipped (robot CLI not installed)

## Incomplete runs

- `narrow-selenium-login-01`: gating check 'robot_pass:tests/login.robot' skipped: robot CLI not installed

## Process checks (treatment arm, not in deltas)

- `narrow-browser-login-01` `loaded_skill`: 3/3

## Adversarial tier (reported only, never gates)

- `adv-web-wrong-library`: treatment pass rate 0%
