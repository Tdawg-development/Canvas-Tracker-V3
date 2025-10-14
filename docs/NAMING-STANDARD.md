# Documentation Naming Standard

## Purpose
Establish consistent, descriptive naming conventions for all Canvas Tracker V3 documentation files to improve discoverability, maintainability, and professionalism.

## Naming Conventions

### File Name Format
```
[scope]-[type]-[specific-topic].md
```

### Components

#### 1. **Scope** (Optional for well-defined categories)
- `system-` - System-wide documentation
- `canvas-` - Canvas API specific
- `database-` - Database specific  
- `testing-` - Testing specific
- `project-` - Project management

#### 2. **Type** (Required)
- `architecture` - System design and patterns
- `guide` - Step-by-step instructions
- `reference` - Lookup information and specs
- `analysis` - Technical analysis and assessments
- `report` - Analysis results and findings
- `summary` - High-level overviews
- `changelog` - Change tracking
- `standard` - Standards and conventions

#### 3. **Specific Topic** (Required)
- Clear, descriptive topic using kebab-case
- Should indicate exact content scope

### Special Cases

#### Index Files
- **Main documentation index**: `README.md`
- **Category indexes**: `README.md` (within category folders)

#### Project Files
- **Version tracking**: `CHANGELOG.md`
- **Major summaries**: `[TOPIC]-SUMMARY.md` (ALL CAPS for visibility)

#### Legacy/Archive Files  
- **Development notes**: `[topic]-notes.txt`
- **Quick references**: `[topic]-reference.txt`

## Naming Examples by Category

### Architecture Documentation
- ✅ `system-architecture.md` (instead of `ARCHITECTURE.md`)
- ✅ `routing-architecture.md` (instead of `routing_tree.md`)
- ✅ `layer-design-guide.md`

### API Documentation
- ✅ `canvas-interface-guide.md` (instead of `canvas-interface-README.md`)
- ✅ `canvas-data-reference.md` (instead of `Canvas-Data-Object-Tree.md`)
- ✅ `canvas-performance-guide.md`

### Database Documentation  
- ✅ `database-architecture.md` ✅ (already good)
- ✅ `database-operations-guide.md` (instead of `db_operations_architecture.md`)
- ✅ `schema-reference.md`

### Testing Documentation
- ✅ `testing-strategy-analysis.md` (instead of `comprehensive_testing_analysis.md`)
- ✅ `query-builder-testing-analysis.md` (instead of `query_builder_unit_testing_analysis.md`)
- ✅ `unit-testing-guide.md`

### Analysis Documentation
- ✅ `implementation-accuracy-analysis.md` (instead of `implementation-vs-documentation-analysis.md`)
- ✅ `query-builder-analysis.md` ✅ (already good)
- ✅ `code-quality-report.md`

### Project Documentation
- ✅ `CHANGELOG.md` ✅ (standard convention)
- ✅ `file-structure-reference.md` (instead of `file_paths.md`)
- ✅ `DOCUMENTATION-REORGANIZATION-SUMMARY.md` (instead of `REORGANIZATION-SUMMARY.md`)

## Formatting Rules

### Case Conventions
- **File names**: `kebab-case` (lowercase with hyphens)
- **Exception - Project summaries**: `SCREAMING-KEBAB-CASE` for high visibility
- **Exception - Standard files**: `CHANGELOG.md`, `README.md`

### Length Guidelines
- **Target length**: 20-40 characters
- **Maximum length**: 60 characters
- **Minimum length**: 10 characters

### Character Rules
- **Use**: letters, numbers, hyphens
- **Avoid**: underscores, spaces, special characters
- **Never use**: CAPS except for project summaries

## Benefits of This Standard

### Discoverability
- **Predictable naming** makes files easy to find
- **Semantic prefixes** indicate content type immediately
- **Consistent patterns** reduce cognitive load

### Maintainability  
- **Clear scope indication** prevents file purpose confusion
- **Logical grouping** through naming patterns
- **Easy refactoring** with consistent structure

### Professionalism
- **Industry standard** kebab-case formatting
- **Clean appearance** in file lists and URLs
- **Version control friendly** names

### Searchability
- **Keyword rich** names improve search results
- **Pattern matching** enables bulk operations
- **IDE integration** with predictable naming

## Implementation Priority

### High Priority Renames (Confusing/Unclear)
1. `Canvas-Data-Object-Tree.md` → `canvas-data-reference.md`
2. `canvas-interface-README.md` → `canvas-interface-guide.md`
3. `comprehensive_testing_analysis.md` → `testing-strategy-analysis.md`
4. `implementation-vs-documentation-analysis.md` → `implementation-accuracy-analysis.md`

### Medium Priority Renames (Style Consistency)
1. `ARCHITECTURE.md` → `system-architecture.md`
2. `routing_tree.md` → `routing-architecture.md`
3. `db_operations_architecture.md` → `database-operations-guide.md`
4. `query_builder_unit_testing_analysis.md` → `query-builder-testing-analysis.md`

### Low Priority Renames (Minor Improvements)
1. `file_paths.md` → `file-structure-reference.md`
2. `query_builder_analysis.md` → `query-builder-analysis.md` (just underscore)

## File Organization Standard

### Within Categories
Files should be organized by type, then by specificity:
```
category/
├── README.md
├── [category]-architecture.md
├── [category]-guide.md
├── [category]-reference.md
└── [specific-topic]-analysis.md
```

This naming standard ensures consistent, professional documentation that scales with project growth.