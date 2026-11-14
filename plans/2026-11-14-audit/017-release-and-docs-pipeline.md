# Plan 017: The release and docs pipeline holds least privilege, pinned tools and honest docs

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/2026-11-14-audit/README.md` — unless a reviewer dispatched you and
> told you they maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat b283eb13..HEAD -- .github/workflows/release.yml .github/workflows/docs.yml package.json .gitignore README.md docs/installation.md houdini_package.json .scripts/pack_icons.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none (touches `README.md` line 23 and 48; plan 018 may
  touch README lines 73-74: rebase if both land)
- **Category**: security, docs
- **Planned at**: commit `b283eb13`, 2026-11-14

## Why this matters

The release workflow gives every job write access to the repository, Pages
and an identity token, though only some jobs need any of it. It installs an
unpinned `auto-changelog` from npm and then pushes a commit to `main` with
that token: a compromised npm release would run with write access to the
repo. It publishes to PyPI with a long-lived username/password secret, when
PyPI "trusted publishing" (a short-lived token PyPI issues to this exact
workflow, no stored secret) is available. Separately, every push to `main`
redeploys the docs under the last released version number, so the docs for
a released version show API that is not released yet. Smaller items: the
README lists a "Screenshots" section that does not exist, its build badge
tracks the release workflow instead of the tests, the Houdini example file
has a stale version and a half-filled path, and the icon packing script
cannot rebuild the default icon library (Lucide).

After this plan: each job has only the permissions it needs; the changelog
tool is pinned by a committed lock file; the PyPI switch to trusted
publishing is prepared and gated on the owner; `main` deploys docs as `dev`
and only a tag deploys `<version>` + `latest`; the README, Houdini example
and pack script are correct.

**Public behaviour that changes**: the docs site gets a `dev` version built
from `main`; `latest` and numbered versions change only on a release tag.
No change to the Python package.

## Current state

Files:

- `.github/workflows/release.yml` — release on a `v*.*.*` tag: changelog,
  GitHub release, tests, PyPI.
- `.github/workflows/docs.yml` — builds and deploys the docs with `mike`
  (a tool that keeps one docs folder per version on the `gh-pages` branch).
- `package.json` — the npm manifest for `auto-changelog`.
- `.gitignore` — ignores `package-lock.json` (line 6).
- `README.md` — badge (line 23), table of contents (lines 41-49), Houdini
  note (line 111).
- `docs/installation.md` — "DCC Integration" (lines 82-85).
- `houdini_package.json` — a Houdini package example.
- `.scripts/pack_icons.py` — packs an upstream icon repo into
  `fxgui/icons/<library>.zip`.

`release.yml` (excerpts):

```yaml
# .github/workflows/release.yml:1-5
# This workflow handles the complete release process:
# 1. Generate changelog from conventional commits
# 2. Create a GitHub release with changelog content
# 3. Build and publish Python package to PyPI
# 4. Deploy documentation to GitHub Pages
```

```yaml
# .github/workflows/release.yml:28-31  (an input no job reads)
      skip-docs:
        description: "Skip documentation deployment"
        type: boolean
        default: false
```

```yaml
# .github/workflows/release.yml:44-47  (applies to every job)
permissions:
  contents: write
  pages: write
  id-token: write
```

```yaml
# .github/workflows/release.yml:80-86
      - name: Install dependencies
        if: steps.check-npm.outputs.exists == 'true'
        run: npm install && npm install -g auto-changelog

      - name: Generate changelog
        if: steps.check-npm.outputs.exists == 'true'
        run: npm run changelog
```

```yaml
# .github/workflows/release.yml:142-157
      - name: Remove package-lock.json
        if: steps.check-npm.outputs.exists == 'true'
        run: rm -f package-lock.json

      - name: Commit and push changelog
        if: steps.check-npm.outputs.exists == 'true'
        run: |
          git config --global user.name 'github-actions[bot]'
          git config --global user.email 'github-actions[bot]@users.noreply.github.com'
          git add CHANGELOG.md
          if [ -n "$(git status --porcelain)" ]; then
            git commit -m '[DOC] CHANGELOG' -m '[skip ci]'
            git push origin main
          else
            echo "No changes to commit"
          fi
```

```yaml
# .github/workflows/release.yml:184-220
  # Step 3: Build and publish to PyPI
  tests:
    name: Tests
    uses: ./.github/workflows/tests.yml

  publish-pypi:
    name: Publish to PyPI
    needs: [create-release, tests]
    if: ${{ always() && !cancelled() && needs.create-release.result == 'success' && needs.tests.result == 'success' && inputs.skip-pypi != true && startsWith(github.ref, 'refs/tags/v') }}
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        ...
      - name: Install build dependencies
        run: |
          python -m pip install --upgrade pip
          pip install setuptools wheel twine build

      - name: Build package
        run: |
          python -m build

      - name: Publish package to PyPI
        env:
          TWINE_USERNAME: ${{ secrets.PYPI_USERNAME }}
          TWINE_PASSWORD: ${{ secrets.PYPI_PASSWORD }}
        run: |
          twine upload dist/*
```

Credentials: `release.yml:36-42` declares two `workflow_call` secrets and
`release.yml:217-218` reads them: a PyPI username and a PyPI password or API
token, stored as GitHub repository secrets. No secret value is in the repo.

Which job needs what:

| Job | Needs |
|---|---|
| `generate-changelog` | `contents: write` (pushes the CHANGELOG commit to `main`) |
| `create-release` | `contents: write` (creates the draft release) |
| `tests` (calls `tests.yml`) | `contents: read` |
| `publish-pypi` | `contents: read`; `id-token: write` only once trusted publishing is on |
| any | `pages: write` — nothing uses it: docs deploy by pushing the `gh-pages` branch from `docs.yml` |

`package.json` today:

```json
{
    "scripts": {
        "changelog": "auto-changelog -p --unreleased"
    },
    "devDependencies": {
        "auto-changelog": "^2.5.0"
    }
}
```

`npm view auto-changelog version` answered `2.7.0` on 2026-11-14, so `^2.5.0`
resolves to 2.7.0 today; pinning `2.7.0` keeps today's output. `npm run`
puts `node_modules/.bin` first on the PATH, so the extra global install is
redundant. `node_modules/` stays git-ignored (`.gitignore:5`).

`docs.yml`:

```yaml
# .github/workflows/docs.yml:3-9
on:
  push:
    branches:
      - main
    tags:
      - "v*"
  workflow_dispatch:
```

```yaml
# .github/workflows/docs.yml:55-63
      - name: Deploy docs (versioned)
        if: github.ref == 'refs/heads/main' || startsWith(github.ref, 'refs/tags/')
        run: |
          # One version per tag, the newest also as "latest".
          VERSION=$(git describe --tags --abbrev=0 | sed 's/^v//')
          mike deploy --push --update-aliases "$VERSION" latest
          git fetch origin gh-pages:gh-pages --force
          mike set-default --push latest
          mike list
```

On a push to `main`, `git describe --tags --abbrev=0` returns the last
release tag, so `main`'s unreleased docs overwrite that release's docs and
`latest`.

README:

```html
<!-- README.md:22-23 -->
    <!-- GitHub build workflow -->
    <img src="https://img.shields.io/github/actions/workflow/status/healkeiser/fxgui/release.yml?&label=Build&logo=github-actions&logoColor=white" alt="Build"> &nbsp;&nbsp;
```

```markdown
<!-- README.md:43-49 -->
- [Table of Contents](#table-of-contents)
- [About](#about)
- [Installation](#installation)
- [Example](#example)
- [Documentation](#documentation)
- [Screenshots](#screenshots)
- [Contact](#contact)
```

There is no `## Screenshots` heading in `README.md`.

```markdown
<!-- README.md:110-111 -->
> [!IMPORTANT]
> In order to have access to the module inside your application, make sure to add `fxgui` to the `$PYTHONPATH` of the DCCs. For Houdini, you can find the [`houdini_package.json` example file](./houdini_package.json).
```

`docs/installation.md:82-85`:

```markdown
## DCC Integration

!!! question
    In order to have access to the module inside your application, make sure to add `fxgui` to the `$PYTHONPATH` of the DCCs. For Houdini, you can find the `houdini_package.json` example file.
```

`houdini_package.json` (whole file):

```json
{
    "path": [
        "$FXGUI"
    ],
    "load_package_once": true,
    "enable": true,
    "version": "4.1.0",
    "env": [
        {
            "PYTHONPATH": [
                {
                    "houdini_os == 'windows'": "Path/to/fxgui"
                },
                {
                    "houdini_os == 'linux'": ""
                },
                {
                    "houdini_os == 'macos'": ""
                },
                {
                    "method": "append"
                }
            ]
        }
    ]
}
```

It is referenced only by `README.md:111` and `docs/installation.md:85`
(checked with grep); it is not shipped in the package (`*.json` is excluded
in `MANIFEST.in` and `pyproject.toml`). `$FXGUI` is defined nowhere, the
`"path"` entry adds it to Houdini's own search path (fxgui has no Houdini
content), `"version": "4.1.0"` is years stale (fxgui is 14.x), and Linux and
macOS get an empty path. It stays as an example, rewritten.

`.scripts/pack_icons.py:23-31`:

```python
# What each library keeps, as globs relative to the upstream root. The paths
# inside the zip match the library's pattern in `fxicons`.
_CONTENTS = {
    "material": ["svg/*/*.svg", "LICENSE"],
    "fontawesome": ["svgs/*/*.svg", "LICENSE.txt"],
    "simple": ["icons/*.svg", "LICENSE.md"],
}

_ICONS_ROOT = Path(__file__).resolve().parent.parent / "fxgui" / "icons"
```

and `pack_icons.py:51-56` writes each file under its path relative to the
upstream root:

```python
    with zipfile.ZipFile(target, "w") as archive:
        for path in files:
            # A fixed date, so packing the same icons twice gives the same zip.
            info = zipfile.ZipInfo(path.relative_to(source).as_posix(), (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes(), compresslevel=9)
```

The shipped `fxgui/icons/lucide.zip` holds 1930 entries: `svg/<name>.svg`
(1929 icons) and `LICENSE.txt`; `fxgui/fxicons.py:178-181` reads it with
pattern `{root}/{library}/{extension}/{icon_name}.{extension}`, i.e.
`svg/<name>.svg`. The upstream repo, https://github.com/lucide-icons/lucide,
keeps its icons as `icons/<name>.svg` (beside one `.json` per icon) and its
licence as `LICENSE`. So Lucide needs a rename on the way in:
`icons/` → `svg/`, `LICENSE` → `LICENSE.txt`. The shipped zip's SVGs were
not made by this script (their dates are 2026-10-26, not the script's fixed
1980 date): this plan does **not** replace the shipped zip.

## Commands you will need

Run everything from the worktree root. `PY` means
`C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe`.

| Purpose | Command | Expected on success |
|---|---|---|
| YAML parses | `PY -c "import sys,yaml; [yaml.safe_load(open(f, encoding='utf-8')) for f in sys.argv[1:]]; print('ok')" .github/workflows/release.yml .github/workflows/docs.yml` | `ok` |
| actionlint (if installed) | `actionlint .github/workflows/release.yml .github/workflows/docs.yml` | no output, exit 0. Not installed on the planning machine: skip it and say so; do not install it |
| Lock file | `npm install --package-lock-only` | exit 0, writes `package-lock.json`, no `node_modules/` |
| Changelog dry run | `npm ci && npx auto-changelog --version` | `2.7.0` |
| Docs build | `PY -m zensical build` (only if zensical is installed in the venv) | exit 0 |
| Whole test suite | `PY -m pytest -q -n 8` | `3178 passed, 6 skipped` (unchanged: no Python package code changes) |
| Lint (as CI) | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\ruff.exe check --select F,B,BLE .` | `All checks passed!` |

Never run the tests on the real Qt platform (`tests/conftest.py` forces
`offscreen`). Never paste, print or echo a secret.

## Scope

**In scope**:

- `.github/workflows/release.yml`
- `.github/workflows/docs.yml`
- `package.json`, `package-lock.json` (create), `.gitignore` (one line)
- `README.md` (badge, table of contents, Houdini note)
- `docs/installation.md` ("DCC Integration")
- `houdini_package.json`
- `.scripts/pack_icons.py`

**Out of scope** (do NOT touch):

- `.github/workflows/tests.yml` — plan 018 owns the test matrix and its
  triggers.
- `fxgui/icons/lucide.zip` — do not repack the shipped icons; this plan only
  makes the script able to.
- `CHANGELOG.md` — the release workflow writes it.
- GitHub or PyPI settings — only the owner can change them (Phase B below
  is gated on that).
- Action version bumps (`actions/checkout@v4` vs `@v5`) — unrelated.

## Git workflow

- Work in a git worktree, never the shared checkout. After creating it, run
  `git submodule update --init --depth 1` if `.gitmodules` exists.
- Branch: `fix/release-and-docs-pipeline`.
- Commits in the repo style, e.g. `[BUILD] release: per-job permissions, pinned auto-changelog`,
  `[BUILD] docs: main deploys as dev`, `[DOC] README and Houdini example`.
- Do not push, tag or release; a workflow change is only proven on the next
  real release, which the operator runs.

## Steps

### Phase A — no owner action needed

### Step 1: Per-job least permissions in `release.yml`

1. Replace the top-level block at `release.yml:44-47` with:

   ```yaml
   # Each job asks for what it needs; nothing else may write.
   permissions:
     contents: read
   ```

2. Add a `permissions:` block to each job, right under its `name:` line:
   - `generate-changelog`: `contents: write` (comment: pushes the CHANGELOG commit)
   - `create-release`: `contents: write` (comment: creates the draft release)
   - `tests`: `contents: read` (a reusable-workflow call takes `permissions:` at the job level)
   - `publish-pypi`: `contents: read`

   `pages: write` and `id-token: write` disappear (Phase B adds
   `id-token: write` back to `publish-pypi` only).

3. Fix the header comment (`release.yml:1-5`): replace line 5 with
   `# Docs deploy from docs.yml on the same tag push, not from here.` and keep
   lines 1-4.

4. Keep the `skip-docs` input (a caller elsewhere may still pass it; removing
   a `workflow_call` input breaks such a caller) but change its description to
   `"Ignored: docs.yml deploys the docs on a tag push"`.

**Verify**:
- YAML parse command → `ok`.
- `PY -c "import yaml; w=yaml.safe_load(open('.github/workflows/release.yml', encoding='utf-8')); print(w['permissions']); print({k: j.get('permissions') for k, j in w['jobs'].items()})"`
  → `{'contents': 'read'}` then
  `{'generate-changelog': {'contents': 'write'}, 'create-release': {'contents': 'write'}, 'tests': {'contents': 'read'}, 'publish-pypi': {'contents': 'read'}}`.
- `grep -n "pages: write\|id-token" .github/workflows/release.yml` → no output.

### Step 2: Pin auto-changelog with a committed lock

1. `package.json`: change `"auto-changelog": "^2.5.0"` to `"auto-changelog": "2.7.0"`
   (first run `npm view auto-changelog version`; if it no longer prints
   `2.7.0`, still pin `2.7.0`, the version CI used at planning time).
2. `.gitignore:6`: delete the `package-lock.json` line (keep `node_modules/`
   and the comment above it, reworded to `# Node.js modules`).
3. Run `npm install --package-lock-only` → creates `package-lock.json`.
4. `release.yml:80-82`: change the step to

   ```yaml
         - name: Install dependencies
           if: steps.check-npm.outputs.exists == 'true'
           # The lock pins auto-changelog and everything it pulls in.
           run: npm ci
   ```

5. Delete the `Remove package-lock.json` step (`release.yml:142-144`).
   `npm ci` never rewrites the lock, and `node_modules/` is ignored, so
   `git status --porcelain` in the next step still sees only `CHANGELOG.md`.

**Verify**:
- `git check-ignore package-lock.json` → no output (exit 1: it is no longer ignored).
- `npm ci && npx auto-changelog --version` → `2.7.0`. Then delete the local
  `node_modules/` folder.
- `grep -n "npm install\|package-lock" .github/workflows/release.yml` → no output.
- `git status --porcelain` → `package.json`, `package-lock.json`, `.gitignore`,
  `release.yml` only (plus earlier steps' files).

### Step 3: Docs — `main` deploys as `dev`, a tag as `<version>` + `latest`

Replace `docs.yml:55-63` with two steps:

```yaml
      # main is unreleased: it never touches a released version or latest.
      - name: Deploy docs (dev)
        if: github.ref == 'refs/heads/main'
        run: |
          mike deploy --push dev
          mike list

      - name: Deploy docs (release)
        if: startsWith(github.ref, 'refs/tags/')
        run: |
          VERSION="${GITHUB_REF_NAME#v}"
          mike deploy --push --update-aliases "$VERSION" latest
          git fetch origin gh-pages:gh-pages --force
          mike set-default --push latest
          mike list
```

Keep the earlier steps (`Configure Git`, `Fetch gh-pages branch`) and their
`if:` as they are.

**Verify**:
- YAML parse command → `ok`.
- `grep -n "git describe" .github/workflows/docs.yml` → no output.
- `grep -n "mike deploy" .github/workflows/docs.yml` → two lines, one with
  `dev`, one with `"$VERSION" latest`.

### Step 4: README — badge and table of contents

1. `README.md:22-23`: change the comment to `<!-- Tests workflow -->` and the
   image to
   `<a href="https://github.com/healkeiser/fxgui/actions/workflows/tests.yml"><img src="https://img.shields.io/github/actions/workflow/status/healkeiser/fxgui/tests.yml?branch=main&label=Tests&logo=github-actions&logoColor=white" alt="Tests"></a> &nbsp;&nbsp;`
2. `README.md:48`: delete `- [Screenshots](#screenshots)`.

**Verify**: `grep -n "release.yml\|Screenshots" README.md` → no output;
`grep -c "tests.yml" README.md` → `1` (the line holds two mentions; grep
counts lines).

### Step 5: A correct Houdini package example

Replace `houdini_package.json` with:

```json
{
    "load_package_once": true,
    "env": [
        { "FXGUI_LIBS": "C:/path/to/fxgui_libs" },
        { "PYTHONPATH": { "value": "$FXGUI_LIBS", "method": "append" } }
    ]
}
```

Then replace `README.md:110-111` with:

```markdown
> [!IMPORTANT]
> A DCC's Python only sees fxgui if it is on its `PYTHONPATH`. For Houdini, install fxgui and its dependencies into a folder of their own with a Python of the same version as Houdini's (3.11 for Houdini 21): `python3.11 -m pip install --target C:/path/to/fxgui_libs fxgui`. PySide6 is not installed, since fxgui does not depend on it. Then copy [`houdini_package.json`](./houdini_package.json) into Houdini's `packages` folder and set `FXGUI_LIBS` in it to that folder.
```

and `docs/installation.md:84-85` with the same text as a `!!! question`
block (four-space indented), linking the file as
`[houdini_package.json](https://github.com/healkeiser/fxgui/blob/main/houdini_package.json)`
(an absolute link: the file is not part of the docs site, and the docs build
is strict on relative links).

**Verify**:
- `PY -c "import json; print(json.load(open('houdini_package.json')))"` → prints the dict, no error.
- `grep -n "4.1.0\|Path/to/fxgui\|\$FXGUI\"" houdini_package.json` → no output.
- If zensical is installed: `PY -m zensical build` → exit 0.

### Step 6: `pack_icons.py` rebuilds Lucide

1. Add `"lucide": ["icons/*.svg", "LICENSE"],` to `_CONTENTS`.
2. Below `_CONTENTS`, add:

   ```python
   # Where an upstream path lands in the zip when fxicons expects another.
   _RENAMES = {"lucide": {"icons/": "svg/", "LICENSE": "LICENSE.txt"}}
   ```

3. In `pack`, compute the name in the zip through the renames:

   ```python
           name = path.relative_to(source).as_posix()
           for old, new in _RENAMES.get(library, {}).items():
               if name.startswith(old):
                   name = new + name[len(old):]
                   break
           # A fixed date, so packing the same icons twice gives the same zip.
           info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
   ```

4. Add an optional `target: Optional[Path] = None` parameter to `pack`
   (default `_ICONS_ROOT / f"{library}.zip"`, Args entry
   `target: Where to write the zip; fxgui/icons/<library>.zip by default.`)
   and a `--output` argument (`type=Path`, default `None`) in the `__main__`
   block passed as `target`, so a pack can be checked without overwriting a
   shipped zip. Add `from typing import Optional` under the `# Built-in`
   imports.
5. In the module docstring add the usage line
   `python .scripts/pack_icons.py lucide ~/src/lucide` and the upstream line
   `lucide: https://github.com/lucide-icons/lucide`.

**Verify** (a fake upstream tree, no network):

```
PY -c "import pathlib, runpy, sys, tempfile, zipfile; d = pathlib.Path(tempfile.mkdtemp()); (d/'icons').mkdir(); (d/'icons'/'a.svg').write_text('<svg/>'); (d/'icons'/'a.json').write_text('{}'); (d/'LICENSE').write_text('ISC'); out = d/'out.zip'; sys.argv = ['pack_icons.py', 'lucide', str(d), '--output', str(out)]; runpy.run_path('.scripts/pack_icons.py', run_name='__main__'); print(sorted(zipfile.ZipFile(out).namelist()))"
```

→ a line `...out.zip: 2 files, 0.0 MB` then `['LICENSE.txt', 'svg/a.svg']`.
`git status --porcelain fxgui/icons` → no output (the shipped zips are untouched).

### Step 7: Whole-repo checks for Phase A

**Verify**:
- `PY -m pytest -q -n 8` → `3178 passed, 6 skipped` (or today's base, unchanged).
- `...\ruff.exe check --select F,B,BLE .` → `All checks passed!`
- `git status --porcelain` lists only in-scope files.

Commit Phase A. Then report to the operator and go on to Phase B only if
the operator has confirmed the PyPI setting below.

### Phase B — trusted publishing (STOP for the operator first)

**STOP before Step 8** unless the operator has confirmed, in writing, that on
https://pypi.org/manage/project/fxgui/settings/publishing/ a GitHub trusted
publisher exists with: owner `healkeiser`, repository `fxgui`, workflow
`release.yml`, environment `pypi`. Without it, the next release fails to
publish. If it is not confirmed, leave `publish-pypi` on twine (Phase A
state), mark the plan "DONE (Phase A); Phase B waiting on PyPI trusted
publisher" in the README row, and stop.

### Step 8: Publish with `pypa/gh-action-pypi-publish`

In `publish-pypi`:

1. Add, beside `runs-on:`:

   ```yaml
       # PyPI trusts this workflow in this environment: no stored token.
       environment:
         name: pypi
         url: https://pypi.org/p/fxgui
       permissions:
         contents: read
         id-token: write
   ```

   (replacing the `permissions: contents: read` from Step 1).
2. Change `pip install setuptools wheel twine build` to `pip install build`.
3. Replace the `Publish package to PyPI` step (with its `env:`) by:

   ```yaml
         - name: Publish package to PyPI
           uses: pypa/gh-action-pypi-publish@release/v1
   ```

4. Keep the `secrets:` declarations in `workflow_call` (lines 36-42) so a
   caller that passes them does not break, but change both descriptions to
   `"Unused: PyPI trusted publishing"`.

**Verify**:
- YAML parse command → `ok`.
- `grep -n "twine\|TWINE_\|secrets\.PYPI" .github/workflows/release.yml` → no output.
- `grep -n "id-token: write" .github/workflows/release.yml` → exactly one line, inside `publish-pypi`.

Commit Phase B separately (`[BUILD] release: publish to PyPI by trusted publishing`).
Tell the operator: after the first release that publishes this way, revoke
the old PyPI API token on pypi.org and delete the `PYPI_USERNAME` and
`PYPI_PASSWORD` repository secrets on GitHub (rotation: the old token stops
being a standing risk).

## Test plan

No Python test: these are CI and docs files. Checks instead:

- YAML parse of both workflows; `actionlint` when available.
- Permission map printed per job (Step 1).
- `npx auto-changelog --version` is `2.7.0` after `npm ci` (Step 2).
- Fake-upstream pack gives `['LICENSE.txt', 'svg/a.svg']` (Step 6).
- The docs build, when zensical is installed.
- Dry reading of the job graph after editing: `generate-changelog` →
  `create-release`; `tests` in parallel; `publish-pypi` needs both and runs
  only on a `refs/tags/v` ref. No `needs:` or `if:` changed in this plan.

## Done criteria

- [ ] `release.yml` top-level permissions are `contents: read`; each job has its own block (Step 1 print)
- [ ] `grep -n "pages: write" .github/workflows/*.yml` → no output
- [ ] `package-lock.json` is committed; `package.json` pins `"auto-changelog": "2.7.0"`
- [ ] `grep -n "npm install -g\|rm -f package-lock" .github/workflows/release.yml` → no output
- [ ] `docs.yml` deploys `dev` on `main` and `<version>` + `latest` on a tag only
- [ ] `grep -n "Screenshots\|release.yml" README.md` → no output
- [ ] `houdini_package.json` parses and holds no `4.1.0` / `Path/to/fxgui`
- [ ] Step 6 verification prints `['LICENSE.txt', 'svg/a.svg']`
- [ ] Test suite and ruff unchanged and green
- [ ] Phase B done, or the README row says it waits on the PyPI trusted publisher
- [ ] `plans/2026-11-14-audit/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- The code at the locations in "Current state" does not match the excerpts.
- Phase B without the operator's written confirmation of the PyPI trusted
  publisher (see the Phase B gate).
- `npm install --package-lock-only` resolves `auto-changelog` to a version
  other than `2.7.0`, or reports a vulnerability rated high or critical
  (`npm audit` output): report it, do not upgrade transitive packages by hand.
- Any step seems to need a GitHub or PyPI setting, a secret value, a push,
  a tag or a test release.
- The docs build fails on a link in `docs/installation.md` after Step 5.
- A change seems to need `tests.yml` (plan 018 owns it).

## Maintenance notes

- Bumping `auto-changelog` now means editing `package.json` and running
  `npm install --package-lock-only`; review the lock diff like code.
- With trusted publishing, renaming `release.yml` or the `pypi` environment
  breaks publishing until the PyPI publisher is updated to match.
- A reusable call of `release.yml` from another repository cannot publish
  through this repo's trusted publisher; it is only meant to run here.
- The docs version list gains `dev`; nothing removes old versions.
- Deferred: repacking the shipped `lucide.zip` from upstream (its current
  SVGs came from another source; repacking changes every icon's file and
  needs a visual check).
- Reviewers: read the permission map job by job, and check no step uses
  `secrets.*` after Phase B.
- Pascal: nothing to change; the `latest` docs it links to now match the
  released fxgui it pins.
