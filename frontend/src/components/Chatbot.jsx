import React, { useState, useEffect, useRef } from 'react';
import './Chatbot.css';

const Chatbot = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    {
      text: "Hey! I'm Smartie, your personal MadeWithNestle assistant. Ask me anything, and I'll quickly search the entire site to find the answers you need!",
      sender: 'bot'
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [sessionId, setSessionId] = useState('');
  const messagesEndRef = useRef(null);

  // Generate a session ID on component mount
  useEffect(() => {
    setSessionId('session-' + Math.random().toString(36).substr(2, 9));
  }, []);

  // Scroll to bottom of messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return;

    // Add user message
    const userMessage = { text: inputValue, sender: 'user' };
    setMessages(prev => [...prev, userMessage]);
    setInputValue('');

    try {
      // Call backend API
      const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: inputValue,
          session_id: sessionId
        }),
      });

      if (!response.ok) throw new Error('Network response was not ok');

      const data = await response.json();
      
      // Add bot response
      setMessages(prev => [
        ...prev,
        { 
          text: data.response, 
          sender: 'bot',
          references: data.references 
        }
      ]);
    } catch (error) {
      console.error('Error:', error);
      setMessages(prev => [
        ...prev,
        { 
          text: "Sorry, I'm having trouble connecting to the server. Please try again later.", 
          sender: 'bot' 
        }
      ]);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleSendMessage();
    }
  };

  return (
    <div className={`chatbot-container ${isOpen ? 'expanded' : ''}`}>
      <div className="chatbot-header" onClick={() => setIsOpen(!isOpen)}>
        <div className="chatbot-icon">
          <img src="https://www.madewithnestle.ca/sites/default/files/2021-09/nestle-logo.png" alt="Smartie" />
        </div>
        <div className="chatbot-title">Smartie</div>
        <div className="chatbot-toggle">
          {isOpen ? '−' : '+'}
        </div>
      </div>
      
      {isOpen && (
        <div className="chatbot-body">
          <div className="chatbot-messages">
            {messages.map((message, index) => (
              <div key={index} className={`message ${message.sender}`}>
                <div className="message-content">
                  {message.text.split('\n').map((paragraph, i) => (
                    <p key={i}>{paragraph}</p>
                  ))}
                  {message.references && message.references.length > 0 && (
                    <div className="references">
                      <p>References:</p>
                      <ul>
                        {message.references.map((ref, i) => (
                          <li key={i}>
                            <a href={ref} target="_blank" rel="noopener noreferrer">
                              {ref}
                            </a>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
          
          <div className="chatbot-input">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask me anything about Nestlé products..."
            />
            <button onClick={handleSendMessage}>Send</button>
          </div>
        </div>
      )}
    </div>
  );
};

export default Chatbot;