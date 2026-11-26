from datetime import datetime
from app import db


class ClubMembership(db.Model):
    __tablename__ = 'club_memberships'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    club_id = db.Column(db.Integer, db.ForeignKey('clubs.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    member_role = db.Column(db.String(50), nullable=False, default='Member')
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('club_id', 'user_id', name='uq_club_member'),
    )

    # Relationships
    club = db.relationship('Club', back_populates='memberships')
    user = db.relationship('User', back_populates='club_memberships')

    def __repr__(self):
        return f"<ClubMembership User {self.user_id} -> Club {self.club_id} ({self.member_role})>"
