from datetime import datetime
from app import db

class Expense(db.Model):
    __tablename__ = 'expenses'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # Venue, Logistics, Marketing, Prizes, Catering, Misc
    receipt_file = db.Column(db.String(255), nullable=True)
    status = db.Column(db.Enum('pending', 'approved', 'rejected', name='expense_statuses'), nullable=False, default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship
    event = db.relationship('Event', back_populates='expenses')

    def __repr__(self):
        return f"<Expense {self.title} (${self.amount}) - Event {self.event_id}>"
