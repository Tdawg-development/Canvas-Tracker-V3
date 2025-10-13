/**
 * Canvas Courses API Component
 * Modular component for accessing Canvas course data
 * Curriculum-focused: Handles course retrieval and filtering
 */

import { CanvasClient } from './CanvasClient';
import {
  CanvasCourse,
  CanvasApiResponse,
} from './CanvasTypes';

export class CanvasCoursesApi {
  constructor(private readonly client: CanvasClient) {}

  /**
   * Get all courses accessible to the authenticated user
   */
  public async getAllCourses(options: {
    includeEnrollments?: boolean;
    state?: 'unpublished' | 'available' | 'completed' | 'deleted';
    perPage?: number;
  } = {}): Promise<CanvasApiResponse<CanvasCourse[]>> {
    const params: Record<string, string | number | boolean> = {
      per_page: options.perPage || 100,
    };

    const includes: string[] = [];
    
    // Always try to include total_students, though Canvas Free may not return it
    includes.push('total_students');
    
    if (includes.length > 0) {
      params.include = includes.join(',');
    }

    if (options.state) {
      params.state = options.state;
    }

    const response = await this.client.get<CanvasCourse[]>('courses', { params });
    
    // If Canvas didn't provide total_students and we need accurate counts,
    // fetch them using the dedicated students endpoint
    if (response.data && options.includeEnrollments) {
      // Fetch student counts in parallel for better performance
      const studentCountPromises = response.data.map(async (course) => {
        if (course.total_students === undefined) {
          try {
            // Get actual student count using the users endpoint
            const studentsResponse = await this.client.get<any[]>(`courses/${course.id}/users`, {
              params: {
                enrollment_type: 'student',
                enrollment_state: 'active',
                per_page: 100 // Get up to 100 students per course
              }
            });
            
            const studentCount = studentsResponse.data?.length || 0;
            return { courseId: course.id, count: studentCount };
          } catch (error) {
            // Silently handle errors and default to 0
            return { courseId: course.id, count: 0 };
          }
        }
        return { courseId: course.id, count: course.total_students || 0 };
      });
      
      const studentCounts = await Promise.all(studentCountPromises);
      
      // Apply the student counts to the courses
      const countMap = new Map(studentCounts.map(sc => [sc.courseId, sc.count]));
      response.data.forEach(course => {
        const count = countMap.get(course.id);
        if (count !== undefined) {
          course.total_students = count;
        }
      });
    }
    
    return response;
  }

  /**
   * Get specific courses by their IDs (for curriculum)
   */
  public async getCoursesByIds(
    courseIds: number[],
    options: {
      includeEnrollments?: boolean;
      includeTotalStudents?: boolean;
    } = {}
  ): Promise<CanvasApiResponse<CanvasCourse[]>> {
    // Canvas API doesn't support bulk course retrieval by IDs
    // We need to make individual requests and aggregate results
    const results: CanvasCourse[] = [];
    const errors: any[] = [];

    for (const courseId of courseIds) {
      const response = await this.getCourseById(courseId, options);
      
      if (response.data) {
        results.push(response.data);
      }
      
      if (response.errors) {
        errors.push(...response.errors);
      }
    }

    if (errors.length > 0) {
      return {
        data: results,
        errors: errors,
      };
    }
    
    return {
      data: results,
    };
  }

  /**
   * Get a single course by ID
   */
  public async getCourseById(
    courseId: number,
    options: {
      includeEnrollments?: boolean;
      includeTotalStudents?: boolean;
    } = {}
  ): Promise<CanvasApiResponse<CanvasCourse>> {
    const params: Record<string, string | number | boolean> = {};
    const includes: string[] = [];

    if (options.includeEnrollments) {
      includes.push('enrollments');
    }

    if (options.includeTotalStudents) {
      includes.push('total_students');
    }

    if (includes.length > 0) {
      params.include = includes.join(',');
    }

    return this.client.get<CanvasCourse>(`courses/${courseId}`, { params });
  }

  /**
   * Get courses for current enrollment term
   */
  public async getCurrentTermCourses(options: {
    includeEnrollments?: boolean;
    perPage?: number;
  } = {}): Promise<CanvasApiResponse<CanvasCourse[]>> {
    const params: Record<string, string | number | boolean> = {
      state: 'available',
      per_page: options.perPage || 100,
    };

    if (options.includeEnrollments) {
      params.include = 'enrollments';
    }

    return this.client.get<CanvasCourse[]>('courses', { params });
  }

  /**
   * Search courses by name or course code
   */
  public async searchCourses(
    searchTerm: string,
    options: {
      perPage?: number;
    } = {}
  ): Promise<CanvasApiResponse<CanvasCourse[]>> {
    const params: Record<string, string | number | boolean> = {
      search_term: searchTerm,
      per_page: options.perPage || 50,
    };

    return this.client.get<CanvasCourse[]>('courses', { params });
  }

  /**
   * Get course statistics for curriculum insights
   */
  public async getCourseStatistics(courseId: number): Promise<CanvasApiResponse<{
    course: CanvasCourse;
    studentCount: number;
    assignmentCount: number;
    enrollmentStats: {
      active: number;
      completed: number;
      inactive: number;
    };
  }>> {
    // This requires multiple API calls to aggregate statistics
    const [courseResponse, _studentsResponse, _assignmentsResponse] = await Promise.all([
      this.getCourseById(courseId, { includeTotalStudents: true }),
      this.client.get<any[]>(`courses/${courseId}/users`, {
        params: { enrollment_type: 'student', per_page: 1 }
      }),
      this.client.get<any[]>(`courses/${courseId}/assignments`, {
        params: { per_page: 1 }
      }),
    ]);

    if (courseResponse.errors) {
      return { errors: courseResponse.errors };
    }

    if (!courseResponse.data) {
      return { errors: [{ message: 'Course not found', error_code: 'COURSE_NOT_FOUND' }] };
    }

    // Note: This is a simplified version. In a real implementation,
    // we'd need to get enrollment statistics separately
    return {
      data: {
        course: courseResponse.data,
        studentCount: courseResponse.data.total_students || 0,
        assignmentCount: 0, // Would need to parse from Link header for total count
        enrollmentStats: {
          active: courseResponse.data.total_students || 0,
          completed: 0,
          inactive: 0,
        },
      },
    };
  }

  /**
   * Validate if courses exist and are accessible (for curriculum setup)
   */
  public async validateCoursesExist(courseIds: number[]): Promise<{
    valid: number[];
    invalid: number[];
    errors: Array<{ courseId: number; error: string }>;
  }> {
    const valid: number[] = [];
    const invalid: number[] = [];
    const errors: Array<{ courseId: number; error: string }> = [];

    for (const courseId of courseIds) {
      const response = await this.getCourseById(courseId);
      
      if (response.data) {
        valid.push(courseId);
      } else {
        invalid.push(courseId);
        const errorMessage = response.errors?.[0]?.message || 'Course not accessible';
        errors.push({ courseId, error: errorMessage });
      }
    }

    return { valid, invalid, errors };
  }
}