# Agent Compatibility

RepoStage is designed for Codex, Claude, and other coding agents that can operate on a local filesystem.

The first implementation may be validated in Codex/Multica, but the Skill contract should remain portable. A different agent runtime should be able to read the instructions, use the templates and scripts, and produce the same output shape.

## Target Agent Capabilities

RepoStage assumes the agent can:

- Read local files.
- Write output files.
- Run local shell commands.
- Fetch or clone a public GitHub repository.
- Inspect generated HTML/CSS.
- Report validation results to the user.

Browser rendering and screenshots are preferred, but they should not be mandatory for the core generation path. If screenshots are unavailable, the agent should still produce files and record that visual QA was not completed.

## Portability Rules

Skill instructions should:

- Use plain Markdown.
- Keep workflow steps explicit and ordered.
- Store reusable logic in scripts instead of relying on one agent's hidden behavior.
- Keep inputs and outputs as normal files.
- Avoid depending on Multica issue IDs, Codex-only tools, or Claude-only conventions in the core workflow.
- Put platform-specific notes in separate compatibility sections.

Scripts should:

- Use stable command-line interfaces.
- Accept explicit input and output paths.
- Emit machine-readable reports where useful.
- Fail with clear messages.
- Avoid requiring interactive prompts for the main path.

Templates should:

- Be static files in the repository.
- Avoid remote runtime dependencies.
- Work without a hosted service.

## Runtime Notes

### Codex / Multica

Codex can use the Skill inside a Multica issue workflow, write generated files into a checked-out repo, run validation commands, and post results back to the issue.

Multica issue management is not part of the core RepoStage product contract. It is only one orchestration environment.

### Claude

Claude should be able to use the same `SKILL.md`, templates, scripts, and checklists in a local project workspace.

The Skill should not assume access to Codex-specific tools. If Claude lacks browser automation, it should record visual QA as skipped and still complete the file outputs.

### Generic Coding Agents

Other agents can use RepoStage if they can follow Markdown instructions, run shell commands, and edit files. They may skip optional capabilities such as browser screenshots, but must preserve the source-grounding and output-file contract.

## Compatibility Acceptance Criteria

RepoStage is portable enough when:

- The Skill can be understood from repository files alone.
- The core workflow does not reference hidden platform state.
- Generated outputs use the same file contract across agents.
- Validation reports clearly state which checks were run and which were skipped.
- Platform-specific orchestration is documented separately from the Skill's product behavior.
