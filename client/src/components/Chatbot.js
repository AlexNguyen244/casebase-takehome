import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

const API_BASE_URL = 'http://localhost:8000';

const Chatbot = ({ uploadedPDFs }) => {
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'bot',
      text: "Hi! I'm Casey, your AI assistant for CaseBase. Ask me anything about your uploaded documents!",
      timestamp: new Date().toISOString(),
    },
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [error, setError] = useState(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const handleSendMessage = async (e) => {
    e.preventDefault();

    if (!inputMessage.trim()) return;

    // Check if documents are uploaded
    if (uploadedPDFs.length === 0) {
      const errorMsg = {
        id: Date.now(),
        type: 'bot',
        text: "Please upload at least one PDF document before asking questions. I need documents to search through!",
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
      return;
    }

    const userMessage = {
      id: Date.now(),
      type: 'user',
      text: inputMessage,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    const currentMessage = inputMessage;
    setInputMessage('');
    setIsTyping(true);
    setError(null);

    try {
      // Build conversation history (last 5 messages for context)
      const conversationHistory = messages
        .slice(-10) // Get last 10 messages
        .map(msg => ({
          role: msg.type === 'user' ? 'user' : 'assistant',
          content: msg.text
        }));

      // Call the chat API
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: currentMessage,
          conversation_history: conversationHistory,
          file_filter: null, // Search across all documents
          top_k: 5
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to get response from AI');
      }

      const data = await response.json();

      const botResponse = {
        id: Date.now() + 1,
        type: 'bot',
        text: data.data.message,
        sources: data.data.sources,
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, botResponse]);
    } catch (error) {
      console.error('Chat error:', error);
      setError(error.message);

      const errorResponse = {
        id: Date.now() + 1,
        type: 'bot',
        text: "I'm sorry, I encountered an error processing your question. Please try again.",
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, errorResponse]);
    } finally {
      setIsTyping(false);
    }
  };

  const formatTime = (isoString) => {
    const date = new Date(isoString);
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="bg-white rounded-lg shadow-md flex flex-col h-[600px]">
      <div className="bg-gradient-to-r from-primary to-primary-dark text-white p-6 rounded-t-lg">
        <h2 className="text-2xl font-bold text-center">Hey, I'm Casey!</h2>
        <p className="text-center text-blue-100 text-sm mt-1">
          Ask me anything about your documents
        </p>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${
              message.type === 'user' ? 'justify-end' : 'justify-start'
            }`}
          >
            {message.type === 'bot' && (
              <div className="flex-shrink-0 mr-3">
                <div className="bg-primary rounded-full p-2 w-10 h-10 flex items-center justify-center">
                  <Bot className="w-5 h-5 text-white" />
                </div>
              </div>
            )}

            <div
              className={`max-w-[75%] ${
                message.type === 'user'
                  ? 'bg-primary text-white'
                  : 'bg-gray-100 text-gray-800'
              } rounded-2xl px-4 py-3`}
            >
              {message.type === 'bot' ? (
                <div className="text-sm prose prose-sm max-w-none">
                  <ReactMarkdown
                    components={{
                      p: ({node, ...props}) => <p className="mb-2 last:mb-0" {...props} />,
                      strong: ({node, ...props}) => <strong className="font-semibold" {...props} />,
                      ul: ({node, ...props}) => <ul className="list-disc ml-4 mb-2" {...props} />,
                      ol: ({node, ...props}) => <ol className="list-decimal ml-4 mb-2" {...props} />,
                      li: ({node, ...props}) => <li className="mb-1" {...props} />,
                      code: ({node, ...props}) => <code className="bg-gray-200 px-1 rounded" {...props} />,
                    }}
                  >
                    {message.text}
                  </ReactMarkdown>
                </div>
              ) : (
                <p className="text-sm whitespace-pre-line">{message.text}</p>
              )}

              {message.sources && message.sources.length > 0 && (
                <div className="mt-2 pt-2 border-t border-gray-300">
                  <p className="text-xs font-semibold text-gray-600 mb-1">Sources:</p>
                  {message.sources.slice(0, 3).map((source, idx) => (
                    <p key={idx} className="text-xs text-gray-500">
                      • {source.file_name.split('/').pop()} (relevance: {(source.relevance_score * 100).toFixed(1)}%)
                    </p>
                  ))}
                </div>
              )}

              <p
                className={`text-xs mt-1 ${
                  message.type === 'user' ? 'text-blue-100' : 'text-gray-500'
                }`}
              >
                {formatTime(message.timestamp)}
              </p>
            </div>
          </div>
        ))}

        {isTyping && (
          <div className="flex justify-start">
            <div className="flex-shrink-0 mr-3">
              <div className="bg-primary rounded-full p-2 w-10 h-10 flex items-center justify-center">
                <Bot className="w-5 h-5 text-white" />
              </div>
            </div>
            <div className="bg-gray-100 rounded-2xl px-4 py-3">
              <div className="flex space-x-2">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="border-t border-gray-200 p-4">
        <p className="text-xs text-center text-gray-500 mb-3">
          Privacy notice • <span className="underline cursor-pointer">Terms</span>
        </p>

        <form onSubmit={handleSendMessage} className="flex space-x-2">
          <input
            ref={inputRef}
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            placeholder="Ask me about your documents..."
            className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
          />
          <button
            type="submit"
            disabled={!inputMessage.trim()}
            className="bg-primary hover:bg-primary-dark disabled:bg-gray-300 disabled:cursor-not-allowed text-white p-3 rounded-lg transition-all"
          >
            <Send className="w-5 h-5" />
          </button>
        </form>
      </div>
    </div>
  );
};

export default Chatbot;
