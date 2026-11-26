from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import login_required, current_user
from app import db
from app.models.club import Club
from app.models.club_membership import ClubMembership
from app.models.user import User
from app.models.event import Event
from app.models.registration import Registration
from app.models.expense import Expense
from app.models.certificate import Certificate
from app.models.gallery import EventGallery
from app.models.feedback import Feedback
from app.utils.decorators import role_required
from app.utils.file_uploader import try_save_uploaded_file

coordinator_bp = Blueprint('coordinator', __name__)

def get_coordinator_club():
    """Helper to get the active club assigned to current logged-in coordinator."""
    return Club.query.filter_by(coordinator_id=current_user.id, status='approved', is_archived=False).first()


def get_authorized_event(event_id):
    """Fetch an event and verify the current user is an admin or its club coordinator."""
    event = Event.query.get_or_404(event_id)
    if not current_user.is_admin:
        if not event.club or event.club.is_archived or event.club.coordinator_id != current_user.id:
            abort(403)
    return event


@coordinator_bp.route('/dashboard')
@login_required
@role_required('coordinator', 'admin')
def dashboard():
    club = get_coordinator_club()
    
    if not club and not current_user.is_admin:
        return render_template('coordinator/no_club.html')

    events = Event.query.filter_by(club_id=club.id).order_by(Event.event_date.desc()).all() if club else []
    
    # Overview stats
    total_events = len(events)
    published_events = sum(1 for e in events if e.status == 'published')
    total_registrations = sum(e.registered_count for e in events)
    total_spent = sum(e.total_expense_amount for e in events)
    allocated_budget = float(club.allocated_budget) if club else 0.0

    return render_template('coordinator/dashboard.html',
                           club=club,
                           events=events,
                           total_events=total_events,
                           published_events=published_events,
                           total_registrations=total_registrations,
                           total_spent=total_spent,
                           allocated_budget=allocated_budget)


@coordinator_bp.route('/club-profile', methods=['GET', 'POST'])
@login_required
@role_required('coordinator', 'admin')
def club_profile():
    club = get_coordinator_club()
    if not club:
        flash('You have not been assigned to a club yet.', 'warning')
        return redirect(url_for('coordinator.dashboard'))

    if request.method == 'POST':
        new_name = request.form.get('name', '').strip()
        if not new_name:
            flash('Club name cannot be empty.', 'danger')
            return redirect(url_for('coordinator.club_profile'))

        duplicate_club = Club.query.filter(Club.name == new_name, Club.id != club.id).first()
        if duplicate_club:
            flash(f'Another club named "{new_name}" already exists.', 'danger')
            return redirect(url_for('coordinator.club_profile'))

        logo_url, upload_err = try_save_uploaded_file(request.files.get('logo'), folder_subpath='logos')
        if upload_err:
            flash(upload_err, 'danger')
            return redirect(url_for('coordinator.club_profile'))

        club.name = new_name
        club.description = request.form.get('description', '').strip()
        if logo_url:
            club.logo_url = logo_url

        db.session.commit()
        flash('Club profile updated successfully.', 'success')
        return redirect(url_for('coordinator.club_profile'))

    return render_template('coordinator/club_profile.html', club=club)


@coordinator_bp.route('/events/create', methods=['GET', 'POST'])
@login_required
@role_required('coordinator', 'admin')
def create_event():
    club = get_coordinator_club()
    if not club:
        flash('You need an assigned club to create events.', 'danger')
        return redirect(url_for('coordinator.dashboard'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        venue = request.form.get('venue', '').strip()
        category = request.form.get('category', 'General').strip()
        event_date_str = request.form.get('event_date')
        reg_deadline_str = request.form.get('reg_deadline')
        capacity = request.form.get('capacity', type=int, default=100)
        allocated_budget = request.form.get('allocated_budget', type=float, default=0.0)
        status = request.form.get('status', 'draft')

        if not title or not venue or not event_date_str or not reg_deadline_str:
            flash('Please fill in all required event details.', 'danger')
            return render_template('coordinator/create_event.html', club=club)

        try:
            event_date = datetime.strptime(event_date_str, '%Y-%m-%dT%H:%M')
            reg_deadline = datetime.strptime(reg_deadline_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid date/time format.', 'danger')
            return render_template('coordinator/create_event.html', club=club)

        if status not in ['draft', 'published']:
            status = 'draft'

        banner_image, upload_err = try_save_uploaded_file(request.files.get('banner'), folder_subpath='banners')
        if upload_err:
            flash(upload_err, 'danger')
            return render_template('coordinator/create_event.html', club=club)

        new_event = Event(
            club_id=club.id,
            title=title,
            description=description,
            venue=venue,
            category=category,
            event_date=event_date,
            reg_deadline=reg_deadline,
            capacity=capacity,
            allocated_budget=allocated_budget,
            status=status,
            banner_image=banner_image
        )

        db.session.add(new_event)
        db.session.commit()

        flash(f'Event "{title}" created successfully.', 'success')
        return redirect(url_for('coordinator.event_details', event_id=new_event.id))

    return render_template('coordinator/create_event.html', club=club)


@coordinator_bp.route('/events/<int:event_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('coordinator', 'admin')
def edit_event(event_id):
    event = get_authorized_event(event_id)

    if request.method == 'POST':
        banner_image, upload_err = try_save_uploaded_file(request.files.get('banner'), folder_subpath='banners')
        if upload_err:
            flash(upload_err, 'danger')
            return render_template('coordinator/edit_event.html', event=event)

        event.title = request.form.get('title', '').strip()
        event.description = request.form.get('description', '').strip()
        event.venue = request.form.get('venue', '').strip()
        event.category = request.form.get('category', 'General').strip()
        event.capacity = request.form.get('capacity', type=int, default=100)
        event.allocated_budget = request.form.get('allocated_budget', type=float, default=0.0)
        new_status = request.form.get('status', 'draft')
        if new_status in ['draft', 'published', 'completed', 'cancelled']:
            event.status = new_status

        event_date_str = request.form.get('event_date')
        reg_deadline_str = request.form.get('reg_deadline')
        
        if event_date_str:
            try:
                event.event_date = datetime.strptime(event_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                pass

        if reg_deadline_str:
            try:
                event.reg_deadline = datetime.strptime(reg_deadline_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                pass

        if banner_image:
            event.banner_image = banner_image

        db.session.commit()
        flash('Event details updated successfully.', 'success')
        return redirect(url_for('coordinator.event_details', event_id=event.id))

    return render_template('coordinator/edit_event.html', event=event)


@coordinator_bp.route('/events/<int:event_id>')
@login_required
@role_required('coordinator', 'admin')
def event_details(event_id):
    event = get_authorized_event(event_id)
    registrations = Registration.query.filter_by(event_id=event.id).order_by(Registration.registered_at.desc()).all()
    expenses = Expense.query.filter_by(event_id=event.id).order_by(Expense.created_at.desc()).all()
    gallery_images = EventGallery.query.filter_by(event_id=event.id).all()
    feedbacks = Feedback.query.filter_by(event_id=event.id).order_by(Feedback.submitted_at.desc()).all()
    certificates = Certificate.query.filter_by(event_id=event.id).all()

    cert_user_ids = {c.user_id for c in certificates}

    return render_template('coordinator/event_details.html',
                           event=event,
                           registrations=registrations,
                           expenses=expenses,
                           gallery_images=gallery_images,
                           feedbacks=feedbacks,
                           certificates=certificates,
                           cert_user_ids=cert_user_ids)


@coordinator_bp.route('/events/<int:event_id>/attendance', methods=['GET', 'POST'])
@login_required
@role_required('coordinator', 'admin')
def attendance(event_id):
    event = get_authorized_event(event_id)

    if request.method == 'POST':
        registration_id = request.form.get('registration_id', type=int)
        attended_status = request.form.get('attended') == 'true'

        registration = Registration.query.get_or_404(registration_id)
        if registration.event_id != event.id:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': 'Registration does not belong to this event.'}), 403
            abort(403)

        registration.attended = attended_status
        db.session.commit()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'attended': registration.attended})

        flash(f'Attendance status updated for {registration.user.name}.', 'success')
        return redirect(url_for('coordinator.attendance', event_id=event.id))

    registrations = Registration.query.filter_by(event_id=event.id).all()
    return render_template('coordinator/attendance.html', event=event, registrations=registrations)


@coordinator_bp.route('/events/<int:event_id>/expenses', methods=['GET', 'POST'])
@login_required
@role_required('coordinator', 'admin')
def expenses(event_id):
    event = get_authorized_event(event_id)

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        amount = request.form.get('amount', type=float, default=0.0)
        category = request.form.get('category', 'Miscellaneous').strip()

        if not title or amount is None or amount <= 0:
            flash('Valid title and amount are required.', 'danger')
            return redirect(url_for('coordinator.expenses', event_id=event.id))

        receipt_file, upload_err = try_save_uploaded_file(request.files.get('receipt'), folder_subpath='receipts')
        if upload_err:
            flash(upload_err, 'danger')
            return redirect(url_for('coordinator.expenses', event_id=event.id))

        new_expense = Expense(
            event_id=event.id,
            title=title,
            amount=amount,
            category=category,
            receipt_file=receipt_file,
            status='pending'
        )

        db.session.add(new_expense)
        db.session.commit()

        flash(f'Expense "{title}" of ${amount:,.2f} logged and submitted for audit approval.', 'success')
        return redirect(url_for('coordinator.expenses', event_id=event.id))

    expenses_list = Expense.query.filter_by(event_id=event.id).order_by(Expense.created_at.desc()).all()
    return render_template('coordinator/expenses.html', event=event, expenses=expenses_list)


@coordinator_bp.route('/events/<int:event_id>/gallery', methods=['GET', 'POST'])
@login_required
@role_required('coordinator', 'admin')
def gallery(event_id):
    event = get_authorized_event(event_id)

    if request.method == 'POST':
        caption = request.form.get('caption', '').strip()
        image_file = request.files.get('image')

        if image_file and image_file.filename != '':
            image_url, upload_err = try_save_uploaded_file(image_file, folder_subpath='gallery')
            if upload_err:
                flash(upload_err, 'danger')
            elif image_url:
                new_img = EventGallery(
                    event_id=event.id,
                    image_url=image_url,
                    caption=caption
                )
                db.session.add(new_img)
                db.session.commit()
                flash('Photo added to event gallery.', 'success')
        else:
            flash('Please select an image file to upload.', 'warning')

        return redirect(url_for('coordinator.gallery', event_id=event.id))

    images = EventGallery.query.filter_by(event_id=event.id).order_by(EventGallery.uploaded_at.desc()).all()
    return render_template('coordinator/gallery.html', event=event, gallery_images=images)


@coordinator_bp.route('/events/<int:event_id>/generate-certificates', methods=['POST'])
@login_required
@role_required('coordinator', 'admin')
def generate_certificates(event_id):
    event = get_authorized_event(event_id)
    target_user_id = request.form.get('user_id', type=int)

    if target_user_id:
        regs = Registration.query.filter_by(event_id=event.id, user_id=target_user_id, attended=True).all()
    else:
        regs = Registration.query.filter_by(event_id=event.id, attended=True).all()

    if not regs:
        flash('No attended participants eligible for certificate generation.', 'warning')
        return redirect(url_for('coordinator.event_details', event_id=event.id))

    issued_count = 0
    for reg in regs:
        existing = Certificate.query.filter_by(event_id=event.id, user_id=reg.user_id).first()
        if not existing:
            new_cert = Certificate(event_id=event.id, user_id=reg.user_id)
            db.session.add(new_cert)
            issued_count += 1

    db.session.commit()
    flash(f'Issued certificates for {issued_count} attended participant(s).', 'success')
    return redirect(url_for('coordinator.event_details', event_id=event.id))


@coordinator_bp.route('/members', methods=['GET', 'POST'])
@login_required
@role_required('coordinator', 'admin')
def members():
    club = get_coordinator_club()
    if not club:
        flash('You have not been assigned to an active club yet.', 'warning')
        return redirect(url_for('coordinator.dashboard'))

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add':
            user_id = request.form.get('user_id', type=int)
            member_role = request.form.get('member_role', 'Member').strip() or 'Member'
            user = User.query.get_or_404(user_id)
            if not user.is_active:
                flash('Cannot add an inactive user to the club.', 'warning')
                return redirect(url_for('coordinator.members'))

            existing = ClubMembership.query.filter_by(club_id=club.id, user_id=user.id).first()
            if existing:
                flash(f'{user.name} is already a member of {club.name}.', 'info')
                return redirect(url_for('coordinator.members'))

            db.session.add(ClubMembership(club_id=club.id, user_id=user.id, member_role=member_role))
            db.session.commit()
            flash(f'Added {user.name} to {club.name}.', 'success')

        elif action == 'remove':
            membership_id = request.form.get('membership_id', type=int)
            membership = ClubMembership.query.get_or_404(membership_id)
            if membership.club_id != club.id:
                abort(403)
            member_name = membership.user.name
            db.session.delete(membership)
            db.session.commit()
            flash(f'Removed {member_name} from {club.name}.', 'info')

        elif action == 'update_role':
            membership_id = request.form.get('membership_id', type=int)
            member_role = request.form.get('member_role', 'Member').strip() or 'Member'
            membership = ClubMembership.query.get_or_404(membership_id)
            if membership.club_id != club.id:
                abort(403)
            membership.member_role = member_role
            db.session.commit()
            flash(f'Updated club role for {membership.user.name}.', 'success')

        return redirect(url_for('coordinator.members'))

    memberships = ClubMembership.query.filter_by(club_id=club.id).order_by(ClubMembership.joined_at.desc()).all()
    existing_ids = {m.user_id for m in memberships}
    available_users = User.query.filter(User.is_active == True, ~User.id.in_(existing_ids) if existing_ids else True).order_by(User.name.asc()).all()
    return render_template('coordinator/members.html', club=club, memberships=memberships, available_users=available_users)
