import React from 'react';
import '../Sidebar.css';

interface Group {
  id: number;
  name: string;
  created_at: string;
}

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
  savedGroups: Group[];
  currentGroupId: number | null;
  onSelectGroup: (groupId: number) => void;
  onUnsaveGroup: (groupId: number) => void;
  username: string;
}

const Sidebar: React.FC<SidebarProps> = ({
  isOpen,
  onClose,
  savedGroups,
  currentGroupId,
  onSelectGroup,
  onUnsaveGroup,
  username
}) => {
  return (
    <>
      {isOpen && <div className="sidebar-overlay" onClick={onClose} />}
      <div className={`sidebar ${isOpen ? 'open' : ''}`}>
        <div className="sidebar-header">
          <h2>Grupos Guardados</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        <div className="sidebar-content">
          {savedGroups.length === 0 ? (
            <p className="no-groups">No tienes grupos guardados aún</p>
          ) : (
            <ul className="groups-list">
              {savedGroups.map(group => (
                <li
                  key={group.id}
                  className={`group-item ${currentGroupId === group.id ? 'active' : ''}`}
                >
                  <div
                    className="group-info"
                    onClick={() => onSelectGroup(group.id)}
                  >
                    <span className="group-name">{group.name}</span>
                    {currentGroupId === group.id && (
                      <span className="current-badge">Actual</span>
                    )}
                  </div>
                  <button
                    className="unsave-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      onUnsaveGroup(group.id);
                    }}
                    title="Eliminar de favoritos"
                  >
                    ×
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="sidebar-footer">
          <div className="user-info">
            <div className="user-avatar">{username.charAt(0).toUpperCase()}</div>
            <span className="username">{username}</span>
          </div>
          <button className="settings-btn" title="Configuración">
            ⚙
          </button>
        </div>
      </div>
    </>
  );
};

export default Sidebar;
