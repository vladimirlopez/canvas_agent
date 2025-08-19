// src/canvas.ts
import { setTimeout as wait } from 'node:timers/promises';
import { fetch } from 'undici';

export interface CanvasRequestOptions {
  method: string;
  path: string;
  body?: any;
  contentType?: string;
  maxRetries?: number;
}

export class CanvasClient {
  constructor(private baseUrl: string, private token: string) {
    // Ensure baseUrl doesn't end with slash
    this.baseUrl = baseUrl.replace(/\/+$/, '');
  }

  private headers(extra: Record<string, string> = {}): Record<string, string> {
    return {
      'Authorization': `Bearer ${this.token}`,
      'Accept': 'application/json',
      'User-Agent': 'MCP-Canvas/0.1.0',
      ...extra,
    };
  }

  async request<T>(options: CanvasRequestOptions): Promise<T> {
    const { method, path, body, contentType = 'application/json', maxRetries = 5 } = options;
    const url = new URL(path, this.baseUrl).toString();
    
    const requestOptions: any = { 
      method, 
      headers: this.headers() 
    };

    if (body) {
      if (contentType === 'application/json') {
        requestOptions.headers['Content-Type'] = 'application/json';
        requestOptions.body = JSON.stringify(body);
      } else if (body instanceof FormData) {
        // For multipart uploads, don't set Content-Type (let browser/undici set it with boundary)
        requestOptions.body = body;
      } else {
        requestOptions.headers['Content-Type'] = contentType;
        requestOptions.body = body;
      }
    }

    for (let attempt = 0; attempt < maxRetries; attempt++) {
      try {
        const response = await fetch(url, requestOptions);
        
        // Handle rate limiting
        if (response.status === 429) {
          const retryAfter = Number(response.headers.get('Retry-After') ?? '1');
          const backoffTime = (retryAfter + attempt) * 1000;
          console.warn(`Rate limited. Retrying in ${backoffTime}ms (attempt ${attempt + 1}/${maxRetries})`);
          await wait(backoffTime);
          continue;
        }

        // Handle other HTTP errors
        if (!response.ok) {
          const errorText = await response.text().catch(() => '');
          const error = new Error(
            `Canvas ${method} ${path} failed: ${response.status} ${response.statusText}${errorText ? ': ' + errorText : ''}`
          );
          
          // Don't retry on client errors (4xx), only server errors (5xx) and rate limits
          if (response.status >= 400 && response.status < 500 && response.status !== 429) {
            throw error;
          }
          
          if (attempt === maxRetries - 1) {
            throw error;
          }
          
          // Exponential backoff for server errors
          await wait(Math.pow(2, attempt) * 1000);
          continue;
        }

        // Success - parse JSON response
        const result = await response.json() as T;
        return result;

      } catch (error) {
        if (attempt === maxRetries - 1) {
          throw error;
        }
        
        // Network errors - retry with backoff
        await wait(Math.pow(2, attempt) * 1000);
      }
    }

    throw new Error(`Canvas ${method} ${path} failed after ${maxRetries} retries`);
  }

  // Convenience methods
  async get<T>(path: string): Promise<T> {
    return this.request<T>({ method: 'GET', path });
  }

  async post<T>(path: string, body?: any): Promise<T> {
    return this.request<T>({ method: 'POST', path, body });
  }

  async put<T>(path: string, body?: any): Promise<T> {
    return this.request<T>({ method: 'PUT', path, body });
  }

  async delete<T>(path: string): Promise<T> {
    return this.request<T>({ method: 'DELETE', path });
  }

  // Test connection method
  async testConnection(): Promise<{ success: boolean; user?: any; error?: string }> {
    try {
      const user = await this.get('/api/v1/users/self');
      return { success: true, user };
    } catch (error) {
      return { 
        success: false, 
        error: error instanceof Error ? error.message : 'Unknown error' 
      };
    }
  }
}
