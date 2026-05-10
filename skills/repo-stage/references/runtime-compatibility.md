# Runtime Compatibility

RepoStage is portable when the agent can read local files, write output files, run shell commands, and fetch a public GitHub repository.

## Codex / Multica

Codex can use Multica for issue assignment, status, comments, and repository checkout. Those actions are orchestration, not core Skill behavior. The generated RepoStage output must still be normal files.

## Claude

Claude should read `SKILL.md`, use the scripts and templates directly, and write the same output contract. If browser automation is not available, Claude should mark desktop and mobile screenshot checks as skipped in `validation-report.md`.

## Generic Coding Agents

Generic agents can run the included Python scripts with a shell. If they cannot clone repositories, they may use any equivalent public repository fetch method and should record the substitution in `validation-report.md`.

## Optional Capability Degradation

- No browser automation: create files and record visual QA as skipped.
- No GitHub API token: use repository files only and record metadata gaps.
- GitHub rate limit: use cloned files when possible and record unavailable metadata.
- No generated image support: omit generated assets and keep the page text-led.
