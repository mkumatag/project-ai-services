---
name: write-proposal
description: Use when the user wants to write, create, draft, or generate a proposal, design document, design plan, implementation proposal, service plan, or high-level design for the docs/proposals/ directory.
---

# Write Proposal

Follow these steps every time a proposal document is requested.

## Step 1 — Determine the document type

Ask the user (or infer from context) which document type applies:

| Type | When to use |
|:-----|:------------|
| `Design Plan` | Feature or configuration change within a known component |
| `Implementation Proposal` | New microservice or endpoint being introduced |
| `High-Level Design` | Infrastructure, architecture, or cross-cutting system change |
| `Service Plan` | New catalog service (standalone container + assets) |
| `Design Proposal` | Focused, well-scoped feature — fewer than 5 files changed |
| `Executive Brief` | Leadership-facing one-pager — no code, no diagrams |
| `Release Plan` | Quarter-scoped delivery plan across multiple pillars |

If the type is ambiguous, use `ask_followup_question` to confirm before proceeding.

## Step 2 — Load the template

Read `docs/proposals/PROPOSAL_TEMPLATE.md` using `read_file`.
Do not start writing until this file has been read in the current context.

## Step 3 — Determine required sections

Use the section inclusion table at the bottom of `PROPOSAL_TEMPLATE.md` to decide which
sections are **required** vs **optional** for the chosen document type.

Required for every type:
- Title (pattern: `[Component / Feature Name] — [Document Type]`)
- Metadata block (author, reviewers, status, Jira epic, dates)
- Overview / Goal / Scope / Non-Goals
- Problem Statement
- Proposed Solution

## Step 4 — Gather missing information

Before writing, identify any gaps. Use `ask_followup_question` for the most critical unknowns.
Typical questions:
- What is the Jira epic key?
- Who are the reviewers?
- What is the target runtime (Podman only, or also OpenShift)?
- Is this sync-only, async-only, or both?

Do NOT ask for information that is already clear from context.

## Step 5 — Write the proposal

Follow the template exactly:
1. Title line: `# [Component] — [Document Type]`
2. Metadata block immediately below the title
3. Sections in the order defined in the template
4. Every Mermaid diagram must use one of: `graph LR`, `flowchart TB`, `sequenceDiagram`, `stateDiagram-v2`
5. Node labels in diagrams must include port numbers when networking is involved
6. Delete all `<!-- ... -->` comment blocks — they must not appear in the final document
7. Endpoint specs must each have: request JSON example, response JSON example, and error table

## Step 6 — Style check against committed references

Before finalising, verify the document matches the style of a committed reference for the same type:

| Type | Committed reference |
|:-----|:--------------------|
| `Implementation Proposal` | `docs/proposals/entity_extraction_service_proposal.md` |
| `Implementation Proposal` | `docs/proposals/translation_service_proposal.md` |
| `High-Level Design` | `docs/proposals/mcp-sidecar-proposal.md` |
| `High-Level Design` | `docs/proposals/manageiq-authn-authz-plan.md` |
| `Design Proposal` | `docs/proposals/similarity-search-proposal.md` |
| `Design Proposal` | `docs/proposals/docling_conversion_queue.md` |
| `Design Plan` | `docs/proposals/catalog/application-deployment-api-proposal.md` |

Read the relevant reference only if style clarification is needed — do not read all of them.

## Step 7 — Save the file

Save to `docs/proposals/<kebab-case-name>.md` using `write_file`.

File naming rules:
- Lowercase, hyphen-separated, descriptive
- No uppercase, no underscores in the stem, no generic names like `proposal.md`

## Step 8 — Confirm

Report the file path written and list the sections included. Note any sections that were
intentionally omitted and why.
