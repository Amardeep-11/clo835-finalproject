#!/usr/bin/env python3
"""
Enhanced Flask Application for Final Project
Features:
- Configurable background image from S3
- MySQL database integration
- ConfigMap and Secret support
- Logging for background image URL
- Environment variable support
"""

import os
import logging
import boto3
import requests
from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Configuration from environment variables and ConfigMap
BACKGROUND_IMAGE_URL = os.getenv('BACKGROUND_IMAGE_URL', 'https://example.com/default-bg.jpg')
STUDENT_NAME = os.getenv('STUDENT_NAME', 'Amardeep Puri')
DB_HOST = os.getenv('DB_HOST', 'mysql-service')
DB_NAME = os.getenv('DB_NAME', 'clo835_db')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'password')
S3_BUCKET = os.getenv('S3_BUCKET', 'clo835-final-project')
S3_IMAGE_KEY = os.getenv('S3_IMAGE_KEY', 'background.jpg')

# Log the background image URL
logger.info(f"Background image URL: {BACKGROUND_IMAGE_URL}")

def get_db_connection():
    """Create database connection"""
    try:
        connection = mysql.connector.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        return connection
    except Error as e:
        logger.error(f"Error connecting to MySQL Database: {e}")
        return None

def init_database():
    """Initialize database with required tables"""
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            
            # Create database if not exists
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
            cursor.execute(f"USE {DB_NAME}")
            
            # Create users table
            create_table_query = """
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
            cursor.execute(create_table_query)
            connection.commit()
            logger.info("Database initialized successfully")
            
        except Error as e:
            logger.error(f"Error initializing database: {e}")
        finally:
            cursor.close()
            connection.close()

def download_background_image():
    """Download background image from S3 and save locally"""
    try:
        # Create static/images directory if it doesn't exist
        os.makedirs('static/images', exist_ok=True)
        
        # Download image from S3
        s3_client = boto3.client('s3')
        local_path = 'static/images/background.jpg'
        
        s3_client.download_file(S3_BUCKET, S3_IMAGE_KEY, local_path)
        logger.info(f"Background image downloaded from S3: s3://{S3_BUCKET}/{S3_IMAGE_KEY}")
        
        return f"/static/images/background.jpg"
    except Exception as e:
        logger.error(f"Error downloading background image: {e}")
        # Fallback to default background
        return BACKGROUND_IMAGE_URL

@app.route('/')
def index():
    """Main page with user list and background image"""
    connection = get_db_connection()
    users = []
    
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
            users = cursor.fetchall()
        except Error as e:
            logger.error(f"Error fetching users: {e}")
        finally:
            cursor.close()
            connection.close()
    
    # Get background image path
    background_image = download_background_image()
    
    return render_template('index.html', 
                         users=users, 
                         student_name=STUDENT_NAME,
                         background_image=background_image)

@app.route('/add_user', methods=['POST'])
def add_user():
    """Add a new user to the database"""
    name = request.form.get('name')
    email = request.form.get('email')
    
    if not name or not email:
        flash('Name and email are required!', 'error')
        return redirect(url_for('index'))
    
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            insert_query = "INSERT INTO users (name, email) VALUES (%s, %s)"
            cursor.execute(insert_query, (name, email))
            connection.commit()
            flash('User added successfully!', 'success')
            logger.info(f"User added: {name} ({email})")
        except Error as e:
            logger.error(f"Error adding user: {e}")
            flash('Error adding user!', 'error')
        finally:
            cursor.close()
            connection.close()
    
    return redirect(url_for('index'))

@app.route('/delete_user/<int:user_id>')
def delete_user(user_id):
    """Delete a user from the database"""
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            delete_query = "DELETE FROM users WHERE id = %s"
            cursor.execute(delete_query, (user_id,))
            connection.commit()
            flash('User deleted successfully!', 'success')
            logger.info(f"User deleted with ID: {user_id}")
        except Error as e:
            logger.error(f"Error deleting user: {e}")
            flash('Error deleting user!', 'error')
        finally:
            cursor.close()
            connection.close()
    
    return redirect(url_for('index'))

@app.route('/health')
def health():
    """Health check endpoint"""
    return {'status': 'healthy', 'student_name': STUDENT_NAME}

if __name__ == '__main__':
    # Initialize database
    init_database()
    
    # Get port from environment variable or default to 81
    port = int(os.getenv('PORT', 8080))
    
    # Start Flask app on the specified port
    app.run(host='0.0.0.0', port=port, debug=True)
