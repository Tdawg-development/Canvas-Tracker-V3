/**
 * Canvas Staging Data Classes
 * 
 * Raw data structures that mirror Canvas API responses exactly.
 * No transformation or processing - just clean staging of Canvas data.
 */

// Assignment Object (from Modules API)
export class CanvasAssignmentStaging {
  id: number;
  position: number;
  published: boolean;
  title: string;
  type: string; // "assignment" || "quiz"
  url: string;
  content_details: {
    points_possible: number;
  };

  constructor(data: any) {
    this.id = data.id;
    this.position = data.position;
    this.published = data.published;
    this.title = data.title;
    this.type = data.type;
    this.url = data.url;
    this.content_details = {
      points_possible: data.content_details?.points_possible || 0
    };
  }
}

// Module Object
export class CanvasModuleStaging {
  id: number;
  position: number;
  published: boolean;
  assignments: CanvasAssignmentStaging[];

  constructor(data: any) {
    this.id = data.id;
    this.position = data.position;
    this.published = data.published;
    this.assignments = [];

    // Process module items and extract assignments/quizzes
    if (data.items && Array.isArray(data.items)) {
      this.assignments = data.items
        .filter((item: any) => item.type === 'Assignment' || item.type === 'Quiz')
        .map((item: any) => new CanvasAssignmentStaging(item));
    }
  }
}

// Student Object
export class CanvasStudentStaging {
  id: number;
  user_id: number;
  created_at: string;
  last_activity_at: string | null;
  current_score: number | null;
  final_score: number | null;
  user: {
    id: number;
    name: string;
    sortable_name: string;
    login_id: string;
  };

  constructor(data: any) {
    this.id = data.id;
    this.user_id = data.user_id;
    this.created_at = data.created_at;
    this.last_activity_at = data.last_activity_at;
    this.current_score = data.grades?.current_score || null;
    this.final_score = data.grades?.final_score || null;
    this.user = {
      id: data.user?.id || data.user_id,
      name: data.user?.name || 'Unknown',
      sortable_name: data.user?.sortable_name || 'Unknown',
      login_id: data.user?.login_id || 'Unknown'
    };
  }
}

// Course Object
export class CanvasCourseStaging {
  id: number;
  name: string;
  course_code: string;
  calendar: {
    ics: string;
  };
  students: CanvasStudentStaging[];
  modules: CanvasModuleStaging[];

  constructor(data: any) {
    this.id = data.id;
    this.name = data.name;
    this.course_code = data.course_code;
    this.calendar = {
      ics: data.calendar?.ics || ''
    };
    this.students = [];
    this.modules = [];
  }

  addStudents(studentsData: any[]): void {
    this.students = studentsData.map(student => new CanvasStudentStaging(student));
  }

  addModules(modulesData: any[]): void {
    this.modules = modulesData.map(module => new CanvasModuleStaging(module));
  }

  // Helper method to get all assignments across all modules
  getAllAssignments(): CanvasAssignmentStaging[] {
    return this.modules.flatMap(module => module.assignments);
  }

  // Helper method to get summary statistics
  getSummary() {
    const totalAssignments = this.getAllAssignments().length;
    const publishedAssignments = this.getAllAssignments().filter(a => a.published).length;
    const totalPoints = this.getAllAssignments()
      .filter(a => a.published)
      .reduce((sum, a) => sum + a.content_details.points_possible, 0);

    return {
      course_id: this.id,
      course_name: this.name,
      students_count: this.students.length,
      modules_count: this.modules.length,
      total_assignments: totalAssignments,
      published_assignments: publishedAssignments,
      total_possible_points: totalPoints,
      students_with_scores: this.students.filter(s => s.current_score !== null).length
    };
  }
}