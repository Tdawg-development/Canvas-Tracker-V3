# Canvas Tracker V3 - Archived Demos

This directory contains Canvas API demo files that are no longer actively used but are preserved for historical reference and potential future value.

## Archive Date
**October 13, 2025**

## Reason for Archiving
These demos were archived during a codebase cleanup to:
- Remove obsolete code that uses deprecated components
- Reduce cognitive load for new developers
- Keep the active demos directory focused on current, useful examples
- Preserve historical development work for reference

## Archived Categories

### 🗂️ Legacy Data Constructor Demos (Obsolete)
These demos use the old `CanvasDataConstructor` component which has been superseded by the newer `CanvasGatewayHttp` architecture:

- **`output-raw-course-data.ts`** - Raw course data output with old constructor
- **`test-all-courses.ts`** - Course listing test with old constructor  
- **`test-optimized-student-staging.ts`** - Student staging with old constructor
- **`test-student-analytics.ts`** - Student analytics with old constructor
- **`test-student-assignment-analytics.ts`** - Assignment analytics with old constructor

### 🔍 Specific API Exploration Demos (Served Their Purpose)
These demos were created to explore specific Canvas API endpoints and patterns. Their insights have been incorporated into the main codebase:

- **`demo-all-students-enrollments.ts`** - Bulk enrollments API exploration
- **`demo-grades-solution.ts`** - Grades page API replication study
- **`diagnose-submissions.ts`** - Submissions API diagnosis tool
- **`get-real-test-data.ts`** - One-time data extraction utility

## Current Active Demos

The following demos remain active in `../` (parent directory):

- ✅ **`test-get-curriculum-data.ts`** - Tests the core getCurriculumData function
- ✅ **`test-canvas-api.ts`** - Comprehensive Canvas API integration testing
- ✅ **`canvas-staging-demo.ts`** - Interactive staging data structure demo

## Using Archived Demos

⚠️ **WARNING**: These archived demos may not work with the current codebase because:
- They import deprecated components (`CanvasDataConstructor`)
- They use old API patterns that have been refactored
- Dependencies may have changed

### If You Need to Use Archived Demos:
1. **For reference only** - Review the logic and patterns, but don't run directly
2. **For restoration** - Update imports to use current components (`CanvasGatewayHttp`)
3. **For learning** - Study the Canvas API exploration techniques used

## Migration Notes

### From CanvasDataConstructor → CanvasGatewayHttp
If you need to update archived demos:

```typescript
// OLD (Archived)
import { CanvasDataConstructor } from '../staging/canvas-data-constructor';
const constructor = new CanvasDataConstructor();

// NEW (Current)
import { CanvasGatewayHttp } from './src/infrastructure/http/canvas/CanvasGatewayHttp';
const gateway = new CanvasGatewayHttp(config);
```

### Current Architecture Benefits
- Better separation of concerns
- Proper rate limiting with Canvas Free API
- Cleaner error handling
- More focused responsibilities

---

*These demos represent valuable development work and Canvas API research. While archived, they remain available for reference and learning.*