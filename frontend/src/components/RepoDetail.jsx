import { useState, useEffect } from 'react'
import { Routes, Route, Link, useParams, useLocation } from 'react-router-dom'
import { ArrowLeft, GitGraph, FileText, MessageSquare, Loader2 } from 'lucide-react'
import { repos } from '../services/api'
import RepoGraph from './RepoGraph'
import FileExplorer from './FileExplorer'
import ChatInterface from './ChatInterface'

export default function RepoDetail() {
  const { id } = useParams()
  const [repo, setRepo] = useState(null)
  const [status, setStatus] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const location = useLocation()

  useEffect(() => {
    loadRepo()
    const interval = setInterval(pollStatus, 3000)
    return () => clearInterval(interval)
  }, [id])

  const loadRepo = async () => {
    try {
      const { data } = await repos.get(id)
      setRepo(data)
    } catch (err) {
      console.error('Failed to load repo')
    } finally {
      setIsLoading(false)
    }
  }

  const pollStatus = async () => {
    try {
      const { data } = await repos.getStatus(id)
      setStatus(data)
      if (data.status === 'completed') {
        loadRepo()
      }
    } catch (err) {
      console.error('Status poll failed')
    }
  }

  const isActive = (path) => location.pathname.includes(path)

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    )
  }

  if (!repo) {
    return (
      <div className="card text-center py-12">
        <p className="text-slate-400">Repository not found</p>
        <Link to="/" className="btn-primary mt-4 inline-block">
          Go Back
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link to="/" className="p-2 hover:bg-slate-700 rounded-lg transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold">{repo.name}</h1>
            <p className="text-slate-400 text-sm">{repo.owner}</p>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          {status?.status === 'in_progress' && (
            <div className="flex items-center gap-2 text-amber-400">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span className="text-sm">{status.status_message}</span>
            </div>
          )}
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="border-b border-slate-700">
        <nav className="flex gap-6">
          <Link
            to={`/repo/${id}/graph`}
            className={`flex items-center gap-2 pb-4 border-b-2 transition-colors ${
              isActive('/graph') 
                ? 'border-blue-500 text-blue-400' 
                : 'border-transparent text-slate-400 hover:text-white'
            }`}
          >
            <GitGraph className="w-4 h-4" />
            Graph
          </Link>
          <Link
            to={`/repo/${id}/files`}
            className={`flex items-center gap-2 pb-4 border-b-2 transition-colors ${
              isActive('/files') 
                ? 'border-blue-500 text-blue-400' 
                : 'border-transparent text-slate-400 hover:text-white'
            }`}
          >
            <FileText className="w-4 h-4" />
            Files
          </Link>
          <Link
            to={`/repo/${id}/chat`}
            className={`flex items-center gap-2 pb-4 border-b-2 transition-colors ${
              isActive('/chat') 
                ? 'border-blue-500 text-blue-400' 
                : 'border-transparent text-slate-400 hover:text-white'
            }`}
          >
            <MessageSquare className="w-4 h-4" />
            Chat
          </Link>
        </nav>
      </div>

      {/* Content */}
      <Routes>
        <Route path="/" element={<RepoGraph repoId={id} />} />
        <Route path="/graph" element={<RepoGraph repoId={id} />} />
        <Route path="/files/*" element={<FileExplorer repoId={id} />} />
        <Route path="/chat" element={<ChatInterface repoId={id} />} />
      </Routes>
    </div>
  )
}