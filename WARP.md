# Canvas Tracker V3 - Project Rules

## Project Overview
Canvas Tracker v3 is a rebuilt application focusing on rigorous architecture, clear component boundaries, and technical debt prevention. These rules ensure we avoid the issues encountered in previous versions.

## Core Development Principles

### 1. Architecture & Component Boundaries
- Define clear component responsibilities before implementation
- Each component must have a single, well-defined purpose
- Components must NOT directly access other components' internal state
- Use proper interfaces and data flow patterns exclusively
- Document component boundaries and interactions before coding

### 2. Feature Scope Control (CRITICAL)
- Implement ONLY explicitly requested features
- No additional functionality, improvements, or "nice-to-have" features without explicit approval
- Stick to minimum viable implementation that satisfies requirements
- Remove any emojis or non-functional decorative elements from code
- If unsure about scope, ask for clarification before implementation

### 3. Code Quality & Technical Debt Prevention
- All new features MUST include corresponding unit tests before completion
- No code merges without passing tests and adhering to established patterns
- Follow consistent naming conventions and file organization
- Keep dependencies minimal and purpose-driven
- Each dependency must be justified and documented

### 4. Testing & Validation Protocol
- Every component must have unit tests covering happy path AND edge cases
- Tests must be updated whenever component behavior changes
- Run full test suite before considering any feature complete
- Document test coverage expectations for each component type

### 5. Documentation Requirements
- Maintain `file_paths.md` as living documentation of project structure
- Maintain `routing_tree.md` for navigation and route documentation
- Update documentation immediately when adding components, routes, or structural changes
- Always consult these files before making architectural decisions

### 6. Change Management
- Before modifying existing components, document current behavior
- Create tests to preserve existing functionality during changes
- Make incremental, well-reasoned changes only
- No refactoring without explicit requirements

### 7. Code Standards
- Remove debug comments, console.logs, and temporary code before completion
- Use established project patterns consistently
- Follow the existing codebase structure and conventions
- No deviation from agreed-upon architectural decisions

### 8. Communication & Validation
- Confirm understanding of requirements before implementation
- Ask questions about ambiguous specifications
- Validate completed work against original requirements
- Report completion with summary of what was implemented

## Enforcement
These rules take precedence over general coding suggestions. When in doubt, follow the most restrictive interpretation to avoid scope creep and technical debt.

## Technology Stack
*To be defined based on project requirements*