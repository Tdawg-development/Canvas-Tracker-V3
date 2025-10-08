# Canvas Tracker V3 - Complete File Hierarchy Tree

## Project Root
```
Canvas-Tracker-V3/
├── .git/                           # Git version control
├── .gitignore                      # Git ignore patterns
├── README.md                       # Project overview
├── WARP.md                         # Project development rules
├── ARCHITECTURE.md                 # Clean architecture documentation
├── file_paths.md                   # This file - complete file structure
├── routing_tree.md                 # Logic flow and data routing documentation
├── package.json                    # Node.js project configuration ✅ CREATED
├── package-lock.json               # Dependency lock file ✅ CREATED
├── tsconfig.json                   # TypeScript configuration ✅ CREATED
├── .env.example                    # Environment variables template ✅ CREATED
├── .env                            # Environment variables (gitignored)
├── .eslintrc.js                    # ESLint configuration ✅ CREATED
├── .prettierrc                     # Prettier configuration ✅ CREATED
├── jest.config.js                  # Jest testing configuration ✅ CREATED
└── node_modules/                   # NPM dependencies ✅ CREATED
```

## Source Code Structure (/src)
```
src/
├── interface/                      # External interfaces (HTTP, CLI, GraphQL)
│   ├── http/                      # HTTP interface layer
│   │   ├── server.ts              # Express server setup
│   │   ├── routes/                # HTTP route definitions
│   │   │   ├── index.ts           # Route registry
│   │   │   ├── students.route.ts  # Student-related endpoints
│   │   │   ├── courses.route.ts   # Course-related endpoints
│   │   │   ├── assignments.route.ts # Assignment-related endpoints
│   │   │   ├── grades.route.ts    # Grade-related endpoints
│   │   │   ├── analytics.route.ts # Analytics endpoints
│   │   │   └── student-cards.route.ts # Student card endpoints
│   │   ├── presenters/            # Response formatting
│   │   │   ├── students.presenter.ts
│   │   │   ├── courses.presenter.ts
│   │   │   ├── assignments.presenter.ts
│   │   │   ├── grades.presenter.ts
│   │   │   ├── analytics.presenter.ts
│   │   │   └── student-cards.presenter.ts
│   │   ├── middleware/             # HTTP middleware
│   │   │   ├── auth.middleware.ts
│   │   │   ├── validation.middleware.ts
│   │   │   ├── error.middleware.ts
│   │   │   ├── cors.middleware.ts
│   │   │   └── logging.middleware.ts
│   │   └── support/               # HTTP utilities
│   │       ├── request-id.ts      # Request ID generation
│   │       ├── response-envelope.ts # Standardized responses
│   │       └── http-errors.ts     # HTTP error utilities
│   └── cli/                       # Command line interface (optional)
│       ├── commands/              # CLI commands
│       ├── parsers/               # Argument parsers
│       └── cli-main.ts            # CLI entry point
│
├── application/                   # Application layer - use cases and orchestration
│   ├── students/                  # Student domain application services
│   │   ├── use-cases/            # Student use cases
│   │   │   ├── CreateStudent.ts
│   │   │   ├── UpdateStudent.ts
│   │   │   ├── DeleteStudent.ts
│   │   │   ├── GetStudent.ts
│   │   │   ├── GetStudentList.ts
│   │   │   ├── BuildStudentCard.ts # Primary use case
│   │   │   ├── ComputeMissingAssignments.ts
│   │   │   ├── CalculateTenure.ts
│   │   │   ├── SyncStudentFromCanvas.ts
│   │   │   └── GenerateStudentReport.ts
│   │   └── ports/                # Student domain interfaces
│   │       ├── StudentRepo.ts    # Student repository interface
│   │       ├── StudentCardBuilder.ts # Student card building interface
│   │       └── StudentAnalytics.ts # Student analytics interface
│   ├── courses/                  # Course domain application services
│   │   ├── use-cases/            # Course use cases
│   │   │   ├── CreateCourse.ts
│   │   │   ├── UpdateCourse.ts
│   │   │   ├── DeleteCourse.ts
│   │   │   ├── GetCourse.ts
│   │   │   ├── GetCourseList.ts
│   │   │   ├── SyncCourseFromCanvas.ts
│   │   │   ├── GetCourseStudents.ts
│   │   │   └── GetCourseAnalytics.ts
│   │   └── ports/                # Course domain interfaces
│   │       ├── CourseRepo.ts     # Course repository interface
│   │       └── CourseAnalytics.ts # Course analytics interface
│   ├── assignments/              # Assignment domain application services
│   │   ├── use-cases/            # Assignment use cases
│   │   │   ├── CreateAssignment.ts
│   │   │   ├── UpdateAssignment.ts
│   │   │   ├── DeleteAssignment.ts
│   │   │   ├── GetAssignment.ts
│   │   │   ├── GetAssignmentList.ts
│   │   │   ├── SyncAssignmentFromCanvas.ts
│   │   │   └── GetMissingAssignments.ts
│   │   └── ports/                # Assignment domain interfaces
│   │       └── AssignmentRepo.ts # Assignment repository interface
│   ├── grades/                   # Grade domain application services
│   │   ├── use-cases/            # Grade use cases
│   │   │   ├── RecordGrade.ts
│   │   │   ├── UpdateGrade.ts
│   │   │   ├── GetGrade.ts
│   │   │   ├── GetGradeHistory.ts
│   │   │   ├── SyncGradeFromCanvas.ts
│   │   │   └── CalculateGPA.ts
│   │   └── ports/                # Grade domain interfaces
│   │       └── GradeRepo.ts      # Grade repository interface
│   ├── analytics/                # Analytics application services
│   │   ├── use-cases/            # Analytics use cases
│   │   │   ├── GenerateStudentAnalytics.ts
│   │   │   ├── GenerateCourseAnalytics.ts
│   │   │   ├── GenerateInstructorAnalytics.ts
│   │   │   └── GenerateSystemAnalytics.ts
│   │   └── ports/                # Analytics domain interfaces
│   │       └── AnalyticsRepo.ts  # Analytics repository interface
│   └── sync/                     # Canvas synchronization services
│       ├── use-cases/            # Sync use cases
│       │   ├── SyncAllData.ts
│       │   ├── SyncStudentData.ts
│       │   ├── SyncCourseData.ts
│       │   ├── SyncAssignmentData.ts
│       │   └── SyncGradeData.ts
│       └── ports/                # Sync interfaces
│           └── CanvasGateway.ts  # Canvas API interface
│
├── domain/                       # Domain layer - pure business logic
│   ├── entities/                 # Domain entities
│   │   ├── Student.ts           # Student entity
│   │   ├── Course.ts            # Course entity
│   │   ├── Assignment.ts        # Assignment entity
│   │   ├── Grade.ts             # Grade entity
│   │   ├── Instructor.ts        # Instructor entity
│   │   └── Enrollment.ts        # Student-Course relationship
│   ├── value-objects/           # Domain value objects
│   │   ├── StudentId.ts         # Student identifier VO
│   │   ├── CourseId.ts          # Course identifier VO
│   │   ├── AssignmentId.ts      # Assignment identifier VO
│   │   ├── GradeId.ts           # Grade identifier VO
│   │   ├── InstructorId.ts      # Instructor identifier VO
│   │   ├── Email.ts             # Email address VO
│   │   ├── GradeValue.ts        # Grade value VO
│   │   ├── DateRange.ts         # Date range VO
│   │   └── PercentageScore.ts   # Percentage score VO
│   ├── services/                # Domain services (pure business logic)
│   │   ├── GradeCalculator.ts   # Grade calculation logic
│   │   ├── TenureCalculator.ts  # Student tenure calculation
│   │   ├── RiskAssessment.ts    # Student risk assessment
│   │   ├── PerformanceAnalyzer.ts # Performance analysis
│   │   └── CompletionTracker.ts # Assignment completion tracking
│   └── events/                  # Domain events (optional)
│       ├── StudentCreated.ts
│       ├── StudentUpdated.ts
│       ├── CourseCreated.ts
│       ├── GradeRecorded.ts
│       └── AssignmentCompleted.ts
│
├── infrastructure/              # Infrastructure layer - external concerns
│   ├── persistence/            # Database and persistence
│   │   ├── knex/              # Knex configuration
│   │   │   ├── knexfile.ts    # Knex configuration file
│   │   │   ├── db.ts          # Database connection
│   │   │   └── migrations/    # Database migrations
│   │   │       ├── 001_create_students.ts
│   │   │       ├── 002_create_courses.ts
│   │   │       ├── 003_create_assignments.ts
│   │   │       ├── 004_create_grades.ts
│   │   │       ├── 005_create_instructors.ts
│   │   │       └── 006_create_enrollments.ts
│   │   ├── mappers/           # Data mapping between domain and persistence
│   │   │   ├── StudentMapper.ts
│   │   │   ├── CourseMapper.ts
│   │   │   ├── AssignmentMapper.ts
│   │   │   ├── GradeMapper.ts
│   │   │   ├── InstructorMapper.ts
│   │   │   └── EnrollmentMapper.ts
│   │   └── repositories/      # Repository implementations
│   │       ├── StudentRepoKnex.ts
│   │       ├── CourseRepoKnex.ts
│   │       ├── AssignmentRepoKnex.ts
│   │       ├── GradeRepoKnex.ts
│   │       ├── InstructorRepoKnex.ts
│   │       └── AnalyticsRepoKnex.ts
│   ├── http/                  # External HTTP clients ✅ CREATED
│   │   ├── canvas/           # Canvas API integration ✅ CREATED
│   │   │   ├── CanvasGatewayHttp.ts # Canvas API implementation
│   │   │   ├── CanvasClient.ts # Raw Canvas API client ✅ CREATED
│   │   │   ├── CanvasCoursesApi.ts # Modular courses API component ✅ CREATED
│   │   │   ├── CanvasAdaptiveScheduler.ts # Intelligent rate limiting scheduler ✅ CREATED
│   │   │   ├── CanvasGatewayHttp.ts # Canvas API implementation ✅ CREATED
│   │   │   ├── CanvasMappers.ts # Canvas data mapping
│   │   │   └── CanvasTypes.ts # Canvas API type definitions ✅ CREATED
│   │   └── common/           # Common HTTP utilities ✅ CREATED
│   │       ├── HttpClient.ts # Generic HTTP client
│   │       ├── RetryPolicy.ts # Retry mechanism
│   │       └── CircuitBreaker.ts # Circuit breaker pattern
│   ├── cache/                # Caching layer
│   │   ├── RedisClient.ts    # Redis client setup
│   │   ├── CacheService.ts   # Cache service implementation
│   │   └── CacheKeys.ts      # Cache key constants
│   ├── logging/              # Logging infrastructure
│   │   ├── Logger.ts         # Winston logger setup
│   │   ├── LoggerConfig.ts   # Logging configuration
│   │   └── RequestLogger.ts  # Request logging middleware
│   ├── schedulers/           # Background job scheduling
│   │   ├── SyncJobs.ts       # Canvas sync jobs
│   │   ├── AnalyticsJobs.ts  # Analytics computation jobs
│   │   └── CleanupJobs.ts    # Data cleanup jobs
│   ├── monitoring/           # System monitoring
│   │   ├── HealthCheck.ts    # Health check implementation
│   │   ├── Metrics.ts        # Application metrics
│   │   └── AlertManager.ts   # Alert management
│   └── config/               # Configuration management
│       ├── Environment.ts    # Environment variable handling
│       ├── DatabaseConfig.ts # Database configuration
│       ├── RedisConfig.ts    # Redis configuration
│       ├── CanvasConfig.ts   # Canvas API configuration
│       └── CompositionRoot.ts # Dependency injection setup
│
├── shared/                   # Shared utilities and contracts
│   ├── dto/                  # Data transfer objects
│   │   ├── students/        # Student DTOs
│   │   │   ├── CreateStudentDto.ts
│   │   │   ├── UpdateStudentDto.ts
│   │   │   ├── StudentDto.ts
│   │   │   ├── StudentListDto.ts
│   │   │   └── StudentCardDto.ts
│   │   ├── courses/         # Course DTOs
│   │   │   ├── CreateCourseDto.ts
│   │   │   ├── UpdateCourseDto.ts
│   │   │   ├── CourseDto.ts
│   │   │   └── CourseListDto.ts
│   │   ├── assignments/     # Assignment DTOs
│   │   │   ├── CreateAssignmentDto.ts
│   │   │   ├── UpdateAssignmentDto.ts
│   │   │   ├── AssignmentDto.ts
│   │   │   └── AssignmentListDto.ts
│   │   ├── grades/          # Grade DTOs
│   │   │   ├── RecordGradeDto.ts
│   │   │   ├── GradeDto.ts
│   │   │   └── GradeHistoryDto.ts
│   │   └── analytics/       # Analytics DTOs
│   │       ├── StudentAnalyticsDto.ts
│   │       ├── CourseAnalyticsDto.ts
│   │       └── SystemAnalyticsDto.ts
│   ├── schema/              # Zod validation schemas
│   │   ├── common.schema.ts # Common schemas (IDs, pagination, etc.)
│   │   ├── student.schema.ts # Student validation schemas
│   │   ├── course.schema.ts  # Course validation schemas
│   │   ├── assignment.schema.ts # Assignment validation schemas
│   │   ├── grade.schema.ts   # Grade validation schemas
│   │   └── analytics.schema.ts # Analytics validation schemas
│   ├── errors/              # Error handling
│   │   ├── AppError.ts      # Base application error
│   │   ├── DomainError.ts   # Domain-specific errors
│   │   ├── ValidationError.ts # Validation errors
│   │   ├── NotFoundError.ts # Not found errors
│   │   └── ErrorCodes.ts    # Error code constants
│   ├── types/               # Shared TypeScript types
│   │   ├── Common.ts        # Common types
│   │   ├── ApiResponse.ts   # API response types
│   │   ├── Pagination.ts    # Pagination types
│   │   └── Canvas.ts        # Canvas API types
│   └── utils/               # Utility functions
│       ├── DateUtils.ts     # Date manipulation utilities
│       ├── ValidationUtils.ts # Validation utilities
│       ├── FormatUtils.ts   # Formatting utilities
│       └── AsyncUtils.ts    # Async operation utilities
│
└── frontend/                # Frontend React application
    ├── public/              # Static public files
    │   ├── index.html       # Main HTML template
    │   ├── favicon.ico      # Favicon
    │   └── manifest.json    # Web app manifest
    ├── src/                 # Frontend source code
    │   ├── components/      # Reusable UI components
    │   │   ├── common/      # Common components
    │   │   │   ├── Button/
    │   │   │   │   ├── Button.tsx
    │   │   │   │   ├── Button.module.css
    │   │   │   │   └── Button.test.tsx
    │   │   │   ├── Input/
    │   │   │   ├── Modal/
    │   │   │   ├── Table/
    │   │   │   └── Loading/
    │   │   ├── students/    # Student-specific components
    │   │   │   ├── StudentCard/
    │   │   │   ├── StudentList/
    │   │   │   ├── StudentForm/
    │   │   │   └── StudentProfile/
    │   │   ├── courses/     # Course-specific components
    │   │   │   ├── CourseCard/
    │   │   │   ├── CourseList/
    │   │   │   └── CourseForm/
    │   │   ├── assignments/ # Assignment-specific components
    │   │   │   ├── AssignmentCard/
    │   │   │   ├── AssignmentList/
    │   │   │   └── AssignmentForm/
    │   │   ├── grades/      # Grade-specific components
    │   │   │   ├── GradeCard/
    │   │   │   ├── GradeList/
    │   │   │   └── GradeForm/
    │   │   └── analytics/   # Analytics components
    │   │       ├── Chart/
    │   │       ├── Dashboard/
    │   │       └── Report/
    │   ├── pages/           # Page components and routing
    │   │   ├── Dashboard/
    │   │   ├── Students/
    │   │   ├── Courses/
    │   │   ├── Assignments/
    │   │   ├── Grades/
    │   │   ├── Analytics/
    │   │   └── Settings/
    │   ├── hooks/           # Custom React hooks
    │   │   ├── useStudents.ts
    │   │   ├── useCourses.ts
    │   │   ├── useAssignments.ts
    │   │   ├── useGrades.ts
    │   │   ├── useAnalytics.ts
    │   │   └── useApi.ts
    │   ├── services/        # Frontend services
    │   │   ├── ApiService.ts
    │   │   ├── AuthService.ts
    │   │   └── StorageService.ts
    │   ├── styles/          # Styling
    │   │   ├── globals.css  # Global styles
    │   │   ├── variables.css # CSS variables
    │   │   └── themes/      # Theme configurations
    │   ├── utils/           # Frontend utilities
    │   │   ├── formatters.ts
    │   │   ├── validators.ts
    │   │   └── constants.ts
    │   ├── api-sdk/         # Generated API client
    │   │   ├── client.ts    # Generated API client
    │   │   ├── types.ts     # Generated types
    │   │   └── endpoints.ts # Generated endpoints
    │   ├── App.tsx          # Main App component
    │   ├── App.css          # App styles
    │   ├── index.tsx        # React entry point
    │   └── vite-env.d.ts    # Vite type definitions
    ├── package.json         # Frontend package configuration
    ├── vite.config.ts       # Vite configuration
    ├── tailwind.config.js   # Tailwind CSS configuration
    └── tsconfig.json        # TypeScript configuration for frontend
```

## Testing Structure (/tests)
```
tests/
├── unit/                   # Unit tests
│   ├── domain/            # Domain layer tests
│   │   ├── entities/
│   │   ├── value-objects/
│   │   └── services/
│   ├── application/       # Application layer tests
│   │   ├── students/
│   │   ├── courses/
│   │   ├── assignments/
│   │   ├── grades/
│   │   └── analytics/
│   └── shared/            # Shared utilities tests
│       ├── dto/
│       ├── schema/
│       └── utils/
├── integration/           # Integration tests
│   ├── infrastructure/   # Infrastructure tests
│   │   ├── persistence/
│   │   ├── http/
│   │   └── cache/
│   └── interface/        # Interface tests
│       └── http/
├── e2e/                  # End-to-end tests
│   ├── api/             # API E2E tests
│   └── frontend/        # Frontend E2E tests
├── fixtures/            # Test data fixtures
│   ├── students.json
│   ├── courses.json
│   ├── assignments.json
│   └── grades.json
└── helpers/             # Test helper utilities
    ├── database.ts      # Database test helpers
    ├── api.ts          # API test helpers
    └── mocks.ts        # Mock implementations
```

## Documentation (/docs)
```
docs/
├── api/                  # API documentation
│   ├── openapi.yaml     # OpenAPI specification
│   ├── endpoints/       # Endpoint documentation
│   └── examples/        # API usage examples
├── architecture/        # Architecture documentation
│   ├── decisions/       # Architecture Decision Records (ADRs)
│   │   ├── 001-clean-architecture.md
│   │   ├── 002-database-choice.md
│   │   ├── 003-canvas-integration.md
│   │   └── 004-frontend-framework.md
│   └── diagrams/        # Architecture diagrams
├── deployment/          # Deployment documentation
│   ├── docker/         # Docker configurations
│   ├── kubernetes/     # Kubernetes configurations
│   └── ci-cd/          # CI/CD pipeline documentation
└── user/               # User documentation
    ├── setup.md        # Setup instructions
    ├── usage.md        # Usage guide
    └── troubleshooting.md # Troubleshooting guide
```

## Configuration Files
```
.github/                 # GitHub configuration
├── workflows/          # GitHub Actions
│   ├── ci.yml         # Continuous integration
│   ├── cd.yml         # Continuous deployment
│   └── codeql.yml     # Security scanning
└── ISSUE_TEMPLATE/    # Issue templates
    ├── bug_report.md
    └── feature_request.md

docker/                 # Docker configurations
├── Dockerfile         # Main application Dockerfile
├── docker-compose.yml # Local development setup
└── .dockerignore      # Docker ignore patterns

scripts/               # Build and deployment scripts ✅ CREATED
├── commit.ps1        # Git add + commit utility ✅ CREATED
├── build.sh          # Build script
├── deploy.sh         # Deployment script
├── migrate.sh        # Database migration script
└── seed.sh           # Database seeding script
```

## Total File Count Estimate
- **Configuration files**: ~15
- **Source code files**: ~150-200
- **Test files**: ~100-150  
- **Documentation files**: ~30-50
- **Frontend files**: ~100-150

**Total estimated files**: ~400-600 files (excluding node_modules and generated files)

This structure follows Clean Architecture principles with clear separation of concerns and maintains the strict boundaries outlined in our WARP.md rules.