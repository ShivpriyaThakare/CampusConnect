from datetime import datetime
from app import db

class Registration(db.Model):
    __tablename__ = 'registrations'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)
    attended = db.Column(db.Boolean, nullable=False, default=False)

    __table_args__ = (
        db.UniqueConstraint('event_id', 'user_id', name='uq_event_user'),
    )

    # Relationships
    event = db.relationship('Event', back_populates='registrations')
    user = db.relationship('User', back_populates='registrations')

    def __repr__(self):
        return f"<Registration User {self.user_id} -> Event {self.event_id}>"
