from flask import Flask, jsonify
import logging
import os
from logging.handlers import RotatingFileHandler

app = Flask(__name__)

# Create log directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")

os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "application.log")

# Configure rotating file handler
file_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=10 * 1024 * 1024,
    backupCount=5
)

file_handler.setLevel(logging.INFO)

formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)

file_handler.setFormatter(formatter)

# Configure application logger
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)


@app.route("/")
def home():
    app.logger.info("Home endpoint accessed")

    return jsonify({
        "application": "Python AWS Automation Demo",
        "status": "running",
        "message": "Python application is running successfully"
    })


@app.route("/health")
def health():
    app.logger.info("Health check endpoint accessed")

    return jsonify({
        "status": "healthy"
    })


@app.route("/api/data")
def data():
    app.logger.info("Data endpoint accessed")

    return jsonify({
        "data": [
            {"id": 1, "name": "DevOps"},
            {"id": 2, "name": "Python"},
            {"id": 3, "name": "AWS"},
            {"id": 4, "name": "Automation"}
        ]
    })


@app.errorhandler(404)
def not_found(error):
    app.logger.warning("404 endpoint requested")

    return jsonify({
        "error": "Endpoint not found"
    }), 404


@app.errorhandler(500)
def internal_error(error):
    app.logger.error("Internal server error")

    return jsonify({
        "error": "Internal server error"
    }), 500


if __name__ == "__main__":
    app.logger.info("Starting Python application")

    app.run(
        host="0.0.0.0",
        port=5000
    )