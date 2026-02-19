import React, { useState, useRef, useEffect } from 'react';
import { Send, User, Bot, Loader2, Sparkles, CornerDownLeft } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { sendChatQuery } from '../services/api.js';
import { cn } from '../utils/cn.js';

/**
 * @param {{ repoId: string }} props
 */
export default function ChatInterface({ repoId }) {
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      role: 'assistant',
      content: "I've indexed this repository. Ask me anything about the architecture, logic flow, or specific implementations!",
      timestamp: new Date().toISOString(),
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await sendChatQuery(repoId, input, messages);

      const assistantMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.answer || response.response,
        sources: response.sources,
        timestamp: new Date().toISOString(),
      };
      
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Chat error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-900/50">
      {/* Messages */}
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-4 space-y-6 scroll-smooth"
      >
        {messages.map((msg) => (
          <div 
            key={msg.id}
            className={cn(
              "flex gap-3 max-w-[90%]",
              msg.role === 'user' ? "ml-auto flex-row-reverse" : "mr-auto"
            )}
          >
            <div className={cn(
              "w-8 h-8 rounded-lg flex items-center justify-center shrink-0 shadow-sm",
              msg.role === 'user' ? "bg-slate-700 text-slate-300" : "bg-primary-600 text-white"
            )}>
              {msg.role === 'user' ? <User size={16} /> : <Bot size={16} />}
            </div>
            
            <div className="flex flex-col gap-2">
              <div className={cn(
                "p-3 rounded-2xl text-sm leading-relaxed",
                msg.role === 'user' 
                  ? "bg-primary-600 text-white rounded-tr-none shadow-lg shadow-primary-900/10" 
                  : "bg-slate-800 text-slate-200 border border-slate-700 rounded-tl-none"
              )}>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {msg.content}
                </ReactMarkdown>
              </div>

              {msg.sources && msg.sources.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-1">
                  {msg.sources.map((source, i) => (
                    <div 
                      key={i}
                      className="text-[10px] bg-slate-950/50 text-slate-500 border border-slate-800 px-2 py-1 rounded hover:text-primary-400 hover:border-primary-900/30 transition-colors cursor-pointer"
                    >
                      {source.filePath.split('/').pop()}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex gap-3 mr-auto animate-pulse">
            <div className="w-8 h-8 rounded-lg bg-primary-600/50 flex items-center justify-center shrink-0">
              <Sparkles size={16} className="text-white animate-spin" />
            </div>
            <div className="p-3 rounded-2xl bg-slate-800 border border-slate-700 text-slate-500 text-sm">
              Archaeologist is thinking...
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="p-4 bg-slate-900 border-t border-slate-800">
        <form 
          onSubmit={handleSubmit}
          className="relative flex items-center bg-slate-950 rounded-xl border border-slate-700 focus-within:border-primary-500/50 focus-within:ring-1 focus-within:ring-primary-500/20 transition-all p-2"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about components, logic..."
            className="flex-1 bg-transparent border-none focus:ring-0 text-sm text-slate-200 placeholder-slate-600 px-2 py-1"
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="p-2 bg-primary-600 hover:bg-primary-500 text-white rounded-lg transition-colors disabled:opacity-30"
          >
            <CornerDownLeft size={16} />
          </button>
        </form>
        <p className="text-[10px] text-center text-slate-600 mt-2">
          Uses RAG to analyze the code context.
        </p>
      </div>
    </div>
  );
}
