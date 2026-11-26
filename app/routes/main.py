from datetime import datetime
from flask import Blueprint, render_template, request, flash, redirect, url_for, abort
from flask_login import current_user
from app.models.club import Club
from app.models.event import Event
from app.models.gallery import EventGallery
from app.models.feedback import Feedback
from app.models.user import User

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    featured_events = (
        Event.query.join(Club)
        .filter(Event.status == 'published', Club.status == 'approved', Club.is_archived == False)
        .order_by(Event.event_date.asc())
        .limit(6)
        .all()
    )
    clubs = Club.query.filter_by(status='approved', is_archived=False).limit(4).all()
    recent_gallery = EventGallery.query.order_by(EventGallery.uploaded_at.desc()).limit(8).all()
    
    stats = {
        'total_events': Event.query.join(Club).filter(Event.status == 'published', Club.is_archived == False).count(),
        'total_clubs': Club.query.filter_by(status='approved', is_archived=False).count(),
        'total_students': User.query.filter_by(role='student').count(),
        'gallery_count': EventGallery.query.count()
    }
    
    return render_template('main/index.html', 
                           featured_events=featured_events, 
                           clubs=clubs, 
                           recent_gallery=recent_gallery,
                           stats=stats)


@main_bp.route('/events')
def events():
    search_query = request.args.get('search', '').strip()
    category_filter = request.args.get('category', '').strip()
    club_filter = request.args.get('club_id', type=int)

    query = Event.query.join(Club).filter(Event.status == 'published', Club.status == 'approved', Club.is_archived == False)

    if search_query:
        query = query.filter((Event.title.ilike(f'%{search_query}%')) | (Event.description.ilike(f'%{search_query}%')) | (Event.venue.ilike(f'%{search_query}%')))
    
    if category_filter:
        query = query.filter(Event.category == category_filter)

    if club_filter:
        query = query.filter(Event.club_id == club_filter)

    all_events = query.order_by(Event.event_date.asc()).all()
    clubs = Club.query.filter_by(status='approved', is_archived=False).all()
    categories = ['Technical', 'Cultural', 'Sports', 'Workshop', 'Seminar', 'Hackathon', 'General']

    return render_template('main/events.html', 
                           events=all_events, 
                           clubs=clubs, 
                           categories=categories,
                           search_query=search_query,
                           category_filter=category_filter,
                           club_filter=club_filter)


@main_bp.route('/events/<int:event_id>')
def event_detail(event_id):
    event = Event.query.get_or_404(event_id)
    if event.club and event.club.is_archived and not (current_user.is_authenticated and current_user.is_admin):
        abort(404)
    feedbacks = Feedback.query.filter_by(event_id=event.id).order_by(Feedback.submitted_at.desc()).all()
    gallery_images = EventGallery.query.filter_by(event_id=event.id).all()
    
    return render_template('main/event_detail.html', 
                           event=event, 
                           feedbacks=feedbacks, 
                           gallery_images=gallery_images)


@main_bp.route('/clubs')
def clubs():
    approved_clubs = Club.query.filter_by(status='approved', is_archived=False).order_by(Club.name.asc()).all()
    return render_template('main/clubs.html', clubs=approved_clubs)


@main_bp.route('/clubs/<int:club_id>')
def club_detail(club_id):
    club = Club.query.get_or_404(club_id)
    if (club.is_archived or club.status != 'approved') and not (current_user.is_authenticated and current_user.is_admin):
        abort(404)
    events = Event.query.filter_by(club_id=club.id, status='published').order_by(Event.event_date.asc()).all()
    return render_template('main/club_detail.html', club=club, events=events)


@main_bp.route('/gallery')
def gallery():
    images = EventGallery.query.order_by(EventGallery.uploaded_at.desc()).all()
    return render_template('main/gallery.html', images=images)
