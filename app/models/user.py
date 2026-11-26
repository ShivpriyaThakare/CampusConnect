from datetime import datetime
from flask_login import UserMixin
from app import db, bcrypt

class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum('admin', 'coordinator', 'student', name='user_roles'), nullable=False, default='student')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    managed_clubs = db.relationship('Club', back_populates='coordinator', lazy=True)
    club_memberships = db.relationship('ClubMembership', back_populates='user', cascade='all, delete-orphan', lazy=True)
    registrations = db.relationship('Registration', back_populates='user', cascade='all, delete-orphan', lazy=True)
    certificates = db.relationship('Certificate', back_populates='user', cascade='all, delete-orphan', lazy=True)
    feedbacks = db.relationship('Feedback', back_populates='user', cascade='all, delete-orphan', lazy=True)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_coordinator(self):
        return self.role == 'coordinator'

    @property
    def is_student(self):
        return self.role == 'student'

    def __repr__(self):
        return f"<User {self.name} ({self.role})>"
