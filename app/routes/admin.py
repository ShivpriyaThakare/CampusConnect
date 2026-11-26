import secrets
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from app import db
from app.models.user import User
from app.models.club import Club
from app.models.club_membership import ClubMembership
from app.models.event import Event
from app.models.expense import Expense
from app.models.registration import Registration
from app.models.gallery import EventGallery
from app.utils.decorators import role_required
from app.utils.file_uploader import try_save_uploaded_file

admin_bp = Blueprint('admin', __name__)

CLUB_CATEGORIES = ['Technical', 'Cultural', 'Sports', 'Academic', 'Arts & Media', 'Community', 'General']
EVENT_CATEGORIES = ['Technical', 'Cultural', 'Sports', 'Workshop', 'Seminar', 'Hackathon', 'General']
MEMBER_ROLES = ['Member', 'Lead', 'Secretary', 'Treasurer']


def _assign_club_coordinator(club, coordinator_id):
    """
    Assign or replace a club's coordinator.
    Promotes a student to 'coordinator' role when assigned; preserves admin role.
    Returns (success: bool, message: str).
    """
    if not coordinator_id:
        club.coordinator_id = None
        return True, f'Removed coordinator assignment from "{club.name}".'

    user = db.session.get(User, coordinator_id)
    if not user:
        return False, 'Selected user does not exist.'
    if not user.is_active:
        return False, f'Cannot assign inactive user "{user.name}" as coordinator.'

    if user.role == 'student':
        user.role = 'coordinator'

    club.coordinator_id = user.id
    return True, f'Assigned {user.name} as coordinator for "{club.name}".'


def _add_club_membership(club_id, user_id, member_role='Member'):
    """Create a ClubMembership safely, preventing duplicates."""
    club = db.session.get(Club, club_id)
    user = db.session.get(User, user_id)
    if not club or not user:
        return False, 'Selected club or user does not exist.'
    if club.is_archived:
        return False, f'Cannot add members to archived club "{club.name}".'

    existing = ClubMembership.query.filter_by(club_id=club.id, user_id=user.id).first()
    if existing:
        return False, f'{user.name} is already a member of "{club.name}".'

    membership = ClubMembership(
        club_id=club.id,
        user_id=user.id,
        member_role=member_role or 'Member'
    )
    db.session.add(membership)
    return True, f'Added {user.name} to "{club.name}".'


@admin_bp.route('/dashboard')
@login_required
@role_required('admin')
def dashboard():
    total_users = User.query.count()
    total_students = User.query.filter_by(role='student').count()
    total_coordinators = User.query.filter_by(role='coordinator').count()
    total_clubs = Club.query.filter_by(is_archived=False).count()
    archived_clubs_count = Club.query.filter_by(is_archived=True).count()
    total_events = Event.query.count()
    total_registrations = Registration.query.count()
    total_memberships = ClubMembership.query.count()

    # Financial Audits Summary
    total_allocated_budget = float(
        db.session.query(db.func.sum(Club.allocated_budget)).filter(Club.is_archived == False).scalar() or 0.0
    )
    total_spent_expenses = float(
        db.session.query(db.func.sum(Expense.amount)).filter(Expense.status == 'approved').scalar() or 0.0
    )
    pending_expenses_count = Expense.query.filter_by(status='pending').count()
    pending_clubs_count = Club.query.filter_by(status='pending', is_archived=False).count()

    recent_events = Event.query.order_by(Event.created_at.desc()).limit(5).all()
    pending_expenses = Expense.query.filter_by(status='pending').order_by(Expense.created_at.desc()).limit(5).all()
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()

    return render_template(
        'admin/dashboard.html',
        total_users=total_users,
        total_students=total_students,
        total_coordinators=total_coordinators,
        total_clubs=total_clubs,
        archived_clubs_count=archived_clubs_count,
        total_events=total_events,
        total_registrations=total_registrations,
        total_memberships=total_memberships,
        total_allocated_budget=total_allocated_budget,
        total_spent_expenses=total_spent_expenses,
        pending_expenses_count=pending_expenses_count,
        pending_clubs_count=pending_clubs_count,
        recent_events=recent_events,
        pending_expenses=pending_expenses,
        recent_users=recent_users
    )


# ---------------------------------------------------------------------------
# Club Management (Create, View, Edit, Archive/Restore, Approve/Reject)
# ---------------------------------------------------------------------------

@admin_bp.route('/clubs', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def clubs():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'create':
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            category = request.form.get('category', 'General').strip() or 'General'
            contact_info = request.form.get('contact_info', '').strip()
            coordinator_id = request.form.get('coordinator_id', type=int)
            allocated_budget = request.form.get('allocated_budget', type=float, default=0.0)

            if not name:
                flash('Club name is required.', 'danger')
                return redirect(url_for('admin.clubs'))

            if Club.query.filter_by(name=name).first():
                flash(f'A club named "{name}" already exists.', 'danger')
                return redirect(url_for('admin.clubs'))

            if allocated_budget is None or allocated_budget < 0:
                allocated_budget = 0.0

            logo_url, upload_err = try_save_uploaded_file(request.files.get('logo'), folder_subpath='logos')
            if upload_err:
                flash(upload_err, 'danger')
                return redirect(url_for('admin.clubs'))

            new_club = Club(
                name=name,
                description=description,
                category=category,
                contact_info=contact_info or None,
                allocated_budget=allocated_budget,
                status='approved',
                is_archived=False,
                logo_url=logo_url
            )
            if coordinator_id:
                ok, msg = _assign_club_coordinator(new_club, coordinator_id)
                if not ok:
                    flash(msg, 'danger')
                    return redirect(url_for('admin.clubs'))

            try:
                db.session.add(new_club)
                db.session.commit()
                flash(f'Club "{name}" created successfully and published to the Clubs directory.', 'success')
            except IntegrityError:
                db.session.rollback()
                flash('Could not create club due to a database constraint.', 'danger')

        elif action == 'edit':
            club_id = request.form.get('club_id', type=int)
            club = Club.query.get_or_404(club_id)
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            category = request.form.get('category', 'General').strip() or 'General'
            contact_info = request.form.get('contact_info', '').strip()
            coordinator_id = request.form.get('coordinator_id', type=int)
            allocated_budget = request.form.get('allocated_budget', type=float, default=0.0)
            status = request.form.get('status', club.status)

            if not name:
                flash('Club name cannot be empty.', 'danger')
                return redirect(url_for('admin.clubs'))

            duplicate = Club.query.filter(Club.name == name, Club.id != club.id).first()
            if duplicate:
                flash(f'Another club named "{name}" already exists.', 'danger')
                return redirect(url_for('admin.clubs'))

            logo_url, upload_err = try_save_uploaded_file(request.files.get('logo'), folder_subpath='logos')
            if upload_err:
                flash(upload_err, 'danger')
                return redirect(url_for('admin.clubs'))

            club.name = name
            club.description = description
            club.category = category
            club.contact_info = contact_info or None
            if allocated_budget is not None and allocated_budget >= 0:
                club.allocated_budget = allocated_budget
            if status in ['pending', 'approved', 'rejected']:
                club.status = status
            if logo_url:
                club.logo_url = logo_url

            ok, msg = _assign_club_coordinator(club, coordinator_id)
            if not ok:
                flash(msg, 'danger')
                return redirect(url_for('admin.clubs'))

            db.session.commit()
            flash(f'Club "{club.name}" updated successfully.', 'success')

        elif action in ['archive', 'delete']:
            club_id = request.form.get('club_id', type=int)
            club = Club.query.get_or_404(club_id)
            club.is_archived = True
            db.session.commit()
            flash(f'Club "{club.name}" has been archived. Historical events, registrations, and expenses were preserved.', 'info')

        elif action == 'restore':
            club_id = request.form.get('club_id', type=int)
            club = Club.query.get_or_404(club_id)
            club.is_archived = False
            db.session.commit()
            flash(f'Club "{club.name}" has been restored.', 'success')

        elif action == 'approve':
            club_id = request.form.get('club_id', type=int)
            club = Club.query.get_or_404(club_id)
            club.status = 'approved'
            db.session.commit()
            flash(f'Club "{club.name}" approved.', 'success')

        elif action == 'reject':
            club_id = request.form.get('club_id', type=int)
            club = Club.query.get_or_404(club_id)
            club.status = 'rejected'
            db.session.commit()
            flash(f'Club "{club.name}" rejected.', 'warning')

        elif action == 'edit_budget':
            club_id = request.form.get('club_id', type=int)
            new_budget = request.form.get('allocated_budget', type=float, default=0.0)
            if new_budget is None or new_budget < 0:
                flash('Allocated budget must be a non-negative number.', 'danger')
                return redirect(url_for('admin.clubs'))
            club = Club.query.get_or_404(club_id)
            club.allocated_budget = new_budget
            db.session.commit()
            flash(f'Budget for "{club.name}" updated to ${new_budget:,.2f}.', 'success')

        return redirect(url_for('admin.clubs'))

    search_query = request.args.get('search', '').strip()
    category_filter = request.args.get('category', '').strip()
    status_filter = request.args.get('status', 'active').strip()

    query = Club.query
    if status_filter == 'archived':
        query = query.filter(Club.is_archived == True)
    elif status_filter == 'all':
        pass
    elif status_filter in ['pending', 'approved', 'rejected']:
        query = query.filter(Club.is_archived == False, Club.status == status_filter)
    else:
        query = query.filter(Club.is_archived == False)

    if search_query:
        query = query.filter(
            (Club.name.ilike(f'%{search_query}%')) |
            (Club.description.ilike(f'%{search_query}%')) |
            (Club.contact_info.ilike(f'%{search_query}%'))
        )
    if category_filter:
        query = query.filter(Club.category == category_filter)

    all_clubs = query.order_by(Club.created_at.desc()).all()
    eligible_coordinators = User.query.filter_by(is_active=True).order_by(User.name.asc()).all()

    return render_template(
        'admin/clubs.html',
        clubs=all_clubs,
        coordinators=eligible_coordinators,
        categories=CLUB_CATEGORIES,
        search_query=search_query,
        category_filter=category_filter,
        status_filter=status_filter
    )


@admin_bp.route('/clubs/<int:club_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def club_detail(club_id):
    club = Club.query.get_or_404(club_id)

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'assign_coordinator':
            coordinator_id = request.form.get('coordinator_id', type=int)
            ok, msg = _assign_club_coordinator(club, coordinator_id)
            if ok:
                db.session.commit()
                flash(msg, 'success')
            else:
                flash(msg, 'danger')

        elif action == 'remove_coordinator':
            club.coordinator_id = None
            db.session.commit()
            flash(f'Removed coordinator from "{club.name}".', 'info')

        elif action == 'add_member':
            user_id = request.form.get('user_id', type=int)
            member_role = request.form.get('member_role', 'Member').strip() or 'Member'
            ok, msg = _add_club_membership(club.id, user_id, member_role)
            if ok:
                db.session.commit()
                flash(msg, 'success')
            else:
                flash(msg, 'warning')

        elif action == 'remove_member':
            membership_id = request.form.get('membership_id', type=int)
            membership = ClubMembership.query.get_or_404(membership_id)
            if membership.club_id == club.id:
                name = membership.user.name
                db.session.delete(membership)
                db.session.commit()
                flash(f'Removed {name} from "{club.name}".', 'info')

        return redirect(url_for('admin.club_detail', club_id=club.id))

    memberships = ClubMembership.query.filter_by(club_id=club.id).order_by(ClubMembership.joined_at.desc()).all()
    events = Event.query.filter_by(club_id=club.id).order_by(Event.event_date.desc()).all()
    member_user_ids = {m.user_id for m in memberships}
    available_users = User.query.filter(
        User.is_active == True,
        ~User.id.in_(member_user_ids) if member_user_ids else True
    ).order_by(User.name.asc()).all()
    all_active_users = User.query.filter_by(is_active=True).order_by(User.name.asc()).all()

    return render_template(
        'admin/club_detail.html',
        club=club,
        memberships=memberships,
        events=events,
        available_users=available_users,
        all_active_users=all_active_users,
        member_roles=MEMBER_ROLES,
        categories=CLUB_CATEGORIES
    )


# ---------------------------------------------------------------------------
# Club Coordinator Assignments
# ---------------------------------------------------------------------------

@admin_bp.route('/coordinators', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def coordinators():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'assign':
            coordinator_id = request.form.get('coordinator_id', type=int)
            club_id = request.form.get('club_id', type=int)
            club = Club.query.get_or_404(club_id)
            ok, msg = _assign_club_coordinator(club, coordinator_id)
            if ok:
                db.session.commit()
                flash(msg, 'success')
            else:
                flash(msg, 'danger')

        elif action == 'remove_coordinator':
            club_id = request.form.get('club_id', type=int)
            club = Club.query.get_or_404(club_id)
            club.coordinator_id = None
            db.session.commit()
            flash(f'Removed coordinator from "{club.name}".', 'info')

        elif action == 'create':
            name = request.form.get('name', '').strip()
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            club_id = request.form.get('club_id', type=int)

            if not name or not email or not password:
                flash('All fields are required.', 'danger')
                return redirect(url_for('admin.coordinators'))

            if User.query.filter_by(email=email).first():
                flash('Email already registered.', 'danger')
                return redirect(url_for('admin.coordinators'))

            new_user = User(name=name, email=email, role='coordinator')
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.flush()

            if club_id:
                club = db.session.get(Club, club_id)
                if club:
                    club.coordinator_id = new_user.id

            db.session.commit()
            flash(f'Coordinator account for "{name}" created.', 'success')

        return redirect(url_for('admin.coordinators'))

    coordinators_list = User.query.filter_by(role='coordinator').order_by(User.name.asc()).all()
    eligible_users = User.query.filter_by(is_active=True).order_by(User.name.asc()).all()
    clubs_list = Club.query.filter_by(is_archived=False).order_by(Club.name.asc()).all()
    return render_template(
        'admin/coordinators.html',
        coordinators=coordinators_list,
        eligible_users=eligible_users,
        clubs=clubs_list
    )


# ---------------------------------------------------------------------------
# Member & User Management
# ---------------------------------------------------------------------------

@admin_bp.route('/users', methods=['GET', 'POST'])
@admin_bp.route('/members', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def users():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add_member':
            mode = request.form.get('mode', 'new')
            club_id = request.form.get('club_id', type=int)
            member_role = request.form.get('member_role', 'Member').strip() or 'Member'

            if mode == 'existing':
                existing_user_id = request.form.get('existing_user_id', type=int)
                if not existing_user_id or not club_id:
                    flash('Please select both a user and a club.', 'danger')
                    return redirect(url_for('admin.users'))
                ok, msg = _add_club_membership(club_id, existing_user_id, member_role)
                if ok:
                    db.session.commit()
                    flash(msg, 'success')
                else:
                    flash(msg, 'warning')
                return redirect(url_for('admin.users'))

            name = request.form.get('name', '').strip()
            email = request.form.get('email', '').strip().lower()
            role = request.form.get('role', 'student')
            password = request.form.get('password', '')

            if not name or not email:
                flash('Name and email are required.', 'danger')
                return redirect(url_for('admin.users'))

            if role not in ['admin', 'coordinator', 'student']:
                role = 'student'

            if User.query.filter_by(email=email).first():
                flash('An account with this email already exists.', 'danger')
                return redirect(url_for('admin.users'))

            if password and len(password) < 6:
                flash('Password must be at least 6 characters long.', 'danger')
                return redirect(url_for('admin.users'))

            generated_invite = False
            if not password:
                password = secrets.token_urlsafe(12)
                generated_invite = True

            new_user = User(name=name, email=email, role=role, is_active=True)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.flush()

            if club_id:
                ok, msg = _add_club_membership(club_id, new_user.id, member_role)
                if not ok:
                    db.session.rollback()
                    flash(msg, 'danger')
                    return redirect(url_for('admin.users'))

            db.session.commit()
            if generated_invite:
                flash(f'Member "{name}" created with a secure random password.', 'success')
            else:
                flash(f'Member "{name}" added successfully.', 'success')
            return redirect(url_for('admin.users'))

        if action == 'edit_member':
            user_id = request.form.get('user_id', type=int)
            user = User.query.get_or_404(user_id)
            name = request.form.get('name', '').strip()
            email = request.form.get('email', '').strip().lower()
            new_role = request.form.get('role', user.role)
            is_active = request.form.get('is_active') == 'true'
            club_id = request.form.get('club_id', type=int)
            member_role = request.form.get('member_role', 'Member').strip() or 'Member'

            if not name or not email:
                flash('Name and email are required.', 'danger')
                return redirect(url_for('admin.users'))

            dup = User.query.filter(User.email == email, User.id != user.id).first()
            if dup:
                flash('Another user already uses that email address.', 'danger')
                return redirect(url_for('admin.users'))

            if user.id == current_user.id and not is_active:
                flash('You cannot deactivate your own admin account.', 'warning')
                return redirect(url_for('admin.users'))

            user.name = name
            user.email = email
            if new_role in ['admin', 'coordinator', 'student']:
                user.role = new_role
            user.is_active = is_active

            if club_id:
                existing = ClubMembership.query.filter_by(club_id=club_id, user_id=user.id).first()
                if not existing:
                    db.session.add(ClubMembership(club_id=club_id, user_id=user.id, member_role=member_role))
                else:
                    existing.member_role = member_role

            db.session.commit()
            flash(f'Updated member details for "{user.name}".', 'success')
            return redirect(url_for('admin.users'))

        if action == 'assign_to_club':
            user_id = request.form.get('user_id', type=int)
            club_id = request.form.get('club_id', type=int)
            member_role = request.form.get('member_role', 'Member').strip() or 'Member'
            ok, msg = _add_club_membership(club_id, user_id, member_role)
            if ok:
                db.session.commit()
                flash(msg, 'success')
            else:
                flash(msg, 'warning')
            return redirect(url_for('admin.users'))

        if action == 'remove_from_club':
            membership_id = request.form.get('membership_id', type=int)
            membership = ClubMembership.query.get_or_404(membership_id)
            member_name = membership.user.name
            club_name = membership.club.name
            db.session.delete(membership)
            db.session.commit()
            flash(f'Removed {member_name} from "{club_name}".', 'info')
            return redirect(url_for('admin.users'))

        if action == 'delete_member':
            user_id = request.form.get('user_id', type=int)
            user = User.query.get_or_404(user_id)
            if user.id == current_user.id:
                flash('You cannot delete your own currently logged-in account.', 'danger')
                return redirect(url_for('admin.users'))
            name = user.name
            db.session.delete(user)
            db.session.commit()
            flash(f'Removed user "{name}" from the system.', 'info')
            return redirect(url_for('admin.users'))

        user_id = request.form.get('user_id', type=int)
        user = User.query.get_or_404(user_id)

        if action == 'toggle_status':
            if user.id == current_user.id:
                flash('You cannot deactivate your own account.', 'warning')
                return redirect(url_for('admin.users'))
            user.is_active = not user.is_active
            db.session.commit()
            status_str = "activated" if user.is_active else "deactivated"
            flash(f'User "{user.name}" {status_str}.', 'info')

        elif action == 'change_role':
            new_role = request.form.get('role')
            if new_role in ['admin', 'coordinator', 'student']:
                user.role = new_role
                db.session.commit()
                flash(f'User "{user.name}" role updated to {new_role}.', 'success')

        return redirect(url_for('admin.users'))

    search_query = request.args.get('search', '').strip()
    role_filter = request.args.get('role', '').strip()
    club_filter = request.args.get('club_id', type=int)

    query = User.query
    if search_query:
        query = query.filter(
            (User.name.ilike(f'%{search_query}%')) |
            (User.email.ilike(f'%{search_query}%'))
        )
    if role_filter:
        query = query.filter(User.role == role_filter)
    if club_filter:
        query = query.join(ClubMembership).filter(ClubMembership.club_id == club_filter)

    all_users = query.order_by(User.created_at.desc()).all()
    clubs_list = Club.query.filter_by(is_archived=False).order_by(Club.name.asc()).all()

    return render_template(
        'admin/users.html',
        users=all_users,
        clubs=clubs_list,
        member_roles=MEMBER_ROLES,
        role_filter=role_filter,
        club_filter=club_filter,
        search_query=search_query
    )


# ---------------------------------------------------------------------------
# Platform-Wide Event, Registration, Gallery & Budget Audit Management
# ---------------------------------------------------------------------------

@admin_bp.route('/events', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def events():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'create':
            club_id = request.form.get('club_id', type=int)
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            venue = request.form.get('venue', '').strip()
            category = request.form.get('category', 'General').strip() or 'General'
            event_date_str = request.form.get('event_date')
            reg_deadline_str = request.form.get('reg_deadline')
            capacity = request.form.get('capacity', type=int, default=100)
            allocated_budget = request.form.get('allocated_budget', type=float, default=0.0)
            status = request.form.get('status', 'published')

            club = db.session.get(Club, club_id) if club_id else None
            if not club or not title or not venue or not event_date_str or not reg_deadline_str:
                flash('Club, title, venue, and schedule dates are required.', 'danger')
                return redirect(url_for('admin.events'))

            try:
                event_date = datetime.strptime(event_date_str, '%Y-%m-%dT%H:%M')
                reg_deadline = datetime.strptime(reg_deadline_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('Invalid date/time format.', 'danger')
                return redirect(url_for('admin.events'))

            if status not in ['draft', 'published', 'completed', 'cancelled']:
                status = 'published'

            new_event = Event(
                club_id=club.id,
                title=title,
                description=description,
                venue=venue,
                category=category,
                event_date=event_date,
                reg_deadline=reg_deadline,
                capacity=max(1, capacity or 100),
                allocated_budget=max(0.0, allocated_budget or 0.0),
                status=status
            )
            db.session.add(new_event)
            db.session.commit()
            flash(f'Event "{title}" created under "{club.name}".', 'success')

        elif action == 'update_status':
            event_id = request.form.get('event_id', type=int)
            new_status = request.form.get('status')
            ev = Event.query.get_or_404(event_id)
            if new_status in ['draft', 'published', 'completed', 'cancelled']:
                ev.status = new_status
                db.session.commit()
                flash(f'Event "{ev.title}" status updated to {new_status}.', 'success')

        elif action == 'delete':
            event_id = request.form.get('event_id', type=int)
            ev = Event.query.get_or_404(event_id)
            title = ev.title
            db.session.delete(ev)
            db.session.commit()
            flash(f'Deleted event "{title}".', 'info')

        return redirect(url_for('admin.events'))

    search_query = request.args.get('search', '').strip()
    club_filter = request.args.get('club_id', type=int)
    status_filter = request.args.get('status', '').strip()

    query = Event.query.join(Club)
    if search_query:
        query = query.filter((Event.title.ilike(f'%{search_query}%')) | (Event.venue.ilike(f'%{search_query}%')))
    if club_filter:
        query = query.filter(Event.club_id == club_filter)
    if status_filter:
        query = query.filter(Event.status == status_filter)

    all_events = query.order_by(Event.event_date.desc()).all()
    clubs_list = Club.query.filter_by(is_archived=False).order_by(Club.name.asc()).all()

    return render_template(
        'admin/events.html',
        events=all_events,
        clubs=clubs_list,
        categories=EVENT_CATEGORIES,
        search_query=search_query,
        club_filter=club_filter,
        status_filter=status_filter
    )


@admin_bp.route('/registrations', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def registrations():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add':
            event_id = request.form.get('event_id', type=int)
            user_id = request.form.get('user_id', type=int)
            ev = Event.query.get_or_404(event_id)
            user = User.query.get_or_404(user_id)
            if Registration.query.filter_by(event_id=ev.id, user_id=user.id).first():
                flash(f'{user.name} is already registered for "{ev.title}".', 'info')
            else:
                db.session.add(Registration(event_id=ev.id, user_id=user.id))
                db.session.commit()
                flash(f'Registered {user.name} for "{ev.title}".', 'success')

        elif action == 'toggle_attendance':
            reg_id = request.form.get('registration_id', type=int)
            reg = Registration.query.get_or_404(reg_id)
            reg.attended = not reg.attended
            db.session.commit()
            flash(f'Updated attendance for {reg.user.name}.', 'success')

        elif action == 'remove':
            reg_id = request.form.get('registration_id', type=int)
            reg = Registration.query.get_or_404(reg_id)
            name = reg.user.name
            db.session.delete(reg)
            db.session.commit()
            flash(f'Removed registration for {name}.', 'info')

        return redirect(url_for('admin.registrations'))

    event_filter = request.args.get('event_id', type=int)
    search_query = request.args.get('search', '').strip()

    query = Registration.query.join(User).join(Event)
    if event_filter:
        query = query.filter(Registration.event_id == event_filter)
    if search_query:
        query = query.filter((User.name.ilike(f'%{search_query}%')) | (User.email.ilike(f'%{search_query}%')))

    regs = query.order_by(Registration.registered_at.desc()).all()
    events_list = Event.query.order_by(Event.event_date.desc()).all()
    users_list = User.query.filter_by(is_active=True).order_by(User.name.asc()).all()

    return render_template(
        'admin/registrations.html',
        registrations=regs,
        events=events_list,
        users=users_list,
        event_filter=event_filter,
        search_query=search_query
    )


@admin_bp.route('/gallery', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def gallery():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'upload':
            event_id = request.form.get('event_id', type=int)
            caption = request.form.get('caption', '').strip()
            ev = Event.query.get_or_404(event_id)
            image_file = request.files.get('image')

            if not image_file or image_file.filename == '':
                flash('Please select an image file to upload.', 'warning')
                return redirect(url_for('admin.gallery'))

            image_url, upload_err = try_save_uploaded_file(image_file, folder_subpath='gallery')
            if upload_err:
                flash(upload_err, 'danger')
                return redirect(url_for('admin.gallery'))

            db.session.add(EventGallery(event_id=ev.id, image_url=image_url, caption=caption))
            db.session.commit()
            flash(f'Photo uploaded to "{ev.title}".', 'success')

        elif action == 'delete':
            image_id = request.form.get('image_id', type=int)
            img = EventGallery.query.get_or_404(image_id)
            db.session.delete(img)
            db.session.commit()
            flash('Gallery photo deleted.', 'info')

        return redirect(url_for('admin.gallery'))

    event_filter = request.args.get('event_id', type=int)
    query = EventGallery.query
    if event_filter:
        query = query.filter(EventGallery.event_id == event_filter)
    images = query.order_by(EventGallery.uploaded_at.desc()).all()
    events_list = Event.query.order_by(Event.event_date.desc()).all()

    return render_template(
        'admin/gallery.html',
        images=images,
        events=events_list,
        event_filter=event_filter
    )


@admin_bp.route('/budget-audits', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def budget_audits():
    if request.method == 'POST':
        expense_id = request.form.get('expense_id', type=int)
        status = request.form.get('status')  # approved / rejected
        expense = Expense.query.get_or_404(expense_id)

        if status in ['approved', 'rejected']:
            expense.status = status
            db.session.commit()
            flash(f'Expense "{expense.title}" status changed to {status}.', 'success')

        return redirect(url_for('admin.budget_audits'))

    club_filter = request.args.get('club_id', type=int)
    status_filter = request.args.get('status', '').strip()

    query = Expense.query.join(Event).join(Club)

    if club_filter:
        query = query.filter(Event.club_id == club_filter)

    if status_filter:
        query = query.filter(Expense.status == status_filter)

    all_expenses = query.order_by(Expense.created_at.desc()).all()
    clubs_list = Club.query.filter_by(status='approved', is_archived=False).all()

    # Budget summary per club
    club_budgets = []
    for club in clubs_list:
        total_spent = sum(e.total_expense_amount for e in club.events)
        approved_spent = sum(
            sum(float(exp.amount) for exp in e.expenses if exp.status == 'approved')
            for e in club.events
        )
        club_budgets.append({
            'club': club,
            'allocated': float(club.allocated_budget),
            'total_spent': total_spent,
            'approved_spent': approved_spent,
            'remaining': float(club.allocated_budget) - approved_spent
        })

    return render_template(
        'admin/budget_audits.html',
        expenses=all_expenses,
        clubs=clubs_list,
        club_budgets=club_budgets,
        club_filter=club_filter,
        status_filter=status_filter
    )


# ---------------------------------------------------------------------------
# Admin JSON REST API Endpoints (Full CRUD for Clubs, Members & Assignments)
# ---------------------------------------------------------------------------

@admin_bp.route('/api/stats', methods=['GET'])
@login_required
@role_required('admin')
def api_stats():
    return jsonify({
        'total_users': User.query.count(),
        'total_clubs': Club.query.filter_by(is_archived=False).count(),
        'archived_clubs': Club.query.filter_by(is_archived=True).count(),
        'total_events': Event.query.count(),
        'total_coordinators': User.query.filter_by(role='coordinator').count(),
        'total_registrations': Registration.query.count(),
        'total_memberships': ClubMembership.query.count(),
        'pending_expenses': Expense.query.filter_by(status='pending').count(),
    })


@admin_bp.route('/api/clubs', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def api_clubs():
    if request.method == 'GET':
        include_archived = request.args.get('include_archived') == 'true'
        q = Club.query if include_archived else Club.query.filter_by(is_archived=False)
        clubs_list = q.order_by(Club.created_at.desc()).all()
        return jsonify([
            {
                'id': c.id,
                'name': c.name,
                'description': c.description,
                'category': c.category,
                'contact_info': c.contact_info,
                'coordinator_id': c.coordinator_id,
                'coordinator_name': c.coordinator.name if c.coordinator else None,
                'status': c.status,
                'is_archived': c.is_archived,
                'allocated_budget': float(c.allocated_budget),
                'member_count': c.member_count,
                'event_count': c.event_count,
            }
            for c in clubs_list
        ])

    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'Club name is required.'}), 400
    if Club.query.filter_by(name=name).first():
        return jsonify({'error': f'Club "{name}" already exists.'}), 409

    club = Club(
        name=name,
        description=(data.get('description') or '').strip(),
        category=(data.get('category') or 'General').strip() or 'General',
        contact_info=(data.get('contact_info') or '').strip() or None,
        allocated_budget=max(0.0, float(data.get('allocated_budget') or 0.0)),
        status='approved',
        is_archived=False
    )
    if data.get('coordinator_id'):
        ok, msg = _assign_club_coordinator(club, int(data['coordinator_id']))
        if not ok:
            return jsonify({'error': msg}), 400

    db.session.add(club)
    db.session.commit()
    return jsonify({'id': club.id, 'name': club.name, 'status': club.status}), 201


@admin_bp.route('/api/clubs/<int:club_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
@role_required('admin')
def api_club_item(club_id):
    club = Club.query.get_or_404(club_id)
    if request.method == 'GET':
        return jsonify({
            'id': club.id,
            'name': club.name,
            'description': club.description,
            'category': club.category,
            'contact_info': club.contact_info,
            'coordinator_id': club.coordinator_id,
            'is_archived': club.is_archived,
            'member_count': club.member_count,
            'event_count': club.event_count,
        })

    if request.method == 'DELETE':
        club.is_archived = True
        db.session.commit()
        return jsonify({'archived': True, 'id': club.id})

    data = request.get_json(silent=True) or {}
    if 'name' in data and data['name']:
        new_name = data['name'].strip()
        if Club.query.filter(Club.name == new_name, Club.id != club.id).first():
            return jsonify({'error': f'Club "{new_name}" already exists.'}), 409
        club.name = new_name
    if 'description' in data:
        club.description = (data['description'] or '').strip()
    if 'category' in data and data['category']:
        club.category = data['category'].strip()
    if 'contact_info' in data:
        club.contact_info = (data['contact_info'] or '').strip() or None
    if 'coordinator_id' in data:
        ok, msg = _assign_club_coordinator(club, data['coordinator_id'])
        if not ok:
            return jsonify({'error': msg}), 400
    db.session.commit()
    return jsonify({'updated': True, 'id': club.id})


@admin_bp.route('/api/members', methods=['GET', 'POST', 'DELETE'])
@login_required
@role_required('admin')
def api_members():
    if request.method == 'GET':
        memberships = ClubMembership.query.all()
        return jsonify([
            {
                'id': m.id,
                'club_id': m.club_id,
                'club_name': m.club.name,
                'user_id': m.user_id,
                'user_name': m.user.name,
                'user_email': m.user.email,
                'member_role': m.member_role,
            }
            for m in memberships
        ])

    data = request.get_json(silent=True) or {}
    if request.method == 'POST':
        club_id = data.get('club_id')
        user_id = data.get('user_id')
        member_role = (data.get('member_role') or 'Member').strip()
        if not club_id or not user_id:
            return jsonify({'error': 'club_id and user_id are required.'}), 400
        ok, msg = _add_club_membership(int(club_id), int(user_id), member_role)
        if not ok:
            return jsonify({'error': msg}), 409
        db.session.commit()
        return jsonify({'message': msg}), 201

    membership_id = data.get('membership_id')
    if not membership_id:
        return jsonify({'error': 'membership_id is required.'}), 400
    membership = ClubMembership.query.get_or_404(int(membership_id))
    db.session.delete(membership)
    db.session.commit()
    return jsonify({'removed': True})


@admin_bp.route('/api/coordinators/assign', methods=['POST'])
@login_required
@role_required('admin')
def api_assign_coordinator():
    data = request.get_json(silent=True) or {}
    club_id = data.get('club_id')
    coordinator_id = data.get('coordinator_id')
    if not club_id:
        return jsonify({'error': 'club_id is required.'}), 400
    club = Club.query.get_or_404(int(club_id))
    ok, msg = _assign_club_coordinator(club, int(coordinator_id) if coordinator_id else None)
    if not ok:
        return jsonify({'error': msg}), 400
    db.session.commit()
    return jsonify({'message': msg, 'club_id': club.id, 'coordinator_id': club.coordinator_id})
