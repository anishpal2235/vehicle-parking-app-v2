# Parking Management System v2

A comprehensive parking management system built with Flask backend and modern web frontend.

## Project Structure

```
parking_app_v2/
├── backend/                 # Backend Python/Flask code
│   ├── app/                # Main application logic
│   │   └── main.py        # Flask app factory
│   ├── config/             # Configuration files
│   │   ├── config.py      # Main configuration
│   │   └── email_config.py # Email configuration
│   ├── models/             # Database models
│   │   └── models.py      # SQLAlchemy models
│   ├── routes/             # API routes and endpoints
│   │   ├── auth_routes.py # Authentication routes
│   │   ├── admin_routes.py # Admin panel routes
│   │   └── user_routes.py # User dashboard routes
│   ├── services/           # Business logic services
│   │   ├── email_service.py # Email functionality
│   │   ├── notification_service.py # Notification system
│   │   ├── report_service.py # Report generation
│   │   └── cache_service.py # Caching system
│   ├── utils/              # Utility functions
│   │   └── helpers.py     # Helper functions
│   ├── jobs/               # Background jobs and scheduling
│   ├── main.py            # Main entry point
│   ├── wsgi.py            # WSGI entry point for production
│   ├── requirements.txt   # Python dependencies
│   ├── Procfile          # Heroku deployment
│   ├── runtime.txt        # Python runtime
│   ├── gunicorn.conf.py  # Gunicorn configuration
│   └── render.yaml        # Render deployment config
├── frontend/               # Frontend assets
│   ├── templates/         # HTML templates
│   │   ├── base.html     # Base template
│   │   ├── index.html    # Home page
│   │   ├── auth/         # Authentication pages
│   │   ├── admin/        # Admin panel pages
│   │   ├── user/         # User dashboard pages
│   │   └── reports/      # Report pages
│   └── static/            # Static assets
│       ├── css/           # Stylesheets
│       ├── js/            # JavaScript files
│       ├── img/           # Images
│       ├── exports/       # Export files
│       └── manifest.json  # PWA manifest
├── instance/               # Instance-specific files (database, etc.)
├── requirements.txt        # Root requirements (points to backend)
└── README.md              # This file
```

## Features

- **User Management**: Registration, authentication, and profile management
- **Admin Panel**: Comprehensive admin dashboard for system management
- **Parking Management**: Vehicle entry/exit, slot allocation, and billing
- **Reporting System**: Detailed reports and analytics
- **Email Notifications**: Automated email alerts and reminders
- **PWA Support**: Progressive Web App capabilities
- **Responsive Design**: Mobile-friendly interface

## Installation

### Prerequisites
- Python 3.8+
- pip
- SQLite (or other database)

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd parking_app_v2
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   cd backend
   python main.py
   ```

4. **Access the application**
   - Open your browser and go to `http://localhost:5000`
   - Default admin credentials: `admin@parking.com` / `Akpal@123`

## Development

### Backend Development
- All Python code is in the `backend/` directory
- Use `backend/main.py` as the entry point for development
- Configuration files are in `backend/config/`
- Database models are in `backend/models/`

### Frontend Development
- HTML templates are in `frontend/templates/`
- Static assets (CSS, JS, images) are in `frontend/static/`
- Templates use Jinja2 syntax and extend from `base.html`

## Deployment

### Local Development
```bash
cd backend
python main.py
```

### Production Deployment
```bash
cd backend
gunicorn main:app
```

### Cloud Deployment
The project includes configuration files for:
- **Heroku**: `Procfile` and `runtime.txt`
- **Render**: `render.yaml`

## Configuration

Key configuration files:
- `backend/config/config.py`: Main application configuration
- `backend/config/email_config.py`: Email service configuration
- Environment variables can override configuration settings

## Database

The system uses SQLite by default. The database file is created automatically in the `instance/` directory on first run.

## Security Features

- CSRF protection
- Secure session management
- Password hashing
- Input validation
- SQL injection protection

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License. 