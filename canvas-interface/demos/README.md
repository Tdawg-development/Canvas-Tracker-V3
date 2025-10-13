# Canvas Tracker V3 - Active Demos

This directory contains current, maintained demo files for testing and exploring Canvas API functionality.

## 🚀 Automated Demo System

**NEW**: Demos are now automatically discovered! Any `.ts` file you add to this directory will be automatically available through npm scripts.

### Usage
```bash
# List all available demos
npm run demo:list

# Run interactive demo selector
npm run demo:interactive
npm run demo  # same as above

# Run a specific demo by name
npm run demo test-get-curriculum-data
npm run demo canvas-staging-demo
npm run demo test-canvas-api
```

### How it works
- The system scans this directory for `.ts` files
- Automatically formats demo names (e.g., `test-canvas-api` → "Test Canvas Api")
- No need to manually update `package.json` when adding new demos
- Interactive mode lets you browse and select demos

## Current Active Demos

### 🎯 **`test-get-curriculum-data.ts`**
**Purpose**: Unit test for the core `getCurriculumData()` function  
**Usage**: `npm run demo test-get-curriculum-data`  
**Features**:
- Interactive course ID input (supports 1+ courses)
- Comprehensive output with performance metrics
- Validation checks and error handling
- Raw JSON data output
- Performance analysis and projections

### 🧪 **`test-canvas-api.ts`**  
**Purpose**: Comprehensive Canvas API integration testing  
**Usage**: `npm run demo test-canvas-api`  
**Features**:
- Tests all major Canvas endpoints
- API discovery and exploration
- Rate limit monitoring
- Performance benchmarking
- Raw HTTP response analysis
- Pagination testing
- Grades API exploration

### 🎪 **`canvas-staging-demo.ts`**
**Purpose**: Interactive demo of Canvas staging data structures  
**Usage**: `npm run demo canvas-staging-demo`  
**Features**:
- Interactive course ID input
- Complete staging data display
- Large dataset warnings
- Summary statistics
- Course validation
- Module and assignment exploration

## Quick Start

1. **Ensure environment is configured**:
   ```bash
   # Required in .env
   CANVAS_URL=https://canvas.instructure.com/
   CANVAS_TOKEN=your_api_token_here
   ```

2. **Run a demo**:
   ```bash
   # List all available demos
   npm run demo:list
   
   # Run interactive demo selector
   npm run demo
   
   # Run specific demos
   npm run demo test-get-curriculum-data
   npm run demo test-canvas-api
   npm run demo canvas-staging-demo
   ```

## Dependencies

All demos use the current Canvas architecture:
- `CanvasGatewayHttp` - Main Canvas API gateway
- `CanvasClient` - HTTP client with rate limiting
- `CanvasCoursesApi` - Modular courses API component
- `CanvasTypes` - TypeScript type definitions

## Architecture Integration

These demos test the **Clean Architecture** Canvas integration:
```
demos/ → CanvasGatewayHttp → CanvasClient → Canvas API
```

Features tested:
- ✅ Canvas Free API rate limiting (600 req/hour)
- ✅ Error handling and retries
- ✅ Multi-course data retrieval
- ✅ Performance metrics and monitoring
- ✅ Real API response analysis

## Archived Demos

Obsolete and legacy demos have been moved to `./archive/` directory. See `./archive/README.md` for details.

## Contributing

When adding new demos:
1. Follow the naming pattern: `test-{functionality}.ts` or `demo-{purpose}.ts`
2. Use the current Canvas architecture components
3. Include comprehensive error handling
4. Add performance monitoring
5. Document purpose and usage in this README

---

*These demos provide comprehensive testing and exploration of Canvas API integration within the Canvas Tracker V3 architecture.*