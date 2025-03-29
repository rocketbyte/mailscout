# Email Scout Service

A customizable service that reads Gmail emails, filters them based on patterns, and extracts specific data from email content.

## Features

- Gmail API integration for secure email access
- Customizable email filtering by subject, sender, or other criteria
- Data extraction from email content using configurable patterns
- REST API for configuration and data retrieval
- Asynchronous processing for handling large volumes of emails

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

## Running the Application

```
uvicorn src.api.main:app --reload
```

## API Documentation

Once running, access the API documentation at:
```
http://localhost:8000/docs
```

## Adding Custom Email Filters

Custom email filters can be added through the API or by editing the configuration files in `src/config/email_filters.json`.