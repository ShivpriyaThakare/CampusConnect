from datetime import datetime
from app import db

class Event(db.Model):
    __tablename__ = 'events'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    club_id = db.Column(db.Integer, db.ForeignKey('clubs.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    venue = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(50), nullable=False, default='General')
    event_date = db.Column(db.DateTime, nullable=False)
    reg_deadline = db.Column(db.DateTime, nullable=False)
    capacity = db.Column(db.Integer, nullable=False, default=100)
    banner_image = db.Column(db.String(255), nullable=True)
    allocated_budget = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    status = db.Column(db.Enum('draft', 'published', 'completed', 'cancelled', name='event_statuses'), nullable=False, default='draft')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    club = db.relationship('Club', back_populates='events')
    registrations = db.relationship('Registration', back_populates='event', cascade='all, delete-orphan', lazy=True)
    expenses = db.relationship('Expense', back_populates='event', cascade='all, delete-orphan', lazy=True)
    certificates = db.relationship('Certificate', back_populates='event', cascade='all, delete-orphan', lazy=True)
    gallery_images = db.relationship('EventGallery', back_populates='event', cascade='all, delete-orphan', lazy=True)
    feedbacks = db.relationship('Feedback', back_populates='event', cascade='all, delete-orphan', lazy=True)

    @property
    def registered_count(self):
        return len(self.registrations)

    @property
    def is_full(self):
        return len(self.registrations) >= self.capacity

    @property
    def total_expense_amount(self):
        return sum(float(exp.amount) for exp in self.expenses)

    @property
    def average_rating(self):
        if not self.feedbacks:
            return 0.0
        return round(sum(fb.rating for fb in self.feedbacks) / len(self.feedbacks), 1)

    def __repr__(self):
        return f"<Event {self.title} ({self.status})>"
