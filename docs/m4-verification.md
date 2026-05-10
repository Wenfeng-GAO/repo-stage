# M4 Verification Guide

Use this guide to verify the M4 external-validation deliverable.

Branch:

```text
origin/agent/cto/978afd99
```

Latest M4 commit:

```text
126a0c5 Complete M4 validation readiness
```

## What You Are Verifying

M4 is about validating whether RepoStage output is useful enough for real
open-source projects.

This branch provides:

- Five generated examples under `examples/m4/`.
- One static site per example.
- One `repo-profile.json` per example.
- One `README-gap-report.md` per example.
- One `validation-report.md` per example.
- One `review-notes.md` per example.
- Desktop and mobile screenshots per example.
- A repeatable generation script at `scripts/generate-m4-examples.mjs`.
- External outreach guidance in `docs/m4-external-validation.md`.

It does not yet include the final two real maintainer or target-user feedback
responses. Those must be collected after review.

## Quick Verification

From the repository root:

```bash
git fetch origin
git checkout agent/cto/978afd99
git pull
```

Confirm the branch is on the expected commit:

```bash
git rev-parse --short HEAD
```

Expected:

```text
126a0c5
```

Check that the five M4 examples exist:

```bash
find examples/m4 -maxdepth 2 -name repo-profile.json | sort
```

Expected repos:

```text
examples/m4/browser-use-browser-use/repo-profile.json
examples/m4/docusealco-docuseal/repo-profile.json
examples/m4/modelcontextprotocol-servers/repo-profile.json
examples/m4/pmndrs-zustand/repo-profile.json
examples/m4/sharkdp-bat/repo-profile.json
```

Validate the required files:

```bash
node -e "const fs=require('fs'); let count=0; for (const d of fs.readdirSync('examples/m4')) { const dir='examples/m4/'+d; const f=dir+'/repo-profile.json'; if (!fs.existsSync(f)) continue; const p=JSON.parse(fs.readFileSync(f,'utf8')); for (const required of ['README-gap-report.md','validation-report.md','review-notes.md','site/index.html','site/styles.css','screenshots/desktop.png','screenshots/mobile.png']) { if (!fs.existsSync(dir+'/'+required)) throw new Error(dir+'/'+required+' missing'); } if (!p.m4Validation?.upstreamCommit) throw new Error(d+' missing upstreamCommit'); count++; } if (count < 5) throw new Error('expected 5 examples'); console.log('validated examples:', count);"
```

Expected:

```text
validated examples: 5
```

Run the test suites:

```bash
npm test
python3 -m unittest discover -s tests
git diff --check
```

Expected:

- `npm test`: 14 passing tests.
- `python3 -m unittest discover -s tests`: 30 passing tests.
- `git diff --check`: no output.

## Review The Generated Pages

Open these files in a browser:

```text
examples/m4/sharkdp-bat/site/index.html
examples/m4/pmndrs-zustand/site/index.html
examples/m4/modelcontextprotocol-servers/site/index.html
examples/m4/browser-use-browser-use/site/index.html
examples/m4/docusealco-docuseal/site/index.html
```

For each page, check:

- The hero describes the real project without obvious exaggeration.
- The quickstart uses plausible commands from the repo.
- The features are specific to the project.
- No fake stars, downloads, testimonials, customers, benchmarks, or adoption
  claims appear.
- The desktop and mobile screenshots exist:
  - `screenshots/desktop.png`
  - `screenshots/mobile.png`

Read the matching `review-notes.md`. Each file should answer:

- Whether the hero explains the project in 10 seconds.
- Which claims still feel broad or need maintainer confirmation.
- Which section a maintainer would edit first.
- Whether the page is better than sending users directly to the README.
- Whether the internal reviewer would use, publish, or adapt it.

## Reproduce The Examples

Optional rerun:

```bash
node scripts/generate-m4-examples.mjs
```

The script:

- Fetches and resets each upstream repo checkout.
- Records the upstream commit in `repo-profile.json`.
- Calls the canonical local generator: `python3 -m repo_stage.cli generate`.
- Applies the M4 maintainer-style edit pass.
- Regenerates reports and screenshots.

Important: GitHub API metadata availability can affect non-core metadata such as
language, topics, license naming, or rate-limit warnings. The committed artifacts
are the review baseline. If rerunning the script changes files, inspect whether
the diff is only metadata enrichment/degradation before replacing committed M4
evidence.

To avoid accidental changes while reviewing, prefer the quick verification
checks above over rerunning generation.

## External Feedback Verification

M4 is not fully accepted until at least two real maintainers or target users give
clear feedback.

Use the outreach template in `docs/m4-external-validation.md`.

Record responses in `examples/m4/README.md` under `Review Status`:

```text
Repo | Reviewer | Relationship To Project | Verdict | Would Use/Publish/Adapt? | Required Edits
```

A response counts only if it gives a clear `Yes`, `No`, or `Maybe` on whether
they would use, publish, or adapt the generated page.

## Pass Criteria

This M4 branch is ready for external outreach when:

- The five local examples exist and pass the quick verification command.
- Tests pass.
- Each `review-notes.md` has repo-specific internal review notes.
- Each `validation-report.md` shows generated output status and M4 metadata.
- The reviewer agrees the remaining work is external feedback, not local
  artifact readiness.

M4 is fully complete only after:

- At least two real maintainers or target users provide clear feedback.
- Repeated edit requests are updated from that feedback.
- The next milestone decision is based on that feedback.
