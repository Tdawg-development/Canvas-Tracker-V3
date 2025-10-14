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
  
  /**
   * Check if this assignment is a quiz
   */
  isQuiz(): boolean {
    return this.type.toLowerCase() === 'quiz';
  }
  
  /**
   * Check if this assignment is a regular assignment (not a quiz)
   */
  isAssignment(): boolean {
    return this.type.toLowerCase() === 'assignment';
  }
}

// Module Object
export class CanvasModuleStaging {
  id: number;
  name: string;
  position: number;
  published: boolean;
  assignments: CanvasAssignmentStaging[];

  constructor(data: any) {
    this.id = data.id;
    this.name = data.name;
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
  
  /**
   * Get only published assignments from this module
   */
  getPublishedAssignments(): CanvasAssignmentStaging[] {
    return this.assignments.filter(assignment => assignment.published);
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
  
  // Assignment analytics data
  submitted_assignments: any[];
  missing_assignments: any[];
  private courseId?: number;
  private dataConstructor?: any;

  constructor(data: any, courseId?: number, dataConstructor?: any) {
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
    
    // Initialize assignment arrays
    this.submitted_assignments = [];
    this.missing_assignments = [];
    
    // Store references for async loading
    this.courseId = courseId;
    this.dataConstructor = dataConstructor;
    
    // Note: Assignment analytics will be loaded separately via loadAssignmentAnalytics()
    // This cannot be done automatically in constructor due to async nature
  }
  
  /**
   * Check if student has missing assignments based on current vs final score
   * If current_score == final_score, student has no missing assignments
   */
  hasMissingAssignments(): boolean {
    // If either score is null, we can't determine - assume they might have missing assignments
    if (this.current_score === null || this.final_score === null) {
      return true;
    }
    
    // If scores are different, student has missing assignments
    return this.current_score !== this.final_score;
  }
  
  /**
   * Load assignment analytics and populate submitted/missing arrays
   * Optimized: Only calls API for students who actually have missing assignments
   */
  async loadAssignmentAnalytics(): Promise<void> {
    if (!this.courseId || !this.dataConstructor) {
      return;
    }
    
    // Optimization: Check if student has missing assignments first
    if (!this.hasMissingAssignments()) {
      console.log(`   ✅ Student ${this.user.name} (${this.user_id}): current_score == final_score, no missing assignments - skipping API call`);
      // No missing assignments, set arrays accordingly
      this.submitted_assignments = []; // We could populate this but it's not critical for missing assignment tracking
      this.missing_assignments = [];
      return;
    }
    
    console.log(`   📊 Student ${this.user.name} (${this.user_id}): current_score (${this.current_score}) != final_score (${this.final_score}) - loading assignment analytics`);
    
    try {
      const analytics = await this.dataConstructor.getStudentAssignmentAnalytics(
        this.courseId, 
        this.user_id
      );
      
      // Separate submitted and missing assignments
      this.submitted_assignments = analytics.filter(assignment => 
        assignment.submission.score !== null
      );
      
      this.missing_assignments = analytics.filter(assignment => 
        assignment.submission.score === null
      );
      
    } catch (error) {
      console.warn(`   ❌ Failed to load assignment analytics for student ${this.user_id}:`, error);
      // Keep arrays empty on error
      this.submitted_assignments = [];
      this.missing_assignments = [];
    }
  }
  
  /**
   * Get assignment analytics summary
   */
  getAssignmentSummary() {
    return {
      student_id: this.user_id,
      student_name: this.user.name,
      total_assignments: this.submitted_assignments.length + this.missing_assignments.length,
      submitted_count: this.submitted_assignments.length,
      missing_count: this.missing_assignments.length,
      submission_rate: this.getTotalAssignments() > 0 
        ? ((this.submitted_assignments.length / this.getTotalAssignments()) * 100).toFixed(1) + '%'
        : 'N/A'
    };
  }
  
  /**
   * Get total assignments count
   */
  getTotalAssignments(): number {
    return this.submitted_assignments.length + this.missing_assignments.length;
  }
  
  /**
   * Calculate grade improvement potential based on current vs final score gap
   */
  getGradeImprovementPotential(): number {
    if (this.current_score === null || this.final_score === null) {
      return 0; // Cannot calculate improvement potential without scores
    }
    
    // Return the difference between final possible score and current score
    return Math.max(0, this.final_score - this.current_score);
  }
  
  /**
   * Get student activity status based on last activity timestamp
   */
  getActivityStatus(): { status: string; lastActivity: string | null } {
    if (!this.last_activity_at) {
      return {
        status: 'no_activity_recorded',
        lastActivity: null
      };
    }
    
    const lastActivity = new Date(this.last_activity_at);
    const now = new Date();
    const daysSinceActivity = Math.floor((now.getTime() - lastActivity.getTime()) / (1000 * 60 * 60 * 24));
    
    let status: string;
    if (daysSinceActivity <= 1) {
      status = 'very_recent'; // Active within last day
    } else if (daysSinceActivity <= 7) {
      status = 'recent'; // Active within last week
    } else if (daysSinceActivity <= 30) {
      status = 'moderate'; // Active within last month
    } else {
      status = 'inactive'; // No recent activity
    }
    
    return {
      status,
      lastActivity: this.last_activity_at
    };
  }
  
  /**
   * Validate that student data is complete and valid
   */
  isValid(): boolean {
    // Check for required fields
    if (!this.id || !this.user_id) {
      return false;
    }
    
    // Check user data
    if (!this.user || !this.user.name || this.user.name === 'Unknown') {
      return false;
    }
    
    // Check that scores are valid if present
    if (this.current_score !== null && (this.current_score < 0 || this.current_score > 100)) {
      return false;
    }
    
    if (this.final_score !== null && (this.final_score < 0 || this.final_score > 100)) {
      return false;
    }
    
    return true;
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
    
    // Auto-process modules if provided
    if (data.modules && Array.isArray(data.modules)) {
      this.addModules(data.modules);
    }
    
    // Auto-process students if provided  
    if (data.students && Array.isArray(data.students)) {
      this.addStudents(data.students);
    }
  }

  addStudents(studentsData: any[], dataConstructor?: any): void {
    this.students = studentsData.map(student => 
      new CanvasStudentStaging(student, this.id, dataConstructor)
    );
  }

  addModules(modulesData: any[]): void {
    this.modules = modulesData.map(module => new CanvasModuleStaging(module));
  }

  // Helper method to get all assignments across all modules
  getAllAssignments(): CanvasAssignmentStaging[] {
    return this.modules.flatMap(module => module.assignments);
  }

  /**
   * Load assignment analytics for all students in the course
   * Optimized: Only calls API for students with missing assignments (current_score != final_score)
   */
  async loadAllStudentAnalytics(): Promise<void> {
    console.log(`📈 Loading assignment analytics for ${this.students.length} students...`);
    
    // Pre-analyze students to see who needs API calls
    const studentsWithMissingAssignments = this.students.filter(student => student.hasMissingAssignments());
    const studentsWithoutMissingAssignments = this.students.filter(student => !student.hasMissingAssignments());
    
    console.log(`⚡ OPTIMIZATION: ${studentsWithoutMissingAssignments.length} students have current_score == final_score (no missing assignments)`);
    console.log(`📊 API calls needed: ${studentsWithMissingAssignments.length}/${this.students.length} students`);
    
    const startTime = Date.now();
    let successCount = 0;
    let failCount = 0;
    let skippedCount = 0;
    
    // Load analytics for students with missing assignments (in batches)
    const batchSize = 5;
    for (let i = 0; i < this.students.length; i += batchSize) {
      const batch = this.students.slice(i, i + batchSize);
      
      const batchPromises = batch.map(async (student) => {
        try {
          await student.loadAssignmentAnalytics();
          if (student.hasMissingAssignments()) {
            successCount++;
          } else {
            skippedCount++;
          }
        } catch (error) {
          failCount++;
        }
      });
      
      await Promise.all(batchPromises);
      
      // Progress indicator
      if ((i + batchSize) % 10 === 0 || (i + batchSize) >= this.students.length) {
        console.log(`   📈 Processed ${Math.min(i + batchSize, this.students.length)}/${this.students.length} students...`);
      }
    }
    
    const processingTime = Date.now() - startTime;
    console.log(`✅ Assignment analytics processing completed in ${processingTime}ms`);
    console.log(`   📊 API calls made: ${successCount}`);
    console.log(`   ⚡ API calls skipped (no missing assignments): ${skippedCount}`);
    if (failCount > 0) {
      console.log(`   ⚠️ Failed: ${failCount}`);
    }
    console.log(`   🚀 API efficiency: ${skippedCount > 0 ? ((skippedCount / this.students.length) * 100).toFixed(1) + '% calls avoided' : 'No optimization possible'}`);
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
  
  /**
   * Calculate comprehensive course statistics
   */
  calculateCourseStatistics(): {
    averageGrade: number;
    totalStudents: number;
    totalAssignments: number;
    passRate: number;
    gradeDistribution: { range: string; count: number }[];
  } {
    const studentsWithScores = this.students.filter(s => s.current_score !== null);
    
    // Calculate average grade
    const averageGrade = studentsWithScores.length > 0 
      ? studentsWithScores.reduce((sum, student) => sum + (student.current_score || 0), 0) / studentsWithScores.length
      : 0;
    
    // Calculate pass rate (assuming 70% is passing)
    const passingStudents = studentsWithScores.filter(s => (s.current_score || 0) >= 70);
    const passRate = studentsWithScores.length > 0 
      ? (passingStudents.length / studentsWithScores.length) * 100
      : 0;
    
    // Calculate grade distribution
    const gradeDistribution = [
      { range: 'A (90-100)', count: studentsWithScores.filter(s => (s.current_score || 0) >= 90).length },
      { range: 'B (80-89)', count: studentsWithScores.filter(s => (s.current_score || 0) >= 80 && (s.current_score || 0) < 90).length },
      { range: 'C (70-79)', count: studentsWithScores.filter(s => (s.current_score || 0) >= 70 && (s.current_score || 0) < 80).length },
      { range: 'D (60-69)', count: studentsWithScores.filter(s => (s.current_score || 0) >= 60 && (s.current_score || 0) < 70).length },
      { range: 'F (0-59)', count: studentsWithScores.filter(s => (s.current_score || 0) < 60).length }
    ];
    
    return {
      averageGrade: Math.round(averageGrade * 100) / 100, // Round to 2 decimal places
      totalStudents: this.students.length,
      totalAssignments: this.getAllAssignments().length,
      passRate: Math.round(passRate * 100) / 100,
      gradeDistribution
    };
  }
  
  /**
   * Get students within a specific grade range
   */
  getStudentsByGradeRange(minGrade: number, maxGrade: number): CanvasStudentStaging[] {
    return this.students.filter(student => {
      if (student.current_score === null) {
        return false; // Exclude students without scores
      }
      
      return student.current_score >= minGrade && student.current_score <= maxGrade;
    });
  }
}
