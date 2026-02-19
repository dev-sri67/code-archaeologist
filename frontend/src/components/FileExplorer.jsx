import React, { useEffect, useState } from 'react';
import { getRepoFiles, getFileExplanation } from '../services/api.js';
import { ChevronRight, ChevronDown, FileCode, Folder, Info, Loader2 } from 'lucide-react';
import { cn } from '../utils/cn.js';
import toast from 'react-hot-toast';

/**
 * Build a tree structure from a flat list of file objects.
 * Each file has a `path` like "src/utils/helpers.js".
 */
function buildFileTree(flatFiles) {
  const root = [];
  const dirMap = {};

  for (const file of flatFiles) {
    const parts = (file.path || '').split('/');
    let currentLevel = root;

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      const currentPath = parts.slice(0, i + 1).join('/');
      const isFile = i === parts.length - 1;

      let existing = currentLevel.find((n) => n.path === currentPath);
      if (!existing) {
        existing = {
          name: part,
          path: currentPath,
          type: isFile ? 'file' : 'directory',
          ...(isFile ? { id: file.id } : { children: [] }),
        };
        currentLevel.push(existing);
        if (!isFile) dirMap[currentPath] = existing.children;
      }
      if (!isFile) currentLevel = existing.children;
    }
  }

  // Sort: directories first, then alphabetical
  const sortTree = (nodes) => {
    nodes.sort((a, b) => {
      if (a.type !== b.type) return a.type === 'directory' ? -1 : 1;
      return a.name.localeCompare(b.name);
    });
    nodes.forEach((n) => { if (n.children) sortTree(n.children); });
  };
  sortTree(root);
  return root;
}

/**
 * @param {{ repoId: string }} props
 */
export default function FileExplorer({ repoId }) {
  const [files, setFiles] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [expanded, setExpanded] = useState(new Set());
  const [explaining, setExplaining] = useState(null);

  useEffect(() => {
    async function fetchFiles() {
      setIsLoading(true);
      try {
        const response = await getRepoFiles(repoId);
        const flatFiles = response || [];
        // Build tree structure from flat file list
        setFiles(buildFileTree(flatFiles));
      } catch (error) {
        console.error('Failed to fetch files:', error);
      } finally {
        setIsLoading(false);
      }
    }
    if (repoId) fetchFiles();
  }, [repoId]);

  const toggleFolder = (path) => {
    const newExpanded = new Set(expanded);
    if (newExpanded.has(path)) {
      newExpanded.delete(path);
    } else {
      newExpanded.add(path);
    }
    setExpanded(newExpanded);
  };

  const handleExplain = async (file) => {
    setExplaining(file.id);
    try {
      const explanation = await getFileExplanation(file.id);
      // Here you could show a modal or side drawer, for now we toast a summary
      toast((t) => (
        <div className="flex flex-col gap-2 max-w-sm">
          <p className="font-bold text-sm border-b pb-1">AI Explanation: {file.name}</p>
          <p className="text-xs">{explanation.summary}</p>
          <div className="flex gap-2 mt-1">
            <span className="text-[10px] bg-primary-100 text-primary-800 px-1.5 rounded">
              Complexity: {explanation.complexity}
            </span>
          </div>
        </div>
      ), { duration: 6000, position: 'bottom-center' });
    } catch (error) {
      console.error('Explanation failed:', error);
    } finally {
      setExplaining(null);
    }
  };

  const renderTree = (nodes, level = 0) => {
    return nodes.map((node) => {
      const isExpanded = expanded.has(node.path);
      const isDirectory = node.type === 'directory';

      return (
        <div key={node.path} className="select-none">
          <div 
            className={cn(
              "flex items-center gap-1.5 py-1 px-2 hover:bg-slate-800/50 transition-colors cursor-pointer text-sm group",
              level > 0 && "ml-2 border-l border-slate-800/50"
            )}
            style={{ paddingLeft: `${level * 8 + 8}px` }}
          >
            {isDirectory ? (
              <button 
                onClick={() => toggleFolder(node.path)}
                className="p-0.5 hover:bg-slate-700 rounded transition-colors"
              >
                {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              </button>
            ) : (
              <div className="w-5 flex justify-center">
                <FileCode size={14} className="text-slate-500" />
              </div>
            )}
            
            <span 
              className={cn(
                "flex-1 truncate",
                isDirectory ? "text-slate-300 font-medium" : "text-slate-400"
              )}
              onClick={() => isDirectory ? toggleFolder(node.path) : null}
            >
              {node.name}
            </span>

            {!isDirectory && (
              <button
                onClick={() => handleExplain(node)}
                disabled={explaining === node.id}
                className="opacity-0 group-hover:opacity-100 p-1 hover:bg-primary-900/20 hover:text-primary-400 rounded transition-all text-slate-600"
                title="Explain with AI"
              >
                {explaining === node.id ? (
                  <Loader2 size={12} className="animate-spin" />
                ) : (
                  <Info size={12} />
                )}
              </button>
            )}
          </div>

          {isDirectory && isExpanded && node.children && (
            <div className="mt-0.5">
              {renderTree(node.children, level + 1)}
            </div>
          )}
        </div>
      );
    });
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-40 gap-3">
        <Loader2 className="w-5 h-5 text-slate-700 animate-spin" />
        <span className="text-xs text-slate-600">Loading files...</span>
      </div>
    );
  }

  return (
    <div className="py-2">
      {renderTree(files)}
    </div>
  );
}
