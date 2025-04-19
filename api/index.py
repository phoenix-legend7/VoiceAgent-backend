from mangum import Mangum
from fastapi import FastAPI
import sys
import os

# Add the parent directory to the path so we can import from main
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import app

# Mangum handler
handler = Mangum(app)
