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

No additional configuration required. By default, emails are stored as individual JSON files in the `data/emails/processed_emails/` directory.

#### File Storage Options

When saving emails, you can choose between individual files (chunked storage) or a single bulk file:

- **Individual Files (default)**: Each email is stored as a separate JSON file with its ID as the filename
- **Bulk Storage**: All emails are stored in a single JSON file (`emails_bulk.json`) as an array of email objects

To control this behavior:

1. Using the API:
   ```
   # Save as individual files (default)
   POST /process/{filter_id}?use_chunks=true
   
   # Save to a single bulk file
   POST /process/{filter_id}?use_chunks=false
   ```

2. Using environment variables:
   ```
   # Configure the default storage mode (default is "true")
   MAILSCOUT_USE_CHUNKS=false
   ```

3. Using the storage API directly:
   ```python
   # Save as individual file (default)
   storage.save_email(email_data, use_chunks=True)
   
   # Save to bulk file
   storage.save_email(email_data, use_chunks=False)
   ```

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

#### MongoDB Storage Options

Similar to JSON storage, MongoDB supports two storage approaches:

- **Individual Collection (default)**: Each email is stored as a separate document in the main collection
- **Bulk Collection**: Emails are stored as documents in a separate bulk collection

You can configure the bulk collection name (default: "emails_bulk") with:
```
MONGODB_BULK_COLLECTION=my_bulk_collection_name
```

To control this behavior:

1. Using the API:
   ```
   # Save to individual collection (default)
   POST /process/{filter_id}?use_chunks=true
   
   # Save to bulk collection
   POST /process/{filter_id}?use_chunks=false
   ```

2. Using environment variables:
   ```
   # Configure the default storage mode (default is "true")
   MAILSCOUT_USE_CHUNKS=false
   ```

3. Using the storage API directly:
   ```python
   # Save to individual collection (default)
   storage.save_email(email_data, use_chunks=True)
   
   # Save to bulk collection
   storage.save_email(email_data, use_chunks=False)
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