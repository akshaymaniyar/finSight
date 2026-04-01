import { useState, useRef, useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Send, MessageSquare, Sparkles } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { sendMessage, getChatHistory } from '../api/chat';
import type { ChatMessage } from '../types';
import LoadingSpinner from '../components/LoadingSpinner';

const SUGGESTIONS = [
  'How much did I spend on food last month?',
  'What was my total IKEA spend?',
  'Show Zerodha transfers this year',
  'Compare credit card vs debit spending',
  'What are my top 5 expenses this month?',
];

export default function ChatPage() {
  const queryClient = useQueryClient();
  const [input, setInput] = useState('');
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [localMessages, setLocalMessages] = useState<ChatMessage[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const { data: history, isLoading: historyLoading } = useQuery({
    queryKey: ['chat-history', sessionId],
    queryFn: () => getChatHistory(sessionId, 100, 0),
  });

  useEffect(() => {
    if (history?.messages) {
      setLocalMessages(history.messages);
      if (history.messages.length > 0 && !sessionId) {
        setSessionId(history.messages[0].session_id);
      }
    }
  }, [history, sessionId]);

  const mutation = useMutation({
    mutationFn: (message: string) => sendMessage(message, sessionId),
    onMutate: (message) => {
      const tempMsg: ChatMessage = {
        id: Date.now(),
        role: 'user',
        content: message,
        session_id: sessionId || '',
        created_at: new Date().toISOString(),
      };
      setLocalMessages((prev) => [...prev, tempMsg]);
    },
    onSuccess: (data) => {
      setSessionId(data.session_id);
      const assistantMsg: ChatMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: data.assistant_message,
        session_id: data.session_id,
        created_at: new Date().toISOString(),
      };
      setLocalMessages((prev) => [...prev, assistantMsg]);
      queryClient.invalidateQueries({ queryKey: ['chat-history'] });
    },
    onError: () => {
      const errorMsg: ChatMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: 'Sorry, something went wrong. Please try again.',
        session_id: sessionId || '',
        created_at: new Date().toISOString(),
      };
      setLocalMessages((prev) => [...prev, errorMsg]);
    },
  });

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [localMessages, mutation.isPending]);

  const handleSend = () => {
    const msg = input.trim();
    if (!msg || mutation.isPending) return;
    setInput('');
    mutation.mutate(msg);
  };

  const handleSuggestion = (suggestion: string) => {
    setInput('');
    mutation.mutate(suggestion);
  };

  if (historyLoading) {
    return (
      <div className="flex items-center justify-center h-full py-32">
        <LoadingSpinner size={40} text="Loading chat..." />
      </div>
    );
  }

  const showSuggestions = localMessages.length === 0;

  return (
    <div className="flex flex-col h-full">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-4 lg:p-8">
        <div className="max-w-3xl mx-auto space-y-4">
          {showSuggestions && (
            <div className="py-12 text-center">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-indigo-50 mb-6">
                <Sparkles size={28} className="text-indigo-600" />
              </div>
              <h2 className="text-xl font-bold text-gray-900 mb-2">Ask about your finances</h2>
              <p className="text-sm text-gray-500 mb-8 max-w-md mx-auto">
                Get insights about your spending, income, and transactions using natural language.
              </p>
              <div className="flex flex-wrap justify-center gap-2">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => handleSuggestion(s)}
                    className="px-4 py-2 bg-white border border-gray-200 rounded-full text-sm text-gray-700 hover:bg-indigo-50 hover:border-indigo-200 hover:text-indigo-700 transition-colors"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {localMessages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[85%] lg:max-w-[70%] ${
                  msg.role === 'user'
                    ? 'bg-indigo-600 text-white rounded-2xl rounded-br-sm px-4 py-3'
                    : 'bg-white border border-gray-100 shadow-sm rounded-2xl rounded-bl-sm px-4 py-3'
                }`}
              >
                {msg.role === 'assistant' ? (
                  <div className="prose prose-sm max-w-none text-gray-800 [&_p]:mb-2 [&_p:last-child]:mb-0 [&_ul]:mb-2 [&_ol]:mb-2 [&_li]:mb-0.5 [&_code]:bg-gray-100 [&_code]:px-1 [&_code]:py-0.5 [&_code]:rounded [&_code]:text-xs [&_pre]:bg-gray-900 [&_pre]:text-gray-100 [&_pre]:rounded-lg [&_pre]:p-3 [&_pre]:text-xs [&_table]:text-sm [&_th]:px-2 [&_th]:py-1 [&_td]:px-2 [&_td]:py-1 [&_th]:bg-gray-50 [&_table]:border-collapse [&_th]:border [&_th]:border-gray-200 [&_td]:border [&_td]:border-gray-200">
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  </div>
                ) : (
                  <p className="text-sm">{msg.content}</p>
                )}
              </div>
            </div>
          ))}

          {mutation.isPending && (
            <div className="flex justify-start">
              <div className="bg-white border border-gray-100 shadow-sm rounded-2xl rounded-bl-sm px-4 py-3">
                <div className="flex items-center gap-1">
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0ms]" />
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:150ms]" />
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:300ms]" />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input bar */}
      <div className="border-t border-gray-200 bg-white px-4 py-3">
        <div className="max-w-3xl mx-auto">
          <div className="flex items-center gap-3">
            <MessageSquare size={18} className="text-gray-400 shrink-0" />
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder="Ask about your finances..."
              className="flex-1 py-2 text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none"
              disabled={mutation.isPending}
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || mutation.isPending}
              className="p-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <Send size={16} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
