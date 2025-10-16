/**
 * Pipeline Monitor for Canvas Data Pipeline Orchestrator
 * 
 * Tracks pipeline execution stages, timing, performance metrics, and errors.
 * Provides comprehensive monitoring and debugging capabilities.
 */

// ============================================================================
// Pipeline Stage Definitions
// ============================================================================

export enum PipelineStage {
  INITIALIZATION = 'initialization',
  CANVAS_API = 'canvas_api',
  DATA_STAGING = 'data_staging',
  TRANSFORMATION = 'transformation',
  DATABASE_STORAGE = 'database_storage',
  VALIDATION = 'validation',
  CLEANUP = 'cleanup'
}

export enum StageStatus {
  PENDING = 'pending',
  RUNNING = 'running',
  COMPLETED = 'completed',
  FAILED = 'failed',
  SKIPPED = 'skipped'
}

// ============================================================================
// Stage and Monitoring Interfaces
// ============================================================================

export interface StageResult {
  name: string;
  stage: PipelineStage;
  status: StageStatus;
  startTime: number;
  endTime?: number;
  duration?: number;
  metadata?: {
    apiCalls?: number;
    recordCount?: number;
    errors?: string[];
    warnings?: string[];
    [key: string]: any;
  };
}

export interface PipelineMetrics {
  totalDuration: number;
  stageCount: number;
  completedStages: number;
  failedStages: number;
  skippedStages: number;
  averageStageTime: number;
  apiCallsTotal: number;
  recordsProcessed: number;
}

// ============================================================================
// Pipeline Monitor Class
// ============================================================================

export class PipelineMonitor {
  private stages: Map<PipelineStage, StageResult> = new Map();
  private currentStage?: PipelineStage;
  private sessionStartTime: number;
  private sessionId: string;

  constructor() {
    this.sessionStartTime = Date.now();
    this.sessionId = this.generateSessionId();
  }

  // ========================================================================
  // Stage Management
  // ========================================================================

  /**
   * Start tracking a new pipeline stage
   */
  startStage(stage: PipelineStage, metadata?: any): void {
    const stageResult: StageResult = {
      name: stage,
      stage,
      status: StageStatus.RUNNING,
      startTime: Date.now(),
      metadata: metadata || {}
    };

    this.stages.set(stage, stageResult);
    this.currentStage = stage;

    console.log(`📊 Pipeline Monitor: Started stage '${stage}'`);
  }

  /**
   * Complete a pipeline stage successfully
   */
  completeStage(stage: PipelineStage, metadata?: any): void {
    const stageResult = this.stages.get(stage);
    if (!stageResult) {
      console.warn(`⚠️ Pipeline Monitor: Attempted to complete unknown stage '${stage}'`);
      return;
    }

    const endTime = Date.now();
    stageResult.endTime = endTime;
    stageResult.duration = endTime - stageResult.startTime;
    stageResult.status = StageStatus.COMPLETED;
    
    if (metadata) {
      stageResult.metadata = { ...stageResult.metadata, ...metadata };
    }

    // Clear current stage if this was the active one
    if (this.currentStage === stage) {
      this.currentStage = undefined;
    }

    console.log(`✅ Pipeline Monitor: Completed stage '${stage}' in ${stageResult.duration}ms`);
    
    // Log stage metadata if present
    if (stageResult.metadata && Object.keys(stageResult.metadata).length > 0) {
      console.log(`   📋 Stage metadata:`, stageResult.metadata);
    }
  }

  /**
   * Mark a stage as failed
   */
  failStage(stage: PipelineStage, error: string | Error, metadata?: any): void {
    const stageResult = this.stages.get(stage);
    if (!stageResult) {
      console.warn(`⚠️ Pipeline Monitor: Attempted to fail unknown stage '${stage}'`);
      return;
    }

    const endTime = Date.now();
    stageResult.endTime = endTime;
    stageResult.duration = endTime - stageResult.startTime;
    stageResult.status = StageStatus.FAILED;

    // Add error information to metadata
    const errorMessage = error instanceof Error ? error.message : String(error);
    stageResult.metadata = { 
      ...stageResult.metadata, 
      ...metadata,
      errors: [...(stageResult.metadata?.errors || []), errorMessage]
    };

    // Clear current stage if this was the active one
    if (this.currentStage === stage) {
      this.currentStage = undefined;
    }

    console.error(`❌ Pipeline Monitor: Stage '${stage}' failed after ${stageResult.duration}ms: ${errorMessage}`);
  }

  /**
   * Skip a stage (not needed for current configuration)
   */
  skipStage(stage: PipelineStage, reason: string): void {
    const stageResult: StageResult = {
      name: stage,
      stage,
      status: StageStatus.SKIPPED,
      startTime: Date.now(),
      endTime: Date.now(),
      duration: 0,
      metadata: { skipReason: reason }
    };

    this.stages.set(stage, stageResult);

    console.log(`⏭️ Pipeline Monitor: Skipped stage '${stage}' - ${reason}`);
  }

  /**
   * Add warning to current or specified stage
   */
  addWarning(warning: string, stage?: PipelineStage): void {
    const targetStage = stage || this.currentStage;
    if (!targetStage) {
      console.warn(`⚠️ Pipeline Monitor: Cannot add warning - no active stage`);
      return;
    }

    const stageResult = this.stages.get(targetStage);
    if (stageResult && stageResult.metadata) {
      if (!stageResult.metadata.warnings) {
        stageResult.metadata.warnings = [];
      }
      stageResult.metadata.warnings.push(warning);
      
      console.warn(`⚠️ Pipeline Monitor [${targetStage}]: ${warning}`);
    }
  }

  // ========================================================================
  // Status and Results
  // ========================================================================

  /**
   * Get current pipeline stage
   */
  getCurrentStage(): string | undefined {
    return this.currentStage;
  }

  /**
   * Get all stage results
   */
  getStageResults(): StageResult[] {
    return Array.from(this.stages.values());
  }

  /**
   * Get pipeline metrics summary
   */
  getMetrics(): PipelineMetrics {
    const stages = this.getStageResults();
    const completedStages = stages.filter(s => s.status === StageStatus.COMPLETED);
    const failedStages = stages.filter(s => s.status === StageStatus.FAILED);
    const skippedStages = stages.filter(s => s.status === StageStatus.SKIPPED);

    const totalDuration = stages.reduce((sum, stage) => sum + (stage.duration || 0), 0);
    const averageStageTime = completedStages.length > 0 
      ? completedStages.reduce((sum, stage) => sum + (stage.duration || 0), 0) / completedStages.length 
      : 0;

    const apiCallsTotal = stages.reduce((sum, stage) => 
      sum + (stage.metadata?.apiCalls || 0), 0);
    
    const recordsProcessed = stages.reduce((sum, stage) => 
      sum + (stage.metadata?.recordCount || 0), 0);

    return {
      totalDuration,
      stageCount: stages.length,
      completedStages: completedStages.length,
      failedStages: failedStages.length,
      skippedStages: skippedStages.length,
      averageStageTime,
      apiCallsTotal,
      recordsProcessed
    };
  }

  /**
   * Get current pipeline status
   */
  getStatus(): {
    sessionId: string;
    running: boolean;
    currentStage?: string;
    progress: number;
    metrics: PipelineMetrics;
    errors: string[];
    warnings: string[];
  } {
    const stages = this.getStageResults();
    const metrics = this.getMetrics();
    
    const allErrors: string[] = [];
    const allWarnings: string[] = [];
    
    stages.forEach(stage => {
      if (stage.metadata?.errors) {
        allErrors.push(...stage.metadata.errors);
      }
      if (stage.metadata?.warnings) {
        allWarnings.push(...stage.metadata.warnings);
      }
    });

    // Calculate progress based on completed vs total stages
    const progress = stages.length > 0 
      ? (metrics.completedStages + metrics.skippedStages) / stages.length 
      : 0;

    return {
      sessionId: this.sessionId,
      running: this.currentStage !== undefined,
      currentStage: this.currentStage,
      progress: Math.round(progress * 100) / 100,
      metrics,
      errors: allErrors,
      warnings: allWarnings
    };
  }

  // ========================================================================
  // Reporting and Analysis
  // ========================================================================

  /**
   * Generate a detailed pipeline report
   */
  generateReport(): {
    session: {
      id: string;
      startTime: Date;
      duration: number;
    };
    summary: {
      success: boolean;
      stagesTotal: number;
      stagesCompleted: number;
      stagesFailed: number;
      stagesSkipped: number;
    };
    performance: {
      totalTime: number;
      averageStageTime: number;
      apiCalls: number;
      recordsProcessed: number;
      efficiency: string;
    };
    stages: StageResult[];
    issues: {
      errors: string[];
      warnings: string[];
    };
  } {
    const stages = this.getStageResults();
    const metrics = this.getMetrics();
    const status = this.getStatus();

    // Calculate efficiency rating
    let efficiency = 'Unknown';
    if (metrics.totalDuration > 0) {
      if (metrics.totalDuration < 5000) efficiency = 'Excellent';
      else if (metrics.totalDuration < 15000) efficiency = 'Good';
      else if (metrics.totalDuration < 30000) efficiency = 'Fair';
      else efficiency = 'Needs Optimization';
    }

    return {
      session: {
        id: this.sessionId,
        startTime: new Date(this.sessionStartTime),
        duration: Date.now() - this.sessionStartTime
      },
      summary: {
        success: metrics.failedStages === 0,
        stagesTotal: metrics.stageCount,
        stagesCompleted: metrics.completedStages,
        stagesFailed: metrics.failedStages,
        stagesSkipped: metrics.skippedStages
      },
      performance: {
        totalTime: metrics.totalDuration,
        averageStageTime: Math.round(metrics.averageStageTime),
        apiCalls: metrics.apiCallsTotal,
        recordsProcessed: metrics.recordsProcessed,
        efficiency
      },
      stages,
      issues: {
        errors: status.errors,
        warnings: status.warnings
      }
    };
  }

  /**
   * Print pipeline summary to console
   */
  printSummary(): void {
    const report = this.generateReport();
    
    console.log('\n📊 Pipeline Execution Summary');
    console.log('================================');
    console.log(`Session ID: ${report.session.id}`);
    console.log(`Duration: ${report.session.duration}ms`);
    console.log(`Success: ${report.summary.success ? '✅' : '❌'}`);
    console.log(`Stages: ${report.summary.stagesCompleted}/${report.summary.stagesTotal} completed`);
    
    if (report.summary.stagesFailed > 0) {
      console.log(`Failed Stages: ${report.summary.stagesFailed}`);
    }
    
    if (report.summary.stagesSkipped > 0) {
      console.log(`Skipped Stages: ${report.summary.stagesSkipped}`);
    }

    console.log(`\n⚡ Performance:`);
    console.log(`   Total Time: ${report.performance.totalTime}ms`);
    console.log(`   Average Stage: ${report.performance.averageStageTime}ms`);
    console.log(`   API Calls: ${report.performance.apiCalls}`);
    console.log(`   Records: ${report.performance.recordsProcessed}`);
    console.log(`   Efficiency: ${report.performance.efficiency}`);

    if (report.issues.errors.length > 0) {
      console.log(`\n❌ Errors (${report.issues.errors.length}):`);
      report.issues.errors.forEach((error, i) => {
        console.log(`   ${i + 1}. ${error}`);
      });
    }

    if (report.issues.warnings.length > 0) {
      console.log(`\n⚠️ Warnings (${report.issues.warnings.length}):`);
      report.issues.warnings.forEach((warning, i) => {
        console.log(`   ${i + 1}. ${warning}`);
      });
    }

    console.log('\n================================\n');
  }

  // ========================================================================
  // Utility Methods
  // ========================================================================

  /**
   * Reset the monitor for a new pipeline run
   */
  reset(): void {
    this.stages.clear();
    this.currentStage = undefined;
    this.sessionStartTime = Date.now();
    this.sessionId = this.generateSessionId();

    console.log(`🔄 Pipeline Monitor: Reset for new session ${this.sessionId}`);
  }

  /**
   * Check if pipeline has any failures
   */
  hasFailures(): boolean {
    return Array.from(this.stages.values()).some(stage => stage.status === StageStatus.FAILED);
  }

  /**
   * Check if pipeline is currently running
   */
  isRunning(): boolean {
    return this.currentStage !== undefined;
  }

  /**
   * Get stage by name
   */
  getStage(stage: PipelineStage): StageResult | undefined {
    return this.stages.get(stage);
  }

  /**
   * Get the slowest stage
   */
  getSlowestStage(): StageResult | undefined {
    const stages = this.getStageResults().filter(s => s.duration !== undefined);
    if (stages.length === 0) return undefined;

    return stages.reduce((slowest, current) => 
      (current.duration || 0) > (slowest.duration || 0) ? current : slowest
    );
  }

  /**
   * Get the fastest stage
   */
  getFastestStage(): StageResult | undefined {
    const stages = this.getStageResults().filter(s => s.duration !== undefined && s.status === StageStatus.COMPLETED);
    if (stages.length === 0) return undefined;

    return stages.reduce((fastest, current) => 
      (current.duration || Infinity) < (fastest.duration || Infinity) ? current : fastest
    );
  }

  // ========================================================================
  // Private Methods
  // ========================================================================

  private generateSessionId(): string {
    return `pipeline_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Create a new pipeline monitor instance
 */
export function createPipelineMonitor(): PipelineMonitor {
  return new PipelineMonitor();
}

/**
 * Format stage duration for display
 */
export function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${(ms / 60000).toFixed(1)}m`;
}

/**
 * Get stage status icon
 */
export function getStageStatusIcon(status: StageStatus): string {
  switch (status) {
    case StageStatus.PENDING: return '⏳';
    case StageStatus.RUNNING: return '🔄';
    case StageStatus.COMPLETED: return '✅';
    case StageStatus.FAILED: return '❌';
    case StageStatus.SKIPPED: return '⏭️';
    default: return '❓';
  }
}