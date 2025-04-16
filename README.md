# Millis-AI Backend

FastAPI backend for the Millis-AI application.

## Setup

1. Create a virtual environment (optional but recommended):
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file based on `.env.example`:
   ```
   cp .env.example .env
   ```
   Then edit the `.env` file with your actual values.

## Running the Application

Run the development server:
```
python main.py
```

Or with uvicorn directly:
```
uvicorn main:app --reload
```

## API Documentation

Once the application is running, you can access:

- Interactive API documentation: http://localhost:8000/docs
- Alternative API documentation: http://localhost:8000/redoc
- API Health Check: http://localhost:8000/api/v1/health

## Project Structure

```
.
├── app/
│   ├── core/          # Application configuration
│   ├── models/        # Database models
│   ├── routers/       # API route handlers
│   └── schemas/       # Pydantic schemas
├── main.py            # Application entry point
├── requirements.txt   # Project dependencies
└── .env               # Environment variables (not in version control)
``` 