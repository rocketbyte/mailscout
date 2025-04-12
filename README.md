# Email Scout Service

[![workflow status](https://github.com/rocketbyte/mailscout/actions/workflows/main.yml/badge.svg)](https://github.com/rocketbyte/mailscout/actions)

A customizable service that reads Gmail emails, filters them based on patterns, and extracts specific data from email content.

## Features

- Gmail API integration for secure email access
- Customizable email filtering by subject, sender, or other criteria
- Data extraction from email content using configurable patterns
- REST API for configuration and data retrieval
- Asynchronous processing for handling large volumes of emails
- Modular storage system with support for:
  - Local JSON file storage
  - MongoDB database storage

## Setup

1. Clone the repository
2. Set up Python environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Set up Google API credentials:
   - Go to [Google Developer Console](https://console.developers.google.com/)
   - Create a project and enable the Gmail API
   - Create OAuth credentials (Desktop application)
   - Download the credentials and configure them in `.env` file (see `.env.example`)

4. Run the authentication script to get your refresh token:
   ```
   python src/utils/auth_setup.py
   ```

5. Create `.env` file based on `.env.example` with your credentials

## Storage Configuration

MailScout supports multiple storage backends that can be configured using environment variables:

### JSON File Storage (Default)

No additional configuration required. Emails are stored as JSON files in the `data/emails/processed_emails/` directory.

### MongoDB Storage

To use MongoDB as the storage backend:

1. Install the MongoDB dependency:
   ```
   pip install pymongo
   ```

2. Set the following environment variables in your `.env` file:
   ```
   MAILSCOUT_STORAGE_TYPE=mongodb
   MONGODB_CONNECTION_STRING=mongodb://localhost:27017
   MONGODB_DATABASE=mailscout
   MONGODB_COLLECTION=emails
   ```

## Running the Application

```
uvicorn src.api.main:app --reload
```

For production deployment:
```
python run.py --host 0.0.0.0 --port 8000
```

## API Documentation

Once running, access the API documentation at:
```
http://localhost:8000/docs
```

## Adding Custom Email Filters

Custom email filters can be added through the API or by editing the configuration files in `src/config/email_filters.json`.