import React from 'react';

interface HeaderProps {
  isConnected: boolean;
  onMenuClick?: () => void;
  onLikeGroup?: () => void;
  onExitGroup?: () => void;
  currentGroupName?: string;
  isGroupLiked?: boolean;
}

const Header: React.FC<HeaderProps> = ({
  isConnected,
  onMenuClick,
  onLikeGroup,
  onExitGroup,
  currentGroupName,
  isGroupLiked
}) => {
  return (
    <div className="chat-header">
      <button className="hamburger-menu" onClick={onMenuClick}>
        <div className="hamburger-line"></div>
        <div className="hamburger-line"></div>
        <div className="hamburger-line"></div>
      </button>
      <h2>{currentGroupName || 'RoomRoam'}</h2>
      <div className="header-actions">
        {currentGroupName && (
          <>
            <button
              className={`icon-button like-button ${isGroupLiked ? 'liked' : ''}`}
              onClick={onLikeGroup}
              title={isGroupLiked ? "Ya guardado" : "Guardar grupo"}
            >
              <span className="heart-icon">{isGroupLiked ? '♥' : '♡'}</span>
            </button>
            <button
              className="icon-button exit-button"
              onClick={onExitGroup}
              title="Salir del grupo"
            >
              <span className="exit-icon">⎋</span>
            </button>
          </>
        )}
        <div className="connection-status">
          <span className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`}></span>
          {isConnected ? 'Connected' : 'Connecting...'}
        </div>
      </div>
    </div>
  );
};

export default Header;
