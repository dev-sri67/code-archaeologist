import React, { useState } from 'react';
import { Search, Loader2, ArrowRight, Github } from 'lucide-react';
import { analyzeRepository } from '../services/api.js';
import toast from 'react-hot-toast';

/**
 * @param {{ onAnalysisStart: (repo: import('../types/index.js').Repository) => void }} props
 */
export default function RepositoryInput({ onAnalysisStart }) {
  const [url, setUrl] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!url.trim()) return;

    // Basic GitHub URL validation
    const githubRegex = /github\.com\/([^/]+)\/([^/]+)/;
    if (!githubRegex.test(url)) {
      toast.error('Please enter a valid GitHub repository URL');
      return;
    }

    setIsLoading(true);
    try {
      const response = await analyzeRepository(url);
      onAnalysisStart(response);
      setUrl('');
      toast.success('Analysis started!');
    } catch (error) {
      console.error('Failed to start analysis:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="relative w-full group">
      <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
        <Github className="h-5 w-5 text-slate-500 group-focus-within:text-primary-500 transition-colors" />
      </div>
      
      <input
        type="text"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        placeholder="Paste GitHub URL (e.g., https://github.com/facebook/react)"
        disabled={isLoading}
        className="block w-full pl-12 pr-32 py-3 bg-slate-950/50 border border-slate-700 rounded-xl text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all sm:text-sm disabled:opacity-50"
      />

      <div className="absolute inset-y-0 right-0 p-1.5 flex items-center">
        <button
          type="submit"
          disabled={isLoading || !url.trim()}
          className="h-full px-4 flex items-center justify-center gap-2 bg-primary-600 hover:bg-primary-500 text-white text-sm font-semibold rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-primary-600/20"
        >
          {isLoading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>Analyzing</span>
            </>
          ) : (
            <>
              <span>Dig In</span>
              <ArrowRight className="h-4 w-4" />
            </>
          )}
        </button>
      </div>
    </form>
  );
}
