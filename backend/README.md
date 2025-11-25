# CarAlertz Backend

FastAPI-based backend service for the CarAlertz car monitoring and alert system.

## Overview

The backend provides a REST API for managing car search alerts, scraping car listings, and sending email notifications when matching vehicles are found.

## Architecture

### Core Components

- **FastAPI Application** (`main.py`): Main application entry point with API routes
- **Scraper** (`scraper.py`): Web scraper for fetching car listings from external APIs
- **Scheduler** (`scheduler.py`): Background task scheduler for periodic scraping
- **Database Handler** (`db/db_handler.py`): Database operations abstraction
- **Email Sender** (`email/email_sender.py`): Email notification service
- **Authentication** (`auth.py`): User authentication and authorization
- **Models** (`models.py`): Data models and schemas

### Key Features

- Task management (create, update, delete car search alerts)
- Periodic scraping with configurable intervals
- Email notifications for new matching vehicles
- Firebase integration for database and user management
- CORS support for frontend integration
- Session-based authentication

## Setup

### Prerequisites

- Python 3.8+
- Firebase project with Realtime Database
- Email account for sending notifications

### Environment Variables

Create a `.env` file in `backend/secrets/` with the following variables:

```env
# API URLs
BASE_API_URL=<car listing API URL>
BASE_OPTIONS_API_URL=<options API URL>
BASE_CATALOG_API_URL=<catalog API URL>
BASE_URL=<base website URL>
BASE_API_CAR_AD_URL=<car ad details API URL>

# Firebase Configuration
FIREBASE_DB_URL=<Firebase Realtime Database URL>
FIREBASE_CERTIFICATE_PATH=<path to Firebase service account JSON>

# Email Configuration
SENDER_EMAIL=<sender email address>
EMAIL_PASSWORD=<email password or app password>

# Session Security
SESSION_SECRET_KEY=<random secret key for session encryption>

# CORS (optional, defaults to localhost:3000)
FRONTEND_ORIGINS=<comma-separated list of allowed origins>
```

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure Firebase credentials are in place:
   - Place Firebase service account JSON at the path specified in `FIREBASE_CERTIFICATE_PATH`

3. Run the application:
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8081 --reload
```

## API Endpoints

### Authentication
- `POST /auth/register` - Register a new user
- `POST /auth/login` - Login user
- `POST /auth/logout` - Logout user
- `GET /auth/me` - Get current user info

### Tasks
- `GET /tasks` - List all tasks for authenticated user
- `POST /v2/tasks` - Create a new car search alert
- `PUT /tasks/{task_id}` - Update task (e.g., mileage range)
- `DELETE /tasks/{task_id}` - Delete a task
- `GET /deleted_tasks` - List recently deleted tasks (max 5)

### Car Data
- `GET /manufacturers` - Get list of car manufacturers
- `GET /models/{manufacturer_id}` - Get models for a manufacturer
- `GET /submodels/{model_id}` - Get submodels for a model
- `GET /vehicles-car-catalog` - Get full vehicle catalog

### Debug
- `POST /debug/clear_tasks` - Clear all tasks (debug only)

## Task Scheduler

The scheduler runs in a background thread and periodically executes active tasks:

- Checks for tasks that need to be run
- Executes scraping with task-specific parameters
- Compares results with previous runs
- Sends email notifications for new matches
- Updates task `last_run` timestamp

Tasks are executed based on their `last_run` timestamp and activity status.

## Data Models

### Task
- `id`: Unique task identifier (MD5 hash of search parameters)
- `title`: Human-readable task title
- `mail`: Email address for notifications
- `active`: Whether the task is active
- `params`: Search parameters (manufacturer, model, year, km, etc.)
- `seller_type`: Filter by seller type (all, private, dealer)
- `owner_id`: User ID who owns the task
- `created_at`: Task creation timestamp
- `last_run`: Last execution timestamp

### Seller Types
- `all`: Search all seller types
- `private`: Private sellers only
- `dealer`: Dealers only (solo, platinum, commercial)

## Caching

The scraper uses SQLite-based HTTP caching to reduce API calls:
- Cache location: `cache/scrape_cache.sqlite`
- Default cache timeout: 30 minutes (configurable)

## Logging

Logging is configured via `logger_setup.py`:
- Internal info logger for application events
- Separate log files for different components

## Development

### Code Style
- Uses Python 3.8+ type hints
- Follows PEP 8 style guidelines
- Uses Pydantic for data validation

### Testing
Test files are located in the `test/` directory at the project root.

## Dependencies

Key dependencies:
- `fastapi`: Web framework
- `uvicorn`: ASGI server
- `firebase_admin`: Firebase integration
- `mongoengine`: MongoDB ODM (legacy support)
- `requests`, `aiohttp-client-cache`: HTTP client with caching
- `schedule`: Task scheduling
- `pydantic`: Data validation
- `Jinja2`: Email template rendering

See `requirements.txt` for the complete list.

