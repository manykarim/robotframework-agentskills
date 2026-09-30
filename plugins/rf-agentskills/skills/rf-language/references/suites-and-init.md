# Suites and Init Files

- [Suite structure](#suite-structure)
- [What an init file may contain](#what-an-init-file-may-contain)
- [Visibility: keywords and variables](#visibility-keywords-and-variables)
- [Running part of a tree](#running-part-of-a-tree)
- [Ordering and naming](#ordering-and-naming)
- [Setup and teardown failures](#setup-and-teardown-failures)

A directory of `.robot` files is a suite tree: every directory is a suite and every file is a child suite. An `__init__.robot` file configures its directory's suite.

## Suite structure

```text
tests/
  __init__.robot          # settings for the whole tree
  01__login.robot
  02__checkout.robot
  api/
    __init__.robot        # Suite Setup for the API suites only
    users.robot
    orders.robot
```

- The root suite name comes from the directory: `tests/` becomes `Tests`, so a test's full name is `Tests.Api.Users.Create User`.
- Put suite-wide setup in the init file of the smallest directory that needs it (`tests/api/__init__.robot` for an API session).

## What an init file may contain

Allowed in `__init__.robot` Settings: `Documentation`, `Metadata`, `Name` (RF 6.1+), `Suite Setup`, `Suite Teardown`, `Test Setup`, `Test Teardown`, `Test Tags`, `Test Timeout`, `Library`, `Resource`, `Variables`. Not allowed: `Test Template` and `Default Tags` (robocop ERR17; Robot Framework reports "not allowed in suite initialization file" and ignores the setting). Init files contain no test cases.

```robotframework
*** Settings ***
Documentation     API suite: one session for all API tests.
Resource          ../../resources/api.resource
Suite Setup       Open Api Session
Suite Teardown    Close Api Session
Test Tags         api
```

This is `assets/examples/tests/api/__init__.robot`. It has no `*** Keywords ***` section; the keywords come from `api.resource`.

## Visibility: keywords and variables

- Keywords and variables that `__init__.robot` defines or imports are used only by the init file's own settings (its suite setup and teardown). Child suites do not see them.
- `Test Setup` and `Test Teardown` from an init file are inherited by every test below it, but the keyword name is resolved in each child suite. A child that does not import the resource defining that keyword fails with "No keyword with name '…' found".
- Defining that keyword in the init file's own `*** Keywords ***` section fails the same way.

The fix is one shared resource that the init file and every child suite import:

```robotframework
*** Settings ***
Documentation     A child suite of tests/api: imports the resource its parent init file uses.
Resource          ../../resources/api.resource

*** Test Cases ***
Session Is Open In A Child Suite
    Api Session Should Be Open
```

The dry run catches the missing import ("No keyword with name"), so dry-run from the root directory after editing an init file.

Variables that several suites need go into a resource or variable file that each suite imports, or are created in a suite setup with `VAR … scope=GLOBAL` (or `scope=SUITES` on RF 7.1+, which reaches child suites).

## Running part of a tree

| Command | `__init__.robot` files that run |
|---|---|
| `robot tests` | All |
| `robot --suite users tests` | `tests/__init__.robot` and `tests/api/__init__.robot`, then `users.robot` |
| `robot --test "Tests.Api.Users.Create User" tests` | The init files on the path to that test |
| `robot tests/api/users.robot` | None: the file becomes the root suite and its parents' setups are skipped |
| `robot tests/api` | Only `tests/api/__init__.robot` |

Always start from the root directory and select with `--suite`, `--test` or `--include` when the tree has init files.

## Ordering and naming

- Suites run in file-name order. A `NN__` prefix (two underscores) sets the order and is removed from the suite name: `01__login.robot` becomes the suite `Login`.
- Underscores in file names become spaces in suite names: `user_admin.robot` is `User Admin`.
- The `Name` setting (RF 6.1+) overrides the suite name derived from the file or directory.
- `--parseinclude "02__*.robot"` (RF 6.1+) parses only matching files; init files are still read.

## Setup and teardown failures

| What fails | Effect |
|---|---|
| Suite setup | Every test in the suite and its child suites fails without running; the suite teardown still runs |
| Suite teardown | Every test in the suite is marked failed, even if it passed |
| Test setup | The test body does not run; the test teardown still runs |
| Test body | The test teardown still runs |
| A step in a teardown | The remaining teardown steps still run (teardowns continue on failure) |

- A setup or teardown is one keyword call; several steps go into one user keyword.
- A test's `[Setup]` or `[Teardown]` replaces the suite's `Test Setup`/`Test Teardown`; `[Setup]    NONE` removes it for that test.
- Put clean-up that must happen into the teardown, not at the end of the body.
