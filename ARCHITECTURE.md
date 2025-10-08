# ARCHITECTURE

**Style:** Clean/Hexagonal (a.k.a. Ports & Adapters) with Domain-Driven Design (DDD).  
**Guiding principle:** Business logic never knows frameworks or databases; frameworks/datastores are plugins at the edges ([Clean Architecture](https://8thlight.com/blog/uncle-bob/2012/08/13/the-clean-architecture.html), [Hexagonal](https://alistair.cockburn.us/hexagonal-architecture/), [DDD](https://www.domainlanguage.com/)).

## Acronyms (defined once)

- **DDD** — Domain-Driven Design  
- **DTO** — Data Transfer Object  
- **VO** — Value Object  
- **ADR** — Architecture Decision Record  
- **CI/CD** — Continuous Integration / Continuous Delivery  
- **RBAC** — Role-Based Access Control  
- **PII** — Personally Identifiable Information  
- **SLI/SLO/SLA** — Service Level Indicator / Objective / Agreement  
- **CORS** — Cross-Origin Resource Sharing  
- **CSP** — Content Security Policy

> Claims about specific tools/behaviors are cited inline: **Express** web server & middleware model ([docs](https://expressjs.com/)); **Zod** runtime validation & TypeScript inference ([docs](https://zod.dev/)); **Knex** migrations/query builder ([docs](https://knexjs.org/)); **Redis** for caching ([docs](https://redis.io/)); **Winston** logging transports/levels ([docs](https://github.com/winstonjs/winston)); **OpenAPI** contract format & generators ([site](https://www.openapis.org/)); **node-cron** cron-like schedulers ([repo](https://github.com/kelektiv/node-cron)); **React** component model ([docs](https://react.dev/)); **Vite** dev/build tool ([docs](https://vitejs.dev/)).

---

## 0) Layers & Responsibilities

| Layer | Purpose | Knows About | Never Knows |
|---|---|---|---|
| **Interface** | Parse/validate transport (HTTP/GraphQL/CLI), map DTOs, return status codes | DTO schemas, Application use-cases | SQL, DB clients, HTTP clients, React |
| **Application** | Orchestrate workflows, enforce app policies via **ports** | Domain model, Port interfaces | Frameworks, DB/HTTP libraries |
| **Domain** | Core business model (Entities, VO, pure domain services) | Itself | I/O, dates/clocks without being passed in |
| **Infrastructure** | Implement ports (DB/HTTP/cache/files), schedulers, logging, config | Knex, Redis, HTTP clients, filesystem | React, controllers |
| **Frontend** | UI/UX, view models; uses generated API client & DTOs | OpenAPI/DTOs, Router, State | DB, server internals |

---

## 1) Directory Layout

```
/src
├─ interface/
│  └─ http/
│     ├─ server.ts
│     ├─ routes/
│     │  ├─ students.route.ts
│     │  ├─ courses.route.ts
│     │  └─ student-cards.route.ts
│     └─ presenters/
│
├─ application/
│  ├─ students/
│  │  ├─ use-cases/
│  │  │  ├─ BuildStudentCard.ts
│  │  │  ├─ ComputeMissingAssignments.ts
│  │  │  └─ CalculateTenure.ts
│  │  └─ ports/
│  │     ├─ StudentRepo.ts
│  │     ├─ CourseRepo.ts
│  │     └─ CanvasGateway.ts
│  └─ rti/...
│
├─ domain/
│  ├─ entities/
│  ├─ value-objects/
│  └─ services/
│
├─ infrastructure/
│  ├─ persistence/
│  │  ├─ knex/
│  │  │  ├─ knexfile.ts
│  │  │  └─ migrations/
│  │  ├─ mappers/
│  │  └─ repositories/
│  ├─ http/
│  │  └─ canvas/
│  ├─ cache/
│  ├─ schedulers/
│  ├─ logging/
│  └─ config/
│
├─ shared/
│  ├─ dto/
│  ├─ schema/
│  └─ errors/
└─ frontend/
   ├─ components/
   ├─ pages/
   ├─ hooks/
   ├─ styles/
   └─ api-sdk/
```

---

## 2) Boundary Rules

- **Interface → Application only** (controllers call use-cases; no SQL/HTTP libs here) — Express middlewares and routers wire requests ([Express](https://expressjs.com/)).  
- **Application → Ports only** (interfaces it defines).  
- **Domain is pure** (no I/O; pass clocks/random providers in).  
- **Infrastructure implements Ports** and is composed at app start.  
- **Frontend uses DTOs only** via generated SDK (OpenAPI).

---

## 3) Request Lifecycle (example)

`GET /v1/students/:id/card` → **Controller** validates input (Zod) → **Use-case** `BuildStudentCard` → calls **StudentRepo**, **CourseRepo**, **CanvasGateway** → aggregates **Domain** results → **Presenter** maps to DTO → 200 JSON. (Validation behavior and inference from Zod schemas: [Zod](https://zod.dev/)).

---

## 4) Paste-Ready Stubs (TypeScript)

> These compile as skeletons; flesh out return types and logic as you implement the first slice (“Student Cards”).

### 4.1 Interface: HTTP server & route (Express)

```ts
// src/interface/http/server.ts
import express from "express";
import cors from "cors";
import helmet from "helmet";
import { studentCardsRouter } from "./routes/student-cards.route";
import { createCompositionRoot } from "../../infrastructure/config/composition";
import { requestId } from "./support/request-id";

export async function makeServer() {
  const app = express();
  app.use(helmet());              // Secure headers (CSP, etc.) per docs
  app.use(cors());                // CORS handling per docs
  app.use(express.json());
  app.use(requestId);

  const root = await createCompositionRoot(); // DI wiring

  app.get("/healthz", (_req, res) => res.status(200).send("ok"));   // Liveness
  app.get("/readyz", (_req, res) => res.status(200).send("ready")); // Readiness

  app.use("/v1/student-cards", studentCardsRouter(root));

  app.use((err: any, _req, res, _next) => {
    // Last-resort error boundary: map to uniform envelope
    const status = err?.status ?? 500;
    res.status(status).json({ error: { code: err?.code ?? "INTERNAL", message: err?.message ?? "Unexpected error" } });
  });

  return app;
}

// src/interface/http/routes/student-cards.route.ts
import { Router } from "express";
import { z } from "zod";
import { buildStudentCardResponse } from "../presenters/student-cards.presenter";
import { studentIdParamSchema } from "../../../shared/schema/common.schema";

export const studentCardsRouter = (root: CompositionRoot) => {
  const r = Router();

  r.get("/:studentId", async (req, res, next) => {
    try {
      const { studentId } = studentIdParamSchema.parse(req.params); // Zod validation
      const useCase = root.application.students.buildStudentCard;
      const result = await useCase.execute({ studentId });
      res.status(200).json(buildStudentCardResponse(result));
    } catch (e) { next(e); }
  });

  return r;
};

// src/interface/http/presenters/student-cards.presenter.ts
import type { StudentCard } from "../../../shared/dto/student-card.dto";

export function buildStudentCardResponse(card: StudentCard) {
  return { data: card };
}

// src/interface/http/support/request-id.ts
import { RequestHandler } from "express";
import { randomUUID } from "crypto";
export const requestId: RequestHandler = (req, _res, next) => {
  (req as any).requestId = req.headers["x-request-id"] ?? randomUUID();
  next();
};
```

**Why this shape?** Express routers & middleware provide layered request handling and JSON parsing as documented in Express ([docs](https://expressjs.com/)).

---

### 4.2 Application: use-case & ports

```ts
// src/application/students/use-cases/BuildStudentCard.ts
import type { StudentRepo } from "../ports/StudentRepo";
import type { CourseRepo } from "../ports/CourseRepo";
import type { CanvasGateway } from "../ports/CanvasGateway";
import type { Clock } from "../../../shared/dto/clock";

export interface BuildStudentCardInput { studentId: string }
export interface BuildStudentCard {
  execute(input: BuildStudentCardInput): Promise<import("../../../shared/dto/student-card.dto").StudentCard>;
}

export function makeBuildStudentCard(deps: {
  students: StudentRepo;
  courses: CourseRepo;
  canvas: CanvasGateway;
  clock: Clock;
}): BuildStudentCard {
  return {
    async execute({ studentId }) {
      const student = await deps.students.byId(studentId);
      const courses = await deps.courses.byStudent(studentId);
      const canvasData = await deps.canvas.enrichedStudent(studentId);

      // TODO: invoke pure domain services to compute tenure/risk/etc.
      // return a DTO shape expected by the presenter
      return {
        studentId: student.id.value,
        name: student.name,
        courses: courses.map(c => ({ id: c.id.value, name: c.name })),
        metrics: { /* …computed … */ },
        updatedAt: deps.clock.now().toISOString(),
      };
    },
  };
}

// src/application/students/ports/StudentRepo.ts
import type { Student } from "../../../domain/entities/Student";
export interface StudentRepo {
  byId(id: string): Promise<Student>;
  save(student: Student): Promise<void>;
}

// src/application/students/ports/CourseRepo.ts
import type { Course } from "../../../domain/entities/Course";
export interface CourseRepo {
  byStudent(studentId: string): Promise<Course[]>;
}

// src/application/students/ports/CanvasGateway.ts
export interface CanvasGateway {
  enrichedStudent(studentId: string): Promise<unknown>; // refine type as needed
}
```

---

### 4.3 Domain: entities, value objects, pure rules

```ts
// src/domain/value-objects/StudentId.ts
export class StudentId {
  private constructor(public readonly value: string) {}
  static create(value: string) {
    if (!/^[a-zA-Z0-9_-]+$/.test(value)) throw new Error("Invalid StudentId");
    return new StudentId(value);
  }
}

// src/domain/entities/Student.ts
import { StudentId } from "../value-objects/StudentId";
export class Student {
  constructor(
    public readonly id: StudentId,
    public name: string,
    public tenureMonths: number
  ) {}
}

// src/domain/entities/Course.ts
import { StudentId } from "../value-objects/StudentId";
export class Course {
  constructor(
    public readonly id: { value: string },
    public readonly name: string,
    public readonly studentId: StudentId
  ) {}
}

// src/domain/services/TenureRules.ts
export const TenureRules = {
  monthsBetween(startISO: string, endISO: string, clock: { now: () => Date }) {
    const start = new Date(startISO).getTime();
    const end = new Date(endISO).getTime();
    return Math.max(0, Math.floor((end - start) / (1000 * 60 * 60 * 24 * 30)));
  },
};
```

> Domain functions are pure/deterministic; they do not import frameworks or perform I/O (Clean Architecture guidance).

---

### 4.4 Shared: DTOs & Zod schemas (validation)

```ts
// src/shared/dto/student-card.dto.ts
export interface StudentCard {
  studentId: string;
  name: string;
  courses: { id: string; name: string }[];
  metrics: { [k: string]: number | string | boolean };
  updatedAt: string; // ISO
}

// src/shared/schema/common.schema.ts
import { z } from "zod";
export const studentIdParamSchema = z.object({ studentId: z.string().min(1) });

// src/shared/schema/student-card.schema.ts
import { z } from "zod";
export const studentCardResponseSchema = z.object({
  data: z.object({
    studentId: z.string(),
    name: z.string(),
    courses: z.array(z.object({ id: z.string(), name: z.string() })),
    metrics: z.record(z.union([z.number(), z.string(), z.boolean()])),
    updatedAt: z.string().datetime(),
  }),
});
```

> Zod provides runtime validation and infers TS types from schemas, which is why it’s ideal for boundary validation and contract generation ([Zod docs](https://zod.dev/)). You can generate OpenAPI from Zod using community tooling to produce a typed frontend SDK ([OpenAPI](https://www.openapis.org/)).

---

### 4.5 Infrastructure: composition (DI), repositories, gateway, knex, redis, logging, scheduler

```ts
// src/infrastructure/config/composition.ts
import { makeBuildStudentCard } from "../../application/students/use-cases/BuildStudentCard";
import { StudentRepoKnex } from "../persistence/repositories/StudentRepoKnex";
import { CourseRepoKnex } from "../persistence/repositories/CourseRepoKnex";
import { CanvasGatewayHttp } from "../http/canvas/CanvasGatewayHttp";
import { createDb } from "../persistence/knex/db";
import { createLogger } from "../logging/logger";

export interface CompositionRoot {
  application: {
    students: {
      buildStudentCard: ReturnType<typeof makeBuildStudentCard>;
    };
  };
}

export async function createCompositionRoot(): Promise<CompositionRoot> {
  const db = await createDb();
  const logger = createLogger();

  const repos = {
    students: new StudentRepoKnex(db),
    courses: new CourseRepoKnex(db),
  };
  const canvas = new CanvasGatewayHttp({ baseUrl: process.env.CANVAS_URL!, token: process.env.CANVAS_TOKEN! });

  const clock = { now: () => new Date() };

  return {
    application: {
      students: {
        buildStudentCard: makeBuildStudentCard({ students: repos.students, courses: repos.courses, canvas, clock }),
      },
    },
  };
}
export type { CompositionRoot };
```

```ts
// src/infrastructure/persistence/knex/db.ts
import knex, { Knex } from "knex";
import config from "./knexfile";
export async function createDb(): Promise<Knex> {
  const env = (process.env.NODE_ENV ?? "development") as "development" | "staging" | "production";
  return knex(config[env]); // Knex supports env-specific configs & migrations per docs
}

// src/infrastructure/persistence/knex/knexfile.ts
import type { Knex } from "knex";
const shared: Knex.Config = {
  client: "pg",
  migrations: { tableName: "knex_migrations", directory: "./migrations" },
};
const config: Record<string, Knex.Config> = {
  development: { ...shared, connection: process.env.DATABASE_URL },
  staging:     { ...shared, connection: process.env.DATABASE_URL },
  production:  { ...shared, connection: process.env.DATABASE_URL, pool: { min: 2, max: 10 } },
};
export default config;
```

```ts
// src/infrastructure/persistence/repositories/StudentRepoKnex.ts
import type { Knex } from "knex";
import { StudentRepo } from "../../../application/students/ports/StudentRepo";
import { Student } from "../../../domain/entities/Student";
import { StudentId } from "../../../domain/value-objects/StudentId";

export class StudentRepoKnex implements StudentRepo {
  constructor(private readonly db: Knex) {}
  async byId(id: string): Promise<Student> {
    const row = await this.db("students").where({ id }).first();
    if (!row) throw Object.assign(new Error("Not found"), { status: 404, code: "STUDENT_NOT_FOUND" });
    return new Student(StudentId.create(row.id), row.name, row.tenure_months);
  }
  async save(student: Student): Promise<void> {
    await this.db("students")
      .insert({ id: student.id.value, name: student.name, tenure_months: student.tenureMonths })
      .onConflict("id").merge();
  }
}

// src/infrastructure/persistence/repositories/CourseRepoKnex.ts
import type { Knex } from "knex";
import { CourseRepo } from "../../../application/students/ports/CourseRepo";
import { Course } from "../../../domain/entities/Course";
import { StudentId } from "../../../domain/value-objects/StudentId";

export class CourseRepoKnex implements CourseRepo {
  constructor(private readonly db: Knex) {}
  async byStudent(studentId: string): Promise<Course[]> {
    const rows = await this.db("courses").where({ student_id: studentId });
    return rows.map((r: any) => new Course({ value: r.id }, r.name, StudentId.create(r.student_id)));
  }
}
```

```ts
// src/infrastructure/http/canvas/CanvasGatewayHttp.ts
import fetch from "node-fetch";
import { CanvasGateway } from "../../../application/students/ports/CanvasGateway";

export class CanvasGatewayHttp implements CanvasGateway {
  constructor(private readonly cfg: { baseUrl: string; token: string }) {}
  async enrichedStudent(studentId: string): Promise<unknown> {
    const res = await fetch(`${this.cfg.baseUrl}/api/v1/users/${studentId}`, {
      headers: { Authorization: `Bearer ${this.cfg.token}` },
    });
    if (!res.ok) throw Object.assign(new Error("Canvas error"), { status: res.status, code: "CANVAS_ERROR" });
    return res.json();
  }
}
```

```ts
// src/infrastructure/cache/redisClient.ts
import { createClient } from "redis";
export function makeRedis() {
  const client = createClient({ url: process.env.REDIS_URL });
  client.on("error", (err) => console.error("Redis error", err));
  return client.connect().then(() => client);
} // Redis supports pub/sub, TTL, and key/value caching per docs
```

```ts
// src/infrastructure/logging/logger.ts
import winston from "winston";
export function createLogger() {
  return winston.createLogger({
    level: process.env.LOG_LEVEL ?? "info",
    transports: [new winston.transports.Console()],
    format: winston.format.json(),
  });
} // Winston transports/levels configurable per docs
```

```ts
// src/infrastructure/schedulers/sync-jobs.ts
import cron from "node-cron";
export function scheduleJobs(root: import("../../infrastructure/config/composition").CompositionRoot) {
  // Every 15 minutes, trigger Canvas sync (example)
  cron.schedule("*/15 * * * *", async () => {
    // await root.application.students.syncCanvasDelta.execute();
  });
} // Cron expression handling per node-cron docs
```

---

### 4.6 API error envelope & codes

```ts
// src/shared/errors/errors.ts
export type ErrorCode =
  | "STUDENT_NOT_FOUND"
  | "CANVAS_ERROR"
  | "VALIDATION_ERROR"
  | "INTERNAL";

export interface ApiError {
  code: ErrorCode;
  message: string;
  details?: unknown;
}
```

**HTTP mapping (controller level):**
- `STUDENT_NOT_FOUND` → `404`
- `VALIDATION_ERROR` → `400`
- `CANVAS_ERROR` → `502`
- `INTERNAL` → `500`

---

## 5) Security & Compliance

- **RBAC in Application**: check roles/scopes inside use-cases (keeps policies testable).  
- **CORS** configured in Interface via middleware ([MDN](https://developer.mozilla.org/docs/Web/HTTP/CORS)).  
- **CSP** via `helmet` ([Helmet docs](https://helmetjs.github.io/); [MDN CSP](https://developer.mozilla.org/docs/Web/HTTP/CSP)).  
- Secrets through environment variables; typed config in `infrastructure/config`.

---

## 6) Observability

- **/healthz** (liveness) and **/readyz** (readiness) in Interface.  
- **Structured logs** (JSON) with request IDs (Winston supports multiple transports/levels per docs).  
- Consider Prometheus & OpenTelemetry for metrics/traces later ([OpenTelemetry](https://opentelemetry.io/)).

---

## 7) Testing Strategy (quick map)

- **Domain** — unit tests (pure rules).  
- **Application** — use fake/in-memory ports to test workflows.  
- **Infrastructure** — integration tests (Knex ↔ test DB; Canvas ↔ mock server).  
- **Interface** — contract tests: DTO validation & status codes.  
- **E2E** — a few smoke tests on critical flows.

---

## 8) Frontend (React + Vite + Tailwind)

```
/src/frontend
├─ pages/        # routing & data orchestration
├─ components/   # reusable UI
├─ hooks/        # UI-only hooks
├─ styles/
└─ api-sdk/      # generated from OpenAPI
```

- Generate a typed SDK from OpenAPI so FE uses the same DTOs as the server ([OpenAPI](https://www.openapis.org/)).  
- React component model & effects/state follow React’s rules of hooks ([docs](https://react.dev/)).  
- Vite dev server/build per Vite docs ([docs](https://vitejs.dev/)).

---

## 9) CI/CD & Quality

- **CI**: `lint`, `tsc --noEmit`, unit tests, build, migrations dry-run (`knex migrate:latest --dry-run` — supported per Knex docs).  
- **CD**: run DB migrations once per release; blue/green or rolling.  
- **Quality**: ESLint, Prettier, strict TS.  
- **ADRs** in `/docs/adrs` (format: [adr.github.io](https://adr.github.io/)).

---

## 10) Migration Checklist (use for the refactor)

- [ ] Create `application/*/ports` (move repo/gateway **interfaces** here)  
- [ ] Move **implementations** to `infrastructure/*` (knex/http/cache)  
- [ ] Collapse prior “aggregation layer” into **domain services** (pure) or **application use-cases** (orchestration)  
- [ ] Introduce `shared/schema` (Zod) and wire controllers to it  
- [ ] Generate OpenAPI + FE SDK; place SDK in `frontend/api-sdk`  
- [ ] Add `/healthz`, `/readyz`, request-ID middleware, structured logging  
- [ ] Migrate one slice end-to-end (“Student Card”) using the stubs above

---

## 11) Versioning & Deprecation

- Prefix routes with `/v1`.  
- When changing DTOs, add `/v2` counterparts and set **Sunset**/**Deprecation** headers; maintain a CHANGELOG & ADR note.

---

## 12) Non-Functional Budgets

- P95 simple read < 300ms; error rate < 1%; sync freshness < 10 min.  
- Retries with backoff/jitter for Canvas calls; circuit breaker on repeated failures.

---

## 13) How to Start Locally (placeholder)

- `cp .env.example .env` and fill `DATABASE_URL`, `CANVAS_URL`, `CANVAS_TOKEN`.  
- `npm run db:migrate` (Knex, per docs).  
- `npm run dev:backend` (Express + ts-node/vite-node).  
- `npm run dev:frontend` (Vite).  
- Hit `GET /healthz`.

---

### Appendix: Why this architecture fits your needs

- **Fast lateral changes** — New feature = 1 controller + 1 use-case + 0–N port methods; domain rules stay pure.  
- **Fast vertical swaps** — Change DB/cache/external API by swapping Infra adapters; Application/Domain untouched.  
- **Predictable boundaries** — Each layer’s job is small, explicit, and testable.
