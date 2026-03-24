import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Header, ChatMessages, InputForm, Login, Sidebar } from '../components';
import { WebSocketManager } from '../services/websocketManager';
import { Message } from '../types';

interface Group {
  id: number;
  name: string;
  created_at: string;
}

const Chat: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [username, setUsername] = useState<string>('');
  const [wsConnected, setWsConnected] = useState<boolean>(false);
  const [isLoggedIn, setIsLoggedIn] = useState<boolean>(false);
  const [wsManager, setWsManager] = useState<WebSocketManager | null>(null);
  const [currentGroup, setCurrentGroup] = useState<Group | null>(null);
  const [savedGroups, setSavedGroups] = useState<Group[]>([]);
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(false);
  const [isCurrentGroupLiked, setIsCurrentGroupLiked] = useState<boolean>(false);

  useEffect(() => {
    // Check if user is already logged in
    checkAuthStatus();
  }, []);

  useEffect(() => {
    // Check if current group is liked whenever current group or saved groups change
    if (currentGroup && savedGroups.length > 0) {
      const isLiked = savedGroups.some(group => group.id === currentGroup.id);
      setIsCurrentGroupLiked(isLiked);
    } else {
      setIsCurrentGroupLiked(false);
    }
  }, [currentGroup, savedGroups]);

  const checkAuthStatus = async () => {
    try {
      const response = await axios.get('/api/messages');
      // If request succeeds, user is authenticated
      setIsLoggedIn(true);
      setUsername(response.data.user?.username || '');

      // Load saved groups
      await loadSavedGroups();

      // If user doesn't have a current group, get a random one
      if (!response.data.group_id) {
        await joinRandomGroup();
      } else {
        // Load current group info and messages
        setMessages(response.data.messages || []);
        // We need to get group info separately if needed
      }
    } catch (error) {
      // If request fails, user is not authenticated
      setIsLoggedIn(false);
    }
  };

  const loadSavedGroups = async () => {
    try {
      const response = await axios.get('/api/groups/saved');
      if (response.data.success) {
        setSavedGroups(response.data.groups);
      }
    } catch (error) {
      console.error('Error loading saved groups:', error);
    }
  };

  const joinRandomGroup = async () => {
    try {
      const response = await axios.get('/api/groups/random');
      if (response.data.success) {
        const group = response.data.group;
        setCurrentGroup(group);
        setMessages([]); // Clear messages before loading new group
        await initializeWebSocket();
      }
    } catch (error) {
      console.error('Error joining random group:', error);
    }
  };

  const initializeWebSocket = async () => {
    // Close existing WebSocket if any
    if (wsManager) {
      wsManager.disconnect();
    }

    // Initialize new WebSocket manager
    const newWsManager = new WebSocketManager();
    setWsManager(newWsManager);

    // Set up WebSocket event handlers
    newWsManager.onMessage((newMessage: Message) => {
      setMessages(prevMessages => {
        // Check if message already exists to avoid duplicates
        const exists = prevMessages.some(m => m.id === newMessage.id);
        if (!exists) {
          return [...prevMessages, newMessage];
        }
        return prevMessages;
      });
    });

    newWsManager.onStatusChange(setWsConnected);
  };

  const handleLoginSuccess = async (username: string) => {
    setUsername(username);
    setIsLoggedIn(true);

    // Load saved groups and join a random group
    await loadSavedGroups();
    await joinRandomGroup();
  };

  const handleSendMessage = async (messageText: string) => {
    if (!currentGroup) {
      console.error('No current group');
      return;
    }

    const messageData = {
      text: messageText,
      timestamp: new Date().toISOString()
    };

    try {
      const response = await axios.post<{ success: boolean, message: Message }>('/api/messages', messageData);
      if (response.data.success) {
        // Message will be added via WebSocket broadcast
        console.log('Message sent successfully');
      }
    } catch (error) {
      console.error('Error sending message:', error);
      // Add message locally even if backend fails
      setMessages(prev => [...prev, {...messageData, id: prev.length + 1, username: username}]);
    }
  };

  const handleLikeGroup = async () => {
    if (!currentGroup) return;

    try {
      const response = await axios.post('/api/groups/like');
      if (response.data.success) {
        // Reload saved groups
        await loadSavedGroups();
        console.log('Group saved to favorites');
      }
    } catch (error) {
      console.error('Error liking group:', error);
    }
  };

  const handleExitGroup = async () => {
    if (!currentGroup) return;

    try {
      // Leave current group and join a new random one
      const response = await axios.post('/api/groups/leave', { join_new: true });
      if (response.data.success && response.data.new_group) {
        const newGroup = response.data.new_group;
        setCurrentGroup(newGroup);
        setMessages([]);
        await initializeWebSocket();
      }
    } catch (error) {
      console.error('Error exiting group:', error);
    }
  };

  const handleSelectGroup = async (groupId: number) => {
    try {
      const response = await axios.post(`/api/groups/join/${groupId}`);
      if (response.data.success) {
        const group = response.data.group;
        setCurrentGroup(group);
        setMessages([]);
        await initializeWebSocket();
        setIsSidebarOpen(false);
      }
    } catch (error) {
      console.error('Error joining group:', error);
    }
  };

  const handleUnsaveGroup = async (groupId: number) => {
    try {
      const response = await axios.post(`/api/groups/unsave/${groupId}`);
      if (response.data.success) {
        // Reload saved groups
        await loadSavedGroups();
      }
    } catch (error) {
      console.error('Error unsaving group:', error);
    }
  };

  if (!isLoggedIn) {
    return <Login onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <div className="chat-app">
      <Sidebar
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        savedGroups={savedGroups}
        currentGroupId={currentGroup?.id || null}
        onSelectGroup={handleSelectGroup}
        onUnsaveGroup={handleUnsaveGroup}
        username={username}
      />
      <Header
        isConnected={wsConnected}
        onMenuClick={() => setIsSidebarOpen(true)}
        onLikeGroup={handleLikeGroup}
        onExitGroup={handleExitGroup}
        currentGroupName={currentGroup?.name}
        isGroupLiked={isCurrentGroupLiked}
      />
      <ChatMessages messages={messages} currentUsername={username} />
      <InputForm onSendMessage={handleSendMessage} />
    </div>
  );
};

export default Chat;
