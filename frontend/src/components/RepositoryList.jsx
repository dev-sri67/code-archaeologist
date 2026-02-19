import React, { useEffect, useState } from 'react';
import { getRepositories } from '../services/api.js';
import { getStatusBgColor, timeAgo } from '../utils/format.js';
import { Github, ExternalLink, Trash2, Clock, GitBranch } from 'lucide-react';
import { cn } from '../utils/cn.js';

/**
 * @param {{ onSelect: (repo: import('../types/index.js').Repository) => void }} props
 */
export default function RepositoryList({ onSelect }) {
  const [repos, setRepos] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchRepos() {
      try {
        const response = await getRepositories();
        setRepos(Array.isArray(response) ? response : response.items || []);
      } catch (error) {
        console.error('Failed to fetch repositories:', error);
      } finally {
        setIsLoading(false);
      }
    }
    fetchRepos();
  }, []);

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 animate-pulse">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-48 bg-slate-900 rounded-2xl border border-slate-800" />
        ))}
      </div>
    );
  }

  if (repos.length === 0) {
    return (
      <div className="text-center py-20 bg-slate-900/50 rounded-2xl border border-dashed border-slate-800">
        <p className="text-slate-500 mb-4">No analysis history found.</p>
        <p className="text-sm text-slate-600">Start by entering a URL in the search bar above.</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {repos.map((repo) => (
        <div 
          key={repo.id}
          onClick={() => onSelect(repo)}
          className="group relative bg-slate-900 border border-slate-800 rounded-2xl p-6 hover:border-slate-600 transition-all cursor-pointer shadow-lg hover:shadow-primary-500/5"
        >
          <div className="flex items-start justify-between mb-4">
            <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 group-hover:border-primary-500/50 transition-colors">
              <Github className="w-6 h-6 text-slate-400 group-hover:text-primary-400" />
            </div>
            <span className={cn(
              "px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider",
              getStatusBgColor(repo.status)
            )}>
              {repo.status}
            </span>
          </div>

          <h3 className="text-lg font-bold text-slate-100 mb-1 truncate">
            {repo.name}
          </h3>
          <p className="text-sm text-slate-500 mb-6 truncate">
            {repo.owner}
          </p>

          <div className="grid grid-cols-2 gap-4 pt-4 border-t border-slate-800">
            <div className="flex items-center gap-2 text-slate-400">
              <Clock size={14} />
              <span className="text-xs">{timeAgo(repo.updatedAt)}</span>
            </div>
            <div className="flex items-center gap-2 text-slate-400">
              <GitBranch size={14} />
              <span className="text-xs">{repo.fileCount || 0} files</span>
            </div>
          </div>
          
          <div className="absolute top-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity flex gap-2">
            <button 
              onClick={(e) => {
                e.stopPropagation();
                window.open(repo.url, '_blank');
              }}
              className="p-1.5 hover:bg-slate-800 rounded-md text-slate-500 hover:text-slate-200"
            >
              <ExternalLink size={16} />
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
