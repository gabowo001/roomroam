from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from quart import current_app
import bcrypt
from quart_auth import AuthUser
from datetime import datetime
import os

Base = declarative_base()

# Association table for saved groups (many-to-many relationship)
saved_groups = Table(
    'saved_groups',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('group_id', Integer, ForeignKey('groups.id'), primary_key=True)
)

class User(Base, AuthUser):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    current_group_id = Column(Integer, ForeignKey('groups.id'), nullable=True)

    # Relationships
    messages = relationship('Message', back_populates='user', lazy='select')
    saved_groups_rel = relationship('Group', secondary=saved_groups, back_populates='saved_by_users', lazy='select')
    current_group = relationship('Group', foreign_keys=[current_group_id])

    def set_password(self, password):
        """Hash and set the user's password"""
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password):
        """Check if the provided password matches the stored hash"""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

    def is_authenticated(self):
        """Check if user is authenticated"""
        return True

    def is_active(self):
        """Check if user is active"""
        return True

    def is_anonymous(self):
        """Check if user is anonymous"""
        return False

    def get_id(self):
        """Get the user's ID"""
        return str(self.id)

    @property
    def auth_id(self):
        """Get the user's ID for quart-auth"""
        return self.get_id()

    @classmethod
    def get_user_by_username(cls, username, session=None):
        """Get a user by username"""
        if session is None:
            session = current_app.db_session
        return session.query(cls).filter_by(username=username).first()


class Group(Base):
    __tablename__ = 'groups'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    messages = relationship('Message', back_populates='group', cascade='all, delete-orphan')
    saved_by_users = relationship('User', secondary=saved_groups, back_populates='saved_groups_rel')


class Message(Base):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    group_id = Column(Integer, ForeignKey('groups.id'), nullable=False)

    # Relationships
    user = relationship('User', back_populates='messages')
    group = relationship('Group', back_populates='messages')


def get_db_session():
    """Create and return a database session"""
    DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/postgres')
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def init_db():
    """Initialize the database by creating tables"""
    DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/postgres')
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(bind=engine)