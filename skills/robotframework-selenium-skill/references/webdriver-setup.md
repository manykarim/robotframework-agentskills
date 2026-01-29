# WebDriver Setup Guide

## Overview

SeleniumLibrary requires WebDriver executables to communicate with browsers. This guide covers setup options for all major browsers.

## WebDriver Manager (Recommended)

Use webdriver-manager for automatic driver management:

```bash
pip install webdriver-manager
```

### Chrome with WebDriver Manager

```python
# In a Python file (browser_setup.py)
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

def get_chrome_driver():
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service)
```

### Using in Robot Framework

```robotframework
*** Settings ***
Library    SeleniumLibrary
Library    browser_setup.py

*** Keywords ***
Open Chrome With Manager
    ${driver}=    Get Chrome Driver
    # Register with SeleniumLibrary if needed
```

## Manual WebDriver Setup

### ChromeDriver

1. Check Chrome version: `chrome://version/`
2. Download matching driver from: https://chromedriver.chromium.org/downloads
3. Place in PATH or specify path

```robotframework
Open Browser    ${URL}    chrome    executable_path=/path/to/chromedriver
```

### GeckoDriver (Firefox)

1. Download from: https://github.com/mozilla/geckodriver/releases
2. Place in PATH or specify path

```robotframework
Open Browser    ${URL}    firefox    executable_path=/path/to/geckodriver
```

### EdgeDriver

1. Check Edge version: `edge://version/`
2. Download from: https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/
3. Place in PATH

```robotframework
Open Browser    ${URL}    edge    executable_path=/path/to/msedgedriver
```

## Browser Options

### Chrome Options

```robotframework
*** Keywords ***
Open Chrome With Options
    [Arguments]    ${url}
    ${options}=    Evaluate    sys.modules['selenium.webdriver'].ChromeOptions()    sys
    Call Method    ${options}    add_argument    --headless
    Call Method    ${options}    add_argument    --no-sandbox
    Call Method    ${options}    add_argument    --disable-dev-shm-usage
    Call Method    ${options}    add_argument    --window-size=1920,1080
    Create WebDriver    Chrome    options=${options}
    Go To    ${url}
```

### Common Chrome Arguments

```robotframework
# Headless mode
options=add_argument("--headless")

# Disable sandbox (for CI/Docker)
options=add_argument("--no-sandbox")

# Disable shared memory (for Docker)
options=add_argument("--disable-dev-shm-usage")

# Window size
options=add_argument("--window-size=1920,1080")

# Start maximized
options=add_argument("--start-maximized")

# Disable GPU (for headless)
options=add_argument("--disable-gpu")

# Ignore certificate errors
options=add_argument("--ignore-certificate-errors")

# Disable extensions
options=add_argument("--disable-extensions")

# User agent
options=add_argument("--user-agent=Custom User Agent")

# Download directory
options=add_experimental_option("prefs", {"download.default_directory": "/path/to/downloads"})
```

### Firefox Options

```robotframework
*** Keywords ***
Open Firefox With Options
    [Arguments]    ${url}
    ${options}=    Evaluate    sys.modules['selenium.webdriver'].FirefoxOptions()    sys
    Call Method    ${options}    add_argument    -headless
    Create WebDriver    Firefox    options=${options}
    Go To    ${url}
```

### Common Firefox Arguments

```robotframework
# Headless mode
options=add_argument("-headless")

# Window size (in headless)
options=add_argument("--width=1920")
options=add_argument("--height=1080")
```

### Edge Options

```robotframework
*** Keywords ***
Open Edge With Options
    [Arguments]    ${url}
    ${options}=    Evaluate    sys.modules['selenium.webdriver'].EdgeOptions()    sys
    Call Method    ${options}    add_argument    --headless
    Create WebDriver    Edge    options=${options}
    Go To    ${url}
```

## Headless Browsers

### Built-in Headless Aliases

```robotframework
# Chrome headless
Open Browser    ${URL}    headless_chrome
Open Browser    ${URL}    headlesschrome
Open Browser    ${URL}    gc    # Also headless

# Firefox headless
Open Browser    ${URL}    headless_firefox
Open Browser    ${URL}    headlessfirefox
Open Browser    ${URL}    ff    # Also headless

# Edge headless
Open Browser    ${URL}    headless_edge
```

### Custom Headless Setup

```robotframework
*** Keywords ***
Open Headless Chrome
    [Arguments]    ${url}
    Open Browser    ${url}    chrome
    ...    options=add_argument("--headless");add_argument("--window-size=1920,1080")
```

## Selenium Grid / Remote WebDriver

### Connect to Selenium Grid

```robotframework
*** Variables ***
${GRID_URL}    http://localhost:4444/wd/hub

*** Keywords ***
Open Browser On Grid
    [Arguments]    ${url}    ${browser}=chrome
    Open Browser    ${url}    ${browser}    remote_url=${GRID_URL}
```

### With Desired Capabilities

```robotframework
*** Keywords ***
Open Chrome On Grid With Capabilities
    [Arguments]    ${url}
    ${caps}=    Create Dictionary
    ...    browserName=chrome
    ...    platformName=linux
    ...    browserVersion=latest
    Open Browser    ${url}    chrome
    ...    remote_url=${GRID_URL}
    ...    desired_capabilities=${caps}
```

### Selenium Grid 4 (W3C Capabilities)

```robotframework
*** Keywords ***
Open Browser On Grid 4
    [Arguments]    ${url}
    ${options}=    Evaluate    sys.modules['selenium.webdriver'].ChromeOptions()    sys
    Call Method    ${options}    set_capability    platformName    linux
    Create WebDriver    Remote
    ...    command_executor=${GRID_URL}
    ...    options=${options}
    Go To    ${url}
```

## Docker Setup

### docker-compose.yml for Selenium Grid

```yaml
version: '3'
services:
  selenium-hub:
    image: selenium/hub:latest
    ports:
      - "4444:4444"

  chrome:
    image: selenium/node-chrome:latest
    depends_on:
      - selenium-hub
    environment:
      - SE_EVENT_BUS_HOST=selenium-hub
      - SE_EVENT_BUS_PUBLISH_PORT=4442
      - SE_EVENT_BUS_SUBSCRIBE_PORT=4443

  firefox:
    image: selenium/node-firefox:latest
    depends_on:
      - selenium-hub
    environment:
      - SE_EVENT_BUS_HOST=selenium-hub
      - SE_EVENT_BUS_PUBLISH_PORT=4442
      - SE_EVENT_BUS_SUBSCRIBE_PORT=4443
```

### Standalone Containers

```bash
# Chrome standalone
docker run -d -p 4444:4444 -p 7900:7900 --shm-size="2g" selenium/standalone-chrome:latest

# Firefox standalone
docker run -d -p 4444:4444 -p 7900:7900 --shm-size="2g" selenium/standalone-firefox:latest
```

### Connect from Robot Framework

```robotframework
*** Variables ***
${REMOTE_URL}    http://localhost:4444

*** Keywords ***
Open Browser In Docker
    [Arguments]    ${url}
    Open Browser    ${url}    chrome    remote_url=${REMOTE_URL}
```

## CI/CD Configuration

### GitHub Actions

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install Chrome
        uses: browser-actions/setup-chrome@latest

      - name: Install ChromeDriver
        uses: nanasess/setup-chromedriver@v2

      - name: Install dependencies
        run: |
          pip install robotframework robotframework-seleniumlibrary

      - name: Run tests
        run: |
          robot --variable BROWSER:headless_chrome tests/
```

### GitLab CI

```yaml
test:
  image: python:3.11
  services:
    - selenium/standalone-chrome:latest
  variables:
    SELENIUM_REMOTE_URL: http://selenium__standalone-chrome:4444
  script:
    - pip install robotframework robotframework-seleniumlibrary
    - robot --variable REMOTE_URL:$SELENIUM_REMOTE_URL tests/
```

### Jenkins

```groovy
pipeline {
    agent any

    stages {
        stage('Test') {
            steps {
                sh '''
                    pip install robotframework robotframework-seleniumlibrary webdriver-manager
                    robot --variable BROWSER:headless_chrome tests/
                '''
            }
        }
    }

    post {
        always {
            robot outputPath: '.', passThreshold: 95.0
        }
    }
}
```

## Browser Profiles

### Chrome Profile

```robotframework
*** Keywords ***
Open Chrome With Profile
    [Arguments]    ${url}
    ${options}=    Evaluate    sys.modules['selenium.webdriver'].ChromeOptions()    sys
    Call Method    ${options}    add_argument    user-data-dir=/path/to/profile
    Call Method    ${options}    add_argument    profile-directory=Default
    Create WebDriver    Chrome    options=${options}
    Go To    ${url}
```

### Firefox Profile

```robotframework
*** Keywords ***
Open Firefox With Profile
    [Arguments]    ${url}
    Open Browser    ${url}    firefox
    ...    ff_profile_dir=/path/to/firefox/profile
```

## Download Configuration

### Chrome Download Directory

```robotframework
*** Keywords ***
Configure Chrome Downloads
    [Arguments]    ${download_dir}
    ${prefs}=    Create Dictionary
    ...    download.default_directory=${download_dir}
    ...    download.prompt_for_download=${False}
    ...    download.directory_upgrade=${True}
    ${options}=    Evaluate    sys.modules['selenium.webdriver'].ChromeOptions()    sys
    Call Method    ${options}    add_experimental_option    prefs    ${prefs}
    Create WebDriver    Chrome    options=${options}
```

### Firefox Download Directory

```robotframework
*** Keywords ***
Configure Firefox Downloads
    [Arguments]    ${download_dir}
    ${profile}=    Evaluate    sys.modules['selenium.webdriver'].FirefoxProfile()    sys
    Call Method    ${profile}    set_preference    browser.download.folderList    2
    Call Method    ${profile}    set_preference    browser.download.dir    ${download_dir}
    Call Method    ${profile}    set_preference    browser.helperApps.neverAsk.saveToDisk
    ...    application/pdf,application/octet-stream
    Create WebDriver    Firefox    firefox_profile=${profile}
```

## Troubleshooting WebDriver Issues

### Common Issues

| Issue | Solution |
|-------|----------|
| ChromeDriver version mismatch | Update ChromeDriver to match Chrome version |
| Permission denied | Make driver executable: `chmod +x chromedriver` |
| Driver not in PATH | Add to PATH or use `executable_path` |
| Session not created | Check browser/driver version compatibility |
| DevToolsActivePort | Add `--no-sandbox` and `--disable-dev-shm-usage` |

### Debug Driver Issues

```robotframework
*** Keywords ***
Debug WebDriver
    ${caps}=    Get Browser Capabilities
    Log Dictionary    ${caps}
    ${session}=    Get Session Id
    Log    Session ID: ${session}
```
