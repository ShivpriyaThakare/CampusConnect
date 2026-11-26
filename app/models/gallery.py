from datetime import datetime
from app import db

class EventGallery(db.Model):
    __tablename__ = 'event_gallery'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id', ondelete='CASCADE'), nullable=False)
    image_url = db.Column(db.String(255), nullable=False)
    caption = db.Column(db.String(255), nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship
    event = db.relationship('Event', back_populates='gallery_images')

    def __repr__(self):
        return f"<EventGallery Image {self.id} -> Event {self.event_id}>"
