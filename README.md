# CarAlertz

A car monitoring and alert system that automatically searches for vehicles matching your criteria and sends email notifications when new matches are found.

## Overview

CarAlertz is a full-stack application that helps users monitor car listings from Israeli car websites. Users can create search alerts with specific criteria (manufacturer, model, year, mileage, etc.), and the system periodically checks for new matching vehicles and sends email notifications.

## Project Structure

```
CarAlertz/
├── backend/              # FastAPI backend service
│   ├── db/              # Database handlers and Firebase config
│   ├── email/           # Email notification service
│   ├── handz/           # Handz integration
│   ├── secrets/         # Environment variables and credentials
│   ├── templates/       # Email HTML templates
│   └── main.py          # FastAPI application entry point
├── frontend/            # React frontend application
├── cache/               # SQLite cache files for HTTP requests
├── excel/               # Excel export utilities
├── test/                # Test files
├── license_plate_recognizer/  # License plate recognition utilities
├── find_cars_mimshalti.py    # Standalone script for car data analysis
├── requirements.txt     # Python dependencies
├── Dockerfile           # Docker configuration
└── docker-compose.yml   # Docker Compose configuration
```

## Features

- **Search Alerts**: Create custom search criteria for vehicles
- **Automatic Monitoring**: Background scheduler periodically checks for new matches
- **Email Notifications**: Receive email alerts when new matching vehicles are found
- **Seller Type Filtering**: Filter by private sellers or dealers
- **User Authentication**: Secure user registration and login
- **Task Management**: Create, update, and delete search alerts
- **Car Catalog Integration**: Browse manufacturers, models, and submodels

## Technology Stack

### Backend
- **FastAPI**: Modern Python web framework
- **Firebase**: Realtime Database and Authentication
- **MongoDB/MongoEngine**: Database (legacy support)
- **Uvicorn**: ASGI server
- **Python 3.8+**: Runtime environment

### Frontend
- **React**: UI framework
- **JavaScript/JSX**: Frontend language

### Infrastructure
- **Docker**: Containerization
- **SQLite**: HTTP response caching

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Node.js and npm (for frontend)
- Firebase project with Realtime Database
- Email account for sending notifications
- Docker (optional, for containerized deployment)

### Backend Setup

1. Navigate to the project root:
```bash
cd CarAlertz
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
   - Create `backend/secrets/.env` file
   - See `backend/README.md` for required environment variables

4. Set up Firebase:
   - Place Firebase service account JSON in the path specified in `FIREBASE_CERTIFICATE_PATH`
   - Configure Firebase Realtime Database URL

5. Run the backend:
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8081 --reload
```

The API will be available at `http://localhost:8081`

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm start
```

The frontend will be available at `http://localhost:3000`

### Docker Deployment

1. Build and run with Docker Compose:
```bash
docker-compose up -d
```

2. Or build the Docker image:
```bash
docker build -t caralertz .
docker run -p 8081:8081 caralertz
```

## Usage

1. **Register/Login**: Create an account or log in to an existing one
2. **Create Alert**: Use the criteria form to set up search parameters:
   - Select manufacturer, model, and submodel
   - Set year range
   - Set mileage range
   - Choose seller type (all, private, or dealer)
   - Enter email for notifications
3. **Monitor**: The system automatically checks for new matches periodically
4. **Receive Notifications**: Get email alerts when new matching vehicles are found
5. **Manage Tasks**: View, update, or delete your search alerts from the tasks page

## Configuration

### Environment Variables

See `backend/README.md` for detailed environment variable configuration.

Key variables:
- `BASE_API_URL`: Car listing API endpoint
- `FIREBASE_DB_URL`: Firebase Realtime Database URL
- `SENDER_EMAIL`: Email address for sending notifications
- `EMAIL_PASSWORD`: Email password or app password

### CORS Configuration

Configure allowed frontend origins via `FRONTEND_ORIGINS` environment variable (comma-separated list).

## Development

### Code Style
- Python: Follows PEP 8, uses type hints (Python 3.8+)
- JavaScript: Standard React/JSX conventions

### Testing
- Backend tests: `test/` directory
- Run tests as needed for specific modules

### Logging
- Application logs: `internal_info.log`
- Ad update logs: `ads_updates.log`

## Additional Tools

### `find_cars_mimshalti.py`
Standalone script for analyzing vehicle data from Data.gov.il:
- Fetches vehicle records by manufacturer, model, and year
- Retrieves mileage and ownership history
- Provides statistics and filtering capabilities

Usage:
```bash
python find_cars_mimshalti.py
```

## License

[Add your license information here]

## Contributing

[Add contribution guidelines here]

## Support

[Add support/contact information here]

