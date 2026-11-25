# Simple Key-Value Store

## 1. Open the project

Use Visual Studio Code to open the `simple-kv` folder. On Windows, choose
`Terminal > New Terminal` to open PowerShell. Install Python 3.11 or later
and Git if the following commands do not report versions.

```powershell
py --version
git --version
git log --oneline -6
```

## 2. Run the database

```powershell
py main.py
```

The program waits for a command on standard input. Type one command per line.

```text
SET major Cybersecurity
GET major
EXIT
```

You should see `OK` and `Cybersecurity`. Run `py main.py` again and enter
`GET major` to see the persisted value. Use `EXIT` to return to PowerShell.

## 3. Follow the code

1. `index.py` stores key-value pairs in a list and scans for matches.
2. `storage.py` replays `data.db` at startup. Each change batch is appended
   and synced before acknowledgment. Transactions stage changes until
   `COMMIT`. A clear record makes `FLUSHDB` durable.
3. `main.py` reads one command at a time and prints results. Arguments are
   separated by whitespace. `RANGE` accepts `""` for an open bound, includes
   both bounds, and ends with `END`. A missing `GET` prints a blank line.
   `MGET` prints one result per input key, using `(nil)` for a missing value.
4. `test_database.py` exercises the CLI and tests recovery. The CI workflow
   runs the tests, Ruff linting, and a format check on each push or pull request.

```powershell
py -m unittest -v
py -m pip install ruff==0.11.13
py -m ruff check .
py -m ruff format --check .
```

## 4. Run Gradebot

Download the Windows ZIP for your hardware from the
[Gradebot releases page](https://github.com/jh125486/CSCE4350_gradebot/releases).
Extract it outside this project folder. From the project folder, run its
version command and then use the path to the extracted executable.

```powershell
& "C:\path\to\gradebot.exe" --version
Write-Host "EUID YOUR_EUID"
& "C:\path\to\gradebot.exe" project-1 --dir . --run "py main.py"
```

Gradebot v1.3.0 names the subcommand `project-1`. It can remove or replace
the local practice `data.db` while running tests. Capture the rubric table
and your EUID in the same screenshot. Save it in the project folder as
`gradebot_screenshot.png`. Follow your instructor's directions if Gradebot
asks whether to submit the results to its server.

## 5. Publish the final version

Create an empty public repository on GitHub. Replace the example remote with
your repository's URL. Commit the screenshot and tag that final commit.

```powershell
git add gradebot_screenshot.png
git commit -m "Add Gradebot rubric screenshot"
git tag project
git remote add origin https://github.com/YOUR_USERNAME/simple-kv.git
git push -u origin main
git push origin project
```

Open the repo URL on GitHub and check that the screenshot and tag are visible.
Submit the public repo URL.
