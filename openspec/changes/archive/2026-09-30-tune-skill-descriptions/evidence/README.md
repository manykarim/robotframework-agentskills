# Evidence: tune-skill-descriptions

| File | What it is |
|---|---|
| `trigger-results-current-2026-09-28.json` | Historical: first live trigger run (old harness, empty workspace). Not comparable with the files below. |
| `trigger-results-pre-sharpen-validation-2026-09-29.json` | Historical: pre-sharpen descriptions, validation split, old harness. |
| `rebaseline.json` | Task 2.1: current descriptions (variant `25e6b4b2b5f8`) under the corrected harness (`--tools Skill,Read,Glob,Grep`, `sut-trigger` fixture, `--max-turns 3`), both splits, Haiku 4.5, 3 runs per query, Claude Code 2.1.284. 256 queries, 0 incomplete, spend $16.16. |

## Re-baseline (task 2.1)

Recall and negative accuracy are counted per query (a query is triggered when loads/runs ≥ 0.5). Loads/runs counts single sessions.

| Skill | Train recall | Train pos loads/runs | Train neg acc | Train neg loads | Val recall | Val pos loads/runs | Val neg acc | Val neg loads | Description in listing? |
|---|---|---|---|---|---|---|---|---|---|
| `rf-appium` | 6/7 (0.86) | 17/21 | 6/6 (1.00) | 0 | 3/4 (0.75) | 8/12 | 4/4 (1.00) | 0 | yes |
| `rf-browser` | 4/7 (0.57) | 14/21 | 6/6 (1.00) | 0 | 3/4 (0.75) | 9/12 | 4/4 (1.00) | 0 | yes |
| `rf-language` | 2/8 (0.25) | 7/24 | 7/7 (1.00) | 0 | 0/6 (0.00) | 1/18 | 5/5 (1.00) | 0 | yes |
| `rf-libdoc` | 0/7 (0.00) | 2/21 | 5/6 (0.83) | 3 | 1/4 (0.25) | 3/12 | 4/4 (1.00) | 0 | name only |
| `rf-platynui` | 6/7 (0.86) | 19/21 | 6/6 (1.00) | 0 | 2/4 (0.50) | 6/12 | 4/4 (1.00) | 0 | name only |
| `rf-python-library` | 1/6 (0.17) | 5/18 | 6/6 (1.00) | 0 | 1/4 (0.25) | 2/12 | 4/4 (1.00) | 0 | name only |
| `rf-requests` | 3/7 (0.43) | 10/21 | 6/6 (1.00) | 0 | 1/4 (0.25) | 3/12 | 4/4 (1.00) | 0 | name only |
| `rf-restinstance` | 4/7 (0.57) | 11/21 | 6/6 (1.00) | 0 | 3/4 (0.75) | 9/12 | 4/4 (1.00) | 0 | name only |
| `rf-results` | 0/7 (0.00) | 2/21 | 6/6 (1.00) | 0 | 0/4 (0.00) | 0/12 | 4/4 (1.00) | 0 | name only |
| `rf-robotcode` | 3/7 (0.43) | 10/21 | 6/6 (1.00) | 1 | 2/4 (0.50) | 6/12 | 4/4 (1.00) | 0 | name only |
| `rf-selenium` | 3/7 (0.43) | 10/21 | 6/6 (1.00) | 0 | 3/4 (0.75) | 9/12 | 4/4 (1.00) | 0 | name only |
| `rf-setup` | 5/7 (0.71) | 13/21 | 6/6 (1.00) | 0 | 2/4 (0.50) | 7/12 | 4/4 (1.00) | 0 | name only |

## Key finding: 9 of 12 descriptions were never shown to the model

Every trigger session records a `skill_listing` attachment in `session.jsonl`. In the re-baseline it reads:

```
- rf-appium: Writes and fixes Robot Framework mobile tests …
- rf-browser: Writes and fixes Robot Framework web UI tests …
- rf-language: Writes and reviews Robot Framework test cases …
- rf-libdoc
- rf-platynui
- rf-python-library
…
- rf-setup
- dataviz: Use this skill whenever you are about to create ANY chart …
```

Claude Code 2.1.284 caps the skill listing at `context window × 4 chars/token × 1%` characters (8000 for Haiku 4.5's 200k window; overridable by `SLASH_COMMAND_TOOL_CHAR_BUDGET` or the `skillListingBudgetFraction` setting). Bundled skills always keep their descriptions; the remaining skills, ordered by the user's own usage score (all 0 in a fresh config, so alphabetical), each keep their description only while it still fits, and are otherwise listed by name only. In the re-baseline the bundled skills plus all names used 6266 characters, which left 1734 characters for the 12 rf-* descriptions: rf-appium (501) + rf-browser (530) + rf-language (677) = 1708 fit, nothing else did.

Consequences:

- The re-baseline numbers of rf-libdoc … rf-setup measure the skill *name* only. Their loads come from queries that contain the name's word (`platynui`, `robotcode`, `RESTinstance`, `SeleniumLibrary`), which is why rf-platynui scores 6/7 on train without a visible description.
- Rewording one of those nine descriptions changes nothing under the default budget unless the texts before it in the listing get shorter. The first rf-results candidate was measured this way by mistake (3/21 loads, text not visible).
- Real users hit the same cap: on a 200k-context model all 12 descriptions (≈ 6.4k characters) cannot fit next to Claude Code's bundled skills; on a 1M-context model the budget is 40000 and they all fit.

Diagnostic (rf-results, train, `SLASH_COMMAND_TOOL_CHAR_BUDGET=40000` so that every description is listed):

| rf-results text | Listing | Pos loads/runs | Query recall | Neg loads | Spend |
|---|---|---|---|---|---|
| current (iteration 0) | default | 2/21 | 0/7 | 0 | (re-baseline) |
| current (iteration 0) | 40000 | 8/21 | 2/7 | 0 | $1.02 |
| candidate 1 | default (name only) | 3/21 | 1/7 | 0 | $0.85 |
| candidate 1 | 40000 | 21/21 | 7/7 | 0 | $1.06 |

With the description visible, wording matters a lot; without it, nothing does. The tuning loop (4.2/4.3) therefore measured candidates with `SLASH_COMMAND_TOOL_CHAR_BUDGET=40000` (see design.md, Implementation Notes).

## Failure analysis of the re-baseline (task 2.2)

What the model did on should-trigger runs that did not load the skill, from `stdout.stream.jsonl` of each run (run id = the last part of the run directory `trigger-<skill>-<query>-treatment-<id>`, kept in the scratch re-baseline output). Three behaviours dominate: (a) **answered directly** from its own knowledge, with no tool call; (b) **explored first**: `Glob`/`Read` of the file the query names (often missing in the neutral fixture) or of `tests/smoke.robot`, until the 3-turn limit ended the session; (c) **loaded a different skill**. Counts are over failed runs (train + validation).

| Skill | Answered directly | Explored first (Glob/Read/Grep) | Other skill |
|---|---|---|---|
| rf-appium | 1 | 7 | 0 |
| rf-browser | 5 | 5 | 0 |
| rf-language | 12 | 22 | 0 |
| rf-libdoc | 16 | 12 | 0 (+3 wrong loads on a negative) |
| rf-platynui | 2 | 6 | 0 |
| rf-python-library | 8 | 15 | 0 |
| rf-requests | 10 | 10 | 0 |
| rf-restinstance | 8 | 5 | 0 |
| rf-results | 0 | 32 | 0 |
| rf-robotcode | 1 | 16 | 0 (+1 wrong load on a negative) |
| rf-selenium | 8 | 6 | 0 |
| rf-setup | 5 | 6 | 2 |

- **rf-appium** (description visible). Misses are symptoms and actions on project files: for the locator error the model Globbed `*.robot`, read `smoke.robot` and grepped for the locator (`ap-t06` 6fc0bd5e, 89ff6da2); for "run my suite against the .apk on emulator-5554" it searched for the `.apk` and suites (`ap-v04` 18c6737a, 68ecada1); for hiding the keyboard it answered from memory (`ap-t07` a7be05d1). Ignored words: `accessibility_id`, `emulator-5554`, `.apk`.
- **rf-browser** (visible). How-to questions were answered from memory, including the right keyword (`br-t07` d01f5cd6, dc4fae74, e353fb9f: `Wait For Elements State`; `br-t03` 03658ee0, 1a8ccd32: `>>>` for shadow DOM); a pasted Playwright error led to reading `smoke.robot` (`br-t06` 770b1eb8, c73b89eb). Ignored: "playwright", "browser lib", `TimeoutError: locator.click`.
- **rf-language** (visible, 677 characters). The model treats Robot Framework syntax as general knowledge: tag selection, `Force Tags` and typed arguments were answered directly (`lang-t04` 38cecddf, 46721449; `lang-t11` 489c4448; `lang-t13` 0a28a2e2); edits of named files started with `Read` of that file (`lang-t07` 01cb24d4, 2ec874a9; `lang-t10` 01673472) or a Glob of `*.robot` (`lang-t01` 6c959791). Ignored although in the description: "data-driven", "Given/When/Then", `__init__.robot`, "Force Tags".
- **rf-libdoc** (name only). Keyword names and signatures were answered from memory (`ld-t01` 0255dd8c, `ld-t04` 2fbe1bb8, `ld-t07` 4c1be360); searching a resource file was done with `Grep` (`ld-t05` 20bb5faa, ebac79f1). The only word that loaded the skill was "libdoc" itself, on the negative "show me the doc … via robotcode libdoc" (`ld-n04` 6d78a9be, 7d364691, afcb2506): the rf-robotcode boundary was invisible.
- **rf-platynui** (name only). Loads whenever "PlatynUI" is in the query; misses when it only says "desktop"/"dialog" or names a file to edit: XPath question answered/explored (`pu-t06` 17a21a39, a207fe08), `Read` of `settings.robot` first (`pu-v01` 751ead23, 7b6cee0f).
- **rf-python-library** (name only). Globbed for `*.py` libraries (`pylib-t04` 2c44b082, 6f498c40; `pylib-t09` b80a70d1) or answered directly (`pylib-t03` 261e1773 enum; `pylib-t06` c4eb8417 scope). Ignored: "listener", "scope", "enum", "custom lib".
- **rf-requests** (name only). Even "RequestsLibrary" in the query did not load it: multipart upload, query params and SSL were answered from memory (`rq-t05` 370f92c7, a1038bf5; `rq-t07` 4241c635; `rq-v03` 54de0818); JSON field checks started with reading `smoke.robot` (`rq-t06` 3814a620, 4eb0ded0).
- **rf-restinstance** (name only). Loads when "REST"/"RESTinstance" appears; the pasted type error was explained directly (`ri-t04` 74699f47, b8a267b3); "generate a schema from the current response" got a clarification question (`ri-t05` 15fef8d9, 3e17989d).
- **rf-results** (name only). All 32 failed runs Globbed or Read `output.xml` (not present in the fixture) and used up the 3 turns (`rs-t01` 408dbd30, `rs-t02` 1813c518, `rs-v02` aad9e8b2, `rs-t04` 761df934). Ignored: "output.xml", "pabot", "rerun", "tags".
- **rf-robotcode** (name only). Loads on "robotcode"; misses on `robot.toml`, `robot-debug` and "REPL": it read `robot.toml` first (`rc-t02` 13b5ef80, `rc-t04` 364d824e, `rc-v01` 6abb2e83) or grepped the test name (`rc-t03` 31b1d6eb, 7b6e8854). One wrong load for the RobotCode VS Code extension settings (`rc-n04` f7e5c523).
- **rf-selenium** (name only). WebDriver symptoms were answered directly (`se-t04` 47601a54, a63a7681; `se-t06` 0acd666f, 2ca60838; `se-t07` b02bc815); Grid runs started with reading suites (`se-t03` 95e6be54, e49187fe).
- **rf-setup** (name only). Environment errors answered directly (`su-t07` 5d261f54, 76350655; `su-t03` 11838d5d); dependency edits read `pyproject.toml` first (`su-t04` 921243ba, `su-v01` 06f568c0); the RESTinstance Python-version question loaded rf-restinstance instead (`su-v02` 1bc44fb6, 68504161).

Two harness effects add to this: queries that name a file (`results/output.xml`, `tests/web/checkout.robot`) send the model looking for it in a fixture that does not contain it, and `--max-turns 3` ends the session before a late `Skill` call (several rf-results transcripts say "let me find the output.xml, then use the rf-results skill").

## Tuning results (tasks 4.2/4.3)

Train split only, Haiku 4.5, 3 runs per query, `--concurrency 2`, each candidate staged with every other skill at its current text. All tuning runs after the first used `SLASH_COMMAND_TOOL_CHAR_BUDGET=40000`, so every description was in the listing. Candidate texts, rationales and per-iteration numbers are in `candidates/<skill>.yaml`. "Best" is the selected iteration: 0 negative loads, then the most single-run loads (D6).

| Skill | Iterations | Iteration 0 (re-baseline, default listing) | Best candidate | Selected | Chars |
|---|---|---|---|---|---|
| `rf-results` | 1 | 2/21 loads, 0/7 queries, 0 neg | 21/21, 7/7, 0 neg | 1 | 703 |
| `rf-language` | 4 | 7/24, 2/8, 0 neg | 22/24, 7/8, 0 neg | 2 | 991 |
| `rf-python-library` | 3 | 5/18, 1/6, 0 neg | 17/18, 6/6, 0 neg | 3 | 959 |
| `rf-libdoc` | 4 | 2/21, 0/7, 3 neg | 18/21, 6/7, 0 neg | 2 | 871 |
| `rf-requests` | 2 | 10/21, 3/7, 0 neg | 21/21, 7/7, 0 neg | 2 | 754 |
| `rf-platynui` | 1 | 19/21, 6/7, 0 neg | 20/21, 7/7, 0 neg | 1 | 717 |
| `rf-robotcode` | 1 | 10/21, 3/7, 1 neg | 21/21, 7/7, 0 neg | 1 | 735 |
| `rf-setup` | 3 | 13/21, 5/7, 0 neg | 21/21, 7/7, 0 neg | 3 | 806 |
| `rf-appium` | 1 | 17/21, 6/7, 0 neg | 21/21, 7/7, 0 neg | 1 | 691 |
| `rf-browser` | 2 | 14/21, 4/7, 0 neg | 20/21, 7/7, 0 neg | 2 | 736 |
| `rf-restinstance` | 1 | 11/21, 4/7, 0 neg | 21/21, 7/7, 0 neg | 1 | 575 |
| `rf-selenium` | 1 | 10/21, 3/7, 0 neg | 21/21, 7/7, 0 neg | 1 | 689 |

Iteration 0 was measured under the default listing (9 of 12 descriptions not visible), so the gain mixes the visibility effect and the wording effect. For rf-results both were measured: visibility alone took it from 2/21 to 8/21, the new wording from 8/21 to 21/21.

Stops: rf-language and rf-libdoc did not reach query recall ≥ 0.9 with their selected text. rf-language candidate 4 reached 8/8 queries but only 19/24 runs (every query at 2/3), so candidate 2 (22/24) keeps the best D6 score. rf-libdoc plateaued at 18/21 for candidates 2–4: an explicit "search our <file>.resource for keywords" request is always answered with `Grep`. Candidates that improved recall while adding a negative load (rf-libdoc 1, rf-setup 1–2: a late secondary load while writing a Browser test) were not selected.

Selected texts total about 9.2k characters. Under the default listing budget for Haiku (1734 characters left for all rf-* descriptions in these sessions) at most two of them would be shown. Acceptance (task 5) has to decide on the listing condition first; see design.md.

## Tuning spend (budget $35)

Spend per run from each `trigger-results.json` (`spent_usd`); 0 incomplete queries and 0 budget stops in every run.

| # | Run | Listing | Spend | Cumulative |
|---|---|---|---|---|
| 1 | rf-results-it1 | default | $0.853 | $0.853 |
| 2 | diag rf-results current | 40000 | $1.015 | $1.868 |
| 3 | diag rf-results-it1 | 40000 | $1.059 | $2.927 |
| 4 | rf-language-it1 | 40000 | $1.344 | $4.271 |
| 5 | rf-python-library-it1 | 40000 | $0.971 | $5.243 |
| 6 | rf-libdoc-it1 | 40000 | $1.150 | $6.392 |
| 7 | rf-requests-it1 | 40000 | $1.013 | $7.406 |
| 8 | rf-language-it2 | 40000 | $1.413 | $8.819 |
| 9 | rf-python-library-it2 | 40000 | $0.954 | $9.773 |
| 10 | rf-libdoc-it2 | 40000 | $1.109 | $10.882 |
| 11 | rf-requests-it2 | 40000 | $1.030 | $11.912 |
| 12 | rf-platynui-it1 | 40000 | $1.149 | $13.061 |
| 13 | rf-robotcode-it1 | 40000 | $1.053 | $14.114 |
| 14 | rf-setup-it1 | 40000 | $1.086 | $15.200 |
| 15 | rf-language-it3 | 40000 | $1.342 | $16.542 |
| 16 | rf-python-library-it3 | 40000 | $0.975 | $17.517 |
| 17 | rf-libdoc-it3 | 40000 | $1.122 | $18.638 |
| 18 | rf-setup-it2 | 40000 | $1.059 | $19.697 |
| 19 | rf-appium-it1 | 40000 | $1.108 | $20.805 |
| 20 | rf-browser-it1 | 40000 | $1.045 | $21.850 |
| 21 | rf-restinstance-it1 | 40000 | $1.072 | $22.922 |
| 22 | rf-selenium-it1 | 40000 | $1.084 | $24.006 |
| 23 | rf-language-it4 | 40000 | $1.346 | $25.352 |
| 24 | rf-libdoc-it4 | 40000 | $1.142 | $26.494 |
| 25 | rf-setup-it3 | 40000 | $1.231 | $27.725 |
| 26 | rf-browser-it2 | 40000 | $1.027 | $28.752 |

Tuning total: $28.75 of $35. With the re-baseline ($16.16) the change has spent $44.91 so far (cap after task 4.3: $55).

## Compact set tuning (tasks 4.4/4.5)

Train split, Haiku 4.5, 3 runs per query, `--concurrency 2`, **default listing budget** (no `SLASH_COMMAND_TOOL_CHAR_BUDGET`, no `--listing-budget`), all 12 compact candidates staged together. Texts, rationales and per-iteration numbers are in the `compact` field of `candidates/<skill>.yaml`; the `## When to use` blocks (D12) are in `when_to_use`. Every compact text passes `compact_problems`, the selected set's listing lines total 1697 characters (`listing_problems` passes) and every block passes `when_to_use_problems` (checked offline with the test's helpers).

**Visibility.** In every session of every compact run the `skill_listing` attachment showed all 12 rf-* descriptions (iteration 1: 471/471 sessions; iterations 2–3, validation and the 40000 run: 100% as well). The listing was 7931 of 8000 characters.

| Skill | Re-baseline train (loads, queries, neg acc) | It. 1 (`b7a14079b54d`) | It. 2 (`89165185ac66`) | It. 3 (`7cfa7e52981c`) | Selected |
|---|---|---|---|---|---|
| `rf-appium` | 17/21, 6/7, 6/6 | 21/21, 7/7, 6/6 | – | – | 1 |
| `rf-browser` | 14/21, 4/7, 6/6 | 20/21, 7/7, 6/6 | – | – | 1 |
| `rf-language` | 7/24, 2/8, 7/7 | 13/24, 5/8, 7/7 | **18/24, 6/8, 7/7** | – | 2 |
| `rf-libdoc` | 2/21, 0/7, 5/6 | 17/21, 6/7, 6/6 (1 neg load) | 16/21, 5/7, 6/6 (2 neg loads; same text) | – | 1 |
| `rf-platynui` | 19/21, 6/7, 6/6 | 21/21, 7/7, 6/6 | – | – | 1 |
| `rf-python-library` | 5/18, 1/6, 6/6 | 16/18, 6/6, 6/6 | – | – | 1 |
| `rf-requests` | 10/21, 3/7, 6/6 | 21/21, 7/7, 6/6 | – | – | 1 |
| `rf-restinstance` | 11/21, 4/7, 6/6 | 21/21, 7/7, 6/6 | – | – | 1 |
| `rf-results` | 2/21, 0/7, 6/6 | 18/21, 7/7, 6/6 (1 neg load) | 16/21, 6/7, 6/6 (same text) | – | 1 |
| `rf-robotcode` | 10/21, 3/7, 6/6 | 21/21, 7/7, **5/6** (rc-n04 3/3) | 19/21, 6/7, **5/6** (rc-n04 2/3) | **20/21, 7/7, 6/6** (0 neg loads) | 3 |
| `rf-selenium` | 10/21, 3/7, 6/6 | 21/21, 7/7, 6/6 | – | – | 1 |
| `rf-setup` | 13/21, 5/7, 6/6 | 21/21, 7/7, 6/6 (1 neg load) | – | – | 1 |
| **Sum of positive loads** | 120/252 | 231/252 | | | 232/252 (see note) |

- Iteration 1 is a full train pass (158 queries). Iteration 2 changed rf-language and rf-robotcode and re-ran only those two sets plus the two siblings they compete with (rf-libdoc, rf-results); iteration 3 changed rf-robotcode only and re-ran its set. The other skills' texts were identical in all three variants, so their iteration-1 numbers stand; the selected set's sum (232) combines iteration 1 (8 skills), iteration 2 (rf-language, rf-libdoc, rf-results) and iteration 3 (rf-robotcode). Iterations 1 and 2 were rejected as sets because rf-robotcode lost should-not-trigger accuracy on rc-n04 (the RobotCode VS Code extension settings question), which the rule in D13 forbids.
- rf-libdoc and rf-results moved by 1–2 loads between iterations 1 and 2 with unchanged texts: that is the run-to-run noise of 3 runs per query.
- Remaining train misses: rf-language (lang-t03 goes to rf-libdoc on "No keyword with name", edits of named .resource files start with `Read`), rf-libdoc ld-t05 ("search our common.resource" is answered with `Grep`, as with the rich texts).

## Acceptance: combined validation run (task 5.1, default listing budget)

Selected set (variant `7cfa7e52981c`), validation split, Haiku 4.5, 3 runs per query, default budget, 99 queries, 0 incomplete (`compact-validation.json`). The first invocation stopped at its `--max-cost-usd 7` cap with 15 rf-setup runs not started; a resume into the same output (resume key unchanged) ran them. Recall and accuracy per query (loads/runs ≥ 0.5).

| Skill | Val recall (re-baseline → compact) | Pos loads | Neg acc (re-baseline → compact) | Neg loads | Rule | Decision |
|---|---|---|---|---|---|---|
| `rf-appium` | 0.75 → **1.00** | 8/12 → 11/12 | 1.00 → 1.00 | 0 | (a) | accepted |
| `rf-browser` | 0.75 → 0.75 | 9/12 → 10/12 | 1.00 → 1.00 | 0 | none | **not meeting target** (br-v04 "no web test library chosen yet" 1/3) |
| `rf-language` | 0.00 → 0.50 | 1/18 → 10/18 | 1.00 → 1.00 | 0 | (b) +0.50 | accepted, shortfall 0.30 |
| `rf-libdoc` | 0.25 → 0.75 | 3/12 → 10/12 | 1.00 → 1.00 | 0 | (b) +0.50 | accepted, shortfall 0.05 |
| `rf-platynui` | 0.50 → **1.00** | 6/12 → 11/12 | 1.00 → 1.00 | 1 (pu-n10 1/3) | (a) | accepted |
| `rf-python-library` | 0.25 → 0.50 | 2/12 → 7/12 | 1.00 → 1.00 | 0 | (b) +0.25 | accepted, shortfall 0.30 (hinges on one query) |
| `rf-requests` | 0.25 → **1.00** | 3/12 → 11/12 | 1.00 → 1.00 | 0 | (a) | accepted |
| `rf-restinstance` | 0.75 → 0.75 | 9/12 → 10/12 | 1.00 → 1.00 | 0 | none | **not meeting target** (ri-v01 1/3) |
| `rf-results` | 0.00 → **1.00** | 0/12 → 11/12 | 1.00 → 1.00 | 0 | (a) | accepted |
| `rf-robotcode` | 0.50 → 0.75 | 6/12 → 8/12 | 1.00 → 1.00 | 0 | (b) +0.25 | accepted, shortfall 0.05 (hinges on one query) |
| `rf-selenium` | 0.75 → **1.00** | 9/12 → 12/12 | 1.00 → 1.00 | 0 | (a) | accepted |
| `rf-setup` | 0.50 → **1.00** | 7/12 → 11/12 | 1.00 → 1.00 | 1 (su-n10 1/3) | (a) | accepted |
| **Total** | 21/50 → 41/50 queries | 63/150 → 122/150 | 49/49 → 49/49 | 2 | | 6 (a), 4 (b), 2 none |

- No skill lost should-not-trigger accuracy; the two single negative loads stay below the 0.5 query threshold.
- rf-browser and rf-restinstance meet neither rule: recall is unchanged at 0.75 (one query at 1/3; loads went up by one each). The spec's "A skill meeting neither (a) nor (b) SHALL still ship a compact description" applies: their previous texts break the 160-character rule, so there is no text to revert to. Recorded as not meeting the target.
- Single-query dependence (task 5.2 trigger): rf-python-library and rf-robotcode are accepted under (b) with exactly +0.25 (one query); rf-browser and rf-restinstance miss (a) by one query (1/3 runs). The 5.2 repeat was **not run**: the budget for tasks 4.5–5.3 ($32) was used up by 4.5 ($17.54), 5.1 ($7.50) and 5.3 ($6.93). See design.md Implementation Notes.
- Misses at validation: rf-language lang-t10/t12/t14 (clean up repetitive tests, organise resource/variable files, step keywords for Given/When/Then), rf-python-library pylib-t07/t09 (add `@keyword` to a named .py file, libdoc docs for a library), rf-robotcode rc-v04 (goes to rf-libdoc on "robotcode libdoc").

## Validation at the 1M-context listing budget (task 5.3, report only)

Same variant, validation split, `--listing-budget 40000` (`compact-validation-budget-40000.json`). The `--max-cost-usd 6.9` cap stopped the run with 18 rf-setup runs not started (su-v03, su-v04 and all 4 negatives); it was not resumed because the change budget for these tasks was spent. Under the compact set every description is visible at both budgets, so the difference between the two columns is run-to-run noise, not visibility.

| Skill | Recall default | Recall 40000 | Pos loads default / 40000 | Neg acc default / 40000 |
|---|---|---|---|---|
| `rf-appium` | 1.00 | 1.00 | 11/12 / 11/12 | 1.00 / 1.00 |
| `rf-browser` | 0.75 | 1.00 | 10/12 / 11/12 | 1.00 / 1.00 |
| `rf-language` | 0.50 | 0.50 | 10/18 / 9/18 | 1.00 / 1.00 |
| `rf-libdoc` | 0.75 | 1.00 | 10/12 / 12/12 | 1.00 / 1.00 (1 neg load) |
| `rf-platynui` | 1.00 | 0.75 | 11/12 / 10/12 | 1.00 / 1.00 |
| `rf-python-library` | 0.50 | 1.00 | 7/12 / 9/12 | 1.00 / 1.00 |
| `rf-requests` | 1.00 | 1.00 | 11/12 / 12/12 | 1.00 / 1.00 |
| `rf-restinstance` | 0.75 | 1.00 | 10/12 / 12/12 | 1.00 / 1.00 |
| `rf-results` | 1.00 | 0.75 | 11/12 / 9/12 | 1.00 / 1.00 |
| `rf-robotcode` | 0.75 | 0.50 | 8/12 / 6/12 | 1.00 / 1.00 |
| `rf-selenium` | 1.00 | 1.00 | 12/12 / 12/12 | 1.00 / 1.00 |
| `rf-setup` | 1.00 | 2/2 measured (partial) | 11/12 / 6/6 | 1.00 / not run |

## Compact tuning and acceptance spend (budget for 4.5–5.3: $32)

| # | Run | Listing | Spend | Cumulative (change) |
|---|---|---|---|---|
| 27 | compact-it1 visibility probe (rf-setup validation, 1 run/query; not used for selection) | default | $0.203 | $45.11 |
| 28 | compact-it1 train, all 12 (stopped at $10 cap, then resumed) | default | $10.032 + $2.216 | $57.36 |
| 29 | compact-it2 train (rf-language, rf-robotcode, rf-libdoc, rf-results) | default | $4.162 | $61.52 |
| 30 | compact-it3 train (rf-robotcode) | default | $0.934 | $62.46 |
| 31 | compact validation (5.1; stopped at $7 cap, then resumed) | default | $7.043 + $0.458 | $69.96 |
| 32 | compact validation (5.3) | 40000 | $6.926 | $76.88 |

Tasks 4.5–5.3 spent $31.97 of $32 (4.5: $17.54 including the probe; 5.1: $7.50; 5.3: $6.93). Change total: $76.88 of $90. One full train pass cost $12.25, not the planned ~$8: sessions that load a skill are longer, and loads roughly doubled.

## 7.2 Holdout (Haiku) and cross-model (Sonnet 5), shipped descriptions (variant 7cfa7e52981c, default listing budget)

Files: `final-holdout-haiku.json`, `final-validation-sonnet5.json`.

**Both runs hit their cost caps. The change total reached $90.02 against the $90 cap:**
- holdout: $7.55; 70 runs budget-stopped (rf-selenium and rf-setup not measured, rf-robotcode partial);
- Sonnet 5: $5.59; 15 runs budget-stopped (rf-selenium and rf-setup partial).

Numbers below cover the fully measured skills only.

| Run | Should-trigger recall | Should-not-trigger accuracy |
|---|---|---|
| Holdout, Haiku, 3 runs/query, 10 measured skills | 45/50 (0.90) | 47/50 |
| Validation, Sonnet 5, 1 run/query, 10 fully measured skills | 41/42 (0.98) | 41/41 |

The holdout false positives are all sibling-boundary cases. The compact descriptions no longer carry the boundary, which now sits in each `## When to use` block and only helps after loading:
- rf-appium `ap-h07` (3/3): Appium driver install behind a proxy → belongs to rf-setup.
- rf-libdoc `ld-h06` (2/3): "robotcode installed … robotcode libdoc" → belongs to rf-robotcode.
- rf-results `rs-h06` (3/3): "robotcode is set up … robotcode results" → belongs to rf-robotcode.

Holdout recall misses: rf-language 4/5, rf-libdoc 3/5, rf-results 3/5.

## Completion runs (2026-09-30, extra budget approved by the user). This section supersedes the gaps noted above.

Files:
- `compact-validation-repeat.json` (task 5.2)
- `final-holdout-haiku.json` (complete)
- `final-validation-sonnet5.json` (complete)
- `compact-validation-budget-40000.json` (complete)

Extra spend: $10.97. **Change total: $100.99.**

**5.2 repeat validation** (same shipped variant 7cfa7e52981c, default budget, 3 runs/query). Recall 42/50, should-not-trigger accuracy 49/49. Decisions pool both validation runs (6 runs per query; triggered at a rate of at least 0.5).

| Skill | Re-baseline | Run 1 | Repeat | Pooled | Rule |
|---|---|---|---|---|---|
| rf-appium | 0.75 | 1.00 | 1.00 | 1.00 | (a) |
| rf-browser | 0.75 | 0.75 | 0.75 | 0.75 | not met |
| rf-language | 0.00 | 0.50 | 0.50 | 0.50 | (b), shortfall 0.30 |
| rf-libdoc | 0.25 | 0.75 | 1.00 | 1.00 | (a), up from (b) |
| rf-platynui | 0.50 | 1.00 | 1.00 | 1.00 | (a) |
| rf-python-library | 0.25 | 0.50 | 0.75 | 0.75 | (b), shortfall 0.05 |
| rf-requests | 0.25 | 1.00 | 1.00 | 1.00 | (a) |
| rf-restinstance | 0.75 | 0.75 | 0.75 | 0.75 | not met |
| rf-results | 0.00 | 1.00 | 1.00 | 1.00 | (a) |
| rf-robotcode | 0.50 | 0.75 | 0.50 | 0.75 | (b), shortfall 0.05 |
| rf-selenium | 0.75 | 1.00 | 1.00 | 1.00 | (a) |
| rf-setup | 0.50 | 1.00 | 1.00 | 1.00 | (a) |

Pooled: 43/50 should-trigger queries triggered (re-baseline 21/50), should-not-trigger accuracy 100%. Summary: 7 × (a), 3 × (b), 2 not meeting the target.

**Holdout (Haiku, 3 runs/query), complete: recall 55/60 (0.92), should-not-trigger accuracy 56/60 (0.93).**
- Recall misses: rf-language 4/5, rf-libdoc 3/5, rf-results 3/5.
- False positives, all sibling handoffs:
  - rf-appium `ap-h07` (Appium driver install → rf-setup)
  - rf-libdoc `ld-h06` (robotcode libdoc → rf-robotcode)
  - rf-results `rs-h06` (robotcode results → rf-robotcode)
  - rf-selenium `se-h08` (offline chromedriver setup → rf-setup)

**Sonnet 5 validation (1 run/query), complete: recall 49/50 (0.98), should-not-trigger accuracy 48/49.**
- Miss: rf-python-library 3/4.
- False positive: rf-selenium `se-n09`, a Selenium Grid Docker setup for a Java team (not RF), 1/1.

**40000 listing budget** (1M-context condition, report only), now complete: recall 43/50, should-not-trigger accuracy 49/49. That matches the default budget (41–43/50) within noise, as expected since every description is visible under both.
