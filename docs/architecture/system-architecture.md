# Current System Architecture

**Architecture Style:** Modular Component System  
**Guiding Principle:** Specialized components with clear boundaries and responsibilities, optimized for Canvas LMS integration and data processing.

## Technology Stack

- **Canvas API Integration**: TypeScript with custom HTTP clients
- **Database Layer**: Python with SQLAlchemy ORM
- **Testing**: Pytest (database), Jest (Canvas interface)  
- **Development**: Hybrid Python/TypeScript development workflow
- **Architecture Pattern**: Component-based with clear data boundaries

> This system prioritizes **working Canvas integration** and **reliable data storage** over theoretical architectural purity. Each component is optimized for its specific domain.

---

## Component Architecture Overview

The system consists of **three main components** that work together to provide Canvas LMS integration and data management:

| Component | Technology | Purpose | Responsibilities |
|-----------|------------|---------|------------------|
| **Canvas Interface** | TypeScript | Canvas LMS Integration | API calls, data staging, Canvas-specific logic |
| **Database Layer** | Python | Data Storage & Operations | Models, queries, transactions, data integrity |
| **Infrastructure** | TypeScript | HTTP & Utilities | Canvas HTTP client, API configuration, utilities |

### Design Principles

1. **Component Specialization** - Each component optimized for its domain
2. **Clear Boundaries** - Well-defined interfaces between components  
3. **Technology Choice** - Best tool for each job (Python for data, TypeScript for API)
4. **Practical Focus** - Working systems over theoretical architecture

---

## 1) Actual Project Structure

```
📁 Canvas-Tracker-V3/
├── 📁 canvas-interface/           🟢 TYPESCRIPT - Canvas LMS Integration
│   ├── 📁 core/                   ✅ Core Canvas API interface
│   │   ├── canvas-calls.ts         ✅ Main Canvas API processing
│   │   └── pull-student-grades.ts  ✅ Grade extraction system
│   ├── 📁 staging/                ✅ Canvas data staging (80% of usage)
│   │   ├── canvas-data-constructor.ts  ✅ API orchestration
│   │   └── canvas-staging-data.ts      ✅ Data models
│   ├── 📁 demos/                  ✅ Interactive testing tools
│   ├── 📁 tests/                  ✅ Jest-based testing suite
│   └── index.ts                   ✅ Main exports
│
├── 📁 database/                   🐍 PYTHON - Data Storage & Operations  
│   ├── 📁 models/                 ✅ SQLAlchemy models (4-layer design)
│   │   ├── layer0_lifecycle.py    ✅ Object lifecycle management
│   │   ├── layer1_canvas.py       ✅ Canvas data models
│   │   ├── layer2_historical.py   ✅ Historical/time-series data
│   │   └── layer3_metadata.py     ✅ User metadata
│   ├── 📁 operations/             ✅ Database operations
│   │   ├── base/                  ✅ Base operations
│   │   ├── layer1/                ✅ Canvas data operations
│   │   └── utilities/             ✅ Query utilities
│   └── 📁 tests/                  ✅ Pytest-based comprehensive tests
│
├── 📁 src/                       🔧 INFRASTRUCTURE (minimal)
│   ├── index.ts                   ✅ Main application entry (stub)
│   └── 📁 infrastructure/         ✅ HTTP clients and utilities
│       └── 📁 http/canvas/        ✅ Canvas HTTP client infrastructure
│
└── 📁 docs/                      📚 DOCUMENTATION
    ├── 📁 architecture/           ✅ System architecture docs
    ├── 📁 api/                    ✅ Canvas interface documentation
    ├── 📁 database/               ✅ Database architecture docs
    ├── 📁 testing/                ✅ Testing strategy and analysis
    ├── 📁 analysis/               ✅ Technical analysis reports
    └── 📁 project/                ✅ Project management docs
```

---

## 2) Component Boundaries & Integration

### **Canvas Interface Component** (TypeScript)
- **Responsibility**: All Canvas LMS integration, API calls, data staging
- **Technology**: TypeScript with custom HTTP client
- **Testing**: Jest-based unit and integration tests
- **Key Files**: `canvas-calls.ts`, `canvas-data-constructor.ts`, staging models

### **Database Component** (Python) 
- **Responsibility**: Data storage, queries, transactions, data integrity
- **Technology**: Python with SQLAlchemy ORM
- **Testing**: Pytest with comprehensive model and operation tests
- **Key Files**: 4-layer model architecture, operations, utilities

### **Infrastructure Component** (TypeScript)
- **Responsibility**: HTTP clients, configuration, utilities
- **Technology**: TypeScript 
- **Key Files**: Canvas HTTP client, API configuration

---

## 3) Data Flow & Integration Patterns

### **Canvas Data Extraction Flow**
```
1. Canvas API Call (TypeScript)
   → canvas-interface/core/canvas-calls.ts
   → API orchestration and rate limiting
   → Data staging and transformation

2. Data Processing (TypeScript) 
   → canvas-interface/staging/canvas-data-constructor.ts
   → Build complete course data structures
   → Clean and validate Canvas responses

3. Database Storage (Python)
   → database/operations/layer1/
   → SQLAlchemy models and operations
   → Transaction management and data integrity
```

### **Component Communication**
- **Canvas → Database**: Data transformation and loading workflows
- **Database → Canvas**: Configuration and state management
- **Testing**: Independent test suites for each component

---

## 4) Development Workflow

### **Canvas Interface Development** (TypeScript)
```bash
# Navigate to Canvas interface
cd canvas-interface

# Install dependencies
npm install

# Run interactive demos
npx tsx demos/canvas-staging-demo.ts

# Run tests
npm test
```

### **Database Development** (Python)
```bash
# Navigate to database
cd database

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/

# Run specific test suites
pytest tests/test_layer1_models.py -v
```

### **Component Integration**
Data flows from Canvas interface (TypeScript) → Database operations (Python) through:
1. **Canvas data staging** - Clean and structure Canvas API responses
2. **Data transformation** - Convert TypeScript objects to Python models
3. **Database persistence** - Store using SQLAlchemy operations

---

## 5) Key Features & Capabilities

### **Canvas Integration**
- **Efficient API Usage**: 3-4 calls per course (vs 100s with naive approaches)
- **Rate Limit Management**: Built-in delays and batching
- **Error Handling**: Comprehensive retry and backoff strategies
- **Data Staging**: Clean object models that mirror Canvas API

### **Database Architecture** 
- **4-Layer Design**: Lifecycle, Canvas, Historical, User metadata
- **Data Integrity**: Transaction management and referential integrity
- **Performance**: Optimized queries and bulk operations
- **Testing**: 95% test coverage with comprehensive fixtures

### **Development Experience**
- **Clear Boundaries**: Each component has specific responsibilities
- **Technology Optimization**: Best tool for each job
- **Comprehensive Testing**: Independent test suites for each component
- **Documentation**: Accurate and up-to-date component documentation

---

## 6) Getting Started

### **Prerequisites**
- **Node.js 18+** for TypeScript components
- **Python 3.9+** for database components
- **Canvas LMS** API access with valid token

### **Environment Setup**
```bash
# Copy environment template
cp .env.example .env

# Configure Canvas API access
CANVAS_URL=https://your-canvas-instance.com
CANVAS_TOKEN=your_canvas_api_token

# Configure database (if using)
DATABASE_URL=sqlite:///canvas_tracker.db
```

### **Quick Start**
```bash
# Test Canvas integration
cd canvas-interface
npm install
npx tsx demos/canvas-staging-demo.ts

# Test database operations
cd ../database
pip install -r requirements.txt
pytest tests/test_layer1_models.py -v
```

---

## 7) Component Documentation

For detailed information about each component:

- **[Canvas Interface Guide](../api/canvas-interface-guide.md)** - Complete Canvas integration documentation
- **[Canvas Data Reference](../api/canvas-data-reference.md)** - Data structure specifications
- **[Database Architecture](../database/database_architecture.md)** - 4-layer database design
- **[Testing Strategy](../testing/testing-strategy-analysis.md)** - Comprehensive testing approach

---

## Summary

Canvas Tracker V3 uses a **modular component architecture** where each component is optimized for its specific domain. This approach provides:

✅ **Working Canvas integration** with proven efficiency gains  
✅ **Reliable data storage** with comprehensive testing  
✅ **Clear development workflow** for hybrid Python/TypeScript projects  
✅ **Scalable architecture** that can grow with requirements  

**Next Steps**: Explore component-specific documentation for implementation details and development guidance.
