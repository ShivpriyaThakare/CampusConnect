from datetime import datetime
from app import db

class Club(db.Model):
    __tablename__ = 'clubs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=False, default='General')
    contact_info = db.Column(db.String(150), nullable=True)
    coordinator_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    logo_url = db.Column(db.String(255), nullable=True)
    status = db.Column(db.Enum('pending', 'approved', 'rejected', name='club_statuses'), nullable=False, default='approved')
    is_archived = db.Column(db.Boolean, nullable=False, default=False)
    allocated_budget = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    coordinator = db.relationship('User', back_populates='managed_clubs')
    events = db.relationship('Event', back_populates='club', cascade='all, delete-orphan', lazy=True)
    memberships = db.relationship('ClubMembership', back_populates='club', cascade='all, delete-orphan', lazy=True)

    @property
    def member_count(self):
        return len(self.memberships)

    @property
    def event_count(self):
        return len(self.events)

    @property
    def total_event_expenses(self):
        total = 0.0
        for event in self.events:
            for expense in event.expenses:
                total += float(expense.amount)
        return total

    def __repr__(self):
        return f"<Club {self.name}>"
