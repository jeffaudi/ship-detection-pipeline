"""WSGI entry point for the application."""

from flask import Flask
from flask_cors import CORS
from src import create_app

app = Flask(__name__)
CORS(app)

app = create_app()
