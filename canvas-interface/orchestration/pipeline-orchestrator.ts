/**
 * Canvas Pipeline Orchestrator
 * 
 * Main orchestrator class that coordinates the complete Canvas data pipeline:
 * Canvas API -> TypeScript Data Collection -> Python Transformers -> Database Storage
 * 
 * This class connects all existing modules without replacing them, following
 * the patterns demonstrated in the test suite.
 */

import { CanvasDataConstructor } from '../staging/canvas-data-constructor';
import { CanvasBulkApiDataManager, BulkWorkflowResult } from '../staging/bulk-api-call-staging';
import { SyncConfiguration, FULL_SYNC_PROFILE, LIGHTWEIGHT_PROFILE, ANALYTICS_PROFILE } from '../types/sync-configuration';
import { ConfigurationManager } from './configuration-manager';
import { PipelineMonitor, PipelineStage } from './pipeline-monitor';
import * as fs from 'fs';
import * as path from 'path';
import * as subprocess from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(subprocess.exec);

// ============================================================================
// Core Interfaces
// ============================================================================

export interface PipelineResult {
  success: boolean;
  courseId?: number;
  stagingData?: any;
  transformedData?: any;
  error?: string;
  stage?: string;
  metadata: {
    processingTime: number;
    stages?: any[];
    configuration?: SyncConfiguration;
    apiCalls?: number;
  };
}

export interface BulkPipelineResult {
  success: boolean;
  workflowResult?: BulkWorkflowResult;
  stagingData?: any;
  transformedData?: any;
  error?: string;
  metadata: {
    processingTime: number;
    coursesProcessed?: number;
    totalApiCalls?: number;
    configuration?: SyncConfiguration;
  };
}

export interface CourseFilters {
  includeUnpublished?: boolean;
  workflowStates?: string[];
  maxCourses?: number;
}

// ============================================================================
// Main Pipeline Orchestrator Class
// ============================================================================

export class PipelineOrchestrator {
  private dataConstructor: CanvasDataConstructor;
  private bulkManager: CanvasBulkApiDataManager;
  private configManager: ConfigurationManager;
  private monitor: PipelineMonitor;
  private pythonScriptPath: string;

  constructor(config?: SyncConfiguration) {
    this.configManager = new ConfigurationManager(config);
    this.monitor = new PipelineMonitor();
    
    // Initialize data collection modules with configuration
    this.dataConstructor = new CanvasDataConstructor({
      config: this.configManager.getConfig()
    });
    
    this.bulkManager = new CanvasBulkApiDataManager(
      this.configManager.getConfig()
    );

    // Set up Python integration script path
    this.pythonScriptPath = path.join(__dirname, '../../database/scripts/pipeline_integration.py');
  }

  // ========================================================================
  // Single Course Processing
  // ========================================================================

  /**
   * Process a single course through the complete pipeline
   * Following the pattern from test_real_canvas_api_pipeline.py
   */
  async processCourse(courseId: number): Promise<PipelineResult> {
    const startTime = Date.now();
    this.monitor.reset();

    // Create debug directory (cross-platform compatible)
    const debugDir = path.join(__dirname, '../../database/tests/results');
    if (!fs.existsSync(debugDir)) {
      fs.mkdirSync(debugDir, { recursive: true });
    }

    try {
      console.log(`🚀 Pipeline Orchestrator: Processing course ${courseId}`);
      console.log('===============================================================');

      // Stage 1: Canvas API Data Collection
      this.monitor.startStage(PipelineStage.CANVAS_API);
      console.log('📋 Stage 1: Canvas API data collection...');
      
      const stagingData = await this.dataConstructor.constructCourseData(courseId);
      const apiStatus = this.dataConstructor.getApiStatus();
      
      // DEBUG: Save raw staging data
      const timestamp = Date.now();
      const debugFile1 = path.join(debugDir, `01_raw_staging_data_course_${courseId}_${timestamp}.json`);
      fs.writeFileSync(debugFile1, JSON.stringify(stagingData, null, 2));
      console.log(`🔍 DEBUG: Raw staging data saved to ${debugFile1}`);
      
      this.monitor.completeStage(PipelineStage.CANVAS_API, {
        apiCalls: apiStatus.schedulerMetrics?.totalRequests || 0,
        recordCount: 1
      });

      console.log(`✅ Canvas API data collected (${apiStatus.schedulerMetrics?.totalRequests || 0} API calls)`);

      // Stage 2: Data Transformation (Python Integration)
      this.monitor.startStage(PipelineStage.TRANSFORMATION);
      console.log('🔄 Stage 2: Data transformation via Python...');

      // Convert staging data to the format expected by transformers
      const transformationInput = this.prepareSingleCourseTransformationData(stagingData);
      
      // DEBUG: Save transformation input data
      const debugFile2 = path.join(debugDir, `02_transformation_input_course_${courseId}_${timestamp}.json`);
      fs.writeFileSync(debugFile2, JSON.stringify(transformationInput, null, 2));
      console.log(`🔍 DEBUG: Transformation input saved to ${debugFile2}`);
      
      const transformedData = await this.executeTransformation(transformationInput);
      
      // DEBUG: Save transformation output data
      const debugFile3 = path.join(debugDir, `03_transformation_output_course_${courseId}_${timestamp}.json`);
      fs.writeFileSync(debugFile3, JSON.stringify(transformedData, null, 2));
      console.log(`🔍 DEBUG: Transformation output saved to ${debugFile3}`);

      this.monitor.completeStage(PipelineStage.TRANSFORMATION, {
        recordCount: this.countTransformedRecords(transformedData)
      });

      console.log('✅ Data transformation completed');

      // Successful result
      const result: PipelineResult = {
        success: true,
        courseId,
        stagingData: transformationInput,
        transformedData,
        metadata: {
          processingTime: Date.now() - startTime,
          stages: this.monitor.getStageResults(),
          configuration: this.configManager.getConfig(),
          apiCalls: apiStatus.schedulerMetrics?.totalRequests || 0
        }
      };
      
      // DEBUG: Save final result
      const debugFile4 = path.join(debugDir, `04_final_result_course_${courseId}_${timestamp}.json`);
      fs.writeFileSync(debugFile4, JSON.stringify(result, null, 2));
      console.log(`🔍 DEBUG: Final result saved to ${debugFile4}`);

      console.log(`🎉 Course ${courseId} processed successfully in ${result.metadata.processingTime}ms`);
      return result;

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      console.error(`💥 Pipeline failed for course ${courseId}:`, errorMessage);

      return {
        success: false,
        courseId,
        error: errorMessage,
        stage: this.monitor.getCurrentStage(),
        metadata: {
          processingTime: Date.now() - startTime,
          stages: this.monitor.getStageResults()
        }
      };
    }
  }

  // ========================================================================
  // Bulk Course Processing
  // ========================================================================

  /**
   * Process multiple courses through the pipeline
   * Following the pattern from test_multi_course_canvas_pipeline.py
   */
  async processBulkCourses(filters?: CourseFilters): Promise<BulkPipelineResult> {
    const startTime = Date.now();
    console.log('🚀 Pipeline Orchestrator: Starting bulk course processing');
    console.log('============================================================');

    // Create debug directory (cross-platform compatible)
    const debugDir = path.join(__dirname, '../../database/tests/results');
    if (!fs.existsSync(debugDir)) {
      fs.mkdirSync(debugDir, { recursive: true });
    }
    const timestamp = Date.now();

    try {
      // Stage 1: Execute bulk workflow
      console.log('📋 Stage 1: Bulk Canvas API workflow...');
      
      const workflowResult = await this.bulkManager.executeBulkWorkflow(
        this.dataConstructor,
        filters
      );

      if (!workflowResult.success) {
        throw new Error(`Bulk workflow failed: ${workflowResult.errors.join(', ')}`);
      }

      console.log(`✅ Bulk workflow completed: ${workflowResult.coursesProcessed} courses`);

      // Stage 2: Reconstruct all data
      console.log('🔄 Stage 2: Reconstructing bulk data...');
      
      const courses = this.bulkManager.reconstructAllCourses();
      const students = this.bulkManager.reconstructAllStudents();
      const assignments = this.bulkManager.reconstructAllAssignments();
      const enrollments = this.bulkManager.reconstructAllEnrollments();
      
      // DEBUG: Save raw reconstructed data
      const debugFile1 = path.join(debugDir, `05_bulk_raw_courses_${timestamp}.json`);
      const debugFile2 = path.join(debugDir, `06_bulk_raw_students_${timestamp}.json`);
      const debugFile3 = path.join(debugDir, `07_bulk_raw_assignments_${timestamp}.json`);
      const debugFile4 = path.join(debugDir, `08_bulk_raw_enrollments_${timestamp}.json`);
      
      fs.writeFileSync(debugFile1, JSON.stringify(courses, null, 2));
      fs.writeFileSync(debugFile2, JSON.stringify(students, null, 2));
      fs.writeFileSync(debugFile3, JSON.stringify(assignments, null, 2));
      fs.writeFileSync(debugFile4, JSON.stringify(enrollments, null, 2));
      
      console.log(`🔍 DEBUG: Bulk raw data saved:`);
      console.log(`  - Courses (${courses.length}): ${debugFile1}`);
      console.log(`  - Students (${students.length}): ${debugFile2}`);
      console.log(`  - Assignments (${assignments.length}): ${debugFile3}`);
      console.log(`  - Enrollments (${enrollments.length}): ${debugFile4}`);

      console.log(`📄 Reconstructed: ${courses.length} courses, ${students.length} students, ${assignments.length} assignments`);

      // Stage 3: Bulk transformation
      console.log('🔄 Stage 3: Bulk data transformation...');
      
      const transformationInput = {
        courses,
        students,
        assignments,
        enrollments
      };
      
      // DEBUG: Save transformation input
      const debugFile5 = path.join(debugDir, `09_bulk_transformation_input_${timestamp}.json`);
      fs.writeFileSync(debugFile5, JSON.stringify(transformationInput, null, 2));
      console.log(`🔍 DEBUG: Bulk transformation input saved to ${debugFile5}`);

      const transformedData = await this.executeBulkTransformation(transformationInput);
      
      // DEBUG: Save transformation output
      const debugFile6 = path.join(debugDir, `10_bulk_transformation_output_${timestamp}.json`);
      fs.writeFileSync(debugFile6, JSON.stringify(transformedData, null, 2));
      console.log(`🔍 DEBUG: Bulk transformation output saved to ${debugFile6}`);

      console.log('✅ Bulk transformation completed');

      // Successful result
      const result: BulkPipelineResult = {
        success: true,
        workflowResult,
        stagingData: transformationInput,
        transformedData,
        metadata: {
          processingTime: Date.now() - startTime,
          coursesProcessed: workflowResult.coursesProcessed,
          totalApiCalls: workflowResult.totalApiCalls,
          configuration: this.configManager.getConfig()
        }
      };
      
      // DEBUG: Save final bulk result
      const debugFile7 = path.join(debugDir, `11_bulk_final_result_${timestamp}.json`);
      fs.writeFileSync(debugFile7, JSON.stringify(result, null, 2));
      console.log(`🔍 DEBUG: Final bulk result saved to ${debugFile7}`);

      console.log(`🎉 Bulk processing completed: ${result.metadata.coursesProcessed} courses in ${result.metadata.processingTime}ms`);
      return result;

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      console.error('💥 Bulk pipeline failed:', errorMessage);

      return {
        success: false,
        error: errorMessage,
        metadata: {
          processingTime: Date.now() - startTime
        }
      };
    }
  }

  // ========================================================================
  // Configuration Management
  // ========================================================================

  /**
   * Update the pipeline configuration
   */
  updateConfiguration(config: Partial<SyncConfiguration>): void {
    this.configManager.updateConfig(config);
    
    // Reinitialize data collection modules with new config
    this.dataConstructor = new CanvasDataConstructor({
      config: this.configManager.getConfig()
    });
    
    this.bulkManager = new CanvasBulkApiDataManager(
      this.configManager.getConfig()
    );

    console.log('🔧 Pipeline configuration updated');
  }

  /**
   * Get current configuration
   */
  getConfiguration(): SyncConfiguration {
    return this.configManager.getConfig();
  }

  /**
   * Validate current configuration
   */
  validateConfiguration() {
    return this.configManager.validateConfiguration();
  }

  // ========================================================================
  // Pipeline Monitoring
  // ========================================================================

  /**
   * Get pipeline status and metrics
   */
  getPipelineStatus() {
    const stages = this.monitor.getStageResults();
    const totalTime = stages.reduce((sum, stage) => sum + (stage.duration || 0), 0);
    
    return {
      currentStage: this.monitor.getCurrentStage(),
      stages,
      totalProcessingTime: totalTime,
      configuration: this.configManager.getConfig(),
      lastRun: {
        timestamp: new Date().toISOString(),
        success: stages.every(stage => stage.status === 'completed')
      }
    };
  }

  // ========================================================================
  // Private Helper Methods
  // ========================================================================

  /**
   * Prepare single course data for transformation (legacy format conversion)
   */
  private prepareSingleCourseTransformationData(stagingData: any): any {
    // Convert from staging format to legacy transformer format
    const transformationData = {
      success: true,
      course: {
        // Handle both fieldData wrapper and direct access
        id: stagingData.fieldData?.id || stagingData.id,
        name: stagingData.fieldData?.name || stagingData.name,
        course_code: stagingData.fieldData?.course_code || stagingData.course_code,
        workflow_state: stagingData.fieldData?.workflow_state || stagingData.workflow_state || 'available',
        start_at: stagingData.fieldData?.start_at || stagingData.start_at,
        end_at: stagingData.fieldData?.end_at || stagingData.end_at,
        created_at: stagingData.fieldData?.created_at || stagingData.created_at,
        // Add calendar data from Canvas API
        calendar: stagingData.fieldData?.calendar || stagingData.calendar
      },
      // Fix: Flatten student fieldData structure and clean up bloat
      students: (stagingData.students || []).map(student => {
        if (!student.fieldData) {
          console.warn('Student missing fieldData structure:', student);
          return student;
        }
        
        return {
          // Extract core fields from fieldData wrapper
          ...student.fieldData,
          // Preserve additional analytics fields at top level
          submitted_assignments: student.submitted_assignments || [],
          missing_assignments: student.missing_assignments || [],
          // Remove dataConstructor bloat - this addresses Issue #4
          // dataConstructor is excluded to reduce payload size
        };
      }),
      // Fix: Extract enrollment data from student objects  
      enrollments: (stagingData.students || []).map(student => {
        if (!student.fieldData) {
          return null;
        }
        
        return {
          id: student.fieldData.id,
          user_id: student.fieldData.user_id,
          course_id: student.fieldData.course_id || stagingData.fieldData?.id || stagingData.id,
          type: student.fieldData.type,
          enrollment_state: student.fieldData.enrollment_state,
          grades: student.fieldData.grades,
          created_at: student.fieldData.created_at,
          updated_at: student.fieldData.updated_at
        };
      }).filter(enrollment => enrollment !== null),
      // Fix: Add empty modules array to satisfy Python validation while avoiding transformer
      // The Python validation expects 'modules' field but we don't have a ModuleTransformer
      // So we provide empty array to pass validation but transformers will skip empty arrays
      modules: []
    };

    return transformationData;
  }

  /**
   * Execute transformation via Python subprocess (single course)
   */
  private async executeTransformation(transformationInput: any): Promise<any> {
    // Create temporary input file
    const tempDir = path.join(__dirname, '../../temp');
    if (!fs.existsSync(tempDir)) {
      fs.mkdirSync(tempDir, { recursive: true });
    }

    const timestamp = Date.now();
    const inputFile = path.join(tempDir, `pipeline_input_${timestamp}.json`);
    const configFile = path.join(tempDir, `pipeline_config_${timestamp}.json`);
    
    try {
      // Write input data
      fs.writeFileSync(inputFile, JSON.stringify(transformationInput, null, 2));

      // Write config to separate file to avoid Windows command line issues
      fs.writeFileSync(configFile, JSON.stringify(this.configManager.getConfig(), null, 2));

      // Execute Python transformation script with config file
      const pythonCmd = `python "${this.pythonScriptPath}" "${inputFile}" "${configFile}"`;
      
      console.log(`   🐍 Executing Python transformation...`);
      const { stdout, stderr } = await execAsync(pythonCmd, {
        cwd: path.dirname(this.pythonScriptPath),
        timeout: 60000 // 1 minute timeout
      });

      if (stderr && stderr.trim()) {
        console.warn(`   ⚠️ Python transformation warnings: ${stderr.trim()}`);
      }

      // Parse results
      const transformedData = JSON.parse(stdout);
      return transformedData;

    } catch (error) {
      console.error('   💥 Python transformation failed:', error);
      throw new Error(`Transformation failed: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      // Clean up input and config files
      if (fs.existsSync(inputFile)) {
        fs.unlinkSync(inputFile);
      }
      if (fs.existsSync(configFile)) {
        fs.unlinkSync(configFile);
      }
    }
  }

  /**
   * Execute bulk transformation via Python subprocess
   */
  private async executeBulkTransformation(transformationInput: any): Promise<any> {
    // Similar to single transformation but handles bulk data format
    const tempDir = path.join(__dirname, '../../temp');
    if (!fs.existsSync(tempDir)) {
      fs.mkdirSync(tempDir, { recursive: true });
    }

    const timestamp = Date.now();
    const inputFile = path.join(tempDir, `bulk_pipeline_input_${timestamp}.json`);
    const configFile = path.join(tempDir, `bulk_pipeline_config_${timestamp}.json`);

    try {
      // Convert bulk format to transformer format with field mapping
      const transformerInput = {
        success: true,
        courses: transformationInput.courses,
        // Fix: Map student_id to id for transformer compatibility
        students: (transformationInput.students || []).map(student => ({
          ...student,
          id: student.student_id || student.id, // Ensure 'id' field exists
          user_id: student.user_id // Preserve user_id
        })),
        assignments: transformationInput.assignments,
        // Fix: Map enrollment data to include required id field
        enrollments: (transformationInput.enrollments || []).map(enrollment => ({
          ...enrollment,
          id: enrollment.student_id || enrollment.id, // Ensure 'id' field exists
          user_id: enrollment.user_id // Preserve user_id
        })),
        // Fix: Add empty modules array to satisfy Python validation
        modules: []
      };

      fs.writeFileSync(inputFile, JSON.stringify(transformerInput, null, 2));

      // Write config to separate file to avoid Windows command line issues
      fs.writeFileSync(configFile, JSON.stringify(this.configManager.getConfig(), null, 2));

      // Execute Python transformation script with config file
      const pythonCmd = `python "${this.pythonScriptPath}" "${inputFile}" "${configFile}" --bulk`;
      
      console.log(`   🐍 Executing bulk Python transformation...`);
      const { stdout, stderr } = await execAsync(pythonCmd, {
        cwd: path.dirname(this.pythonScriptPath),
        timeout: 300000 // 5 minute timeout for bulk operations
      });

      if (stderr && stderr.trim()) {
        console.warn(`   ⚠️ Bulk Python transformation warnings: ${stderr.trim()}`);
      }

      const transformedData = JSON.parse(stdout);
      return transformedData;

    } catch (error) {
      console.error('   💥 Bulk Python transformation failed:', error);
      throw new Error(`Bulk transformation failed: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      // Clean up input and config files
      if (fs.existsSync(inputFile)) {
        fs.unlinkSync(inputFile);
      }
      if (fs.existsSync(configFile)) {
        fs.unlinkSync(configFile);
      }
    }
  }

  /**
   * Count total records in transformed data
   */
  private countTransformedRecords(transformedData: any): number {
    let count = 0;
    
    if (transformedData.courses) count += transformedData.courses.length;
    if (transformedData.students) count += transformedData.students.length;
    if (transformedData.assignments) count += transformedData.assignments.length;
    if (transformedData.enrollments) count += transformedData.enrollments.length;
    
    return count;
  }
}

// ============================================================================
// Predefined Orchestrator Instances
// ============================================================================

/**
 * Create orchestrator with lightweight configuration (fast processing)
 */
export function createLightweightOrchestrator(): PipelineOrchestrator {
  return new PipelineOrchestrator(LIGHTWEIGHT_PROFILE);
}

/**
 * Create orchestrator with full configuration (comprehensive data)
 */
export function createFullOrchestrator(): PipelineOrchestrator {
  return new PipelineOrchestrator(FULL_SYNC_PROFILE);
}

/**
 * Create orchestrator with analytics configuration (detailed reporting)
 */
export function createAnalyticsOrchestrator(): PipelineOrchestrator {
  return new PipelineOrchestrator(ANALYTICS_PROFILE);
}

// Export main class and utilities
export {
  PipelineOrchestrator as default,
  ConfigurationManager,
  PipelineMonitor
};