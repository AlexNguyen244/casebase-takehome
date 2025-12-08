import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot } from 'lucide-react';

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

    const userMessage = {
      id: Date.now(),
      type: 'user',
      text: inputMessage,
      timestamp: new Date().toISOString(),
    };

    setMessages([...messages, userMessage]);
    setInputMessage('');
    setIsTyping(true);

    setTimeout(() => {
      const botResponse = {
        id: Date.now() + 1,
        type: 'bot',
        text: generateBotResponse(inputMessage, uploadedPDFs),
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, botResponse]);
      setIsTyping(false);
    }, 1000);
  };

  const generateBotResponse = (message, pdfs) => {
    const lowerMessage = message.toLowerCase();

    if (lowerMessage.includes('hello') || lowerMessage.includes('hi')) {
      return "Hello! How can I help you with your documents today?";
    }

    if (lowerMessage.includes('how many') && lowerMessage.includes('document')) {
      return `You currently have ${pdfs.length} document${pdfs.length !== 1 ? 's' : ''} uploaded.`;
    }

    if (lowerMessage.includes('what') && lowerMessage.includes('document')) {
      if (pdfs.length === 0) {
        return "You haven't uploaded any documents yet. Please upload some PDFs to get started.";
      }
      const fileList = pdfs.map(pdf => `• ${pdf.name}`).join('\n');
      return `Here are your uploaded documents:\n\n${fileList}`;
    }

    if (pdfs.length === 0) {
      return "I'd be happy to help analyze your documents, but you haven't uploaded any PDFs yet. Please upload some documents first!";
    }

    return `I understand you're asking about: "${message}". Once the backend is connected, I'll be able to analyze your ${pdfs.length} uploaded document${pdfs.length !== 1 ? 's' : ''} and provide detailed answers!`;
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
          Ask me anything about CaseBase
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
              <p className="text-sm whitespace-pre-line">{message.text}</p>
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
            placeholder="Ask me about CaseBase features, pricing, or anything else..."
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
