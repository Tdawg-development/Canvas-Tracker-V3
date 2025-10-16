# Canvas Interface System

This directory contains our complete Canvas LMS integration system, organized for clarity and maintainability.

## 📁 Directory Structure

### `/core/`
**Production-ready Canvas interface components**
- `canvas-calls.ts` - Main Canvas API interface with database-ready request/response handling
- `pull-student-grades.ts` - Optimized student grade pulling with minimal API calls

### `/staging/` 
**Canvas data staging system (80% of Canvas interfacing)**
- `canvas-staging-data.ts` - Core data classes that mirror Canvas API responses
- `canvas-data-constructor.ts` - Orchestrates Canvas API calls to build complete staging data

### `/config/`
**API configuration and field mappings**
- `api-field-mappings.ts` - Canvas API parameter configuration system

### `/demos/`
**Interactive demos and testing tools**
- `canvas-staging-demo.ts` - Main demo for Canvas staging system
- `orchestrator-demo.ts` - Pipeline orchestrator demonstration
- `test-canvas-api.ts` - General Canvas API testing
- `test-get-curriculum-data.ts` - Curriculum data testing
- `test-student-assignment-analytics.ts` - Student analytics testing

### `/orchestration/`
**Pipeline orchestration and configuration**
- `configuration-manager.ts` - Sync configuration management
- `pipeline-monitor.ts` - Pipeline monitoring and metrics
- `pipeline-orchestrator.ts` - Main pipeline orchestration engine

### `/types/`
**TypeScript type definitions**
- `canvas-api.ts` - Comprehensive Canvas API interfaces
- `field-mappings.ts` - Field mapping configuration types
- `sync-configuration.ts` - Sync configuration interfaces

### `/utils/`
**Professional utilities**
- `api-param-builder.ts` - Canvas API parameter builder
- `field-mapper.ts` - Professional field mapping engine
- `logger.ts` - Structured logging system
- `timestamp-parser.ts` - Canvas timestamp handling

## 🎯 Primary Canvas Interface (80% of usage)

### Canvas Staging System
The staging system handles the majority of our Canvas interfacing needs:

```typescript
import { CanvasDataConstructor } from './staging/canvas-data-constructor';
import { CanvasCourseStaging } from './staging/canvas-staging-data';

// Build complete Canvas course data structure
const constructor = new CanvasDataConstructor();
const courseData = await constructor.constructCourseData(courseId);
```

**What it provides:**
- ✅ Complete course information
- ✅ All student enrollment data with grades  
- ✅ All modules and assignments
- ✅ Structured, clean data classes
- ✅ Minimal API calls (typically 3-4 per course, may vary 2-6 based on complexity)
- ✅ Ready for database transformation

## 🚀 Quick Start

### Run Interactive Demos
```bash
# Main Canvas staging demo
npx tsx canvas-interface/demos/canvas-staging-demo.ts

# Pipeline orchestrator demo (complete pipeline)
npx tsx canvas-interface/demos/orchestrator-demo.ts

# Canvas API testing
npx tsx canvas-interface/demos/test-canvas-api.ts
```

### Use Canvas Interface in Your Code
```typescript
// Using the main Canvas interface entry point
import { CanvasDataConstructor } from 'canvas-interface';

const constructor = new CanvasDataConstructor();
const courseData = await constructor.constructCourseData(12972117);

// Access structured data
console.log(`Course: ${courseData.name}`);
console.log(`Students: ${courseData.students.length}`);
console.log(`Modules: ${courseData.modules.length}`);
console.log(`Assignments: ${courseData.getAllAssignments().length}`);
```

### Use Pipeline Orchestrator for Full Processing
```typescript
import { PipelineOrchestrator } from 'canvas-interface/orchestration/pipeline-orchestrator';

const orchestrator = new PipelineOrchestrator();
const result = await orchestrator.processCourse(12972117);

// Complete pipeline result
console.log(`Success: ${result.success}`);
console.log(`Processing time: ${result.metadata.processingTime}ms`);
console.log(`API calls: ${result.metadata.apiCalls}`);
```

## 📊 Data Structure Overview

### Course Object
- Basic course info (ID, name, course code)
- Calendar integration
- Contains students and modules arrays

### Student Objects  
- Enrollment details with grades
- User information (name, login, etc.)
- Current/final scores
- Activity tracking

### Module Objects
- Course structure organization
- Contains assignments arrays
- Publication status

### Assignment Objects
- From modules API (not submissions)
- Assignment metadata
- Points possible
- Publication status

## 💡 Design Philosophy

1. **Raw Data Staging** - Preserve Canvas API responses exactly
2. **Minimal API Calls** - Maximum efficiency
3. **Clean Structure** - Easy to work with and transform
4. **Database Ready** - Prepared for loader transformation
5. **Future Proof** - Extensible and maintainable

## 🔧 Configuration

Ensure your `.env` file has:
```
CANVAS_URL=your_canvas_instance_url
CANVAS_TOKEN=your_api_token
```

## 📈 API Efficiency

The staging system is highly optimized:
- **Typically 3-4 API calls** total per course (range: 2-6 calls depending on course complexity)
- **96%+ API call reduction** compared to individual submission calls  
- **Sub-2 second** processing for typical courses (varies with course size and complexity)
- **Rate limit friendly** with built-in batching and delays

### Performance Context by Course Size

| Course Type | Students | Modules | API Calls | Typical Time | Notes |
|-------------|----------|---------|-----------|--------------|-------|
| Small Course | 1-25 | 5-10 | 2-3 calls | <1 second | Minimal data, fastest processing |
| Medium Course | 25-100 | 10-15 | 3-4 calls | 1-2 seconds | Standard optimization applies |
| Large Course | 100-500 | 15-25 | 4-5 calls | 2-4 seconds | More modules/assignments |
| Enterprise Course | 500+ | 25+ | 5-6 calls | 4-8 seconds | Complex structure, maximum calls |

**Assignment Analytics Loading:**
- Only triggered for students with missing assignments (`current_score ≠ final_score`)
- Batch processing: 5 students per batch for optimal performance
- Smart optimization can skip 40-80% of API calls in typical courses

---

**Next Phase:** Build database loader to transform staging data into your final database schema.