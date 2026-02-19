import axios from 'axios';
import toast from 'react-hot-toast';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // Add any auth tokens here if needed
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message = error.response?.data?.error || error.message || 'An error occurred';
    toast.error(message);
    return Promise.reject(error);
  }
);

// Repository APIs
export const repositoryApi = {
  /** @param {string} url */
  analyze: (url) => apiClient.post('/repos/analyze', { url }),
  
  /** @param {string} id */
  getStatus: (id) => apiClient.get(`/repos/${id}/status`),
  
  /** @param {string} id */
  getGraph: (id) => apiClient.get(`/repos/${id}/graph`),
  
  /** @param {string} id */
  getFiles: (id) => apiClient.get(`/repos/${id}/files`),
  
  /** @param {number} [page] @param {number} [limit] */
  list: (page = 1, limit = 20) => 
    apiClient.get('/repos', { params: { page, limit } }),
    
  /** @param {string} id */
  delete: (id) => apiClient.delete(`/repos/${id}`),
};

// File APIs
export const fileApi = {
  /** @param {string} id */
  explain: (id) => apiClient.get(`/files/${id}/explain`),
  
  /** @param {string} repoId @param {string} path */
  getContent: (repoId, path) => apiClient.get(`/files/${repoId}/content`, { params: { path } }),
};

// Chat APIs
export const chatApi = {
  /**
   * @param {Object} params
   * @param {string} params.repoId
   * @param {string} params.query
   * @param {{role: string, content: string}[]} [params.history]
   */
  query: (params) => apiClient.post('/chat/query', params),
};

// Health check
export const healthApi = {
  check: () => apiClient.get('/health'),
};

// Named function exports used by components
export const analyzeRepository = (url) => repositoryApi.analyze(url);
export const getRepositories = (page, limit) => repositoryApi.list(page, limit);
export const getRepoGraph = (repoId) => repositoryApi.getGraph(repoId);
export const getRepoFiles = (repoId) => repositoryApi.getFiles(repoId);
export const getFileExplanation = (fileId) => fileApi.explain(fileId);
export const sendChatQuery = (repoId, query, history) =>
  chatApi.query({ repo_id: repoId, query, history });

export default apiClient;
