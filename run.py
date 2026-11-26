import os
from app import create_app, db, ensure_schema_updates
from seed import seed_database

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        # Create database tables if they do not exist & apply safe migrations
        db.create_all()
        ensure_schema_updates(app)
        # Seed initial test data if database is empty
        seed_database()

    print("\n" + "="*60)
    print(" CampusConnect Web Application is Running!")
    print(" URL: http://127.0.0.1:5000")
    print(" Admin Login:       admin@campusconnect.edu       / admin123")
    print(" Coordinator Login: tech_coord@campusconnect.edu  / coord123")
    print(" Student Login:     student1@campusconnect.edu    / student123")
    print("="*60 + "\n")

    app.run(host='0.0.0.0', port=5000, debug=True)
