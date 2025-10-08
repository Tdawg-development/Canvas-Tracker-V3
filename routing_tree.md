# Canvas Tracker V3 - Logic Flow & Data Routing Tree

## Request Flow Overview
```
HTTP Request → Interface Layer → Application Layer → Domain Layer → Infrastructure Layer
                     ↓               ↓                    ↓               ↓
               [Controllers]    [Use Cases]         [Entities]      [Repositories]
               [Presenters]     [Ports]            [Services]       [Gateways]
               [Middleware]                        [Value Objects]   [Cache/DB]
                     ↑               ↑                    ↑               ↑
HTTP Response ← [Response Format] ← [Business Logic] ← [Pure Logic] ← [Data Access]
```

## Core Request Flows

### 1. Student Card Flow (Primary Use Case)
```
GET /v1/students/:studentId/card

┌─ HTTP Request
│
├─ Interface Layer
│  ├─ server.ts (Express setup)
│  ├─ routes/student-cards.route.ts
│  │  ├─ Validate studentId parameter (Zod)
│  │  ├─ Extract route params
│  │  └─ Call use case via composition root
│  └─ presenters/student-cards.presenter.ts
│     └─ Format response envelope
│
├─ Application Layer  
│  ├─ students/use-cases/BuildStudentCard.ts
│  │  ├─ Input: { studentId: string }
│  │  ├─ Orchestrate business workflow:
│  │  │  ├─ Call StudentRepo.byId()
│  │  │  ├─ Call CourseRepo.byStudent()
│  │  │  ├─ Call CanvasGateway.enrichedStudent()
│  │  │  ├─ Invoke Domain Services for calculations
│  │  │  └─ Assemble StudentCardDto
│  │  └─ Output: StudentCardDto
│  └─ Ports (Interfaces):
│     ├─ StudentRepo.ts
│     ├─ CourseRepo.ts  
│     └─ CanvasGateway.ts
│
├─ Domain Layer (Pure Business Logic)
│  ├─ entities/
│  │  ├─ Student.ts (business rules)
│  │  ├─ Course.ts (business rules)
│  │  └─ Grade.ts (business rules)
│  ├─ value-objects/
│  │  ├─ StudentId.ts (validation)
│  │  ├─ GradeValue.ts (calculation)
│  │  └─ DateRange.ts (date logic)
│  └─ services/
│     ├─ TenureCalculator.ts (pure tenure logic)
│     ├─ RiskAssessment.ts (pure risk logic)
│     └─ PerformanceAnalyzer.ts (pure analysis)
│
└─ Infrastructure Layer (External I/O)
   ├─ persistence/repositories/
   │  ├─ StudentRepoKnex.ts
   │  │  └─ SQL: SELECT * FROM students WHERE id = ?
   │  └─ CourseRepoKnex.ts  
   │     └─ SQL: SELECT * FROM courses WHERE student_id = ?
   ├─ http/canvas/
   │  └─ CanvasGatewayHttp.ts
   │     └─ HTTP: GET /api/v1/users/{studentId}
   └─ cache/
      └─ RedisClient.ts (optional caching)

Response Path:
Infrastructure Data → Domain Entities → Application DTO → Interface Response → HTTP JSON
```

### 2. CRUD Operations Flow Pattern
```
Standard CRUD Pattern: POST|GET|PUT|DELETE /v1/{resource}[/:id]

┌─ HTTP CRUD Request
│
├─ Interface Layer
│  ├─ routes/{resource}.route.ts
│  │  ├─ Validate request (Zod schema)
│  │  ├─ Authentication/Authorization
│  │  ├─ Rate limiting
│  │  └─ Route to appropriate use case
│  ├─ middleware/
│  │  ├─ auth.middleware.ts (JWT validation)
│  │  ├─ validation.middleware.ts (Zod validation)
│  │  ├─ error.middleware.ts (error handling)
│  │  └─ logging.middleware.ts (request logging)
│  └─ presenters/{resource}.presenter.ts
│     └─ Format success/error responses
│
├─ Application Layer
│  ├─ {resource}/use-cases/
│  │  ├─ Create{Resource}.ts
│  │  │  ├─ Validate business rules
│  │  │  ├─ Create domain entity
│  │  │  ├─ Call repository save
│  │  │  └─ Return created DTO
│  │  ├─ Update{Resource}.ts
│  │  │  ├─ Fetch existing entity
│  │  │  ├─ Apply domain validations
│  │  │  ├─ Update entity properties
│  │  │  ├─ Call repository save
│  │  │  └─ Return updated DTO
│  │  ├─ Delete{Resource}.ts
│  │  │  ├─ Verify entity exists
│  │  │  ├─ Check business constraints
│  │  │  ├─ Call repository delete
│  │  │  └─ Return confirmation
│  │  └─ Get{Resource}.ts
│  │     ├─ Call repository find
│  │     ├─ Apply domain formatting
│  │     └─ Return DTO
│  └─ ports/{Resource}Repo.ts (interface)
│
├─ Domain Layer
│  ├─ entities/{Resource}.ts
│  │  ├─ Constructor validation
│  │  ├─ Business rule methods
│  │  ├─ State change methods
│  │  └─ Domain events (optional)
│  ├─ value-objects/
│  │  ├─ {Resource}Id.ts (identity validation)
│  │  └─ Related VOs (email, dates, etc.)
│  └─ Domain events (if applicable)
│     └─ {Resource}Created/Updated/Deleted.ts
│
└─ Infrastructure Layer
   ├─ persistence/repositories/{Resource}RepoKnex.ts
   │  ├─ INSERT/UPDATE/DELETE/SELECT SQL
   │  ├─ Data mapping to/from domain entities
   │  ├─ Error handling (not found, constraint violations)
   │  └─ Transaction management
   └─ persistence/mappers/{Resource}Mapper.ts
      ├─ Entity → Database row
      └─ Database row → Entity
```

### 3. Canvas Synchronization Flow
```
Canvas Sync Flow: Background jobs + manual triggers

┌─ Trigger (Cron job or HTTP endpoint)
│
├─ Interface Layer (if HTTP triggered)
│  └─ routes/sync.route.ts
│     ├─ Authentication check
│     ├─ Rate limiting
│     └─ Call sync use case
│
├─ Application Layer
│  ├─ sync/use-cases/SyncAllData.ts
│  │  ├─ Orchestrate sync sequence:
│  │  │  ├─ SyncStudentData.execute()
│  │  │  ├─ SyncCourseData.execute()  
│  │  │  ├─ SyncAssignmentData.execute()
│  │  │  └─ SyncGradeData.execute()
│  │  ├─ Handle sync errors
│  │  ├─ Update sync timestamps
│  │  └─ Generate sync report
│  ├─ sync/use-cases/SyncStudentData.ts
│  │  ├─ Fetch students from Canvas
│  │  ├─ Compare with local data
│  │  ├─ Create/update/deactivate students
│  │  ├─ Log sync activities
│  │  └─ Return sync statistics
│  └─ ports/CanvasGateway.ts
│
├─ Domain Layer
│  ├─ entities/ (Student, Course, Assignment, Grade)
│  │  └─ Business rules for data consistency
│  ├─ services/
│  │  ├─ DataSyncValidator.ts (validate sync data)
│  │  └─ ConflictResolver.ts (handle data conflicts)
│  └─ Domain events
│     ├─ StudentSynced.ts
│     ├─ CourseSynced.ts
│     └─ SyncCompleted.ts
│
└─ Infrastructure Layer
   ├─ http/canvas/CanvasGatewayHttp.ts
   │  ├─ GET /api/v1/courses
   │  ├─ GET /api/v1/users
   │  ├─ GET /api/v1/assignments
   │  ├─ GET /api/v1/submissions
   │  ├─ Rate limiting compliance
   │  ├─ Error handling & retries
   │  └─ Response caching
   ├─ schedulers/SyncJobs.ts
   │  ├─ Cron schedule definitions
   │  ├─ Job queue management
   │  └─ Error recovery
   └─ persistence/repositories/
      ├─ Batch insert/update operations
      ├─ Conflict detection & resolution
      └─ Sync status tracking
```

### 4. Analytics & Reporting Flow
```
Analytics Flow: Complex data aggregation

┌─ GET /v1/analytics/{type}
│
├─ Interface Layer
│  ├─ routes/analytics.route.ts
│  │  ├─ Validate query parameters
│  │  ├─ Date range validation
│  │  ├─ Permission checks
│  │  └─ Route to analytics use case
│  └─ presenters/analytics.presenter.ts
│     ├─ Format charts/graphs data
│     ├─ Add metadata
│     └─ Cache headers
│
├─ Application Layer
│  ├─ analytics/use-cases/GenerateStudentAnalytics.ts
│  │  ├─ Validate date ranges
│  │  ├─ Fetch aggregated data
│  │  ├─ Apply business calculations
│  │  ├─ Generate insights
│  │  └─ Format for presentation
│  ├─ analytics/use-cases/GenerateCourseAnalytics.ts
│  │  ├─ Course performance metrics
│  │  ├─ Enrollment trends
│  │  ├─ Grade distributions
│  │  └─ Completion rates
│  └─ ports/AnalyticsRepo.ts
│
├─ Domain Layer
│  ├─ services/
│  │  ├─ TrendAnalyzer.ts (trend calculations)
│  │  ├─ StatisticalCalculator.ts (statistics)
│  │  ├─ PerformanceRanking.ts (rankings)
│  │  └─ PredictiveModels.ts (predictions)
│  └─ value-objects/
│     ├─ AnalyticsPeriod.ts
│     ├─ TrendData.ts
│     └─ PerformanceMetrics.ts
│
└─ Infrastructure Layer
   ├─ persistence/repositories/AnalyticsRepoKnex.ts
   │  ├─ Complex aggregation queries
   │  ├─ Time-series data queries  
   │  ├─ Performance optimizations
   │  └─ Query result caching
   ├─ cache/CacheService.ts
   │  ├─ Cache analytics results (30min TTL)
   │  ├─ Cache invalidation on data updates
   │  └─ Cache warming for common queries
   └─ schedulers/AnalyticsJobs.ts
      ├─ Pre-compute heavy analytics (nightly)
      ├─ Update materialized views
      └─ Generate scheduled reports
```

### 5. Error Handling Flow
```
Error Flow: Consistent error handling across layers

┌─ Error Source (Any layer)
│
├─ Domain Layer Errors
│  ├─ ValidationError (business rule violations)
│  ├─ DomainError (domain logic errors)  
│  └─ InvariantError (entity state violations)
│     └─ Bubble up to Application Layer
│
├─ Application Layer Errors  
│  ├─ NotFoundError (resource not found)
│  ├─ AuthorizationError (permission denied)
│  ├─ BusinessRuleError (orchestration failures)
│  └─ IntegrationError (external service failures)
│     └─ Bubble up to Interface Layer
│
├─ Infrastructure Layer Errors
│  ├─ DatabaseError (SQL constraints, connection issues)
│  ├─ NetworkError (HTTP client failures)
│  ├─ CacheError (Redis failures)
│  └─ ExternalServiceError (Canvas API errors)
│     └─ Mapped to Application errors
│
└─ Interface Layer Error Handling
   ├─ middleware/error.middleware.ts
   │  ├─ Catch all unhandled errors
   │  ├─ Map errors to HTTP status codes:
   │  │  ├─ ValidationError → 400 Bad Request
   │  │  ├─ NotFoundError → 404 Not Found  
   │  │  ├─ AuthorizationError → 403 Forbidden
   │  │  ├─ BusinessRuleError → 422 Unprocessable Entity
   │  │  └─ Others → 500 Internal Server Error
   │  ├─ Log errors with context
   │  ├─ Sanitize error messages
   │  └─ Return standardized error response:
   │     {
   │       "error": {
   │         "code": "STUDENT_NOT_FOUND", 
   │         "message": "Student with ID 'abc123' not found",
   │         "details": { "studentId": "abc123" }
   │       }
   │     }
   └─ Error response reaches client
```

## Data Flow Patterns

### 1. Request Data Transformation
```
HTTP JSON → DTO → Domain Entity → Persistence Entity → Database

Example: Creating a Student
1. POST /v1/students
   Body: { "name": "John Doe", "email": "john@example.com" }

2. Interface validates with Zod:
   createStudentSchema.parse(req.body)

3. Application receives CreateStudentDto:
   { name: "John Doe", email: "john@example.com" }

4. Domain creates Student entity:
   new Student(
     StudentId.create(uuid()),
     "John Doe", 
     Email.create("john@example.com")
   )

5. Infrastructure maps to database:
   { id: "uuid-123", name: "John Doe", email: "john@example.com" }

6. SQL INSERT executed:
   INSERT INTO students (id, name, email) VALUES (?, ?, ?)
```

### 2. Response Data Transformation  
```
Database → Persistence Entity → Domain Entity → DTO → HTTP JSON

Example: Fetching Student Card
1. SQL SELECT with JOINs:
   SELECT s.*, c.* FROM students s JOIN enrollments e ON s.id = e.student_id 
   JOIN courses c ON e.course_id = c.id WHERE s.id = ?

2. Infrastructure maps to Domain entities:
   Student + Course[]

3. Domain services calculate business data:
   TenureCalculator.calculate(), RiskAssessment.assess()

4. Application assembles DTO:
   StudentCardDto {
     id, name, email, tenure, riskLevel, courses[], metrics{}
   }

5. Interface presenter formats response:
   { data: { ... }, meta: { timestamp, version } }

6. HTTP JSON response sent to client
```

### 3. Canvas Integration Data Flow
```
Canvas API → Infrastructure → Domain → Application → Local Database

Sync Process:
1. CanvasGatewayHttp.fetchUsers()
   → HTTP GET to Canvas API
   → Raw Canvas JSON response

2. CanvasMapper.toStudentEntity() 
   → Maps Canvas JSON to Domain Student entity
   → Validates business rules

3. SyncStudentData use case
   → Compares Canvas data with local data  
   → Determines create/update/deactivate actions
   → Orchestrates database operations

4. StudentRepoKnex persistence
   → Executes SQL operations
   → Updates sync timestamps
   → Records sync status

5. Domain events triggered
   → StudentSynced event
   → Analytics refresh triggers
   → Cache invalidation
```

## Dependency Flow (Ports & Adapters)

### Inward Dependencies (Interfaces defined by inner layers)
```
Application Layer Ports (Interfaces):
├── StudentRepo (implemented by Infrastructure)
├── CourseRepo (implemented by Infrastructure)  
├── CanvasGateway (implemented by Infrastructure)
├── CacheService (implemented by Infrastructure)
└── Logger (implemented by Infrastructure)

Domain Layer Dependencies:
├── Clock (injected as { now: () => Date })
├── IdGenerator (injected as { generate: () => string })
└── Pure functions only (no interfaces needed)
```

### Outward Dependencies (Implementations in outer layers)
```
Infrastructure Implementations:
├── StudentRepoKnex implements StudentRepo
├── CourseRepoKnex implements CourseRepo
├── CanvasGatewayHttp implements CanvasGateway
├── RedisCacheService implements CacheService
└── WinstonLogger implements Logger

Composition Root assembles all dependencies:
└── CompositionRoot.ts creates all implementations and injects them
```

## Routing Configuration

### HTTP Route Tree
```
/
├── /healthz (GET) → Health check
├── /readyz (GET) → Readiness check
└── /v1/ 
    ├── /students/
    │   ├── GET / → GetStudentList
    │   ├── POST / → CreateStudent
    │   ├── GET /:id → GetStudent
    │   ├── PUT /:id → UpdateStudent
    │   ├── DELETE /:id → DeleteStudent
    │   └── GET /:id/card → BuildStudentCard ⭐
    ├── /courses/
    │   ├── GET / → GetCourseList
    │   ├── POST / → CreateCourse
    │   ├── GET /:id → GetCourse
    │   ├── PUT /:id → UpdateCourse
    │   ├── DELETE /:id → DeleteCourse
    │   └── GET /:id/students → GetCourseStudents
    ├── /assignments/
    │   ├── GET / → GetAssignmentList
    │   ├── POST / → CreateAssignment
    │   ├── GET /:id → GetAssignment
    │   ├── PUT /:id → UpdateAssignment
    │   ├── DELETE /:id → DeleteAssignment
    │   └── GET /missing → GetMissingAssignments
    ├── /grades/
    │   ├── GET / → GetGradeList
    │   ├── POST / → RecordGrade
    │   ├── GET /:id → GetGrade
    │   ├── PUT /:id → UpdateGrade
    │   └── GET /:id/history → GetGradeHistory
    ├── /analytics/
    │   ├── GET /students → GenerateStudentAnalytics
    │   ├── GET /courses → GenerateCourseAnalytics
    │   ├── GET /system → GenerateSystemAnalytics
    │   └── GET /reports/:type → GenerateReport
    └── /sync/
        ├── POST /all → SyncAllData
        ├── POST /students → SyncStudentData
        ├── POST /courses → SyncCourseData
        ├── POST /assignments → SyncAssignmentData
        └── GET /status → GetSyncStatus
```

This routing tree ensures clear request flow through Clean Architecture layers while maintaining strict separation of concerns as defined in our WARP.md rules.