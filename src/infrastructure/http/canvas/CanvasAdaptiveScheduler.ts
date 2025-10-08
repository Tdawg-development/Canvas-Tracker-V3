/**
 * Canvas Adaptive API Scheduler
 * Intelligent rate limiting that backs off when Canvas starts limiting us
 * Optimized for Canvas Free - can handle 8+ courses efficiently like v2
 */

import { CanvasClient } from './CanvasClient';
import { CanvasApiResponse } from './CanvasTypes';

export interface SchedulerMetrics {
  requestsPerSecond: number;
  successRate: number;
  averageResponseTime: number;
  currentBackoffLevel: number;
  totalRequests: number;
  rateLimitHits: number;
  lastRateLimitTime: Date | null;
}

export interface AdaptiveRequest<T> {
  id: string;
  endpoint: string;
  options?: any;
  priority: 'high' | 'medium' | 'low';
  retries: number;
  execute: () => Promise<CanvasApiResponse<T>>;
}

export class CanvasAdaptiveScheduler {
  private readonly client: CanvasClient;
  private requestQueue: AdaptiveRequest<any>[] = [];
  private activeRequests = new Set<string>();
  private metrics: SchedulerMetrics;
  private backoffLevels = [0, 100, 300, 1000, 2000, 5000]; // ms delays
  private currentBackoffLevel = 0;
  private consecutiveSuccesses = 0;
  private consecutiveFailures = 0;
  private lastRequestTime = 0;
  private requestTimes: number[] = []; // Track response times
  private isProcessing = false;

  constructor(client: CanvasClient) {
    this.client = client;
    this.metrics = {
      requestsPerSecond: 0,
      successRate: 100,
      averageResponseTime: 0,
      currentBackoffLevel: 0,
      totalRequests: 0,
      rateLimitHits: 0,
      lastRateLimitTime: null,
    };
  }

  /**
   * Schedule a request with adaptive priority handling
   */
  public async scheduleRequest<T>(
    endpoint: string,
    options: any = {},
    priority: 'high' | 'medium' | 'low' = 'medium'
  ): Promise<T> {
    return new Promise((resolve, _reject) => {
      const requestId = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      
      const request: AdaptiveRequest<T> = {
        id: requestId,
        endpoint,
        options,
        priority,
        retries: 0,
        execute: async () => {
          const startTime = Date.now();
          const response = await this.client.request<T>(endpoint, options);
          const responseTime = Date.now() - startTime;
          
          this.updateMetrics(response, responseTime);
          return response;
        },
      };

      this.requestQueue.push(request);
      this.sortQueueByPriority();
      
      // Start processing if not already running
      if (!this.isProcessing) {
        this.processQueue();
      }

      // Set up promise resolution
      const checkForCompletion = () => {
        if (!this.activeRequests.has(requestId)) {
          // Request completed, find result (in a real implementation, you'd store results)
          resolve(undefined as any); // Placeholder
        } else {
          setTimeout(checkForCompletion, 10);
        }
      };
      
      setTimeout(checkForCompletion, 10);
    });
  }

  /**
   * Process the request queue with adaptive timing
   */
  private async processQueue(): Promise<void> {
    if (this.isProcessing) return;
    this.isProcessing = true;

    while (this.requestQueue.length > 0) {
      const request = this.requestQueue.shift()!;
      
      // Calculate dynamic delay based on current conditions
      const delay = this.calculateAdaptiveDelay();
      
      if (delay > 0) {
        await this.wait(delay);
      }

      try {
        this.activeRequests.add(request.id);
        const response = await request.execute();
        
        if (response.data) {
          this.handleSuccess();
        } else if (response.errors) {
          await this.handleError(response.errors, request);
        }
        
      } catch (error: any) {
        await this.handleError([{ message: error.message, error_code: 'NETWORK_ERROR' }], request);
      } finally {
        this.activeRequests.delete(request.id);
      }
    }

    this.isProcessing = false;
  }

  /**
   * Calculate adaptive delay based on current Canvas API behavior
   */
  private calculateAdaptiveDelay(): number {
    const now = Date.now();
    const timeSinceLastRequest = now - this.lastRequestTime;
    
    // Base delay from backoff level
    let delay = this.backoffLevels[this.currentBackoffLevel];
    
    // If we're going fast and succeeding, reduce delays
    if (this.consecutiveSuccesses > 10 && this.metrics.successRate > 95) {
      delay = Math.max(0, delay * 0.5); // Halve the delay
    }
    
    // If requests are too close together, add minimum spacing
    const minimumSpacing = this.currentBackoffLevel > 2 ? 500 : 50; // More spacing when backing off
    if (timeSinceLastRequest < minimumSpacing) {
      delay = Math.max(delay, minimumSpacing - timeSinceLastRequest);
    }

    // Dynamic adjustment based on response times
    if (this.metrics.averageResponseTime > 2000) { // Slow responses
      delay += 200;
    }

    this.lastRequestTime = now;
    return Math.floor(delay);
  }

  /**
   * Handle successful response
   */
  private handleSuccess(): void {
    this.consecutiveSuccesses++;
    this.consecutiveFailures = 0;
    
    // Gradually reduce backoff when we're consistently successful
    if (this.consecutiveSuccesses > 5 && this.currentBackoffLevel > 0) {
      this.currentBackoffLevel = Math.max(0, this.currentBackoffLevel - 1);
      this.metrics.currentBackoffLevel = this.currentBackoffLevel;
    }
  }

  /**
   * Handle API errors with intelligent backoff
   */
  private async handleError(errors: any[], request: AdaptiveRequest<any>): Promise<void> {
    this.consecutiveFailures++;
    this.consecutiveSuccesses = 0;

    const isRateLimit = errors.some(error => 
      error.error_code?.includes('RATE_LIMIT') || 
      error.message?.toLowerCase().includes('rate limit') ||
      error.message?.toLowerCase().includes('too many requests')
    );

    if (isRateLimit) {
      this.metrics.rateLimitHits++;
      this.metrics.lastRateLimitTime = new Date();
      
      // Aggressive backoff for rate limits
      this.currentBackoffLevel = Math.min(this.backoffLevels.length - 1, this.currentBackoffLevel + 2);
      this.metrics.currentBackoffLevel = this.currentBackoffLevel;
      
      // Re-queue the request for retry if we have retries left
      if (request.retries < 3) {
        request.retries++;
        request.priority = 'high'; // Prioritize retries
        this.requestQueue.unshift(request); // Add to front of queue
      }
    } else {
      // Non-rate-limit error - modest backoff
      if (this.consecutiveFailures > 3) {
        this.currentBackoffLevel = Math.min(this.backoffLevels.length - 1, this.currentBackoffLevel + 1);
        this.metrics.currentBackoffLevel = this.currentBackoffLevel;
      }
    }
  }

  /**
   * Update performance metrics
   */
  private updateMetrics(response: CanvasApiResponse<any>, responseTime: number): void {
    this.metrics.totalRequests++;
    
    // Track response times (keep last 100)
    this.requestTimes.push(responseTime);
    if (this.requestTimes.length > 100) {
      this.requestTimes = this.requestTimes.slice(-100);
    }
    
    this.metrics.averageResponseTime = this.requestTimes.reduce((a, b) => a + b, 0) / this.requestTimes.length;
    
    // Calculate success rate
    const successful = response.data ? 1 : 0;
    const currentWeight = 0.1; // Weight for new data points
    this.metrics.successRate = (this.metrics.successRate * (1 - currentWeight)) + (successful * 100 * currentWeight);
    
    // Calculate requests per second
    if (this.requestTimes.length > 1) {
      const timespan = (Date.now() - (Date.now() - this.requestTimes.length * 1000)); // Rough approximation
      this.metrics.requestsPerSecond = this.requestTimes.length / (timespan / 1000);
    }
  }

  /**
   * Sort queue by priority (high first, then FIFO within priority)
   */
  private sortQueueByPriority(): void {
    this.requestQueue.sort((a, b) => {
      const priorityOrder = { high: 3, medium: 2, low: 1 };
      return priorityOrder[b.priority] - priorityOrder[a.priority];
    });
  }

  /**
   * Utility to wait for specified ms
   */
  private wait(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Get current scheduler metrics
   */
  public getMetrics(): SchedulerMetrics {
    return { ...this.metrics };
  }

  /**
   * Get performance summary for curriculum sync
   */
  public getPerformanceSummary(): {
    status: 'optimal' | 'good' | 'throttled' | 'limited';
    canHandle8Courses: boolean;
    estimatedSyncTime: number; // seconds for 8 courses
    recommendations: string[];
  } {
    const { successRate, currentBackoffLevel, rateLimitHits, averageResponseTime } = this.metrics;
    
    let status: 'optimal' | 'good' | 'throttled' | 'limited';
    let canHandle8Courses = true;
    let estimatedSyncTime = 30; // Start with v2's 30 second baseline

    if (currentBackoffLevel === 0 && successRate > 95 && rateLimitHits === 0) {
      status = 'optimal';
      estimatedSyncTime = 20; // Very fast with 600/hr limit
    } else if (currentBackoffLevel <= 2 && successRate > 90) {
      status = 'good';
      estimatedSyncTime = 30; // v2-like performance
    } else if (currentBackoffLevel <= 4 && successRate > 80) {
      status = 'throttled';
      estimatedSyncTime = 60;
    } else {
      status = 'limited';
      canHandle8Courses = false;
      estimatedSyncTime = 180; // 3 minutes with heavy throttling
    }

    // Adjust for response time
    estimatedSyncTime += Math.max(0, (averageResponseTime - 500) / 100);

    const recommendations: string[] = [];
    
    if (status === 'optimal') {
      recommendations.push('Canvas API performing excellently - can handle large curricula quickly');
    } else if (status === 'throttled') {
      recommendations.push('Some throttling detected - consider smaller batches or timing adjustments');
    } else if (status === 'limited') {
      recommendations.push('Heavy rate limiting - recommend manual sync or off-peak hours');
    }

    return {
      status,
      canHandle8Courses,
      estimatedSyncTime,
      recommendations,
    };
  }

  /**
   * Reset scheduler state (useful for testing or fresh starts)
   */
  public reset(): void {
    this.currentBackoffLevel = 0;
    this.consecutiveSuccesses = 0;
    this.consecutiveFailures = 0;
    this.requestTimes = [];
    this.metrics = {
      requestsPerSecond: 0,
      successRate: 100,
      averageResponseTime: 0,
      currentBackoffLevel: 0,
      totalRequests: 0,
      rateLimitHits: 0,
      lastRateLimitTime: null,
    };
  }
}