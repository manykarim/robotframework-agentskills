## REMOVED Requirements

### Requirement: testcase_builder can emit a runnable suite
**Reason**: `testcase_builder.py` and the `rf-testcase-builder` skill are retired (see capability `skill-catalog`). The model writes test cases directly into `.robot` files, so there is no script output to shape.
**Migration**: Write the `*** Test Cases ***` section directly and validate it with `robot --dryrun` (or `robotcode analyze code`). The remaining output-contract requirements apply to `rf_libdoc.py` only.
