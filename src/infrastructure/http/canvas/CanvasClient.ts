/**
 * Canvas API HTTP Client
 * Base client for making authenticated requests to Canvas API
 * Handles rate limiting, retries, and error responses
 */

import fetch, { Response } from 'node-fetch';
import {
  CanvasApiConfig,
  CanvasApiRequestOptions,
  CanvasApiResponse,
  CanvasApiError,
} from './CanvasTypes';

export class CanvasClient {
  private readonly config: CanvasApiConfig;
  private lastRequestTime: number = 0;
  private requestCount: number = 0;
  private readonly requestWindow: number = 60 * 60 * 1000; // 1 hour in milliseconds

  constructor(config: CanvasApiConfig) {
    // Canvas Free for Teachers: 600 requests/hour, penalties for exceeding
    this.config = {
      rateLimitRequestsPerHour: 600, // Actual Canvas Free limit
      timeout: 30000, // Standard timeout
      retryAttempts: 3, // Standard retries
      retryDelay: 1000, // Standard delay
      ...config,
    };
  }

  /**
   * Make authenticated request to Canvas API
   */
  public async request<T>(
    endpoint: string,
    options: CanvasApiRequestOptions = {}
  ): Promise<CanvasApiResponse<T>> {
    await this.enforceRateLimit();

    const url = this.buildUrl(endpoint, options.params);
    const requestOptions = this.buildRequestOptions(options);

    let lastError: Error | null = null;
    
    for (let attempt = 1; attempt <= this.config.retryAttempts!; attempt++) {
      try {
        const response = await this.makeRequest(url, requestOptions);
        
        if (response.ok) {
          const data = await this.parseResponse<T>(response);
          return { data };
        }
        
        // Handle Canvas API errors
        const error = await this.parseError(response);
        if (response.status < 500 && attempt === 1) {
          // Don't retry client errors (4xx), return immediately
          return { errors: [error] };
        }
        
        lastError = new Error(`Canvas API error: ${error.message}`);
        
      } catch (error) {
        lastError = error as Error;
      }

      // Wait before retry (exponential backoff)
      if (attempt < this.config.retryAttempts!) {
        await this.delay(this.config.retryDelay! * Math.pow(2, attempt - 1));
      }
    }

    // All retries failed
    return {
      errors: [{
        message: lastError?.message || 'Request failed after all retries',
        error_code: 'REQUEST_FAILED',
      }],
    };
  }

  /**
   * GET request helper
   */
  public async get<T>(
    endpoint: string,
    options: Omit<CanvasApiRequestOptions, 'method'> = {}
  ): Promise<CanvasApiResponse<T>> {
    return this.request<T>(endpoint, { ...options, method: 'GET' });
  }

  /**
   * POST request helper
   */
  public async post<T>(
    endpoint: string,
    data: any,
    options: Omit<CanvasApiRequestOptions, 'method'> = {}
  ): Promise<CanvasApiResponse<T>> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Build full URL with query parameters
   */
  private buildUrl(endpoint: string, params?: Record<string, string | number | boolean>): string {
    const baseUrl = this.config.baseUrl.replace(/\/$/, '');
    const cleanEndpoint = endpoint.replace(/^\//, '');
    let url = `${baseUrl}/api/v1/${cleanEndpoint}`;

    if (params && Object.keys(params).length > 0) {
      const searchParams = new URLSearchParams();
      Object.entries(params).forEach(([key, value]) => {
        searchParams.append(key, String(value));
      });
      url += `?${searchParams.toString()}`;
    }

    return url;
  }

  /**
   * Build request options with authentication and defaults
   */
  private buildRequestOptions(options: CanvasApiRequestOptions): any {
    return {
      method: options.method || 'GET',
      headers: {
        'Authorization': `Bearer ${this.config.token}`,
        'Accept': 'application/json',
        'User-Agent': 'Canvas-Tracker-V3',
        ...options.headers,
      },
      timeout: options.timeout || this.config.timeout,
    };
  }

  /**
   * Make the actual HTTP request
   */
  private async makeRequest(url: string, options: any): Promise<Response> {
    this.recordRequest();
    return fetch(url, options);
  }

  /**
   * Parse successful response data
   */
  private async parseResponse<T>(response: Response): Promise<T> {
    const contentType = response.headers.get('content-type');
    
    if (contentType && contentType.includes('application/json')) {
      return (await response.json()) as T;
    }
    
    // Handle non-JSON responses
    const text = await response.text();
    return text as unknown as T;
  }

  /**
   * Parse error response
   */
  private async parseError(response: Response): Promise<CanvasApiError> {
    try {
      const errorData = await response.json() as any;
      
      if (errorData.errors && Array.isArray(errorData.errors) && errorData.errors.length > 0) {
        const firstError = errorData.errors[0];
        return {
          message: firstError.message || `HTTP ${response.status}: ${response.statusText}`,
          error_code: firstError.error_code,
        };
      }
      
      return {
        message: errorData.message || `HTTP ${response.status}: ${response.statusText}`,
        error_code: `HTTP_${response.status}`,
      };
      
    } catch {
      return {
        message: `HTTP ${response.status}: ${response.statusText}`,
        error_code: `HTTP_${response.status}`,
      };
    }
  }

  /**
   * Enforce rate limiting based on Canvas API limits
   */
  private async enforceRateLimit(): Promise<void> {
    const now = Date.now();
    const timeSinceWindow = now - this.lastRequestTime;

    // Reset counter if we're in a new time window
    if (timeSinceWindow >= this.requestWindow) {
      this.requestCount = 0;
      this.lastRequestTime = now;
      return;
    }

    // Check if we've hit the rate limit
    if (this.requestCount >= this.config.rateLimitRequestsPerHour!) {
      const waitTime = this.requestWindow - timeSinceWindow;
      console.warn(`Canvas API rate limit reached. Waiting ${Math.ceil(waitTime / 1000)}s...`);
      await this.delay(waitTime);
      
      // Reset after waiting
      this.requestCount = 0;
      this.lastRequestTime = Date.now();
    }
  }

  /**
   * Record request for rate limiting
   */
  private recordRequest(): void {
    this.requestCount++;
  }

  /**
   * Delay utility for retries and rate limiting
   */
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Get current rate limit status
   */
  public getRateLimitStatus(): {
    requestsInWindow: number;
    maxRequests: number;
    windowResetTime: Date;
  } {
    return {
      requestsInWindow: this.requestCount,
      maxRequests: this.config.rateLimitRequestsPerHour!,
      windowResetTime: new Date(this.lastRequestTime + this.requestWindow),
    };
  }
}