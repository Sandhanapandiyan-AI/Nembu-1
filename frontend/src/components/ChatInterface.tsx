import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import ThinkingAnimation from './ThinkingAnimation';
import DataVisualization from './DataVisualization';
import VoiceInput from './VoiceInput';
import './ChatInterface.css';

interface FieldInfo {
  name: string;
  type: string;
  description: string;
}

interface Message {
  text: string;
  isUser: boolean;
  data?: any;
  isFieldRequest?: boolean;
  fieldInfo?: FieldInfo;
}

const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const handleSend = useCallback(async () => {
    if (!inputText.trim()) return;

    const userMessage: Message = {
      text: inputText,
      isUser: true,
    };

    setMessages(prev => [...prev, userMessage]);
    setInputText('');
    setIsThinking(true);

    try {
      const response = await axios.post('http://localhost:8000/api/chat', {
        message: inputText,
      });

      // The response now contains structured data
      const responseData = response.data;

      // Create a formatted message for display
      let displayText = '';

      // Handle INSERT query field requests
      if (responseData.query_type === 'INSERT_FIELD_REQUEST') {
        // This is a request for a specific field value
        displayText = responseData.message;

        const botMessage: Message = {
          text: displayText,
          isUser: false,
          data: null,
          isFieldRequest: true,
          fieldInfo: responseData.field
        };

        setMessages(prev => [...prev, botMessage]);
        setIsThinking(false);
        return;
      }

      // Skip SQL query display - we're not showing it to the user anymore

      // Add explanation if available
      if (responseData.explanation && responseData.explanation.trim()) {
        displayText += `${responseData.explanation}\n\n`;
      }

      // Add success/error message
      if (!responseData.success && responseData.error) {
        displayText += `Error: ${responseData.error}\n\n`;
      } else if (responseData.message) {
        // For data modification queries (UPDATE, INSERT, DELETE)
        if (responseData.query_type && ['UPDATE', 'INSERT', 'DELETE'].includes(responseData.query_type)) {
          displayText += `✅ ${responseData.message}\n\n`;
        } else {
          // For SELECT queries
          displayText += `${responseData.message}\n\n`;
        }
      }

      const botMessage: Message = {
        text: displayText,
        isUser: false,
        data: responseData.data // Store the structured data for rendering
      };

      setMessages(prev => [...prev, botMessage]);
    } catch (error) {
      console.error('Error sending message:', error);
      setMessages(prev => [...prev, {
        text: "Sorry, I encountered an error while generating the response. Please try again.",
        isUser: false
      }]);
    } finally {
      setIsThinking(false);
    }
  }, [inputText]);

  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      // Ctrl/Cmd + Enter to send message
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        handleSend();
      }
      // Esc to clear input
      if (e.key === 'Escape') {
        setInputText('');
      }
      // Ctrl/Cmd + / to focus input
      if ((e.ctrlKey || e.metaKey) && e.key === '/') {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [handleSend, setInputText]);

  const renderMessage = (message: Message) => {
    const text = message.text;

    if (message.isUser) {
      return (
        <div className="message-bubble user">
          {text}
        </div>
      );
    }

    // Handle field request messages
    if (message.isFieldRequest && message.fieldInfo) {
      const fieldInfo = message.fieldInfo;
      return (
        <div className="message-bubble bot field-request">
          <div>{text}</div>
          <div className="field-info">
            <div><strong>Field:</strong> {fieldInfo.name}</div>
            <div><strong>Type:</strong> {fieldInfo.type}</div>
            <div><strong>Description:</strong> {fieldInfo.description}</div>
          </div>
        </div>
      );
    }

    // Check if data is available for display
    const hasData = message.data &&
                    message.data.columns &&
                    message.data.rows &&
                    message.data.rows.length > 0;

    // We no longer need to check for visualizable data since we always show the table

    // Render the message with text and data table (no SQL code blocks)
    return (
      <div style={{ maxWidth: '100%' }}>
        {/* Render text parts */}
        {text && (
          <div className="message-bubble bot">
            {text}
          </div>
        )}

        {/* Render visualization if data is available */}
        {hasData && (
          <div style={{ marginTop: '1rem' }}>
            {/* Always show data visualization with table as default */}
            <DataVisualization
              data={message.data}
              initialChartType="table"
              showTableByDefault={true}
              formattedHeaders={message.data.columns.map((col: string) => {
                // Format column headers for better readability
                if (col === 'department_identifier' && message.data.columns.includes('department_name')) {
                  return 'Department ID';
                } else if (col === 'department_name') {
                  return 'Department';
                } else if (col === 'employee_identifier') {
                  return 'Employee ID';
                } else if (col === 'employee_first_name') {
                  return 'First Name';
                } else if (col === 'employee_last_name') {
                  return 'Last Name';
                } else if (col === 'employee_salary') {
                  return 'Salary';
                } else if (col === 'employee_hire_date') {
                  return 'Hire Date';
                } else if (col === 'emp_name') {
                  return 'Employee Name';
                }
                return col;
              })}
            />
          </div>
        )}
      </div>
    );
  };

  const handleVoiceInput = (text: string) => {
    setInputText(text);
  };

  return (
    <div className="chat-interface">
      <div className="chat-messages">
        {messages.map((message, index) => (
          <div
            key={index}
            className={`message-container ${message.isUser ? 'user' : 'bot'}`}
          >
            {renderMessage(message)}
          </div>
        ))}
        {isThinking && (
          <div className="thinking-animation">
            <ThinkingAnimation />
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="input-container">
        <textarea
          ref={inputRef}
          className="chat-input"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
          placeholder="Type your question here... (Ctrl + / to focus, Ctrl + Enter to send)"
        />
        <div className="input-actions">
          <VoiceInput
            onSpeechResult={handleVoiceInput}
            disabled={isThinking}
          />
          <button
            className="send-button"
            onClick={() => handleSend()}
            disabled={isThinking || !inputText.trim()}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;
