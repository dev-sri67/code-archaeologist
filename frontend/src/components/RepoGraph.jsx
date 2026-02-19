import React, { useEffect, useState, useCallback } from 'react';
import {
  ReactFlow,
  Controls,
  Background,
  applyEdgeChanges,
  applyNodeChanges,
  MiniMap,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { getRepoGraph } from '../services/api.js';
import { Loader2, Maximize2, ZoomIn, ZoomOut, MousePointer2 } from 'lucide-react';
import { getLanguageColor } from '../utils/format.js';

/**
 * @param {{ repoId: string }} props
 */
export default function RepoGraph({ repoId }) {
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  const onNodesChange = useCallback(
    (changes) => setNodes((nds) => applyNodeChanges(changes, nds)),
    []
  );
  const onEdgesChange = useCallback(
    (changes) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    []
  );

  useEffect(() => {
    async function fetchGraph() {
      setIsLoading(true);
      try {
        const data = await getRepoGraph(repoId);
        
        // Transform backend data to React Flow format if necessary
        // Assuming backend already sends compatible node/edge objects
        setNodes(data.nodes.map(node => ({
          ...node,
          style: { 
            background: '#1e293b', 
            color: '#f1f5f9',
            border: `2px solid ${getLanguageColor(node.data.language)}`,
            borderRadius: '8px',
            padding: '10px',
            fontSize: '12px',
            fontWeight: '500',
            width: 150,
          }
        })));
        setEdges(data.edges);
      } catch (error) {
        console.error('Failed to fetch graph:', error);
      } finally {
        setIsLoading(false);
      }
    }
    
    if (repoId) fetchGraph();
  }, [repoId]);

  if (isLoading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center bg-slate-950">
        <Loader2 className="w-8 h-8 text-primary-500 animate-spin mb-4" />
        <p className="text-slate-400 animate-pulse">Mapping code architecture...</p>
      </div>
    );
  }

  return (
    <div className="flex-1 relative">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
        colorMode="dark"
      >
        <Background color="#1e293b" gap={20} />
        <Controls showInteractive={false} className="bg-slate-900 border-slate-700 fill-slate-100" />
        <MiniMap 
          nodeColor={(node) => getLanguageColor(node.data.language)}
          maskColor="rgba(15, 23, 42, 0.7)"
          className="bg-slate-900 border-slate-700"
        />
      </ReactFlow>

      {/* Legend */}
      <div className="absolute bottom-4 right-4 p-4 bg-slate-900/80 backdrop-blur-md border border-slate-700 rounded-xl pointer-events-none">
        <h4 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">Relationship Key</h4>
        <div className="space-y-1.5">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-primary-500" />
            <span className="text-xs text-slate-300">Imports / Depends</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-purple-500" />
            <span className="text-xs text-slate-300">Extends / Implements</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-green-500" />
            <span className="text-xs text-slate-300">Contains / Defines</span>
          </div>
        </div>
      </div>
    </div>
  );
}
