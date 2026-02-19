import React, { useState } from 'react';
import RepositoryInput from './components/RepositoryInput.jsx';
import RepositoryList from './components/RepositoryList.jsx';
import RepoGraph from './components/RepoGraph.jsx';
import ChatInterface from './components/ChatInterface.jsx';
import FileExplorer from './components/FileExplorer.jsx';
import ErrorBoundary from './components/ErrorBoundary.jsx';
import { Search, History, Share2, MessageSquare, FolderTree } from 'lucide-react';
import { cn } from './utils/cn.js';

function App() {
  const [activeRepo, setActiveRepo] = useState(null);
  const [view, setView] = useState('explore'); // 'explore' | 'list'

  return (
    <ErrorBoundary>
      <div className="flex h-screen w-full bg-slate-950 text-slate-100 overflow-hidden">
      {/* Sidebar */}
      <aside className="w-16 flex flex-col items-center py-6 border-r border-slate-800 bg-slate-900 z-50">
        <div className="mb-8 p-2 bg-primary-600 rounded-xl shadow-lg shadow-primary-500/20">
          <Share2 className="w-6 h-6 text-white" />
        </div>
        
        <nav className="flex flex-col gap-6">
          <button 
            onClick={() => setView('explore')}
            className={cn(
              "p-3 rounded-xl transition-all duration-200",
              view === 'explore' ? "bg-slate-800 text-primary-400" : "text-slate-500 hover:text-slate-300 hover:bg-slate-800"
            )}
            title="Analysis Explorer"
          >
            <Search className="w-6 h-6" />
          </button>
          
          <button 
            onClick={() => setView('list')}
            className={cn(
              "p-3 rounded-xl transition-all duration-200",
              view === 'list' ? "bg-slate-800 text-primary-400" : "text-slate-500 hover:text-slate-300 hover:bg-slate-800"
            )}
            title="Repository List"
          >
            <History className="w-6 h-6" />
          </button>
        </nav>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col relative overflow-hidden">
        {view === 'list' ? (
          <div className="flex-1 p-8 overflow-y-auto">
            <h1 className="text-2xl font-bold mb-8 flex items-center gap-3">
              <History className="text-primary-500" />
              Repository History
            </h1>
            <RepositoryList onSelect={(repo) => {
              setActiveRepo(repo);
              setView('explore');
            }} />
          </div>
        ) : (
          <div className="flex-1 flex flex-col h-full">
            {/* Header / Input */}
            <header className="p-4 border-b border-slate-800 bg-slate-900/50 backdrop-blur-md flex items-center justify-between">
              <div className="flex items-center gap-4 flex-1 max-w-2xl">
                <RepositoryInput onAnalysisStart={(repo) => setActiveRepo(repo)} />
              </div>
              
              {activeRepo && (
                <div className="flex items-center gap-3 px-4 py-2 bg-slate-800 rounded-lg border border-slate-700">
                  <div className="flex flex-col">
                    <span className="text-xs text-slate-400 font-medium">Active Project</span>
                    <span className="text-sm font-semibold text-primary-400 truncate max-w-[200px]">
                      {activeRepo.owner}/{activeRepo.name}
                    </span>
                  </div>
                </div>
              )}
            </header>

            {/* Workspace */}
            {!activeRepo ? (
              <div className="flex-1 flex flex-col items-center justify-center text-center p-8">
                <div className="w-20 h-20 bg-slate-900 rounded-3xl flex items-center justify-center mb-6 border border-slate-800">
                  <Share2 className="w-10 h-10 text-slate-700" />
                </div>
                <h2 className="text-3xl font-bold text-slate-100 mb-4">Start Analysis</h2>
                <p className="text-slate-400 max-w-md mx-auto">
                  Enter a GitHub repository URL above to begin the code archaeology process. 
                  We'll index the codebase, build a relationship graph, and prepare for AI queries.
                </p>
              </div>
            ) : (
              <div className="flex-1 flex overflow-hidden">
                {/* Left Panel: File Explorer */}
                <div className="w-64 border-r border-slate-800 flex flex-col bg-slate-950/50">
                  <div className="p-4 flex items-center gap-2 border-b border-slate-800/50 text-slate-400 font-medium">
                    <FolderTree size={16} />
                    <span>Files</span>
                  </div>
                  <div className="flex-1 overflow-y-auto">
                    <FileExplorer repoId={activeRepo.id} />
                  </div>
                </div>

                {/* Center Panel: Graph Visualization */}
                <div className="flex-1 flex flex-col bg-[#050505]">
                  <RepoGraph repoId={activeRepo.id} />
                </div>

                {/* Right Panel: Chat Interface */}
                <div className="w-96 border-l border-slate-800 flex flex-col bg-slate-900/30">
                  <div className="p-4 flex items-center gap-2 border-b border-slate-800/50 text-slate-400 font-medium">
                    <MessageSquare size={16} />
                    <span>AI Archaeologist</span>
                  </div>
                  <div className="flex-1 overflow-hidden">
                    <ChatInterface repoId={activeRepo.id} />
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </main>
      </div>
    </ErrorBoundary>
  );
}

export default App;
