/**
 * Enhanced API Call-Centric Architecture
 * 
 * Supports both single-course operations and bulk multi-course operations.
 * Organizes Canvas data by API endpoint calls rather than entity types.
 * Supports configuration-driven selective data collection.
 */

import { SyncConfiguration, FULL_SYNC_PROFILE } from '../types/sync-configuration';

import { 
  CanvasCourseApiDataSet,
  CourseInfoCall,
  EnrollmentsCall,
  AssignmentsCall,
  ModulesCall,
  StudentAnalyticsCall,
  DatabaseCourseRecord,
  DatabaseStudentRecord,
  DatabaseAssignmentRecord,
  DatabaseEnrollmentRecord,
  ApiCallMetadata
} from './api-call-staging';

// Bulk-specific interfaces
interface CourseListCall {
  callType: 'course_list';
  endpoint: string; // /courses
  data: CourseListRecord[];
  metadata: ApiCallMetadata;
}

/**
 * Bulk Canvas Data Manager - handles multiple courses simultaneously
 * 
 * This class manages API calls that retrieve data for ALL courses at once,
 * as opposed to the single-course focused CanvasCourseApiDataSet.
 * Supports configuration-driven selective data collection.
 */
export class CanvasBulkApiDataManager {
  // Configuration
  config: SyncConfiguration;
  
  // Bulk API call results (for ALL courses)
  allCoursesList?: CourseListCall;  // GET /courses (all available courses)
  
  // Individual course data sets (keyed by course ID)
  courseDataSets: Map<number, CanvasCourseApiDataSet>;
  
  // Construction metadata
  constructionStartTime: Date;
  constructionEndTime?: Date;
  totalApiCalls: number = 0;
  totalProcessingTime: number = 0;

  constructor(config?: SyncConfiguration) {
    this.config = config || FULL_SYNC_PROFILE;
    this.courseDataSets = new Map();
    this.constructionStartTime = new Date();
  }

  // ===========================================
  // BULK API CALL COLLECTION METHODS
  // ===========================================

  /**
   * Add bulk course list API call result (ALL courses)
   * This is typically the first call made to discover what courses are available
   */
  addAllCoursesList(data: CourseListRecord[], metadata: ApiCallMetadata): void {
    this.allCoursesList = {
      callType: 'course_list',
      endpoint: metadata.endpoint, // GET /courses
      data: data,
      metadata
    };
    this.totalApiCalls += metadata.apiCallsUsed;
    this.totalProcessingTime += metadata.responseTime;
    
    console.log(`📋 Added bulk course list: ${data.length} courses discovered`);
  }

  /**
   * Initialize individual course data sets based on discovered courses
   */
  initializeCourseDataSets(courseIds: number[]): void {
    courseIds.forEach(courseId => {
      if (!this.courseDataSets.has(courseId)) {
        // Pass configuration to each course data set
        this.courseDataSets.set(courseId, new CanvasCourseApiDataSet(courseId, this.config));
      }
    });
    
    console.log(`🏢️ Initialized ${courseIds.length} course data sets`);
  }

  /**
   * Get or create a course data set for a specific course
   */
  getCourseDataSet(courseId: number): CanvasCourseApiDataSet {
    if (!this.courseDataSets.has(courseId)) {
      // Pass configuration to new course data set
      this.courseDataSets.set(courseId, new CanvasCourseApiDataSet(courseId, this.config));
    }
    return this.courseDataSets.get(courseId)!;
  }

  // ===========================================
  // BULK DATABASE RECONSTRUCTION METHODS
  // ===========================================

  /**
   * Reconstruct ALL course records from bulk course list for database insertion
   * This uses the bulk course list API call data
   */
  reconstructAllCourses(): DatabaseCourseRecord[] {
    if (!this.allCoursesList) {
      console.warn('No bulk course list available for reconstruction');
      return [];
    }

    return this.allCoursesList.data.map(courseData => ({
      id: courseData.id,
      name: courseData.name,
      course_code: courseData.course_code,
      calendar_ics: courseData.calendar?.ics || '',
      workflow_state: courseData.workflow_state,
      start_at: courseData.start_at,
      end_at: courseData.end_at,
      created_at: courseData.created_at,
      updated_at: courseData.updated_at,
      last_synced: new Date().toISOString()
    }));
  }

  /**
   * Reconstruct ALL student records from all course data sets
   */
  reconstructAllStudents(): DatabaseStudentRecord[] {
    const allStudents: DatabaseStudentRecord[] = [];
    
    this.courseDataSets.forEach(courseDataSet => {
      const students = courseDataSet.reconstructStudents();
      allStudents.push(...students);
    });
    
    return allStudents;
  }

  /**
   * Reconstruct ALL assignment records from all course data sets
   */
  reconstructAllAssignments(): DatabaseAssignmentRecord[] {
    const allAssignments: DatabaseAssignmentRecord[] = [];
    
    this.courseDataSets.forEach(courseDataSet => {
      const assignments = courseDataSet.reconstructAssignments();
      allAssignments.push(...assignments);
    });
    
    return allAssignments;
  }

  /**
   * Reconstruct ALL enrollment records from all course data sets
   */
  reconstructAllEnrollments(): DatabaseEnrollmentRecord[] {
    const allEnrollments: DatabaseEnrollmentRecord[] = [];
    
    this.courseDataSets.forEach(courseDataSet => {
      const enrollments = courseDataSet.reconstructEnrollments();
      allEnrollments.push(...enrollments);
    });
    
    return allEnrollments;
  }

  // ===========================================
  // BULK MODULAR REBUILD METHODS
  // ===========================================

  /**
   * Rebuild course list by refreshing the bulk course API call
   */
  async rebuildAllCoursesList(dataConstructor: any): Promise<void> {
    console.log('🔄 Rebuilding bulk course list...');
    const startTime = Date.now();
    
    try {
      const coursesData = await dataConstructor.getAllActiveCoursesStaging();
      const metadata: ApiCallMetadata = {
        endpoint: '/courses',
        timestamp: new Date(),
        responseTime: Date.now() - startTime,
        recordCount: coursesData.length,
        apiCallsUsed: 1,
        success: true
      };
      
      // Convert CanvasCourseStaging objects to CourseListRecord format
      const courseRecords = coursesData.map((courseStaging: any) => ({
        id: courseStaging.id,
        name: courseStaging.name,
        course_code: courseStaging.course_code,
        workflow_state: 'available', // From the staging filter
        start_at: courseStaging.start_at || '',
        end_at: courseStaging.end_at || '',
        calendar: { ics: courseStaging.calendar?.ics || '' },
        created_at: courseStaging.created_at || new Date().toISOString(),
        updated_at: courseStaging.updated_at || new Date().toISOString()
      }));
      
      this.addAllCoursesList(courseRecords, metadata);
      console.log(`✅ Bulk course list rebuilt: ${courseRecords.length} courses in ${Date.now() - startTime}ms`);
    } catch (error) {
      console.error(`❌ Failed to rebuild bulk course list: ${error}`);
      throw error;
    }
  }

  /**
   * Rebuild specific data type for ALL courses
   */
  async rebuildAllEnrollments(dataConstructor: any): Promise<void> {
    console.log('🔄 Rebuilding enrollments for all courses...');
    const promises: Promise<void>[] = [];
    
    this.courseDataSets.forEach(courseDataSet => {
      promises.push(courseDataSet.rebuildEnrollments(dataConstructor));
    });
    
    await Promise.all(promises);
    console.log('✅ All course enrollments rebuilt');
  }

  async rebuildAllAssignments(dataConstructor: any): Promise<void> {
    console.log('🔄 Rebuilding assignments for all courses...');
    const promises: Promise<void>[] = [];
    
    this.courseDataSets.forEach(courseDataSet => {
      promises.push(courseDataSet.rebuildAssignments(dataConstructor));
    });
    
    await Promise.all(promises);
    console.log('✅ All course assignments rebuilt');
  }

  // ===========================================
  // BULK WORKFLOW METHODS
  // ===========================================

  /**
   * Complete bulk workflow: Discover courses → Initialize data sets → Build individual course data
   */
  async executeBulkWorkflow(dataConstructor: any, courseFilters?: {
    includeUnpublished?: boolean;
    workflowStates?: string[];
    maxCourses?: number;
  }): Promise<BulkWorkflowResult> {
    const workflowStart = Date.now();
    console.log('🚀 Starting bulk Canvas data workflow...');
    
    try {
      // Step 1: Discover all available courses
      console.log('📋 Step 1: Discovering all available courses...');
      await this.rebuildAllCoursesList(dataConstructor);
      
      if (!this.allCoursesList) {
        throw new Error('Failed to retrieve course list');
      }
      
      // Step 2: Filter courses if needed
      let coursesToProcess = this.allCoursesList.data;
      if (courseFilters) {
        if (courseFilters.workflowStates) {
          coursesToProcess = coursesToProcess.filter(course => 
            courseFilters.workflowStates!.includes(course.workflow_state)
          );
        }
        if (courseFilters.maxCourses) {
          coursesToProcess = coursesToProcess.slice(0, courseFilters.maxCourses);
        }
      }
      
      console.log(`📊 Processing ${coursesToProcess.length} courses (filtered from ${this.allCoursesList.data.length})`);
      
      // Step 3: Initialize course data sets
      const courseIds = coursesToProcess.map(course => course.id);
      this.initializeCourseDataSets(courseIds);
      
      // Step 4: Build individual course data (in batches to respect rate limits)
      const batchSize = 3; // Process 3 courses at a time
      const batches: number[][] = [];
      for (let i = 0; i < courseIds.length; i += batchSize) {
        batches.push(courseIds.slice(i, i + batchSize));
      }
      
      console.log(`⚡ Processing ${batches.length} batches of courses...`);
      
      for (let i = 0; i < batches.length; i++) {
        const batch = batches[i];
        console.log(`📦 Processing batch ${i + 1}/${batches.length}: courses ${batch.join(', ')}`);
        
        const batchPromises = batch.map(async courseId => {
          const courseDataSet = this.getCourseDataSet(courseId);
          
          // Build course data using the enhanced constructor
          await courseDataSet.rebuildCourseInfo(dataConstructor);
          await courseDataSet.rebuildEnrollments(dataConstructor);
          await courseDataSet.rebuildAssignments(dataConstructor);
          
          courseDataSet.completeConstruction();
        });
        
        await Promise.all(batchPromises);
        
        // Small delay between batches to be respectful to Canvas API
        if (i < batches.length - 1) {
          await new Promise(resolve => setTimeout(resolve, 1000));
        }
      }
      
      // Step 5: Calculate final metrics
      this.completeConstruction();
      const workflowTime = Date.now() - workflowStart;
      
      const result: BulkWorkflowResult = {
        success: true,
        coursesDiscovered: this.allCoursesList.data.length,
        coursesProcessed: coursesToProcess.length,
        totalStudents: this.reconstructAllStudents().length,
        totalAssignments: this.reconstructAllAssignments().length,
        totalEnrollments: this.reconstructAllEnrollments().length,
        totalApiCalls: this.totalApiCalls,
        totalProcessingTime: workflowTime,
        averageTimePerCourse: workflowTime / coursesToProcess.length,
        coursesReady: courseIds,
        errors: []
      };
      
      console.log('🎉 Bulk workflow completed successfully!');
      console.log(`📊 Results: ${result.coursesProcessed} courses, ${result.totalStudents} students, ${result.totalAssignments} assignments`);
      console.log(`⚡ Performance: ${result.totalApiCalls} API calls in ${result.totalProcessingTime}ms`);
      
      return result;
      
    } catch (error) {
      console.error('💥 Bulk workflow failed:', error);
      
      return {
        success: false,
        coursesDiscovered: this.allCoursesList?.data.length || 0,
        coursesProcessed: 0,
        totalStudents: 0,
        totalAssignments: 0,
        totalEnrollments: 0,
        totalApiCalls: this.totalApiCalls,
        totalProcessingTime: Date.now() - workflowStart,
        averageTimePerCourse: 0,
        coursesReady: [],
        errors: [error.message || 'Unknown error']
      };
    }
  }

  // ===========================================
  // UTILITY METHODS
  // ===========================================

  /**
   * Get bulk operation summary
   */
  getBulkSummary() {
    return {
      coursesDiscovered: this.allCoursesList?.data.length || 0,
      courseDataSetsInitialized: this.courseDataSets.size,
      totalApiCalls: this.totalApiCalls,
      totalProcessingTime: this.totalProcessingTime,
      constructionTime: this.constructionEndTime ? 
        this.constructionEndTime.getTime() - this.constructionStartTime.getTime() : null,
      individualCourseSummaries: Array.from(this.courseDataSets.entries()).map(
        ([courseId, dataSet]) => ({
          courseId,
          ...dataSet.getCollectionSummary()
        })
      )
    };
  }

  /**
   * Mark bulk construction as complete
   */
  completeConstruction(): void {
    this.constructionEndTime = new Date();
  }

  /**
   * Get courses that are ready for database ingestion (have complete data)
   */
  getReadyCourses(): number[] {
    return Array.from(this.courseDataSets.entries())
      .filter(([_, dataSet]) => {
        const summary = dataSet.getCollectionSummary();
        return summary.hasCompleteCourseInfo && summary.enrollmentCount > 0;
      })
      .map(([courseId, _]) => courseId);
  }
}

// Result interface for bulk workflow
interface BulkWorkflowResult {
  success: boolean;
  coursesDiscovered: number;
  coursesProcessed: number;
  totalStudents: number;
  totalAssignments: number;
  totalEnrollments: number;
  totalApiCalls: number;
  totalProcessingTime: number;
  averageTimePerCourse: number;
  coursesReady: number[];
  errors: string[];
}

// Course list record interface (for bulk course discovery)
interface CourseListRecord {
  id: number;
  name: string;
  course_code: string;
  workflow_state: string;
  start_at: string;
  end_at: string;
  calendar?: { ics?: string };
  created_at: string;
  updated_at: string;
}

export {
  CanvasBulkApiDataManager,
  BulkWorkflowResult,
  CourseListRecord
};