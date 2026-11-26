from datetime import datetime, timedelta
from app import create_app, db
from app.models import User, Club, ClubMembership, Event, Registration, Expense, Certificate, EventGallery, Feedback

def seed_database():
    app = create_app()
    with app.app_context():
        # Check if users already exist
        if User.query.first():
            print("Database already contains data. Skipping seeding.")
            return

        print("Seeding CampusConnect database with initial test & demo data...")

        # 1. Users (Admin, Coordinators, Students)
        admin = User(name="System Administrator", email="admin@campusconnect.edu", role="admin")
        admin.set_password("admin123")

        coord_tech = User(name="Dr. Alan Turing", email="tech_coord@campusconnect.edu", role="coordinator")
        coord_tech.set_password("coord123")

        coord_cult = User(name="Prof. Maya Lin", email="cultural_coord@campusconnect.edu", role="coordinator")
        coord_cult.set_password("coord123")

        coord_sports = User(name="Coach David Beckham", email="sports_coord@campusconnect.edu", role="coordinator")
        coord_sports.set_password("coord123")

        student1 = User(name="Alice Walker", email="student1@campusconnect.edu", role="student")
        student1.set_password("student123")

        student2 = User(name="Bob Smith", email="student2@campusconnect.edu", role="student")
        student2.set_password("student123")

        student3 = User(name="Charlie Davis", email="student3@campusconnect.edu", role="student")
        student3.set_password("student123")

        db.session.add_all([admin, coord_tech, coord_cult, coord_sports, student1, student2, student3])
        db.session.commit()

        # 2. Clubs
        club_tech = Club(
            name="ACM Computer Society",
            description="The premier student computing & software development society organizing hackathons, coding contests, and tech workshops.",
            category="Technical",
            contact_info="acm@campusconnect.edu",
            coordinator_id=coord_tech.id,
            allocated_budget=5000.00,
            status="approved"
        )

        club_cult = Club(
            name="Fine Arts & Drama Club",
            description="Celebrating theatrical performances, live music concerts, fine arts exhibitions, and cultural diversity.",
            category="Cultural",
            contact_info="finearts@campusconnect.edu",
            coordinator_id=coord_cult.id,
            allocated_budget=4500.00,
            status="approved"
        )

        club_sports = Club(
            name="Campus Athletics Club",
            description="Organizing intra-college esports, football leagues, cricket tournaments, and fitness marathons.",
            category="Sports",
            contact_info="athletics@campusconnect.edu",
            coordinator_id=coord_sports.id,
            allocated_budget=3500.00,
            status="approved"
        )

        db.session.add_all([club_tech, club_cult, club_sports])
        db.session.commit()

        # 2b. Initial Club Memberships
        memberships = [
            ClubMembership(club_id=club_tech.id, user_id=student1.id, member_role="Member"),
            ClubMembership(club_id=club_tech.id, user_id=student2.id, member_role="Lead"),
            ClubMembership(club_id=club_cult.id, user_id=student2.id, member_role="Member"),
            ClubMembership(club_id=club_sports.id, user_id=student3.id, member_role="Member"),
        ]
        db.session.add_all(memberships)
        db.session.commit()

        # 3. Events
        now = datetime.utcnow()

        event1 = Event(
            club_id=club_tech.id,
            title="HackConnect 2026 Flagship Hackathon",
            description="36-hour intense hackathon focused on AI agents, cloud architectures, and web development.",
            venue="Tech Innovation Center - Hall A",
            category="Hackathon",
            event_date=now + timedelta(days=10),
            reg_deadline=now + timedelta(days=7),
            capacity=150,
            allocated_budget=1200.00,
            status="published"
        )

        event2 = Event(
            club_id=club_cult.id,
            title="Battle of the Bands & Acoustic Night",
            description="Annual campus musical showdown featuring student bands, solo acoustic acts, and food stalls.",
            venue="Main Campus Amphitheater",
            category="Cultural",
            event_date=now + timedelta(days=15),
            reg_deadline=now + timedelta(days=12),
            capacity=300,
            allocated_budget=1500.00,
            status="published"
        )

        event3 = Event(
            club_id=club_tech.id,
            title="Hands-on Machine Learning Workshop",
            description="Introduction to PyTorch, neural networks, and computer vision for engineering students.",
            venue="Computer Lab 402",
            category="Workshop",
            event_date=now - timedelta(days=5),
            reg_deadline=now - timedelta(days=8),
            capacity=50,
            allocated_budget=400.00,
            status="completed"
        )

        db.session.add_all([event1, event2, event3])
        db.session.commit()

        # 4. Registrations & Attendance
        reg1 = Registration(event_id=event1.id, user_id=student1.id)
        reg2 = Registration(event_id=event1.id, user_id=student2.id)

        # Completed workshop attendance
        reg3 = Registration(event_id=event3.id, user_id=student1.id, attended=True)
        reg4 = Registration(event_id=event3.id, user_id=student2.id, attended=True)

        db.session.add_all([reg1, reg2, reg3, reg4])
        db.session.commit()

        # 5. Certificates for Attended Workshop
        cert1 = Certificate(event_id=event3.id, user_id=student1.id)
        cert2 = Certificate(event_id=event3.id, user_id=student2.id)

        # 6. Expenses
        exp1 = Expense(
            event_id=event1.id,
            title="Cloud Server Vouchers & Mentors Catering",
            amount=450.00,
            category="Logistics & Transport",
            status="approved"
        )

        exp2 = Expense(
            event_id=event3.id,
            title="Workshop Printing & Courseware Materials",
            amount=120.00,
            category="Marketing & Printing",
            status="approved"
        )

        exp3 = Expense(
            event_id=event2.id,
            title="Sound System & Stage Lighting Rental",
            amount=800.00,
            category="Audio/Visual Equipment",
            status="pending"
        )

        # 7. Feedback
        fb1 = Feedback(
            event_id=event3.id,
            user_id=student1.id,
            rating=5,
            comments="Fantastic hands-on workshop! The practical exercises with PyTorch were super helpful."
        )

        fb2 = Feedback(
            event_id=event3.id,
            user_id=student2.id,
            rating=4,
            comments="Great content and clear guidance by the coordinator."
        )

        db.session.add_all([cert1, cert2, exp1, exp2, exp3, fb1, fb2])
        db.session.commit()

        print("Database successfully seeded with standard test accounts!")
        print("-------------------------------------------------------")
        print("Admin:       admin@campusconnect.edu       / admin123")
        print("Coordinator: tech_coord@campusconnect.edu  / coord123")
        print("Student:     student1@campusconnect.edu    / student123")
        print("-------------------------------------------------------")

if __name__ == '__main__':
    seed_database()
