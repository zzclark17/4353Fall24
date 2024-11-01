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

def test_register_invalid(client):
    response = client.post('/register', data={'email': 'unique@example.com', 'password': '', 'role': 'volunteer'})
    assert response.status_code == 200
    assert b"Error: Email and password are required." in response.data



def test_register_success(client):
    # Generate a unique email each time the test runs
    unique_email = f"newuser_{uuid.uuid4()}@example.com"
    response = client.post('/register', data={
        'email': unique_email,
        'password': 'password123',
        'role': 'volunteer'  # This can be omitted since 'volunteer' is the default
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Registration Successful!" in response.data

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

def test_login_invalid(client):
    response = login(client, 'wrong_email@gmail.com', 'wrong_password')
    assert response.status_code == 200
    assert b"Invalid email or password." in response.data


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
        sess['role'] = 'volunteer'  # Non-admin role

    response = client.get('/add_event', follow_redirects=True)

    # Check if redirected to splash screen (e.g., by checking a known element in splash_screen)
    assert response.status_code == 200
    assert b"Welcome to Our Website" in response.data  # Replace with actual splash screen text or title




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
        'event_date': 'invalid_date'  # Invalid date format
    }

    response = client.post('/add_event', data=incomplete_event_data, follow_redirects=True)
    assert response.status_code == 200
    assert b"Error: Invalid date format. Please use YYYY-MM-DD." in response.data




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
    response = client.get('/edit_event/5')
    assert response.status_code == 200
    assert b"Edit Event" in response.data


def test_edit_event_not_found(client):
    login_as_admin(client)
    response = client.get('/edit_event/9999')
    assert response.status_code == 200
    assert b"Event not found." in response.data

    
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

def test_update_profile_success(client):
    # Simulate a logged-in user by setting the session with user_id
    with client.session_transaction() as sess:
        sess['user_id'] = 11  # Set a valid user_id

    # Define profile data to update
    update_data = {
        'full_name': 'John Doe',
        'address_1': '123 Main St',
        'address_2': 'Apt 4B',
        'city': 'Anytown',
        'state': 'TX',
        'zip_code': '12345',
        'skills[]': ['first_aid', 'CPR'],  # List for multi-value form field
        'start_date': '2024-01-01',
        'end_date': '2024-12-31'
    }

    # Make POST request to update profile
    response = client.post('/update_profile', data=update_data, follow_redirects=True)

    # Check that the response redirects to 'show_profile_info'
    assert response.status_code == 200
    assert b"Profile Information" in response.data  # Adjust based on the content of the profile page

def test_update_profile_redirect_if_not_logged_in(client):
    # Attempt to update profile without being logged in (no user_id in session)
    update_data = {
        'full_name': 'John Doe',
        'address_1': '123 Main St',
        'address_2': 'Apt 4B',
        'city': 'Anytown',
        'state': 'TX',
        'zip_code': '12345',
        'skills[]': ['first_aid', 'CPR'],
        'start_date': '2024-01-01',
        'end_date': '2024-12-31'
    }

    # Make POST request to update profile without setting session user_id
    response = client.post('/update_profile', data=update_data, follow_redirects=True)

    # Check if redirected to splash screen
    assert response.status_code == 200
    assert b"Welcome to Our Website" in response.data  # Adjust to match the splash screen content

def test_show_profile_info_not_logged_in(client):
    # Attempt to access the profile without being logged in
    response = client.get('/show_profile_info', follow_redirects=True)
    
    # Check for redirection to the splash screen
    assert response.status_code == 200
    assert b"Welcome to Our Website" in response.data  # Adjust to the content of splash_screen

def test_show_profile_info_user_not_found(client):
    # Simulate a logged-in user by setting a user_id that does not exist in the database
    with client.session_transaction() as sess:
        sess['user_id'] = 999  # Set to an ID that does not exist

    response = client.get('/show_profile_info')
    
    # Check that it returns "User not found."
    assert response.status_code == 200
    assert b"User not found." in response.data

def test_show_profile_info_success(client):
    # Add a test user to the database for this test
    with engine.begin() as conn:
        conn.execute(text('''
            INSERT INTO Users (id, full_name, email, password, skills, availability_start, availability_end)
            VALUES (:id, :full_name, :email, :password, :skills, :availability_start, :availability_end)
            ON CONFLICT(id) DO NOTHING
        '''), {
            'id': 1,
            'full_name': 'John Doe',
            'email': 'testuser@example.com',
            'password': 'hashedpassword',  # Use a hashed password as appropriate
            'skills': 'first_aid,CPR',
            'availability_start': '2024-01-01',
            'availability_end': '2024-12-31'
        })

    # Simulate a logged-in user with a valid user_id
    with client.session_transaction() as sess:
        sess['user_id'] = 1  # ID matches the test user added above

    response = client.get('/show_profile_info')
    
    # Check that the profile page loads correctly and displays the user's info
    assert response.status_code == 200
    assert b"John Doe" in response.data  # Check if the full name appears
    assert b"first_aid" in response.data  # Verify skills are parsed correctly
    assert b"2024-01-01" in response.data  # Verify availability dates are displayed
    assert b"2024-12-31" in response.data
####def test_delete_event_not_logged_in(client):
    # Attempt to delete an event without being logged in
    response = client.post('/delete_event/1', follow_redirects=True)

    # Check if redirected to splash screen
    assert response.status_code == 200
    assert b"Welcome to Our Website" in response.data  # Adjust based on splash screen content

def test_delete_event_non_admin(client):
    # Simulate a logged-in user with a non-admin role
    with client.session_transaction() as sess:
        sess['user_id'] = 2  # Assume user_id 2 exists
        sess['role'] = 'volunteer'  # Non-admin role

    # Attempt to delete an event
    response = client.post('/delete_event/1', follow_redirects=True)

    # Check if redirected to splash screen
    assert response.status_code == 200
    assert b"Welcome to Our Website" in response.data  # Adjust based on splash screen content


def test_delete_event_failure(client, monkeypatch):
    # Simulate a logged-in admin user
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['role'] = 'admin'

    # Mock the engine to raise an exception on execute
    def mock_execute(*args, **kwargs):
        raise Exception("Database deletion failed")

    with monkeypatch.context() as m:
        m.setattr(engine, "begin", lambda: mock_execute)

        # Attempt to delete an event, expecting a failure message
        response = client.post('/delete_event/1')
        assert response.status_code == 200
        assert b"Error: Failed to delete event." in response.data

def test_login_as_admin(client):
    # Use the helper function to simulate an admin login
    login_as_admin(client)
    
    # Verify session values
    with client.session_transaction() as sess:
        assert sess['user_id'] == 5
        assert sess['role'] == 'admin'

def test_login_as_volunteer(client):
    # Use the helper function to simulate a volunteer login
    login_as_volunteer(client)
    
    # Verify session values
    with client.session_transaction() as sess:
        assert sess['user_id'] == 11
        assert sess['role'] == 'volunteer'

def test_insert_event():
    # Call the insert_event function to insert a test event into the database
    insert_event()
    
    # Query the database to check if the event was added
    with engine.begin() as conn:
        result = conn.execute(
            text("SELECT * FROM Events WHERE id = 1")
        ).mappings()  # Use .mappings() to get a dictionary-like row
    
        event = result.fetchone()
    
    # Verify event details
    assert event is not None
    assert event['event_name'] == 'Test Event'
    assert event['event_description'] == 'A description'
    assert event['location'] == 'Test Location'
    assert event['required_skills'] == 'first_aid,cpr'
    assert event['urgency'] == 'high'
    assert str(event['event_date']) == '2024-11-20'

def test_insert_event_duplicate():
    # Insert the event once
    insert_event()

    # Insert the event a second time to check for duplicate handling
    insert_event()

    # Query the database to check that there is still only one event
    with engine.begin() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM Events WHERE id = 1"))
        count = result.scalar()
    
    # Verify that only one event exists due to 'ON CONFLICT DO NOTHING'
    assert count == 1

def test_edit_profile_access(client):
    # Simulate a logged-in user by setting the session with user_id
    with client.session_transaction() as sess:
        sess['user_id'] = 11  # Set to a valid user ID

    # Perform a GET request to the edit_profile route
    response = client.get('/edit_profile', follow_redirects=True)
    
    # Check if the status code is 200, indicating successful access
    assert response.status_code == 200
    
    # Check if the edit profile page is displayed with expected elements
    assert b"Edit Profile" in response.data
    assert b"full_name" in response.data  # Checking for form field presence
    assert b"address_1" in response.data
    assert b"city" in response.data


@pytest.fixture
def client(request):
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test_secret_key'
    
    with app.test_client() as client:
        # Establish a database connection and start a transaction
        connection = engine.connect()
        transaction = connection.begin()

        # Push the app context and yield the client to the test
        with app.app_context():
            yield client

        # Check if the test is marked with `commit`
        if not request.node.get_closest_marker("commit"):
            # Rollback after each test unless marked with `commit`
            transaction.rollback()
        else:
            # Commit the transaction if marked with `commit`
            transaction.commit()

        connection.close()

