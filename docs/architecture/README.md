# Architecture Documentation

This folder contains high-level system architecture documentation for Canvas Tracker V3.

## 📁 Files in this Category

### Core Architecture
- **[system-architecture.md](./system-architecture.md)** - Complete system architecture using Clean/Hexagonal pattern with DDD
  - Layer definitions (Interface, Application, Domain, Infrastructure)  
  - Directory structure and boundaries
  - Request lifecycle examples
  - TypeScript implementation stubs

### System Design
- **[routing-architecture.md](./routing-architecture.md)** - Logic flow and data routing architecture
  - Component interactions
  - Data flow patterns
  - Integration points

## 🎯 Purpose

These documents define the foundational architectural patterns and principles that guide the entire Canvas Tracker V3 system design. They establish:

- **Separation of concerns** through clean layer boundaries
- **Domain-driven design** principles for business logic isolation  
- **Dependency inversion** for testable, maintainable code
- **Hexagonal architecture** for framework independence

## 📖 Reading Order

1. **Start with system-architecture.md** for complete system overview
2. **Review routing-architecture.md** for data flow understanding

## 🔗 Related Documentation

- **[Database Architecture](../database/)** - Database layer implementation details
- **[API Documentation](../api/)** - Canvas interface specifications
- **[Testing Strategy](../testing/)** - How architecture supports testing

---

*Part of [Canvas Tracker V3 Documentation](../README.md)*