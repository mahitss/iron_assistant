/**
 * Kairo Centralized API Client
 * Manages request headers, authentication identity, correlation IDs, and unified error parsing.
 */

export class ApiError extends Error {
  constructor(message, status, code, data = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code || `HTTP_${status}`;
    this.data = data;
  }
}

export class ApiClient {
  constructor(options = {}) {
    this.baseUrl = options.baseUrl || '';
    this.userId = options.userId || 'default_user';
    this.token = options.token || null;
    this.defaultHeaders = {
      'Content-Type': 'application/json',
      ...options.headers,
    };
  }

  setUserId(userId) {
    this.userId = userId;
  }

  setToken(token) {
    this.token = token;
  }

  _generateRequestId() {
    return 'req_' + Math.random().toString(36).substring(2, 11) + Date.now().toString(36);
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const headers = {
      ...this.defaultHeaders,
      'x-request-id': this._generateRequestId(),
      'x-user-id': this.userId,
      ...options.headers,
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const config = {
      ...options,
      headers,
    };

    let response;
    try {
      response = await fetch(url, config);
    } catch (networkError) {
      throw new ApiError(
        `Network error: Unable to reach Kairo backend at ${url}`,
        0,
        'NETWORK_ERROR',
        networkError
      );
    }

    if (response.status === 204) {
      return null;
    }

    let data;
    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      try {
        data = await response.json();
      } catch (parseErr) {
        data = null;
      }
    } else {
      data = await response.text();
    }

    if (!response.ok) {
      const message = data && typeof data === 'object'
        ? (data.detail || data.message || `Request failed with status ${response.status}`)
        : `Request failed with status ${response.status}`;
      const code = data && typeof data === 'object' ? data.code : `HTTP_${response.status}`;
      throw new ApiError(message, response.status, code, data);
    }

    return data;
  }

  get(endpoint, headers = {}) {
    return this.request(endpoint, { method: 'GET', headers });
  }

  post(endpoint, body = null, headers = {}) {
    return this.request(endpoint, {
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
      headers,
    });
  }

  patch(endpoint, body = null, headers = {}) {
    return this.request(endpoint, {
      method: 'PATCH',
      body: body ? JSON.stringify(body) : undefined,
      headers,
    });
  }

  delete(endpoint, headers = {}) {
    return this.request(endpoint, { method: 'DELETE', headers });
  }
}

export const api = new ApiClient();
