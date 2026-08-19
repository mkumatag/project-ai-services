# Proposal Document Rules

When the user asks you to write, create, draft, or generate a proposal, design document, design
plan, implementation proposal, service plan, high-level design, or any similar document intended
for the `docs/proposals/` directory, you **must** follow these rules.

## Always use the project proposal template

The canonical template is at `docs/proposals/PROPOSAL_TEMPLATE.md`.
Before writing any proposal:

1. Read `docs/proposals/PROPOSAL_TEMPLATE.md` to load the current template structure.
2. Choose the correct **document type** from the types listed in the template title comment:
   - `Design Plan` — a feature or configuration change within a known component
   - `Implementation Proposal` — a new microservice or endpoint
   - `High-Level Design` — infrastructure, architecture, or cross-cutting system change
   - `Service Plan` — a new catalog service (standalone container + assets)
   - `Design Proposal` — a focused, well-scoped feature (< 5 files changed)
   - `Executive Brief` — leadership-facing one-pager (no code, no diagrams)
   - `Release Plan` — a quarter-scoped delivery plan across multiple pillars
3. Use the **section inclusion table** at the bottom of the template to determine which sections
   are required vs optional for the chosen document type.
4. Fill in the metadata block (author, reviewers, status, Jira epic, dates).
5. Delete all template comment blocks (`<!-- ... -->`) from the final document.
6. Save the file as `docs/proposals/<kebab-case-name>.md`.

## Style references — committed documents only

Use only the following **committed** documents as style and structure references.
Do NOT reference untracked or staged files.

Microservice / endpoint proposals:
- `docs/proposals/entity_extraction_service_proposal.md`
- `docs/proposals/translation_service_proposal.md`
- `docs/proposals/summarization_endpoint_design_doc.md`
- `docs/proposals/similarity-search-proposal.md`
- `docs/proposals/digitize_documents_endpoints.md`
- `docs/proposals/conversational_rag.md`

Infrastructure / architecture proposals:
- `docs/proposals/mcp-sidecar-proposal.md`
- `docs/proposals/manageiq-authn-authz-plan.md`

Configuration / catalog proposals:
- `docs/proposals/catalog/application-deployment-api-proposal.md`
- `docs/proposals/catalog/catalog-services-installation-proposal.md`
- `docs/proposals/catalog/db-design-proposal.md`

Security proposals:
- `docs/proposals/password-generator-security-proposal.md`
- `docs/proposals/non-root-user-configuration-proposal.md`

Queue / async design proposals:
- `docs/proposals/docling_conversion_queue.md`
- `docs/proposals/import_export_apis_design.md`

## File naming convention

File names must be lowercase, hyphen-separated, and descriptive:
- `fraud-detection-service-plan.md`  ✓
- `vllm-deployment-profiles.md`      ✓
- `FraudDetection.md`                ✗
- `proposal.md`                      ✗

## Mermaid diagrams

Every proposal with an architecture section must include at least one Mermaid diagram.
Use `graph LR` for component topology, `sequenceDiagram` for request/response flows,
`stateDiagram-v2` for state machines. Node labels must include port numbers when
networking is involved.

## Non-Goals and What Is NOT in Scope

Every proposal must contain either a **Non-Goals** subsection in the Overview or a dedicated
**What Is NOT in Scope** section. Be explicit — reviewers use this to prevent scope creep.
Always include at minimum: OpenShift/Kubernetes support (if Podman-only), horizontal scaling
(if single-replica), and UI (if API-only).
