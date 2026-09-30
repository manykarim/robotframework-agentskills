# Authentication and Storage State

- Log in once, reuse the state
- HTTP authentication
- Cookies
- Local and session storage

## Log in once, reuse the state

A context's cookies and local storage can be saved and loaded into new contexts, so only one test (or Suite Setup) goes through the login form.

```robotframework
*** Settings ***
Library           Browser
Suite Setup       Log In Once

*** Variables ***
${URL}            https://app.example.com
${USER}           demo
${PASSWORD}       demo

*** Test Cases ***
Dashboard Shows User
    New Context    storageState=${STATE}
    New Page       ${URL}/dashboard
    Get Text       .user-menu    contains    ${USER}

*** Keywords ***
Log In Once
    New Browser    chromium    headless=True
    New Context
    New Page       ${URL}/login
    Fill Text      input[name="username"]    ${USER}
    Fill Secret    input[name="password"]    $PASSWORD
    Click          button[type="submit"]
    Get Url        contains    /dashboard
    ${state}=      Save Storage State
    VAR    ${STATE}    ${state}    scope=SUITE
```

- `Save Storage State` takes no arguments. It writes to `${OUTPUTDIR}/browser/state/` and returns the path; those files are deleted when the next run starts, so the state is reused within one run. Copy the file (for example with `Copy File`) if another run must reuse it.
- `storageState=` needs the full path returned by `Save Storage State`.
- The state file holds session secrets; keep it out of version control.
- Only cookies and local storage are saved; session storage is not part of it.

## HTTP authentication

For basic or digest auth, give credentials to the context instead of the URL:

```robotframework
*** Keywords ***
Open Protected Site
    New Context    httpCredentials={'username': '$USER', 'password': '$PASSWORD'}
    New Page       https://intranet.example.com
```

Write the values as `$NAME` (Robot Framework variable) or `%NAME` (environment variable), or pass a dictionary of Robot Framework 7.4 `Secret` values built with `VAR    &{creds}`. Plain values such as `{'username': 'u', 'password': 'p'}` are rejected with "Direct assignment of values or variables as 'httpCredentials' is not allowed". For token-based APIs behind the UI, `extraHTTPHeaders={'Authorization': 'Bearer ${TOKEN}'}` on `New Context` sends a header with every request.

## Cookies

```robotframework
*** Test Cases ***
Cookie Handling
    Add Cookie    session    abc123    url=https://app.example.com
    ${cookie}=    Get Cookie    session
    Should Be Equal    ${cookie.value}    abc123
    ${all}=       Get Cookies
    Delete All Cookies
```

`Add Cookie` needs either `url=` or both `domain=` and `path=`. `Get Cookie` returns a dot-accessible dictionary by default.

## Local and session storage

```robotframework
*** Test Cases ***
Storage Handling
    LocalStorage Set Item      theme    dark
    LocalStorage Get Item      theme    ==    dark
    LocalStorage Remove Item   theme
    LocalStorage Clear
    SessionStorage Set Item    step    2
    SessionStorage Get Item    step    ==    2
```

Storage belongs to the page's origin: open a page on the application's URL before setting items. Getters take assertion operators like other getters.
