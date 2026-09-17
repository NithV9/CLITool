# CLITool
## Description
CLI tool created primarily with the python click library to provide basic info on a directory not limited to but including code statistics, dependency info, git status, and basic health check. Can help with getting familiarized with unknown or vague codebases.
### Libraries
* click, pyflakes, and pytest(for testing)
## Features
 #### Six independent features, each answering a different question about the target directory:
* Usage: python cli.py {flag} {directory}      
#### Flag	What it reports
* -i, --directory PATH	Overview: total file/directory counts, empty files, duplicate filenames, language breakdown by file count, and whether the directory is a git repository
* -s, --project PATH	Lines of code per language, the single largest file, and the average file size
* -g, --git PATH	Current branch, modified/staged/untracked files, and the most recent commit — or a clean message if the directory isn't a git repo
* -a, --dir PATH	Parses package.json for production/development dependency counts, then reports the five largest installed packages by actual on-disk size (requires npm install to have been run — falls back to a clear message if node_modules isn't present)
* -h, --health PATH	Checks for the presence of README.md, LICENSE, .gitignore, .env, and package.json
* -t, --test PATH	Walks every .py file and reports function count, average length, average cyclomatic complexity, average nesting depth, and a pyflakes-based warning count

Every flag accepts a directory only (a file path is rejected with a clear error), and every scan skips .git, node_modules, __pycache__, and virtual environment folders, so results reflect the project itself rather than version control or other irrelevant code

## Testing
* Utilized Claude to create the test suites (includes the sample codebase and pytests) in test_cli.py which covers the pure logic helpers directly (complexity/nesting/length calculations, duplicate and empty-file detection) and every flag end-to-end via Click's CliRunner, including the edge cases that came up during development — an empty target directory, a non-git directory, a missing package.json, dependencies declared but not installed, and vendored code that should be excluded from the scan.
* Run with: pytest -v

## Constraints
* -a's size ranking depends on node_modules reflecting what's declared in package.json — it reports installed packages accurately but has no way to estimate the size of a dependency that hasn't been installed.
* The -c (print-statement counting) flag from earlier iterations was removed after being folded into -i's duplicate/empty-file checks; a dedicated "debug statement" scanner may return in a future version with per-file output rather than a single aggregate count.
* Everything lives in a single cli.py file--sorry for the unorganized format--which still works, but any issues could be a bit annoying to troubleshoot
