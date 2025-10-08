# Canvas Tracker V3 - Project Rules

## Project Overview
Canvas Tracker v3 is a rebuilt application focusing on rigorous architecture, clear component boundaries, and technical debt prevention. These rules ensure we avoid the issues encountered in previous versions.

## ⚠️ CRITICAL RULES - READ FIRST
1. **ALWAYS consult `file_paths.md`, `routing_tree.md`, and `ARCHITECTURE.md` before implementing anything**
2. **UPDATE tree documents immediately when adding ANY file, route, or component**
3. **NO deviations from documented structure without explicit approval + documentation updates**

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
- **MANDATORY**: Refer to tree documents and ARCHITECTURE.md for implementation guidance
- **MANDATORY**: Any deviation from documented structure requires explicit approval AND documentation updates
- **MANDATORY**: Update tree documents whenever ANY file or component is added to the project

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

### 9. Architectural Adherence (CRITICAL)
- **Before implementing ANY change**: Consult `file_paths.md`, `routing_tree.md`, and `ARCHITECTURE.md` first
- **Implementation guidance**: All architectural patterns and file locations are pre-defined in our documentation
- **Deviation protocol**: Any deviation from documented structure requires:
  1. Explicit approval from project lead
  2. Update to affected documentation files BEFORE implementation
  3. Justification in commit message
- **Documentation updates**: Update tree documents immediately when adding:
  1. New files or directories
  2. New routes or endpoints  
  3. New components or services
  4. New dependencies or integrations
- **No exceptions**: This rule applies to ALL additions, no matter how small

## Enforcement
These rules take precedence over general coding suggestions. When in doubt, follow the most restrictive interpretation to avoid scope creep and technical debt.

## Technology Stack
*To be defined based on project requirements*