# Downloads and Uploads

- Uploads
- Downloads
- Where files go

## Uploads

```robotframework
*** Test Cases ***
Upload Through Input Element
    Upload File By Selector    input[type="file"]    ${CURDIR}/data/report.pdf
    Upload File By Selector    input#photos    ${CURDIR}/a.png    ${CURDIR}/b.png
    Get Text    .upload-status    contains    uploaded

Upload Through Custom Button
    ${promise}=    Promise To Upload File    ${CURDIR}/data/report.pdf
    Click    button#choose-file
    Wait For    ${promise}
```

- `Upload File By Selector` needs the `<input type="file">` element; extra paths upload several files, and a directory uploads all files directly in it.
- When the site opens a file chooser from a non-input button, start `Promise To Upload File` before the click and `Wait For` it afterwards.
- Large uploads can exceed the library `timeout`; raise it with `Set Browser Timeout` for that test.

## Downloads

```robotframework
*** Test Cases ***
Download Report
    ${promise}=    Promise To Wait For Download    ${OUTPUT_DIR}/report.csv
    Click    text=Export CSV
    ${file}=    Wait For    ${promise}
    File Should Exist    ${file}[saveAs]
    Should Be Equal    ${file}[suggestedFilename]    report.csv

Download Direct Link
    ${file}=    Download    https://example.com/files/manual.pdf
    Log    ${file}[saveAs]
```

- Start `Promise To Wait For Download` before the click that triggers the download; waiting afterwards can miss the event.
- It returns a `DownloadInfo` dictionary with `saveAs` (where the file is) and `suggestedFilename`. `wait_for_finished=False` returns when the download starts; check it later with `Get Download State`.
- `Download` fetches a URL directly; when a page element starts the download, use the promise instead.
- `File Should Exist` comes from `OperatingSystem`; import it for file checks.

## Where files go

- Without `saveAs`, files get a generated name and are deleted when the context closes. Pass `saveAs` (absolute, or relative to the browser's `downloadsPath`) to keep them.
- `New Context` has `acceptDownloads=True` by default; a context created with `acceptDownloads=False` never produces downloads.
- With a remote browser (`Connect To Browser`), `saveAs` is required to store the file where the browser runs.
