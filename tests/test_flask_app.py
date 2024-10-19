import sys
import os
import pytest
from flask import session
import uuid
from server import app, engine
from sqlalchemy import text
import pandas as pd  # Add this line to import Pandas
import datetime
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))



"""@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test_secret_key'
    
    with app.test_client() as client:
        with engine.begin() as connection:
            transaction = connection.begin()
            
            yield client
            
            transaction.rollback()
"""
def test_splash_screen(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b"Welcome Back!" in response.data
    assert b"Log In" in response.data
    assert b"Register here" in response.data

def test_register(client):
    unique_email = f"testuser_{uuid.uuid4()}@gmail.com"
    start_date = '2024-10-01'
    end_date = '2024-10-05'

    # Send POST request to register the user
    response = client.post('/register', data={
        'email': unique_email,
        'password': 'password123',
        'full_name': 'Test User',
        'address_1': '123 Test St',
        'address_2': '',
        'city': 'Test City',
        'state': 'TX',
        'zip_code': '12345',
        'role': 'volunteer',
        'start_date': start_date,
        'end_date': end_date,
        'skills[]': ['first_aid', 'CPR']
    }, follow_redirects=True)

    assert response.status_code == 201
    assert b"Registration Successful!" in response.data

    # Query Users table for the new user
    user_query = "SELECT * FROM Users WHERE email = :email"
    user_df = pd.read_sql(user_query, engine, params={'email': unique_email})
    assert not user_df.empty, "User was not successfully added to the database."

    user_id = user_df['id'].iloc[0]

    # Add a small delay before querying the availability table to ensure the data is committed
    time.sleep(1)

    # Query Availability table for the newly added user
    availability_query = "SELECT * FROM Availability WHERE user_id = :user_id"
    availability_df = pd.read_sql(availability_query, engine, params={'user_id': user_id})

    # Corrected datetime parsing
    start_date_obj = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date_obj = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()

    # Check if the correct number of availability dates is stored
    assert len(availability_df) == (end_date_obj - start_date_obj).days + 1, f"Availability dates were not stored correctly for user_id: {user_id}. Found {len(availability_df)} dates instead of {5}."

def test_register_invalid(client):
    response = client.post('/register', data={
        'email': '',
        'password': '',
        'full_name': 'Test User',
        'address_1': '123 Test St',
        'city': 'Test City',
        'state': 'TX',
        'zip_code': '12345',
        'role': 'volunteer',
        'start_date': '2024-10-01',
        'end_date': '2024-10-05',
        'skills[]': ['first_aid', 'CPR']
    }, follow_redirects=True)

    assert response.status_code == 400
    assert b"Error: Missing required fields." in response.data

def test_register_invalid_date_format(client):
    unique_email = f"testuser_{uuid.uuid4()}@gmail.com"
    response = client.post('/register', data={
        'email': unique_email,
        'password': 'password123',
        'full_name': 'Test User',
        'address_1': '123 Test St',
        'address_2': '',
        'city': 'Test City',
        'state': 'TX',
        'zip_code': '12345',
        'role': 'volunteer',
        'start_date': 'invalid_date',
        'end_date': '2024-10-05',
        'skills[]': ['first_aid', 'CPR']
    }, follow_redirects=True)

    assert response.status_code == 400
    assert b"Error: Invalid date format." in response.data

def test_register_start_after_end_date(client):
    unique_email = f"testuser_{uuid.uuid4()}@gmail.com"
    response = client.post('/register', data={
        'email': unique_email,
        'password': 'password123',
        'full_name': 'Test User',
        'address_1': '123 Test St',
        'address_2': '',
        'city': 'Test City',
        'state': 'TX',
        'zip_code': '12345',
        'role': 'volunteer',
        'start_date': '2024-10-05',  
        'end_date': '2024-10-01',
        'skills[]': ['first_aid', 'CPR']
    }, follow_redirects=True)

    assert response.status_code == 400
    assert b"Error: End date cannot be before start date." in response.data

###############################################################################################
def login(client, email, password):
    return client.post('/login', data=dict(
        email=email,
        password=password
    ), follow_redirects=True)

def test_login_valid_admin(client):
    response = login(client, 'zaclark@cougarnet.uh.edu', '1234')
    assert response.status_code == 200
    assert b"Admin Profile" in response.data

def test_login_valid_volunteer(client):
    response = login(client, 'kok@gmail.com', '123')
    assert response.status_code == 200
    assert b"Volunteer Profile" in response.data

def test_login_invalid(client):
    response = login(client, 'wrong_email@gmail.com', 'wrong_password')
    assert response.status_code == 200
    assert b"Invalid email or password." in response.data

"""@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test_secret_key'
    with app.test_client() as client:
        yield client"""

def test_admin_profile_access(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['role'] = 'admin'
        sess['full_name'] = 'Admin User'
    response = client.get('/admin_profile')
    assert response.status_code == 200
    assert b"Welcome, Admin User!" in response.data

def test_non_admin_redirect(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 2
        sess['role'] = 'volunteer'
    response = client.get('/admin_profile', follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome Back!" in response.data

##################################################################
def test_volunteer_profile_access(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 2
        sess['role'] = 'volunteer'
        sess['full_name'] = 'Volunteer User'

    response = client.get('/volunteer_profile')
    assert response.status_code == 200
    assert b"Welcome, Volunteer User!" in response.data

    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['role'] = 'admin'
        sess['full_name'] = 'Admin User'

    response = client.get('/volunteer_profile', follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome to Our Website" in response.data

    response = client.get('/volunteer_profile', follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome to Our Website" in response.data

def test_logout(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['role'] = 'admin'
        sess['full_name'] = 'Admin User'

    response = client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome Back!" in response.data

##########################################################################

def login_as_admin(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 5
        sess['role'] = 'admin'
        sess['full_name'] = 'Zachary Clark'

def test_add_event_access_non_admin(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 11
        sess['role'] = 'volunteer'

    response = client.get('/add_event', follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome Back!" in response.data

def test_add_event_form_get(client):
    login_as_admin(client)
    response = client.get('/add_event')
    assert response.status_code == 200
    assert b"Add Event" in response.data

def test_add_event_success(client):
    login_as_admin(client)

    event_data = {
        'event_name': 'Beach Cleanup',
        'event_description': 'Cleaning the beach',
        'location': 'Santa Monica',
        'required_skills[]': ['first_aid', 'CPR'],
        'urgency': 'High',
        'event_date': '2024-11-20'
    }

    response = client.post('/add_event', data=event_data, follow_redirects=True)
    assert response.status_code == 200
    assert b"Admin Profile" in response.data

def test_add_event_failure(client):
    login_as_admin(client)

    incomplete_event_data = {
        'event_name': 'Test Event',
        'event_description': 'Description',
        'location': 'Test Location',
        'required_skills[]': [],
        'urgency': 'High',
        'event_date': ''
    }

    response = client.post('/add_event', data=incomplete_event_data, follow_redirects=True)
    assert response.status_code == 200
    assert b"Error: Event date is missing." in response.data

def login_as_admin(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['role'] = 'admin'
        sess['full_name'] = 'Admin User'

def login_as_non_admin(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 2
        sess['role'] = 'volunteer'
        sess['full_name'] = 'Volunteer User'

def test_manage_events_access_non_admin(client):
    login_as_non_admin(client)
    response = client.get('/manage_events', follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome Back!" in response.data

def test_manage_events_access_admin(client):
    login_as_admin(client)
    response = client.get('/manage_events')
    assert response.status_code == 200
    assert b"Manage Events" in response.data

def test_manage_events_display(client):
    login_as_admin(client)
    response = client.get('/manage_events')
    assert response.status_code == 200
    assert b"Event Name" in response.data
    assert b"Description" in response.data

def login_user(client, user_id):
    with client.session_transaction() as sess:
        sess['user_id'] = user_id

def test_show_profile_info_redirect_if_not_logged_in(client):
    response = client.get('/show_profile_info', follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome Back!" in response.data

def test_show_profile_info_access(client):
    login_user(client, 5)
    response = client.get('/show_profile_info')
    assert response.status_code == 200
    assert b"Profile Information" in response.data

def test_show_profile_info_display(client):
    login_user(client, 5)
    response = client.get('/show_profile_info')
    assert response.status_code == 200
    assert b"User not found" not in response.data
    assert b"Full Name" in response.data

#######################################################################

def login_as_volunteer(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 11
        sess['role'] = 'volunteer'

def login_as_admin(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 5
        sess['role'] = 'admin'

def test_show_history_access_volunteer(client):
    login_as_volunteer(client)
    response = client.get('/show_history')
    assert response.status_code == 200
    assert b"Volunteer History" in response.data

def test_show_history_access_non_volunteer(client):
    login_as_admin(client)
    response = client.get('/show_history', follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome Back!" in response.data

def login_user(client, user_id):
    with client.session_transaction() as sess:
        sess['user_id'] = user_id

def test_notifications_access_logged_in(client):
    login_user(client, 1)
    response = client.get('/notifications')
    assert response.status_code == 200
    assert b"Notifications" in response.data

def test_notifications_access_non_logged_in(client):
    response = client.get('/notifications', follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome Back!" in response.data

def login_as_admin(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 5
        sess['role'] = 'admin'
        sess['Zachary Clark'] = 'Admin User'

def test_edit_event_access(client):
    login_as_admin(client)
    response = client.get('/edit_event/1')
    assert response.status_code == 200
    assert b"Edit Event" in response.data

def test_edit_event_not_found(client):
    login_as_admin(client)
    response = client.get('/edit_event/9999')
    assert response.status_code == 200
    assert b"Event not found." in response.data

def test_edit_event_success(client):
    login_as_admin(client)
    updated_event_data = {
        'event_name': 'Updated Event Name',
        'event_description': 'Updated description',
        'location': 'Updated location',
        'required_skills[]': ['first_aid', 'cpr'],
        'urgency': 'high',
        'event_date': '2024-11-20'
    }
    response = client.post('/edit_event/1', data=updated_event_data, follow_redirects=True)
    assert response.status_code == 200
    assert b"Manage Events" in response.data

def test_edit_event_form_error(client):
    login_as_admin(client)
    incomplete_event_data = {
        'event_name': '',
        'event_description': 'Updated description',
        'location': 'Updated location',
        'required_skills[]': ['first_aid', 'cpr'],
        'urgency': 'high',
        'event_date': '2024-11-20'
    }
    response = client.post('/edit_event/1', data=incomplete_event_data, follow_redirects=False)
    assert response.status_code == 302
    assert b"Event not found." not in response.data

def login_as_admin(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 5
        sess['role'] = 'admin'
        sess['full_name'] = 'Zachary Clark'

def test_delete_event_success(client):
    login_as_admin(client)
    response = client.post('/delete_event/4', follow_redirects=True)
    assert response.status_code == 200
    assert b"Manage Events" in response.data

def test_delete_event_no_session(client):
    response = client.post('/delete_event/1', follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome Back!" in response.data

def test_delete_event_non_admin(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 11
        sess['role'] = 'volunteer'
    response = client.post('/delete_event/26', follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome Back!" in response.data

##############################################################
def login_as_admin(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 5
        sess['role'] = 'admin'

def login_as_volunteer(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 11
        sess['role'] = 'volunteer'

def insert_event():
    event_query = text("""
        INSERT INTO Events (id, event_name, event_description, location, required_skills, urgency, event_date, created_by)
        VALUES (1, 'Test Event', 'A description', 'Test Location', 'first_aid,cpr', 'high', '2024-11-20', 5)
        ON CONFLICT DO NOTHING;
    """)
    
    with engine.begin() as conn:
        conn.execute(event_query)

def delete_event():
    delete_query = text('DELETE FROM Events WHERE id = 1')
    
    with engine.begin() as conn:
        conn.execute(delete_query)

def test_match_volunteers_access_non_admin(client):
    login_as_volunteer(client)
    response = client.get('/match_volunteers/1', follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome Back!" in response.data

def test_match_volunteers_access_admin(client):
    insert_event()
    login_as_admin(client)
    response = client.get('/match_volunteers/1', follow_redirects=True)
    assert response.status_code == 200
    assert b"Match Volunteers" in response.data

def test_match_volunteers_post_success(client):
    insert_event()
    login_as_admin(client)
    selected_volunteer_ids = ['11', '12']
    response = client.post('/match_volunteers/1', data={'volunteer_ids': selected_volunteer_ids}, follow_redirects=True)
    assert response.status_code == 200
    assert b"Manage Events" in response.data
    delete_event()

def test_match_volunteers_no_event(client):
    login_as_admin(client)
    response = client.get('/match_volunteers/9999', follow_redirects=True)
    assert response.status_code == 200
    assert b"Event not found." in response.data

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test_secret_key'
    
    with app.test_client() as client:
        # Use SQLAlchemy's `engine.begin` and mock rollback after each test
        connection = engine.connect()
        transaction = connection.begin()

        # Use a scoped session for each test
        with app.app_context():
            yield client

        # Rollback after each test
        transaction.rollback()
        connection.close()