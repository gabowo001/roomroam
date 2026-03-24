import React, { useState } from 'react';

interface InputFormProps {
  onSendMessage: (message: string) => void;
}

const InputForm: React.FC<InputFormProps> = ({ onSendMessage }) => {
  const [newMessage, setNewMessage] = useState<string>('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMessage.trim()) return;
    
    onSendMessage(newMessage);
    setNewMessage('');
  };

  return (
    <form className="chat-input-form" onSubmit={handleSubmit}>
      <input
        type="text"
        value={newMessage}
        onChange={(e) => setNewMessage(e.target.value)}
        placeholder="Type your message..."
        className="chat-input"
      />
      <button type="submit" className="send-button">
        <span>→</span>
      </button>
    </form>
  );
};

export default InputForm;
