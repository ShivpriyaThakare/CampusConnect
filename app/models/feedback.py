from datetime import datetime
from app import db

class Feedback(db.Model):
    __tablename__ = 'feedback'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1 to 5
    comments = db.Column(db.Text, nullable=True)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('event_id', 'user_id', name='uq_feedback_event_user'),
    )

    # Relationships
    event = db.relationship('Event', back_populates='feedbacks')
    user = db.relationship('User', back_populates='feedbacks')

    def __repr__(self):
        return f"<Feedback Rating {self.rating} by User {self.user_id} on Event {self.event_id}>"
