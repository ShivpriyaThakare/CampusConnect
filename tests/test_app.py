import io
from datetime import datetime, timedelta
import pytest
from app import create_app, db
from app.models import User, Club, ClubMembership, Event, Registration, Expense, Certificate, Feedback
from app.utils.certificate_gen import generate_certificate_pdf
from config import TestingConfig


@pytest.fixture
def app(tmp_path):
    app = create_app(TestingConfig)
    app.config['UPLOAD_FOLDER'] = str(tmp_path / 'uploads')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _login(client, email, password='password123'):
    return client.post('/auth/login', data={'email': email, 'password': password}, follow_redirects=True)


def _seed_core_entities():
    admin = User(name='Admin User', email='admin@college.edu', role='admin')
    admin.set_password('password123')
    coord1 = User(name='Coord One', email='coord1@college.edu', role='coordinator')
    coord1.set_password('password123')
    coord2 = User(name='Coord Two', email='coord2@college.edu', role='coordinator')
    coord2.set_password('password123')
    student = User(name='Student One', email='student1@college.edu', role='student')
    student.set_password('password123')
    db.session.add_all([admin, coord1, coord2, student])
    db.session.commit()

    club1 = Club(name='Tech Club', description='Tech', coordinator_id=coord1.id, allocated_budget=2000.0, status='approved')
    club2 = Club(name='Art Club', description='Art', coordinator_id=coord2.id, allocated_budget=1500.0, status='approved')
    db.session.add_all([club1, club2])
    db.session.commit()

    now = datetime.utcnow()
    ev1 = Event(
        club_id=club1.id,
        title='Tech Summit',
        description='Annual summit',
        venue='Hall A',
        category='Technical',
        event_date=now + timedelta(days=5),
        reg_deadline=now + timedelta(days=3),
        capacity=50,
        allocated_budget=500.0,
        status='published'
    )
    ev2 = Event(
        club_id=club2.id,
        title='Art Expo',
        description='Gallery show',
        venue='Hall B',
        category='Cultural',
        event_date=now + timedelta(days=6),
        reg_deadline=now + timedelta(days=4),
        capacity=30,
        allocated_budget=300.0,
        status='published'
    )
    db.session.add_all([ev1, ev2])
    db.session.commit()

    return {
        'admin_id': admin.id,
        'coord1_id': coord1.id,
        'coord2_id': coord2.id,
        'student_id': student.id,
        'club1_id': club1.id,
        'club2_id': club2.id,
        'ev1_id': ev1.id,
        'ev2_id': ev2.id,
    }


def test_homepage_loads(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'CampusConnect' in response.data


def test_user_registration(client, app):
    response = client.post('/auth/register', data={
        'name': 'Test Student',
        'email': 'teststudent@college.edu',
        'password': 'password123',
        'confirm_password': 'password123',
        'role': 'student'
    }, follow_redirects=True)
    assert response.status_code == 200

    with app.app_context():
        user = User.query.filter_by(email='teststudent@college.edu').first()
        assert user is not None
        assert user.role == 'student'
        assert user.check_password('password123')


def test_rbac_access_control(client, app):
    with app.app_context():
        student = User(name='Regular Student', email='student@college.edu', role='student')
        student.set_password('pass123')
        db.session.add(student)
        db.session.commit()

    _login(client, 'student@college.edu', 'pass123')
    assert client.get('/admin/dashboard').status_code == 403
    assert client.get('/coordinator/dashboard').status_code == 403


def test_coordinator_ownership_and_idor_protection(client, app):
    with app.app_context():
        ids = _seed_core_entities()
        reg1 = Registration(event_id=ids['ev1_id'], user_id=ids['student_id'], attended=True)
        db.session.add(reg1)
        db.session.commit()
        cert1 = Certificate(event_id=ids['ev1_id'], user_id=ids['student_id'])
        db.session.add(cert1)
        db.session.commit()
        reg1_id = reg1.id
        cert1_id = cert1.id

    # Coordinator 2 must not access Coordinator 1's event endpoints
    _login(client, 'coord2@college.edu')
    ev1_id = ids['ev1_id']
    assert client.get(f'/coordinator/events/{ev1_id}').status_code == 403
    assert client.get(f'/coordinator/events/{ev1_id}/edit').status_code == 403
    assert client.get(f'/coordinator/events/{ev1_id}/attendance').status_code == 403
    assert client.get(f'/coordinator/events/{ev1_id}/expenses').status_code == 403
    assert client.get(f'/coordinator/events/{ev1_id}/gallery').status_code == 403
    assert client.post(f'/coordinator/events/{ev1_id}/generate-certificates').status_code == 403
    assert client.get(f'/student/certificates/{cert1_id}/download').status_code == 403

    # Coordinator 2 must not toggle Coordinator 1's registration via their own event endpoint
    ev2_id = ids['ev2_id']
    resp = client.post(
        f'/coordinator/events/{ev2_id}/attendance',
        data={'registration_id': reg1_id, 'attended': 'false'},
        headers={'X-Requested-With': 'XMLHttpRequest'}
    )
    assert resp.status_code == 403


def test_coordinator_expenses_page_and_workflow(client, app):
    with app.app_context():
        ids = _seed_core_entities()
    ev1_id = ids['ev1_id']

    _login(client, 'coord1@college.edu')

    # Previously crashed with UndefinedError: 'float' is undefined
    res = client.get(f'/coordinator/events/{ev1_id}/expenses')
    assert res.status_code == 200
    assert b'$500.00' in res.data

    # Log a valid expense
    res = client.post(f'/coordinator/events/{ev1_id}/expenses', data={
        'title': 'Catering Boxes',
        'amount': '125.50',
        'category': 'Venue & Catering',
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b'Catering Boxes' in res.data

    # Invalid file extension should flash error instead of raising 500
    res = client.post(f'/coordinator/events/{ev1_id}/expenses', data={
        'title': 'Bad Receipt',
        'amount': '50.00',
        'category': 'Miscellaneous',
        'receipt': (io.BytesIO(b'not allowed'), 'script.exe'),
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b'Invalid file format' in res.data


def test_student_registration_attendance_feedback_and_certificate(client, app):
    with app.app_context():
        ids = _seed_core_entities()
    ev1_id = ids['ev1_id']

    # Student registers
    _login(client, 'student1@college.edu')
    res = client.post(f'/student/register/{ev1_id}', follow_redirects=True)
    assert res.status_code == 200
    assert b'Successfully registered' in res.data

    # Feedback before attendance is blocked
    res = client.get(f'/student/feedback/{ev1_id}', follow_redirects=True)
    assert b'only be submitted by students who attended' in res.data

    with app.app_context():
        reg = Registration.query.filter_by(event_id=ev1_id, user_id=ids['student_id']).first()
        assert reg is not None
        reg_id = reg.id

    # Coordinator marks attendance & generates certificate
    client.get('/auth/logout')
    _login(client, 'coord1@college.edu')
    att_res = client.post(
        f'/coordinator/events/{ev1_id}/attendance',
        data={'registration_id': reg_id, 'attended': 'true'},
        headers={'X-Requested-With': 'XMLHttpRequest'}
    )
    assert att_res.status_code == 200
    assert att_res.get_json() == {'success': True, 'attended': True}

    cert_gen_res = client.post(f'/coordinator/events/{ev1_id}/generate-certificates', follow_redirects=True)
    assert cert_gen_res.status_code == 200
    assert b'Issued certificates for 1 attended participant' in cert_gen_res.data

    # Student submits feedback and downloads PDF certificate
    client.get('/auth/logout')
    _login(client, 'student1@college.edu')
    fb_res = client.post(f'/student/feedback/{ev1_id}', data={'rating': '5', 'comments': 'Great event!'}, follow_redirects=True)
    assert fb_res.status_code == 200
    assert b'Thank you! Your feedback has been submitted.' in fb_res.data

    with app.app_context():
        cert = Certificate.query.filter_by(event_id=ev1_id, user_id=ids['student_id']).first()
        assert cert is not None
        cert_id = cert.id

    dl_res = client.get(f'/student/certificates/{cert_id}/download')
    assert dl_res.status_code == 200
    assert dl_res.data.startswith(b'%PDF')


def test_admin_club_duplicate_and_expense_audit(client, app):
    with app.app_context():
        ids = _seed_core_entities()
        exp = Expense(event_id=ids['ev1_id'], title='Sound Rental', amount=200.0, category='Audio/Visual Equipment', status='pending')
        db.session.add(exp)
        db.session.commit()
        exp_id = exp.id

    _login(client, 'admin@college.edu')

    # Duplicate club name is rejected gracefully
    res = client.post('/admin/clubs', data={
        'action': 'create',
        'name': 'Tech Club',
        'description': 'Duplicate',
        'allocated_budget': '1000'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b'already exists' in res.data

    # Approve expense in budget audits
    audit_res = client.post('/admin/budget-audits', data={
        'expense_id': exp_id,
        'status': 'approved'
    }, follow_redirects=True)
    assert audit_res.status_code == 200
    assert b'changed to approved' in audit_res.data


def test_certificate_pdf_generation():
    pdf_buffer = generate_certificate_pdf(
        student_name="Alice Walker",
        event_title="HackConnect 2026",
        club_name="ACM Club",
        event_date_str="October 15, 2026",
        certificate_uid="test-uid-12345"
    )
    pdf_bytes = pdf_buffer.getvalue()
    assert pdf_bytes.startswith(b'%PDF')
    assert len(pdf_bytes) > 1000


def test_admin_club_crud_and_public_visibility(client, app):
    with app.app_context():
        ids = _seed_core_entities()

    _login(client, 'admin@college.edu')

    # 1. Admin creates a new club
    res = client.post('/admin/clubs', data={
        'action': 'create',
        'name': 'Quantum Computing Society',
        'description': 'Exploring qubits and quantum algorithms.',
        'category': 'Technical',
        'contact_info': 'quantum@college.edu',
        'coordinator_id': ids['student_id'],
        'allocated_budget': '2500.00'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b'Quantum Computing Society' in res.data

    with app.app_context():
        club = Club.query.filter_by(name='Quantum Computing Society').first()
        assert club is not None
        assert club.category == 'Technical'
        assert club.contact_info == 'quantum@college.edu'
        assert club.is_archived is False
        assert club.coordinator_id == ids['student_id']
        # Student promoted to coordinator upon assignment
        promoted = db.session.get(User, ids['student_id'])
        assert promoted.role == 'coordinator'
        club_id = club.id

    # 2. Newly created club appears on public /clubs page
    public_clubs = client.get('/clubs')
    assert public_clubs.status_code == 200
    assert b'Quantum Computing Society' in public_clubs.data

    # 3. Admin edits club details
    edit_res = client.post('/admin/clubs', data={
        'action': 'edit',
        'club_id': club_id,
        'name': 'Quantum & AI Society',
        'description': 'Updated description.',
        'category': 'Academic',
        'contact_info': 'qai@college.edu',
        'coordinator_id': ids['coord1_id'],
        'allocated_budget': '3000.00',
        'status': 'approved'
    }, follow_redirects=True)
    assert edit_res.status_code == 200
    assert b'Quantum &amp; AI Society' in edit_res.data or b'Quantum & AI Society' in edit_res.data

    # Admin can view club detail page
    detail_res = client.get(f'/admin/clubs/{club_id}')
    assert detail_res.status_code == 200
    assert b'qai@college.edu' in detail_res.data

    # Attach an event & expense to verify soft delete preserves historical records
    with app.app_context():
        ev = Event(
            club_id=club_id,
            title='Quantum Talk',
            venue='Auditorium',
            category='Seminar',
            event_date=datetime.utcnow() + timedelta(days=2),
            reg_deadline=datetime.utcnow() + timedelta(days=1),
            capacity=40,
            status='published'
        )
        db.session.add(ev)
        db.session.flush()
        db.session.add(Expense(event_id=ev.id, title='Stage Mic', amount=75.0, category='Audio/Visual Equipment', status='approved'))
        db.session.commit()
        ev_id = ev.id

    # 4. Admin archives (soft-deletes) the club
    arch_res = client.post('/admin/clubs', data={'action': 'archive', 'club_id': club_id}, follow_redirects=True)
    assert arch_res.status_code == 200
    assert b'has been archived' in arch_res.data

    # Hidden from public /clubs, but historical event & expense remain intact in DB
    assert b'Quantum' not in client.get('/clubs').data
    with app.app_context():
        assert db.session.get(Club, club_id).is_archived is True
        assert db.session.get(Event, ev_id) is not None
        assert Expense.query.filter_by(event_id=ev_id).count() == 1


def test_admin_member_management_and_club_assignments(client, app):
    with app.app_context():
        ids = _seed_core_entities()

    _login(client, 'admin@college.edu')

    # 5. Admin adds a new member and assigns them to a club
    res = client.post('/admin/users', data={
        'action': 'add_member',
        'mode': 'new',
        'name': 'New Member Mia',
        'email': 'mia@college.edu',
        'role': 'student',
        'password': 'secretpassword',
        'club_id': ids['club1_id'],
        'member_role': 'Lead'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b'New Member Mia' in res.data

    with app.app_context():
        mia = User.query.filter_by(email='mia@college.edu').first()
        assert mia is not None
        assert mia.password_hash != 'secretpassword'
        assert mia.check_password('secretpassword')
        m1 = ClubMembership.query.filter_by(club_id=ids['club1_id'], user_id=mia.id).first()
        assert m1 is not None and m1.member_role == 'Lead'

    # 6. Admin assigns existing student to a club (and duplicate is prevented)
    res2 = client.post('/admin/users', data={
        'action': 'add_member',
        'mode': 'existing',
        'existing_user_id': ids['student_id'],
        'club_id': ids['club2_id'],
        'member_role': 'Member'
    }, follow_redirects=True)
    assert res2.status_code == 200

    res_dup = client.post('/admin/users', data={
        'action': 'add_member',
        'mode': 'existing',
        'existing_user_id': ids['student_id'],
        'club_id': ids['club2_id'],
        'member_role': 'Member'
    }, follow_redirects=True)
    assert b'already a member' in res_dup.data

    with app.app_context():
        membership = ClubMembership.query.filter_by(club_id=ids['club2_id'], user_id=ids['student_id']).first()
        assert membership is not None
        m_id = membership.id

    # 7. Admin removes a member from a club
    rem_res = client.post('/admin/users', data={
        'action': 'remove_from_club',
        'membership_id': m_id
    }, follow_redirects=True)
    assert rem_res.status_code == 200
    with app.app_context():
        assert db.session.get(ClubMembership, m_id) is None


def test_admin_coordinator_assignment_and_replacement(client, app):
    with app.app_context():
        ids = _seed_core_entities()

    _login(client, 'admin@college.edu')

    # 8 & 9. Replace Tech Club coordinator (coord1 -> student)
    res = client.post('/admin/coordinators', data={
        'action': 'assign',
        'club_id': ids['club1_id'],
        'coordinator_id': ids['student_id']
    }, follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        club1 = db.session.get(Club, ids['club1_id'])
        assert club1.coordinator_id == ids['student_id']
        new_coord = db.session.get(User, ids['student_id'])
        assert new_coord.role == 'coordinator'

    # 10. Previous coordinator (coord1) can no longer manage Tech Club events; new coordinator can
    client.get('/auth/logout')
    _login(client, 'coord1@college.edu')
    assert client.get(f"/coordinator/events/{ids['ev1_id']}").status_code == 403

    client.get('/auth/logout')
    _login(client, 'student1@college.edu')
    assert client.get(f"/coordinator/events/{ids['ev1_id']}").status_code == 200
    assert client.get('/coordinator/members').status_code == 200


def test_admin_cross_club_event_and_api_management(client, app):
    with app.app_context():
        ids = _seed_core_entities()

    # 11. Student blocked from admin endpoints & APIs
    _login(client, 'student1@college.edu')
    assert client.get('/admin/events').status_code == 403
    assert client.get('/admin/api/clubs').status_code == 403
    client.get('/auth/logout')

    # 12. Admin manages events across all clubs + JSON API works
    _login(client, 'admin@college.edu')
    create_ev = client.post('/admin/events', data={
        'action': 'create',
        'club_id': ids['club2_id'],
        'title': 'Admin Cross-Club Gala',
        'category': 'Cultural',
        'venue': 'Grand Hall',
        'event_date': '2027-03-15T18:00',
        'reg_deadline': '2027-03-10T23:59',
        'capacity': '200',
        'allocated_budget': '1200',
        'status': 'published'
    }, follow_redirects=True)
    assert create_ev.status_code == 200
    assert b'Admin Cross-Club Gala' in create_ev.data

    assert client.get('/admin/registrations').status_code == 200
    assert client.get('/admin/gallery').status_code == 200

    api_res = client.get('/admin/api/stats')
    assert api_res.status_code == 200
    assert api_res.get_json()['total_clubs'] == 2
