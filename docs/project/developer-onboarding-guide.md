# Developer Onboarding Guide

## Welcome to Canvas Tracker V3

This guide will get you up and running with the **actual** Canvas Tracker V3 system - a modular Canvas LMS integration system with specialized Python and TypeScript components.

## 🎯 System Overview

Canvas Tracker V3 is **NOT** a traditional web application. Instead, it's a **specialized integration system** with three main components:

### **Component Architecture**
```
🟢 Canvas Interface (TypeScript) ← API integration, data staging
🐍 Database Layer (Python)      ← Data storage, operations  
🔧 Infrastructure (TypeScript)   ← HTTP clients, configuration
```

### **Technology Stack**
- **Canvas API Integration**: TypeScript with custom HTTP client
- **Database**: Python with SQLAlchemy ORM
- **Testing**: Pytest (database), Jest (Canvas interface)
- **Development**: Hybrid Python/TypeScript workflow

## 📋 Prerequisites

### **Required**
- **Node.js 18+** (for TypeScript components)
- **Python 3.9+** (for database components) 
- **Canvas LMS API access** with valid token
- **Git** for version control

### **Optional**
- **SQLite** (for database development)
- **VS Code** with Python and TypeScript extensions

## 🚀 Quick Setup (5 minutes)

### 1. Clone and Navigate
```bash
git clone <repository-url>
cd Canvas-Tracker-V3
```

### 2. Environment Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your Canvas credentials
CANVAS_URL=https://your-canvas-instance.com
CANVAS_TOKEN=your_canvas_api_token
```

### 3. Test Canvas Integration (TypeScript)
```bash
# Navigate to Canvas interface
cd canvas-interface

# Install dependencies
npm install

# Run interactive demo (verify Canvas connection)
npx tsx demos/canvas-staging-demo.ts

# Run tests
npm test
```

### 4. Test Database Operations (Python)  
```bash
# Navigate to database
cd ../database

# Install dependencies
pip install -r requirements.txt

# Run comprehensive test suite
pytest tests/ -v

# Run specific component tests
pytest tests/test_layer1_models.py -v
```

If both test suites pass, you're ready to develop! 🎉

## 🛠️ Development Workflow

### **Canvas Interface Development** (TypeScript)

**Location**: `canvas-interface/`
**Purpose**: All Canvas LMS integration and API calls

```bash
cd canvas-interface

# Development commands
npm test                              # Run test suite
npm run test:watch                    # Watch mode testing
npx tsx demos/canvas-staging-demo.ts  # Interactive demo
npx tsx demos/test-canvas-api.ts      # API testing

# Key files to understand
core/canvas-calls.ts                  # Main Canvas API processing
staging/canvas-data-constructor.ts    # API orchestration  
staging/canvas-staging-data.ts        # Data models
tests/                               # Jest-based tests
```

### **Database Development** (Python)

**Location**: `database/`
**Purpose**: Data storage, queries, and operations

```bash
cd database

# Development commands
pytest tests/                         # Full test suite
pytest tests/test_layer1_models.py    # Canvas data models
pytest tests/test_layer0_models.py    # Lifecycle models
pytest -v --tb=short                 # Verbose with short traceback

# Key files to understand  
models/layer1_canvas.py              # Canvas data models
models/layer0_lifecycle.py           # Object lifecycle
operations/layer1/                   # Canvas operations
tests/                              # Pytest-based comprehensive tests
```

### **Infrastructure Development** (TypeScript)

**Location**: `src/infrastructure/`
**Purpose**: HTTP clients and shared utilities

```bash
# Currently minimal - Canvas HTTP client infrastructure
src/infrastructure/http/canvas/       # Canvas HTTP client files
```

## 📊 Understanding the System

### **Data Flow**
```
1. Canvas API Request (TypeScript)
   → canvas-interface/core/canvas-calls.ts
   → Rate limiting and error handling
   
2. Data Staging (TypeScript)  
   → canvas-interface/staging/canvas-data-constructor.ts
   → Clean Canvas API responses
   
3. Database Operations (Python)
   → database/operations/layer1/
   → Store using SQLAlchemy models
```

### **Component Boundaries**
- **Canvas Interface**: Never touches database directly
- **Database Layer**: Never makes Canvas API calls directly
- **Infrastructure**: Provides shared utilities for both components

### **Testing Strategy**
- **Canvas Interface**: Jest-based unit and integration tests
- **Database Layer**: Pytest with comprehensive fixtures and mocks  
- **Integration**: Manual workflows and demos

## 🧪 Testing Philosophy

### **Database Testing** (Excellent Coverage)
```bash
# Comprehensive test suite with 95% coverage
pytest tests/test_layer1_models.py      # Canvas models
pytest tests/test_layer0_models.py      # Lifecycle models  
pytest tests/test_base_and_exceptions.py # Base classes
pytest tests/test_config.py             # Configuration
pytest tests/test_session.py            # Session management
```

### **Canvas Interface Testing** (Growing Coverage)
```bash
# Unit tests for core components
npm test test_canvas_data_constructor   # Data construction
npm test test_canvas_staging_data_models # Data models
npm test test_canvas_api_error_handling  # Error handling
```

## 📁 Project Structure Deep-Dive

### **Canvas Interface Structure**
```
canvas-interface/
├── core/                    # Core Canvas API functionality
│   ├── canvas-calls.ts      # Main Canvas API interface  
│   └── pull-student-grades.ts # Grade extraction system
├── staging/                 # Data staging system (80% of usage)
│   ├── canvas-data-constructor.ts # API orchestration
│   └── canvas-staging-data.ts     # Clean data models
├── demos/                   # Interactive testing tools
├── tests/                   # Jest test suite
└── index.ts                # Main exports
```

### **Database Structure**
```
database/
├── models/                  # SQLAlchemy models (4-layer design)
│   ├── layer0_lifecycle.py # Object lifecycle management
│   ├── layer1_canvas.py    # Canvas data models
│   ├── layer2_historical.py # Time-series data
│   └── layer3_metadata.py  # User metadata
├── operations/              # Database operations
│   ├── base/               # Base operation patterns
│   ├── layer1/             # Canvas-specific operations
│   └── utilities/          # Query utilities
└── tests/                  # Comprehensive pytest suite
```

## 🔧 Common Development Tasks

### **Adding New Canvas API Integration**
1. **Add API call** in `canvas-interface/core/canvas-calls.ts`
2. **Create data model** in `canvas-interface/staging/canvas-staging-data.ts`
3. **Add tests** in `canvas-interface/tests/`
4. **Create demo** in `canvas-interface/demos/`

### **Adding New Database Model**
1. **Define model** in appropriate `database/models/layerX_*.py`
2. **Add operations** in `database/operations/layerX/`
3. **Create tests** in `database/tests/test_layerX_models.py`
4. **Test integration** with Canvas interface

### **Performance Testing**
```bash
# Canvas interface performance
cd canvas-interface
npx tsx demos/test-canvas-performance.ts

# Database performance  
cd database
pytest tests/test_performance.py -v
```

## 📚 Documentation Resources

### **Essential Reading** (Start Here)
1. **[System Architecture](../architecture/system-architecture.md)** - Component overview
2. **[Canvas Interface Guide](../api/canvas-interface-guide.md)** - Canvas API usage
3. **[Database Architecture](../database/database_architecture.md)** - Database design

### **Detailed References**
- **[Canvas Data Reference](../api/canvas-data-reference.md)** - Complete data structures
- **[Testing Strategy](../testing/testing-strategy-analysis.md)** - Testing approach
- **[Performance Analysis](../analysis/)** - Technical deep-dives

## 🐛 Troubleshooting

### **Canvas API Issues**
```bash
# Test Canvas connection
cd canvas-interface
npx tsx demos/test-canvas-api.ts

# Check Canvas configuration  
echo $CANVAS_URL
echo $CANVAS_TOKEN
```

### **Database Issues** 
```bash  
# Test database connectivity
cd database
pytest tests/test_config.py -v

# Reset test database
rm -f test_canvas_tracker.db
pytest tests/test_layer1_models.py -v
```

### **Environment Issues**
```bash
# Verify Node.js version (need 18+)
node --version

# Verify Python version (need 3.9+)
python --version

# Check package installations
cd canvas-interface && npm list
cd database && pip list
```

## 💡 Development Tips

### **Effective Workflow**
1. **Start with tests** - understand existing functionality through test files
2. **Use demos extensively** - they provide working examples of all components
3. **Focus on one component** - don't try to work across Python/TypeScript simultaneously
4. **Read the docs** - they're accurate and up-to-date for this system

### **Common Patterns**
- **Canvas Interface**: Always use staging data models, never raw Canvas responses
- **Database**: Follow 4-layer architecture, use appropriate layer for your data
- **Testing**: Write tests first, use existing fixtures and patterns

### **Performance Considerations**
- **Canvas API**: Batch requests, respect rate limits, use staging system
- **Database**: Use bulk operations, leverage SQLAlchemy optimizations
- **Integration**: Minimize cross-component calls, cache when appropriate

## 🚀 Next Steps

### **Week 1: Get Familiar**
- [ ] Run all test suites successfully
- [ ] Execute interactive demos in both components
- [ ] Read system architecture and Canvas interface docs
- [ ] Understand database 4-layer design

### **Week 2: Start Contributing**
- [ ] Pick a small feature or bug fix
- [ ] Write tests first
- [ ] Follow component boundaries
- [ ] Get code review from team

### **Ongoing: Stay Current**
- [ ] Run tests before committing
- [ ] Update documentation when making changes
- [ ] Use demos to validate your changes
- [ ] Follow hybrid Python/TypeScript best practices

## 📞 Getting Help

### **Component-Specific Questions**
- **Canvas Integration**: See [API Documentation](../api/)
- **Database Operations**: See [Database Documentation](../database/)
- **Testing Approaches**: See [Testing Documentation](../testing/)

### **Architecture Questions**
- Review [System Architecture](../architecture/system-architecture.md)
- Check [Component Integration Guide](../architecture/) (coming soon)

### **Performance Questions**
- Review [Analysis Reports](../analysis/)
- Run performance demos and benchmarks

---

**Welcome to the Canvas Tracker V3 development team!** 🎉

This system prioritizes **working Canvas integration** and **reliable data storage** with clear component boundaries and excellent testing. You're now ready to contribute effectively to this well-architected system.