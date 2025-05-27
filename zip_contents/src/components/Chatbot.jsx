import React, { useState, useEffect, useRef } from 'react';
import './Chatbot.css';

const Chatbot = () => {
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState([
        { text: "Hi! I'm Smartie, your Nestlé assistant. Ask me about products!", sender: 'bot' }
    ]);
    const [inputValue, setInputValue] = useState('');
    const messagesEndRef = useRef(null);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const handleSend = async () => {
        if (!inputValue.trim()) return;

        const userMsg = { text: inputValue, sender: 'user' };
        setMessages(prev => [...prev, userMsg]);
        setInputValue('');

        try {
            const response = await fetch('http://localhost:8000/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: inputValue })
            });
            
            const data = await response.json();
            setMessages(prev => [...prev, { 
                text: data.response, 
                sender: 'bot',
                references: data.references 
            }]);
        } catch (error) {
            setMessages(prev => [...prev, { 
                text: "Sorry, I can't connect right now.", 
                sender: 'bot' 
            }]);
        }
    };

    return (
        <div className={`chatbot ${isOpen ? 'open' : ''}`}>
            <div className="header" onClick={() => setIsOpen(!isOpen)}>
                <div className="icon">🤖</div>
                <h3>Smartie</h3>
                <div className="toggle">{isOpen ? '−' : '+'}</div>
            </div>
            
            {isOpen && (
                <div className="body">
                    <div className="messages">
                        {messages.map((msg, i) => (
                            <div key={i} className={`message ${msg.sender}`}>
                                <p>{msg.text}</p>
                                {msg.references?.length > 0 && (
                                    <div className="refs">
                                        <small>Sources:</small>
                                        {msg.references.map((ref, j) => (
                                            <a key={j} href={ref} target="_blank" rel="noreferrer">
                                                {new URL(ref).pathname}
                                            </a>
                                        ))}
                                    </div>
                                )}
                            </div>
                        ))}
                        <div ref={messagesEndRef} />
                    </div>
                    
                    <div className="input">
                        <input
                            value={inputValue}
                            onChange={(e) => setInputValue(e.target.value)}
                            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                            placeholder="Ask about Nestlé products..."
                        />
                        <button onClick={handleSend}>Send</button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default Chatbot;