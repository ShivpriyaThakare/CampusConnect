# CampusConnect

A full-stack **College Event, Club & Expense Management Portal** built with **Flask**, **SQLAlchemy**, and a **Modern Pastel SaaS** frontend. CampusConnect streamlines event discovery and registration, club and member administration, coordinator assignments, attendance tracking, cross-club expense auditing, and automated PDF certificate generation.

---

## Key Features

### Public & Student Portal
- **Pastel SaaS Directory & Discovery:** Browse upcoming events with live search, category filters (`Technical`, `Cultural`, `Sports`, `Workshop`, `Seminar`, `Hackathon`, `General`), and club filters (`/events`, `/clubs`, `/gallery`).
- **Event Registration & Capacity Controls:** One-click event registration with deadline checks, seat capacity progress tracking, and cancellation prior to attendance.
- **Student Dashboard:** View club memberships, upcoming and past registered events, submit star-rated feedback after attending an event, and download verified PDF certificates.
- **Automated PDF Certificates:** Generates landscape participation certificates with unique verification IDs using **ReportLab** (`app/utils/certificate_gen.py`).

### Club Coordinator Portal
- **Club-Scoped Dashboard:** View club events, registration totals, annual budget allocation, and logged spend (`/coordinator/dashboard`).
- **Event Lifecycle Management:** Create and edit club events, upload event banners, manage attendance via AJAX toggles (`/coordinator/events/<id>/attendance`), upload gallery photos, and issue individual or bulk PDF certificates.
- **Club Member Management:** Add, update roles (`Member`, `Lead`, `Secretary`, `Treasurer`), and remove members for the assigned club (`/coordinator/members`).
- **Expense Logging:** Submit itemized event expenses with receipt image/PDF uploads for administrator review (`/coordinator/events/<id>/expenses`).

### System Administrator Console
- **Centralized Admin Sidebar (`/admin/dashboard`):** Real-time statistics for users, clubs, coordinators, events, registrations, club memberships, budgets, and pending approvals.
- **Club Management (`/admin/clubs`, `/admin/clubs/<id>`):** Create, edit, inspect, archive (soft-delete while preserving historical events/registrations/expenses), and restore clubs with category, contact info, logo, and budget controls.
- **Member & Role Management (`/admin/users`, `/admin/members`):** Search and filter users by role or club, create/invite new users or assign existing users to clubs, edit user info, toggle account status, and update RBAC roles.
- **Coordinator Assignments (`/admin/coordinators`):** Assign, replace, or unassign club coordinators across all clubs.
- **Cross-Club Moderation & Audits:** Manage events (`/admin/events`), registrations (`/admin/registrations`), gallery photos (`/admin/gallery`), and expense audits (`/admin/budget-audits`).
- **JSON REST APIs:** Admin-protected endpoints under `/admin/api/stats`, `/admin/api/clubs`, `/admin/api/members`, and `/admin/api/coordinators/assign`.

### Role-Based Access Control (RBAC)
- **System Administrator (`admin`):** Full platform control across all clubs, members, events, registrations, gallery, and audits.
- **Club Coordinator (`coordinator`):** Strictly scoped to their own assigned, non-archived club (`403 Forbidden` on other clubs or admin routes).
- **Student (`student`):** Browse public directories, manage personal registrations, submit feedback for attended events, and download earned certificates.

---

## Tech Stack

- **Backend:** Python 3.10+, Flask 3.0+, Flask-SQLAlchemy, Flask-Login, Flask-Bcrypt
- **Database:** SQLite (default development fallback `campus_connect.db`) or MySQL 8.0+ (`PyMySQL` + `schema.sql`)
- **PDF & Media Processing:** ReportLab, Pillow
- **Frontend:** Jinja2, Tailwind CSS (CDN), Plus Jakarta Sans / Inter, Vanilla JS (AJAX attendance & modals)
- **Testing:** Pytest

---

## Project Structure

```text
campusConnect/
├── app/
│   ├── __init__.py              # App factory, extensions, filters, schema migration helper
│   ├── models/                  # SQLAlchemy models (User, Club, ClubMembership, Event, etc.)
│   ├── routes/                  # Blueprints: main, auth, student, coordinator, admin
│   ├── static/                  # Custom pastel CSS, client JS, and upload directories
│   ├── templates/               # Jinja2 templates (layouts, partials, role portals, errors)
│   └── utils/                   # RBAC decorators, Pillow uploader, ReportLab PDF generator
├── tests/
│   └── test_app.py              # Pytest suite (auth, RBAC/IDOR, CRUD, PDF, workflows)
├── config.py                    # Development, Testing, and Production configurations
├── requirements.txt             # Python dependencies
├── run.py                       # Application entry point (auto-creates & seeds DB)
├── schema.sql                   # MySQL 8.0+ database schema
└── seed.py                      # Initial demo accounts, clubs, events, and records
```

---

## Quick Start (Local Development)

### 1. Clone the Repository
```bash
git clone https://github.com/ShivpriyaThakare/CampusConnect.git
cd CampusConnect
```

### 2. Create a Virtual Environment & Install Dependencies
```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Run the Application
```bash
python run.py
```
On first startup, `run.py` automatically creates the SQLite database (`campus_connect.db`), applies schema migrations, and seeds demo accounts and sample data.

Open **http://127.0.0.1:5000** in your browser.

---

## Demo Login Accounts

| Role | Email | Password |
| :--- | :--- | :--- |
| **System Administrator** | `admin@campusconnect.edu` | `admin123` |
| **Club Coordinator (ACM)** | `tech_coord@campusconnect.edu` | `coord123` |
| **Club Coordinator (Fine Arts)** | `cultural_coord@campusconnect.edu` | `coord123` |
| **Club Coordinator (Athletics)** | `sports_coord@campusconnect.edu` | `coord123` |
| **Student** | `student1@campusconnect.edu` | `student123` |

---

## Configuration (Optional MySQL Setup)

By default, `config.py` uses SQLite (`campus_connect.db`). To use **MySQL 8.0+**:

1. Import `schema.sql` into your MySQL server:
   ```bash
   mysql -u root -p < schema.sql
   ```
2. Set environment variables before starting the app:
   ```bash
   export SECRET_KEY="your-production-secret-key"
   export DATABASE_URL="mysql+pymysql://root:password@localhost:3306/campus_connect"
   ```

---

## Running Tests

Run the automated test suite using Pytest (uses an isolated in-memory SQLite database via `TestingConfig`):

```bash
pytest -v
```
