from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, abort
from flask_login import login_required, current_user
from app import db
from app.models.event import Event
from app.models.club_membership import ClubMembership
from app.models.registration import Registration
from app.models.certificate import Certificate
from app.models.feedback import Feedback
from app.utils.decorators import role_required
from app.utils.certificate_gen import generate_certificate_pdf

student_bp = Blueprint('student', __name__)

@student_bp.route('/dashboard')
@login_required
@role_required('student', 'coordinator', 'admin')
def dashboard():
    registrations = Registration.query.filter_by(user_id=current_user.id).all()
    reg_event_ids = [r.event_id for r in registrations]

    upcoming_events = Event.query.filter(
        Event.id.in_(reg_event_ids),
        Event.event_date >= datetime.utcnow()
    ).order_by(Event.event_date.asc()).all() if reg_event_ids else []

    past_events = Event.query.filter(
        Event.id.in_(reg_event_ids),
        Event.event_date < datetime.utcnow()
    ).order_by(Event.event_date.desc()).all() if reg_event_ids else []

    certificates = Certificate.query.filter_by(user_id=current_user.id).order_by(Certificate.issued_at.desc()).all()
    memberships = ClubMembership.query.filter_by(user_id=current_user.id).all()

    return render_template('student/dashboard.html',
                           registrations=registrations,
                           upcoming_events=upcoming_events,
                           past_events=past_events,
                           certificates=certificates,
                           memberships=memberships)


@student_bp.route('/register/<int:event_id>', methods=['POST'])
@login_required
def register_event(event_id):
    event = Event.query.get_or_404(event_id)

    if event.status != 'published':
        flash('This event is not open for registration.', 'warning')
        return redirect(url_for('main.event_detail', event_id=event.id))

    if datetime.utcnow() > event.reg_deadline:
        flash('Registration deadline for this event has passed.', 'danger')
        return redirect(url_for('main.event_detail', event_id=event.id))

    if event.is_full:
        flash('Sorry, this event has reached maximum seating capacity.', 'danger')
        return redirect(url_for('main.event_detail', event_id=event.id))

    existing = Registration.query.filter_by(event_id=event.id, user_id=current_user.id).first()
    if existing:
        flash('You are already registered for this event.', 'info')
        return redirect(url_for('main.event_detail', event_id=event.id))

    new_reg = Registration(
        event_id=event.id,
        user_id=current_user.id
    )
    db.session.add(new_reg)
    db.session.commit()

    flash(f'Successfully registered for "{event.title}"!', 'success')
    return redirect(url_for('student.dashboard'))


@student_bp.route('/unregister/<int:event_id>', methods=['POST'])
@login_required
def unregister_event(event_id):
    reg = Registration.query.filter_by(event_id=event_id, user_id=current_user.id).first()
    if not reg:
        flash('Registration not found.', 'warning')
        return redirect(url_for('student.dashboard'))

    if reg.attended:
        flash('Cannot unregister after attendance has been recorded.', 'danger')
        return redirect(url_for('student.dashboard'))

    db.session.delete(reg)
    db.session.commit()

    flash('Successfully cancelled your registration.', 'success')
    return redirect(url_for('student.dashboard'))


@student_bp.route('/feedback/<int:event_id>', methods=['GET', 'POST'])
@login_required
def submit_feedback(event_id):
    event = Event.query.get_or_404(event_id)
    reg = Registration.query.filter_by(event_id=event.id, user_id=current_user.id).first()

    if not reg or not reg.attended:
        flash('Feedback can only be submitted by students who attended the event.', 'danger')
        return redirect(url_for('student.dashboard'))

    existing_feedback = Feedback.query.filter_by(event_id=event.id, user_id=current_user.id).first()

    if request.method == 'POST':
        rating = request.form.get('rating', type=int)
        comments = request.form.get('comments', '').strip()

        if not rating or not (1 <= rating <= 5):
            flash('Please select a star rating between 1 and 5.', 'danger')
            return render_template('student/feedback.html', event=event, existing=existing_feedback)

        if existing_feedback:
            existing_feedback.rating = rating
            existing_feedback.comments = comments
            flash('Your feedback has been updated.', 'success')
        else:
            new_feedback = Feedback(
                event_id=event.id,
                user_id=current_user.id,
                rating=rating,
                comments=comments
            )
            db.session.add(new_feedback)
            flash('Thank you! Your feedback has been submitted.', 'success')

        db.session.commit()
        return redirect(url_for('student.dashboard'))

    return render_template('student/feedback.html', event=event, existing=existing_feedback)


@student_bp.route('/certificates')
@login_required
def certificates():
    certs = Certificate.query.filter_by(user_id=current_user.id).order_by(Certificate.issued_at.desc()).all()
    return render_template('student/certificates.html', certificates=certs)


@student_bp.route('/certificates/<int:certificate_id>/download')
@login_required
def download_certificate(certificate_id):
    cert = Certificate.query.get_or_404(certificate_id)

    # Allow student recipient, admin, or the event's club coordinator to download
    is_event_coordinator = (
        current_user.is_coordinator
        and cert.event.club is not None
        and cert.event.club.coordinator_id == current_user.id
    )
    if cert.user_id != current_user.id and not current_user.is_admin and not is_event_coordinator:
        abort(403)

    cert.download_count += 1
    db.session.commit()

    student_name = cert.user.name
    event_title = cert.event.title
    club_name = cert.event.club.name
    event_date_str = cert.event.event_date.strftime('%B %d, %Y')
    certificate_uid = cert.certificate_uid

    pdf_buffer = generate_certificate_pdf(
        student_name=student_name,
        event_title=event_title,
        club_name=club_name,
        event_date_str=event_date_str,
        certificate_uid=certificate_uid
    )

    filename = f"Certificate_{cert.event.title.replace(' ', '_')}_{cert.certificate_uid[:8]}.pdf"

    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )
