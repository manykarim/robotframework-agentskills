# rf-skill-eval trigger report

Model `claude-haiku-4-5-20251001` · skill-listing budget default · a query is *triggered* when its trigger rate (loads / runs) is >= its set's threshold. TP/FP/TN/FN per split; train and validation are reported separately (tune on train only).

| Skill | Train TP/FP/TN/FN | Train P | Train R | Train Acc | Val TP/FP/TN/FN | Val P | Val R | Val Acc | Stored Val Acc |
|---|---|---|---|---|---|---|---|---|---|
| rf-browser | 1/0/1/1 | 100% | 50% | 67% | 1/1/0/0 | 50% | 100% | 50% | 100% |
| rf-selenium | – | – | – | – | – | – | – | – | – |

## Failing queries

- `rf-browser` `br-t02` (train, should trigger): rate 1/3; other skills loaded: rf-selenium — Click in shadow DOM
- `rf-browser` `br-n07` (validation, should NOT trigger): rate 2/3; other skills loaded: rf-requests — Call /login REST endpoint
- `rf-selenium` `se-n01` (validation, should NOT trigger): incomplete; other skills loaded: none — Record a Playwright trace
