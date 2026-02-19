import { useState, useEffect, useCallback } from 'react';
import { repositoryApi } from '../services/api.js';
import toast from 'react-hot-toast';

/**
 * @returns {{
 *   repositories: import('../types/index.js').Repository[],
 *   loading: boolean,
 *   error: string|null,
 *   refetch: () => Promise<void>,
 *   analyzeRepo: (url: string) => Promise<void>,
 *   deleteRepo: (id: string) => Promise<void>,
 *   getRepoStatus: (id: string) => Promise<import('../types/index.js').Repository>
 * }}
 */
export function useRepositories() {
  const [repositories, setRepositories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchRepositories = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await repositoryApi.list();
      const data = response.data || response;
      setRepositories(Array.isArray(data) ? data : data.items || []);
    } catch (err) {
      setError(err.message || 'Failed to fetch repositories');
      toast.error('Failed to fetch repositories');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRepositories();
  }, [fetchRepositories]);

  /**
   * @param {string} url
   */
  const analyzeRepo = async (url) => {
    try {
      const response = await repositoryApi.analyze(url);
      toast.success('Repository analysis started');
      await fetchRepositories();
      return response.data;
    } catch (err) {
      toast.error(err.message || 'Failed to start analysis');
      throw err;
    }
  };

  /**
   * @param {string} id
   */
  const deleteRepo = async (id) => {
    try {
      await repositoryApi.delete(id);
      toast.success('Repository deleted');
      await fetchRepositories();
    } catch (err) {
      toast.error(err.message || 'Failed to delete repository');
      throw err;
    }
  };

  /**
   * @param {string} id
   * @returns {Promise<import('../types/index.js').Repository>}
   */
  const getRepoStatus = async (id) => {
    const response = await repositoryApi.getStatus(id);
    return response.data;
  };

  return {
    repositories,
    loading,
    error,
    refetch: fetchRepositories,
    analyzeRepo,
    deleteRepo,
    getRepoStatus,
  };
}
