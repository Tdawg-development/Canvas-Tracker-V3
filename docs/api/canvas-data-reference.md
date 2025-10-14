# Canvas Course Data Object Tree

## Overview
This document provides a complete top-down view of the Canvas Course object structure created by the `CanvasDataConstructor`. The tree shows all information contained within one complete course object.

---

## 🏫 CanvasCourseStaging (Root Object)

```typescript
CanvasCourseStaging {
  // Basic Course Information
  id: number                    // Canvas course ID
  name: string                  // Course display name
  course_code: string           // Course code (e.g., "MATH101-001")
  
  // Calendar Integration
  calendar: {
    ics: string                 // ICS calendar URL or content
  }
  
  // Collections
  students: CanvasStudentStaging[]     // Array of enrolled students
  modules: CanvasModuleStaging[]       // Array of course modules
  
  // Helper Methods
  getAllAssignments(): CanvasAssignmentStaging[]
  loadAllStudentAnalytics(): Promise<void>
  getSummary(): CourseSummary
}
```

---

## 👥 CanvasStudentStaging Objects

```typescript
CanvasStudentStaging {
  // Enrollment Information
  id: number                    // Enrollment ID
  user_id: number               // Student's Canvas user ID
  created_at: string            // Enrollment creation date
  last_activity_at: string | null  // Last activity timestamp
  
  // Grade Information
  current_score: number | null  // Current grade percentage
  final_score: number | null    // Final grade percentage (includes zeros for missing)
  
  // Student Profile
  user: {
    id: number                  // Same as user_id above
    name: string                // Full display name
    sortable_name: string       // Last, First format
    login_id: string            // Username/email
  }
  
  // Assignment Analytics (loaded asynchronously)
  submitted_assignments: AssignmentAnalytic[]   // Completed assignments
  missing_assignments: AssignmentAnalytic[]     // Missing/incomplete assignments
  
  // Helper Methods
  hasMissingAssignments(): boolean             // current_score != final_score
  loadAssignmentAnalytics(): Promise<void>     // Loads assignment arrays
  getAssignmentSummary(): StudentSummary
  getTotalAssignments(): number
}
```

### 📊 AssignmentAnalytic Objects (within students)

```typescript
AssignmentAnalytic {
  assignment_id: number         // Canvas assignment ID
  title: string                 // Assignment name
  status: string                // "on_time" | "late" | "missing" | "floating"
  
  submission: {
    score: number | null        // Points earned (null = not submitted)
    submitted_at: string | null // Submission timestamp
    posted_at: string | null    // Grade posting timestamp
  }
  
  points_possible: number       // Maximum points for assignment
  excused: boolean             // Whether student is excused from assignment
}
```

---

## 📚 CanvasModuleStaging Objects

```typescript
CanvasModuleStaging {
  // Module Information
  id: number                    // Canvas module ID
  name: string                  // Module display name
  position: number              // Order position in course
  published: boolean            // Whether module is visible to students
  
  // Assignments within Module
  assignments: CanvasAssignmentStaging[]  // Array of assignments/quizzes in module
}
```

---

## 📝 CanvasAssignmentStaging Objects

```typescript
CanvasAssignmentStaging {
  // Assignment Information
  id: number                    // Canvas assignment/quiz ID
  position: number              // Position within module
  published: boolean            // Whether visible to students
  title: string                 // Assignment name
  type: string                  // "Assignment" | "Quiz"
  url: string                   // Canvas URL to assignment
  
  // Grading Information
  content_details: {
    points_possible: number     // Maximum points for this assignment
  }
}
```

---

## 📈 Summary Objects

### CourseSummary (from course.getSummary())
```typescript
CourseSummary {
  course_id: number
  course_name: string
  students_count: number
  modules_count: number
  total_assignments: number
  published_assignments: number
  total_possible_points: number
  students_with_scores: number
}
```

### StudentSummary (from student.getAssignmentSummary())
```typescript
StudentSummary {
  student_id: number
  student_name: string
  total_assignments: number
  submitted_count: number
  missing_count: number
  submission_rate: string       // Percentage as string with %
}
```

---

## 🔍 Data Loading Process

### 1. Course Construction Flow
```
courseId (input) → CanvasDataConstructor.constructCourseData()
│
├── Step 1: getCourseData() → CanvasCourseStaging
├── Step 2: getStudentsData() → CanvasStudentStaging[]
├── Step 3: getModulesData() → CanvasModuleStaging[]
└── Step 4: Assemble complete object tree
```

### 2. Assignment Analytics Loading (Optimized)
```
course.loadAllStudentAnalytics()
│
└── For each student:
    ├── Check if hasMissingAssignments() (current_score != final_score)
    ├── If YES: Call API → Load submitted_assignments[] & missing_assignments[]
    └── If NO: Skip API call (performance optimization)
```

---

## 💡 Key Design Features

### Performance Optimizations
- **Smart API Calls**: Only loads assignment analytics for students with missing assignments
- **Batch Processing**: Processes students in batches of 5 for assignment analytics
- **Score Comparison**: Uses `current_score != final_score` to detect missing assignments

### Data Relationships
- **Course → Students**: One-to-many relationship
- **Course → Modules**: One-to-many relationship  
- **Modules → Assignments**: One-to-many relationship
- **Students → Assignment Analytics**: One-to-many (loaded on demand)

### Async Loading Pattern
- Core data (course, students, modules) loaded synchronously during construction
- Assignment analytics loaded asynchronously via `loadAssignmentAnalytics()`
- Allows for flexible data loading based on performance needs

---

## 🎯 Usage Examples

### Get Complete Course Data
```typescript
const constructor = new CanvasDataConstructor();
const courseData = await constructor.constructCourseData(12345);
```

### Access Nested Information
```typescript
// Course basics
console.log(`Course: ${courseData.name} (${courseData.course_code})`);
console.log(`Students: ${courseData.students.length}`);

// Student information
courseData.students.forEach(student => {
  console.log(`${student.user.name}: ${student.current_score}%`);
});

// All assignments across modules
const allAssignments = courseData.getAllAssignments();
console.log(`Total assignments: ${allAssignments.length}`);

// Load and analyze missing assignments
await courseData.loadAllStudentAnalytics();
courseData.students.forEach(student => {
  if (student.missing_assignments.length > 0) {
    console.log(`${student.user.name} has ${student.missing_assignments.length} missing assignments`);
  }
});
```

This object tree provides complete visibility into all Canvas course data accessible through the `CanvasDataConstructor` system.