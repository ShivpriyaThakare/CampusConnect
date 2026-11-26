import uuid
from datetime import datetime
from app import db

class Certificate(db.Model):
    __tablename__ = 'certificates'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    certificate_uid = db.Column(db.String(64), unique=True, nullable=False, default=lambda: uuid.uuid4().hex)
    issued_at = db.Column(db.DateTime, default=datetime.utcnow)
    download_count = db.Column(db.Integer, nullable=False, default=0)

    # Relationships
    event = db.relationship('Event', back_populates='certificates')
    user = db.relationship('User', back_populates='certificates')

    def __repr__(self):
        return f"<Certificate {self.certificate_uid} -> User {self.user_id}>"
