# PawCare - Pet Clinic Management System

PawCare is a full-stack pet clinic management system engineered for veterinary clinics to schedule, manage, track, and search patient appointments.

## Architecture & Technology Stack

- **Frontend**: HTML5, CSS3, modern Vanilla JavaScript (responsive UI, real-time search, debounced filtering, inline status update, modal management).
- **Backend**: Python Flask RESTful API with structured routing and data validation.
- **Database**: SQLite3 with WAL (Write-Ahead Logging) mode and persistent Docker volume storage.
- **WSGI Server**: Gunicorn multi-worker WSGI server.
- **Reverse Proxy**: Nginx reverse proxy routing port `80` traffic to Gunicorn.
- **Containerization**: Multi-container Docker & Docker Compose setup (`web` and `nginx`).

---

## Architecture Diagram

```
                 +--------------------------+
                 |    Client Web Browser    |
                 +--------------------------+
                               |
                               | HTTP (Port 80)
                               v
               +-------------------------------+
               |    pawcare_nginx (Nginx)      |
               +-------------------------------+
                               |
                               | Reverse Proxy (Port 5000)
                               v
               +-------------------------------+
               |    pawcare_web (Gunicorn)     |
               |         Flask API             |
               +-------------------------------+
                               |
                               | Read / Write
                               v
               +-------------------------------+
               |    SQLite Database            |
               |    pawcare_db_data (Volume)   |
               +-------------------------------+
```

---

## Features

1. **Dashboard KPI Metrics**: Displays Total Appointments, Scheduled Appointments, Completed Appointments, and Cancelled Appointments in real-time.
2. **Appointment Scheduling**: Form to book appointments with pet species/breed, owner information, date, time, service required, and clinical notes.
3. **Appointment Management**:
   - Live search by pet name, breed, owner name, phone number, and service.
   - Filter by appointment status (Scheduled, Completed, Cancelled).
   - Instant inline status editing with one click.
   - Full appointment editing via modal.
   - Safe deletion with confirmation modal.
4. **Persistent Storage**: Uses a persistent Docker volume (`pawcare_db_data`) mounted to `/app/data/pawcare.db`. Data is preserved across container restarts, rebuilds, and updates.
5. **Production WSGI**: Serves the application with Gunicorn instead of Flask's development server.
6. **Reverse Proxying**: Nginx acts as the front-facing web server forwarding requests to Gunicorn.

---

## Running the Application

### 1. Start with Docker Compose (Recommended)

Run the following command in the project root:

```bash
docker compose up --build -d
```

Once started:
- Access the web interface: **[http://localhost](http://localhost)**
- Health check endpoint: **[http://localhost/health](http://localhost/health)**
- API Statistics: **[http://localhost/api/stats](http://localhost/api/stats)**
- API Appointments: **[http://localhost/api/appointments](http://localhost/api/appointments)**

### 2. Check Container Status & Logs

```bash
# Check running containers
docker compose ps

# View web container logs (Gunicorn / Flask)
docker compose logs -f web

# View nginx container logs
docker compose logs -f nginx
```

### 3. Stop the Application

```bash
docker compose down
```
*(Note: Data stored in the SQLite volume will remain safe and intact.)*

---

## Running Tests

You can run automated tests directly using Docker:

```bash
docker compose exec web python3 -m unittest test_app.py
```

Or run the tests locally (if Python 3 and dependencies are installed):

```bash
python3 -m unittest test_app.py
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Dashboard User Interface |
| `GET` | `/health` | Application health and database connection status |
| `GET` | `/api/stats` | Count of total, scheduled, completed, and cancelled appointments |
| `GET` | `/api/appointments` | Retrieve appointments (supports `?q=<term>` and `?status=<status>`) |
| `POST` | `/api/appointments` | Create a new appointment |
| `GET` | `/api/appointments/<id>` | Retrieve appointment details by ID |
| `PUT` | `/api/appointments/<id>` | Update full appointment details |
| `PATCH` | `/api/appointments/<id>/status` | Update appointment status (`Scheduled`, `Completed`, `Cancelled`) |
| `DELETE` | `/api/appointments/<id>` | Delete appointment |
