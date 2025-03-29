import os
import argparse
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    """Run the MailScout API server."""
    parser = argparse.ArgumentParser(description="Run the MailScout API server")
    parser.add_argument(
        "--host", default="127.0.0.1", help="Host to bind the server to"
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Port to bind the server to"
    )
    parser.add_argument(
        "--reload", action="store_true", help="Enable auto-reload on code changes"
    )
    
    args = parser.parse_args()
    
    # Create data directory if it doesn't exist
    os.makedirs("./data/emails", exist_ok=True)
    
    # Run the server
    uvicorn.run(
        "src.api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )

if __name__ == "__main__":
    main()