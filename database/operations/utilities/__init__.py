"""
Utilities Package.

Core utilities supporting all database operations with our hybrid approach:
- Query builders for simple, performant data retrieval
- Analytics builders for complex analytical computations
- Bulk operations for large dataset processing
- Performance monitoring and optimization tools

Components:
- query_builder.py: Simple, reusable SQL query construction (Core Component)
- analytics_builder.py: Complex analytical computations and insights (Core Component) 
- bulk_operations.py: Batch processing utilities for large datasets
- migration_helper.py: Data migration and transformation tools
- performance_monitor.py: Query performance tracking and optimization

Hybrid Approach:
- Use QueryBuilder for simple, performance-critical queries consumed by frontend
- Use AnalyticsBuilder for complex business intelligence requiring centralized logic
"""

__all__ = [
    # Will be populated as we implement utility components
]