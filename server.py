from flask import Flask, render_template, request, redirect, url_for, session
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import pandas as pd
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy import insert
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from datetime import date
from collections import defaultdict
from io import StringIO, BytesIO
import csv

app = Flask(__name__)

#run the command for pdf generation: pip install reportlab
from flask import send_file
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

@app.route('/')
def home():
    return "Hello"


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)

app = Flask(__name__)
app.secret_key = 'your_secret_key'

engine = create_engine('sqlite:///database.db')


@app.route("/")
def splash_screen():
    return render_template('index.html')

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        
        if not email or not password:
            return "Error: Email and password are required."

        hashed_password = generate_password_hash(password)

        role = 'volunteer'

        existing_user_query = "SELECT * FROM Users WHERE email = :email"
        existing_user_df = pd.read_sql(existing_user_query, engine, params={'email': email})
        if not existing_user_df.empty:
            return "Error: A user with this email already exists."

        user_data = pd.DataFrame({
            'email': [email],
            'password': [hashed_password],
            'role': [role]  
        })

        user_data.to_sql('Users', engine, if_exists='append', index=False)

        return "Registration Successful!"
    else:
        return render_template('registration.html')



@app.route("/login", methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')

    if not email or not password:
        return "Email or password not provided.", 400

    user_query = "SELECT * FROM Users WHERE email = :email"
    user_df = pd.read_sql(user_query, engine, params={'email': email})

    if user_df.empty:
        return "Invalid email or password."

    user = user_df.iloc[0]

    if check_password_hash(user['password'], password):
        session['user_id'] = int(user['id'])
        session['role'] = user['role']
        session['full_name'] = user['full_name']

        if user['role'] == 'admin':
            return redirect(url_for('admin_profile'))
        else:
            return redirect(url_for('volunteer_profile'))
    else:
        return "Invalid email or password."


@app.route('/admin_profile')
def admin_profile():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('splash_screen'))

    return render_template('admin_profile.html',
                           full_name=session.get('full_name'))


@app.route('/volunteer_profile')
def volunteer_profile():
    if 'user_id' not in session or session.get('role') != 'volunteer':
        return redirect(url_for('splash_screen'))

    return render_template('volunteer_profile.html',
                           full_name=session.get('full_name'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('splash_screen'))
@app.route('/generate_reports')
def generate_reports():
    # Check if user is an admin
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('splash_screen'))
    return render_template('GenerateReports.html')

@app.route('/generate_pdf_report', methods=['POST'])
def generate_pdf_report():
    # Placeholder for generating PDF report
    # Code to generate the PDF report will go here
    return "PDF Report generated!"


@app.route('/add_event', methods=['GET', 'POST'])
def add_event():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('splash_screen'))

    if request.method == 'POST':
        event_name = request.form['event_name']
        event_description = request.form['event_description']
        location = request.form['location']
        required_skills_list = request.form.getlist('required_skills[]')
        required_skills = ','.join(required_skills_list)
        urgency = request.form['urgency']
        event_date_str = request.form['event_date']

        # Attempt to parse the date
        try:
            event_date = datetime.strptime(event_date_str, '%Y-%m-%d').date()
        except ValueError:
            return "Error: Invalid date format. Please use YYYY-MM-DD."

        # Continue with the rest of the event creation process...
        event_data = pd.DataFrame({
            'event_name': [event_name],
            'event_description': [event_description],
            'location': [location],
            'required_skills': [required_skills],
            'urgency': [urgency],
            'event_date': [event_date],
            'created_by': [session['user_id']]
        })

        try:
            # Save the event to the Events table
            event_data.to_sql('Events', engine, if_exists='append', index=False)

            # Create notifications for all users
            all_users_query = "SELECT id AS user_id FROM Users"
            all_users_df = pd.read_sql(all_users_query, engine)

            # Prepare notification entries for all users
            notifications_data = []
            for user_id in all_users_df['user_id']:
                notifications_data.append({
                    'user_id': user_id,
                    'event_name': event_name,
                    'event_description': event_description,
                    'location': location,
                    'notifications_date': event_date,
                    'read_status': 0
                })

            # Insert notifications into Notifications table
            if notifications_data:
                notifications_df = pd.DataFrame(notifications_data)
                notifications_df.to_sql('Notifications', engine, if_exists='append', index=False)

        except Exception as e:
            print(e)
            return "Error: Failed to create event."

        return redirect(url_for('admin_profile'))
    else:
        return render_template('add_event.html')


@app.route('/manage_events')
def manage_events():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('splash_screen'))

    events_query = "SELECT * FROM Events"
    events_df = pd.read_sql(events_query, engine)

    # Add a column to check if the event date has passed
    current_date = datetime.now()
    events_df['is_past'] = events_df['event_date'].apply(lambda x: datetime.strptime(x, '%Y-%m-%d') < current_date)

    # Convert DataFrame to a list of dictionaries
    events = events_df.to_dict(orient='records')

    return render_template('manage_events.html', events=events)


@app.route('/show_profile_info')
def show_profile_info():
    if 'user_id' not in session:
        return redirect(url_for('splash_screen'))

    user_query = "SELECT * FROM Users WHERE id = :user_id"
    user_df = pd.read_sql(user_query, engine, params={'user_id': session['user_id']})

    if user_df.empty:
        return "User not found."

    user = user_df.iloc[0].to_dict()

    # Make sure 'skills' are properly fetched
    user['skills'] = user.get('skills', '')
    user['skills'] = user['skills'].split(',') if user['skills'] else []

    # Handle availability formatting
    user['availability_start'] = user.get('availability_start', '') if pd.notna(user.get('availability_start')) else None
    user['availability_end'] = user.get('availability_end', '') if pd.notna(user.get('availability_end')) else None

    return render_template('profile_info.html', user=user)


@app.route('/show_history')
def show_history():
    if 'user_id' not in session or session.get('role') != 'volunteer':
        return redirect(url_for('splash_screen'))
    
    return render_template('volunteer_history.html')


@app.route('/get_volunteer_history')
def get_volunteer_history():
    if 'user_id' not in session or session.get('role') != 'volunteer':
        return redirect(url_for('splash_screen'))

    volunteer_id = session['user_id']

    # Query to get the volunteer history for the logged-in user
    query = """
    SELECT e.event_name, vh.participation_status, vh.hours_volunteered, vh.feedback
    FROM Volunteer_History vh
    JOIN Events e ON vh.event_id = e.id
    WHERE vh.volunteer_id = :volunteer_id
    """
    with engine.connect() as conn:
        result = conn.execute(text(query), {'volunteer_id': volunteer_id})
        
        # Convert each row to a dictionary using row._mapping to access columns by name
        volunteer_history = [
            {
                'event_name': row._mapping['event_name'],
                'participation_status': row._mapping['participation_status'],
                'hours_volunteered': row._mapping['hours_volunteered'],
                'feedback': row._mapping['feedback']
            }
            for row in result
        ]

    return jsonify(volunteer_history)


@app.route('/assigned_events')
def assigned_events():
    # Check if the user is logged in and is a volunteer
    if 'user_id' not in session or session.get('role') != 'volunteer':
        return redirect(url_for('splash_screen'))

    # SQL query to fetch assigned events for the logged-in volunteer
    assigned_events_query = """
        SELECT VolunteerAssignments.id AS assignment_id, Events.event_name, Events.event_date, Events.location, VolunteerAssignments.role
        FROM VolunteerAssignments
        JOIN Events ON VolunteerAssignments.event_id = Events.id
        WHERE VolunteerAssignments.user_id = :user_id
          AND VolunteerAssignments.cancelled = 0
        ORDER BY Events.event_date ASC
    """

    # Execute the query
    assigned_events_df = pd.read_sql(assigned_events_query, engine, params={'user_id': session['user_id']})

    # Convert DataFrame to list of dictionaries
    assigned_events = assigned_events_df.to_dict(orient='records')

    # Convert event_date from string to date in each event dictionary
    for event in assigned_events:
        event['event_date'] = datetime.strptime(event['event_date'], '%Y-%m-%d').date()

    # Render template
    return render_template('assigned_events.html', assigned_events=assigned_events, current_date=date.today())

@app.route('/cancel_assignment/<int:assignment_id>', methods=['POST'])
def cancel_assignment(assignment_id):
    # Check if the user is logged in and is a volunteer
    if 'user_id' not in session or session.get('role') != 'volunteer':
        return redirect(url_for('splash_screen'))

    user_id = session['user_id']
    
    # Query to update the assignment's canceled status in VolunteerAssignments
    cancel_query = """
        UPDATE VolunteerAssignments
        SET cancelled = 1
        WHERE id = :assignment_id
          AND user_id = :user_id
    """
    
    # Query to get the event_id from VolunteerAssignments
    get_event_query = """
        SELECT event_id FROM VolunteerAssignments WHERE id = :assignment_id AND user_id = :user_id
    """
    
    # Insert a "Cancelled" entry into Volunteer_History if not already present
    insert_history_query = """
        INSERT INTO Volunteer_History (volunteer_id, event_id, participation_status, hours_volunteered, feedback)
        VALUES (:user_id, :event_id, 'Cancelled', 0, '')
    """
    
    try:
        with engine.connect() as conn:
            trans = conn.begin()  # Start transaction
            
            # Update the cancellation status
            result = conn.execute(text(cancel_query), {'assignment_id': assignment_id, 'user_id': user_id})
            
            if result.rowcount == 0:
                print("No rows updated: Assignment may not exist or another condition prevented the update.")
            else:
                print(f"Successfully canceled assignment with ID {assignment_id}")
            
            # Retrieve the event_id associated with the assignment
            event_result = conn.execute(text(get_event_query), {'assignment_id': assignment_id, 'user_id': user_id})
            event_row = event_result.fetchone()
            
            if event_row is not None:
                event_id = event_row[0]  # Access the first column directly
                print(f"Found event_id {event_id} for assignment ID {assignment_id}")

                # Check if the entry already exists in Volunteer_History
                history_check_query = """
                    SELECT 1 FROM Volunteer_History WHERE volunteer_id = :user_id AND event_id = :event_id
                """
                history_check_result = conn.execute(text(history_check_query), {'user_id': user_id, 'event_id': event_id})
                
                if history_check_result.fetchone() is None:
                    # Insert into Volunteer_History if no entry exists
                    conn.execute(text(insert_history_query), {'user_id': user_id, 'event_id': event_id})
                    print(f"Added to Volunteer_History with 'Cancelled' status for assignment ID {assignment_id}")
                else:
                    print("History entry already exists, skipping insertion.")
            else:
                print(f"No event found for assignment ID {assignment_id}")

            trans.commit()  # Commit transaction

    except SQLAlchemyError as e:
        print(f"Error during cancel and history insertion: {e}")
        return "An error occurred while canceling the assignment and updating history.", 500

    return redirect(url_for('assigned_events'))

@app.route('/manage_volunteers')
def manage_volunteers():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('splash_screen'))

    # Query to get volunteer assignments along with related event and user details, including user_id and event_id
    query = """
        SELECT VolunteerAssignments.id AS assignment_id,
               VolunteerAssignments.user_id,
               VolunteerAssignments.event_id,
               VolunteerAssignments.role,
               Users.full_name,
               Users.id AS user_id,
               Events.event_name,
               Events.id AS event_id,
               Events.event_date,
               VolunteerAssignments.cancelled
        FROM VolunteerAssignments
        JOIN Users ON VolunteerAssignments.user_id = Users.id
        JOIN Events ON VolunteerAssignments.event_id = Events.id
        WHERE VolunteerAssignments.cancelled = 0
        ORDER BY Events.event_date ASC
    """

    with engine.connect() as conn:
        result = conn.execute(text(query)).mappings()  # Use .mappings() to treat each row as a dictionary-like object
        assignments = [dict(row) for row in result]

    return render_template('manage_volunteers.html', assignments=assignments)



@app.route('/save_individual_update/<int:assignment_id>', methods=['POST'])
def save_individual_update(assignment_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('splash_screen'))

    # Get individual form values
    status = request.form.get('status')
    hours = int(request.form.get('hours', 0))  # Default to 0 if empty
    feedback = request.form.get('feedback', '')

    try:
        # Start transaction to ensure data consistency
        with engine.connect() as conn:
            trans = conn.begin()  # Start transaction

            # Retrieve volunteer_id and event_id from VolunteerAssignments
            result = conn.execute(text("""
                SELECT user_id AS volunteer_id, event_id
                FROM VolunteerAssignments
                WHERE id = :assignment_id
            """), {'assignment_id': assignment_id}).mappings().fetchone()

            if result:
                volunteer_id = result['volunteer_id']
                event_id = result['event_id']

                # Check if a history entry exists for this volunteer and event
                history_check_query = """
                    SELECT 1 FROM Volunteer_History
                    WHERE volunteer_id = :volunteer_id AND event_id = :event_id
                """
                history_check_result = conn.execute(text(history_check_query), {
                    'volunteer_id': volunteer_id,
                    'event_id': event_id
                }).fetchone()

                if history_check_result:
                    # Update the existing entry in Volunteer_History
                    conn.execute(text("""
                        UPDATE Volunteer_History
                        SET participation_status = :status,
                            hours_volunteered = :hours,
                            feedback = :feedback
                        WHERE volunteer_id = :volunteer_id AND event_id = :event_id
                    """), {
                        'status': status,
                        'hours': hours,
                        'feedback': feedback,
                        'volunteer_id': volunteer_id,
                        'event_id': event_id
                    })
                    print(f"Updated Volunteer_History entry for volunteer ID {volunteer_id} and event ID {event_id}.")
                else:
                    # Insert a new entry into Volunteer_History
                    conn.execute(text("""
                        INSERT INTO Volunteer_History (volunteer_id, event_id, participation_status, hours_volunteered, feedback)
                        VALUES (:volunteer_id, :event_id, :status, :hours, :feedback)
                    """), {
                        'volunteer_id': volunteer_id,
                        'event_id': event_id,
                        'status': status,
                        'hours': hours,
                        'feedback': feedback
                    })
                    print(f"Inserted new Volunteer_History entry for volunteer ID {volunteer_id} and event ID {event_id}.")

            trans.commit()  # Commit the transaction

        return redirect(url_for('manage_volunteers'))

    except Exception as e:
        print(f"Error saving individual update: {e}")
        return "An error occurred while saving the update.", 500


@app.route('/notifications')
def notifications():
    if 'user_id' not in session:
        return redirect(url_for('splash_screen'))

    user_id = session['user_id']

    # Fetch user skills
    user_skills_query = """
        SELECT skill_name
        FROM Skills
        JOIN Volunteer_Skills ON Skills.id = Volunteer_Skills.skill_id
        WHERE Volunteer_Skills.user_id = :user_id
    """
    user_skills_df = pd.read_sql(user_skills_query, engine, params={'user_id': user_id})
    user_skills = set(user_skills_df['skill_name'].tolist())

    # Find events with matching skills that don't already have a notification for this user
    matching_events_query = """
        SELECT id, event_name, event_description, location, required_skills, event_date
        FROM Events
        WHERE event_date >= DATE('now', '-1 day')  -- Events happening today or later
        AND (
            SELECT COUNT(1)
            FROM Notifications
            WHERE Notifications.user_id = :user_id
            AND Notifications.event_name = Events.event_name
        ) = 0
    """
    matching_events_df = pd.read_sql(matching_events_query, engine, params={'user_id': user_id})

    # Check if any required skills match user skills and create notifications
    for _, event in matching_events_df.iterrows():
        event_skills = set(event['required_skills'].split(','))
        if user_skills.intersection(event_skills):  # Check if there's at least one matching skill
            notification_data = pd.DataFrame({
                'user_id': [user_id],
                'event_name': [event['event_name']],
                'event_description': [event['event_description']],
                'location': [event['location']],
                'notifications_date': [datetime.now()],
                'read_status': [0]
            })
            notification_data.to_sql('Notifications', engine, if_exists='append', index=False)

    # Fetch all notifications for the logged-in user, sorted by date
    notifications_query = """
        SELECT id, event_name, event_description, location, notifications_date, read_status
        FROM Notifications
        WHERE user_id = :user_id
        ORDER BY notifications_date DESC
    """
    notifications_df = pd.read_sql(notifications_query, engine, params={'user_id': user_id})

    # Convert DataFrame to a list of dictionaries for rendering
    notifications = notifications_df.to_dict(orient='records')

    return render_template('notifications.html', notifications=notifications)


@app.route('/mark_notification_read/<int:notification_id>', methods=['POST'])
def mark_notification_read(notification_id):
    if 'user_id' not in session:
        return redirect(url_for('splash_screen'))

    user_id = session['user_id']
    update_query = """
        UPDATE Notifications
        SET read_status = 1
        WHERE id = :notification_id AND user_id = :user_id
    """
    with engine.begin() as conn:
        conn.execute(text(update_query), {'notification_id': notification_id, 'user_id': user_id})

    return '', 204  # Return a no-content response


@app.route('/edit_event/<int:event_id>', methods=['GET', 'POST'])
def edit_event(event_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('splash_screen'))

    event_query = "SELECT * FROM Events WHERE id = :event_id"
    event_df = pd.read_sql(event_query, engine, params={'event_id': event_id})

    if event_df.empty:
        return "Event not found."

    event = event_df.iloc[0]

    if request.method == 'POST':
        event_name = request.form['event_name']
        event_description = request.form['event_description']
        location = request.form['location']
        required_skills_list = request.form.getlist('required_skills[]')
        required_skills = ','.join(required_skills_list)
        urgency = request.form['urgency']
        event_date_str = request.form['event_date']

        event_date = datetime.strptime(event_date_str, '%Y-%m-%d').date()
        update_query = text("""
            UPDATE Events
            SET event_name = :event_name,
                event_description = :event_description,
                location = :location,
                required_skills = :required_skills,
                urgency = :urgency,
                event_date = :event_date
            WHERE id = :event_id
        """)

        params = {
            'event_name': event_name,
            'event_description': event_description,
            'location': location,
            'required_skills': required_skills,
            'urgency': urgency,
            'event_date': event_date,
            'event_id': event_id
        }

        try:
            with engine.begin() as conn:
                conn.execute(update_query, params)  # This will now work
        except Exception as e:
            print(e)
            return "Error: Failed to update event."

        return redirect(url_for('manage_events'))

    else:
        event_dict = event.to_dict()
        return render_template('edit_event.html', event=event_dict)


@app.route('/delete_event/<int:event_id>', methods=['POST'])
def delete_event(event_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('splash_screen'))

    delete_query = text("DELETE FROM Events WHERE id = :event_id")
    try:
        with engine.begin() as conn:
            conn.execute(delete_query, {'event_id': event_id})
    except Exception as e:
        print(e)
        return "Error: Failed to delete event."

    return redirect(url_for('manage_events'))

'''WORKSSSSS
@app.route('/match_volunteers/<int:event_id>', methods=['GET', 'POST'])
def match_volunteers(event_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('splash_screen'))

    event_query = "SELECT * FROM Events WHERE id = :event_id"
    event_df = pd.read_sql(event_query, engine, params={'event_id': event_id})

    if event_df.empty:
        return "Event not found."

    event = event_df.iloc[0]
    required_skills = set(event['required_skills'].split(',')) if event['required_skills'] else set()
    event_date = event['event_date']

    if isinstance(event_date, str):
        event_date = datetime.strptime(event_date, '%Y-%m-%d').date()
    elif isinstance(event_date, pd.Timestamp):
        event_date = event_date.date()

    users_query = """
        SELECT id, email, full_name, skills, availability_start, availability_end
        FROM Users WHERE role = 'volunteer'
    """
    users_df = pd.read_sql(users_query, engine, index_col=None)

    if 'skills' not in users_df.columns:
        users_df['skills'] = ''

    matching_volunteers = []

    for idx, user in users_df.iterrows():
        user_skills = set()
        if pd.notnull(user.get('skills')):
            user_skills = set(user['skills'].split(','))

        if not required_skills or user_skills & required_skills:
            availability_start = user.get('availability_start')
            availability_end = user.get('availability_end')

            if pd.notnull(availability_start) and pd.notnull(availability_end):
                if isinstance(availability_start, str):
                    availability_start = datetime.strptime(availability_start, '%Y-%m-%d').date()
                elif isinstance(availability_start, pd.Timestamp):
                    availability_start = availability_start.date()

                if isinstance(availability_end, str):
                    availability_end = datetime.strptime(availability_end, '%Y-%m-%d').date()
                elif isinstance(availability_end, pd.Timestamp):
                    availability_end = availability_end.date()

                if availability_start <= event_date <= availability_end:
                    user_dict = user.to_dict()
                    user_dict['start_date_str'] = availability_start.strftime('%Y-%m-%d')
                    user_dict['end_date_str'] = availability_end.strftime('%Y-%m-%d')
                    matching_volunteers.append(user_dict)
            else:
                pass

    if request.method == 'POST':
        selected_volunteer_ids = request.form.getlist('volunteer_ids')
        selected_volunteer_ids = [int(vol_id) for vol_id in selected_volunteer_ids]

        assignment_data = pd.DataFrame({
            'event_id': [event_id] * len(selected_volunteer_ids),
            'user_id': selected_volunteer_ids
        })

        try:
            assignment_data.to_sql('VolunteerAssignments', engine, if_exists='append', index=False)
        except Exception as e:
            print(e)
            return f"Error: Failed to assign volunteers. {e}"
        return redirect(url_for('manage_events'))
    else:
        volunteers = matching_volunteers
        print("Volunteers passed to template:", volunteers)
        return render_template('match_volunteers.html', event=event, volunteers=volunteers)

'''

@app.route('/match_volunteers/<int:event_id>', methods=['GET', 'POST'])
def match_volunteers(event_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('splash_screen'))

    # Fetch event data
    event_query = "SELECT * FROM Events WHERE id = :event_id"
    event_df = pd.read_sql(event_query, engine, params={'event_id': event_id})

    if event_df.empty:
        return "Event not found."

    event = event_df.iloc[0]
    required_skills = set(event['required_skills'].split(',')) if event['required_skills'] else set()
    event_date = event['event_date']
    
    if isinstance(event_date, str):
        event_date = datetime.strptime(event_date, '%Y-%m-%d').date()
    elif isinstance(event_date, pd.Timestamp):
        event_date = event_date.date()

    # Get volunteers matching the skills and availability
    users_query = """
        SELECT id, email, full_name, skills, availability_start, availability_end
        FROM Users WHERE role = 'volunteer'
    """
    users_df = pd.read_sql(users_query, engine, index_col=None)

    matching_volunteers = []

    for idx, user in users_df.iterrows():
        user_skills = set(user['skills'].split(',')) if pd.notnull(user['skills']) else set()
        if not required_skills or user_skills & required_skills:
            availability_start = user['availability_start']
            availability_end = user['availability_end']

            if pd.notnull(availability_start):
                if isinstance(availability_start, str):
                    availability_start = datetime.strptime(availability_start, '%Y-%m-%d').date()
                elif isinstance(availability_start, pd.Timestamp):
                    availability_start = availability_start.date()

            if pd.notnull(availability_end):
                if isinstance(availability_end, str):
                    availability_end = datetime.strptime(availability_end, '%Y-%m-%d').date()
                elif isinstance(availability_end, pd.Timestamp):
                    availability_end = availability_end.date()

            if availability_start and availability_end and availability_start <= event_date <= availability_end:
                user_dict = user.to_dict()
                user_dict['start_date_str'] = availability_start.strftime('%Y-%m-%d') if availability_start else ''
                user_dict['end_date_str'] = availability_end.strftime('%Y-%m-%d') if availability_end else ''
                matching_volunteers.append(user_dict)

    if request.method == 'POST':
        selected_volunteer_ids = [int(vol_id) for vol_id in request.form.getlist('volunteer_ids')]

        # Insert into VolunteerAssignments table
        assignment_data = pd.DataFrame({
            'event_id': [event_id] * len(selected_volunteer_ids),
            'user_id': selected_volunteer_ids,
            'role': ['volunteer'] * len(selected_volunteer_ids),
            'status': ['active'] * len(selected_volunteer_ids),  # New field indicating assignment status
            'cancelled': [0] * len(selected_volunteer_ids)       # 0 means not canceled
        })

        try:
            assignment_data.to_sql('VolunteerAssignments', engine, if_exists='append', index=False)
        except Exception as e:
            print(e)
            return f"Error: Failed to assign volunteers. {e}"

        return redirect(url_for('manage_events'))

    return render_template('match_volunteers.html', event=event, volunteers=matching_volunteers)



@app.route('/edit_profile', methods=['GET'])
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('splash_screen'))

    user_query = "SELECT * FROM Users WHERE id = :user_id"
    user_df = pd.read_sql(user_query, engine, params={'user_id': session['user_id']})

    if user_df.empty:
        return "User not found."

    user = user_df.iloc[0].to_dict()
    user['skills'] = user['skills'].split(',') if user['skills'] else []

    return render_template('edit_profile.html', user=user)

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return redirect(url_for('splash_screen'))

    full_name = request.form['full_name']
    address_1 = request.form['address_1']
    address_2 = request.form.get('address_2', '')
    city = request.form['city']
    state = request.form['state']
    zip_code = request.form['zip_code']
    skills_list = request.form.getlist('skills[]')  
    skills = ','.join(skills_list)
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')

    update_query = '''
        UPDATE Users SET
            full_name = :full_name,
            address_1 = :address_1,
            address_2 = :address_2,
            city = :city,
            state = :state,
            zip_code = :zip_code,
            skills = :skills,
            availability_start = :availability_start,
            availability_end = :availability_end
        WHERE id = :user_id
    '''

    params = {
        'full_name': full_name,
        'address_1': address_1,
        'address_2': address_2,
        'city': city,
        'state': state,
        'zip_code': zip_code,
        'skills': skills,
        'availability_start': start_date,
        'availability_end': end_date,
        'user_id': session['user_id']
    }

    with engine.begin() as conn:
        conn.execute(text(update_query), params)

    return redirect(url_for('show_profile_info'))

#report generation: PDF
@app.route('/generate_volunteer_report')
def generate_volunteer_report():
    # Adjusted query to use LEFT JOIN so we get all users, even those without participation history
    query = """
        SELECT Users.full_name, Volunteer_History.event_id, Volunteer_History.participation_status, 
               Volunteer_History.feedback, Volunteer_History.hours_volunteered, Events.event_name
        FROM Users
        LEFT JOIN Volunteer_History ON Volunteer_History.volunteer_id = Users.id
        LEFT JOIN Events ON Volunteer_History.event_id = Events.id
        ORDER BY Users.full_name, Events.event_name
    """
    with engine.connect() as conn:
        result = conn.execute(text(query)).mappings()
        data = [dict(row) for row in result]

    # Initialize PDF document
    pdf_buffer = BytesIO()
    pdf_canvas = canvas.Canvas(pdf_buffer, pagesize=letter)
    pdf_canvas.setTitle("Volunteer Participation Report")

    # Title
    pdf_canvas.setFont("Helvetica-Bold", 16)
    pdf_canvas.drawString(220, 750, "Volunteer Participation Report")

    # Set starting positions
    y_position = 700
    pdf_canvas.setFont("Helvetica", 10)

    # Keep track of the current volunteer
    current_volunteer = None
    total_hours = 0

    for row in data:
        # Check if we are still on the same volunteer or a new one
        if current_volunteer != row['full_name']:
            # Print total hours for the previous volunteer if not the first entry
            if current_volunteer is not None:
                pdf_canvas.drawString(80, y_position, f"Total Hours Volunteered: {total_hours}")
                y_position -= 20

            # Reset for the new volunteer
            current_volunteer = row['full_name']
            total_hours = 0
            y_position -= 40
            pdf_canvas.setFont("Helvetica-Bold", 12)
            pdf_canvas.drawString(80, y_position, f"Volunteer: {row['full_name']}")
            y_position -= 20
            pdf_canvas.setFont("Helvetica", 10)
            pdf_canvas.drawString(80, y_position, "Event Name                 Status            Hours            Feedback")
            y_position -= 20

        # Add details of each event if they have participation history, otherwise indicate no history
        event_name = row['event_name'] if row['event_name'] else "No Events"
        status = row['participation_status'] if row['participation_status'] else "N/A"
        hours = row['hours_volunteered'] if row['hours_volunteered'] is not None else 0
        feedback = row['feedback'] if row['feedback'] else "N/A"
        
        # Only add to total hours if they have actual history
        if row['hours_volunteered'] is not None:
            total_hours += hours

        pdf_canvas.drawString(80, y_position, f"{event_name:<25} {status:<15} {hours:<10} {feedback}")
        y_position -= 20

        # Add page break if space is running out
        if y_position < 50:
            pdf_canvas.showPage()
            y_position = 750

    # Print the last volunteer's total hours
    if current_volunteer is not None:
        pdf_canvas.drawString(80, y_position, f"Total Hours Volunteered: {total_hours}")

    pdf_canvas.save()

    # Move PDF buffer to start
    pdf_buffer.seek(0)

    return send_file(pdf_buffer, as_attachment=True, download_name="Volunteer_Participation_Report.pdf", mimetype='application/pdf')

@app.route('/generate_csv_volunteer_report', methods=['GET'])
def generate_csv_volunteer_report():
    query = """
        SELECT Users.full_name, Volunteer_History.event_id, Volunteer_History.participation_status, 
               Volunteer_History.feedback, Volunteer_History.hours_volunteered, Events.event_name
        FROM Users
        LEFT JOIN Volunteer_History ON Volunteer_History.volunteer_id = Users.id
        LEFT JOIN Events ON Volunteer_History.event_id = Events.id
        ORDER BY Users.full_name, Events.event_name
    """
    with engine.connect() as conn:
        result = conn.execute(text(query)).mappings()
        data = [dict(row) for row in result]

    # Group data by volunteer
    volunteer_data = defaultdict(list)
    for row in data:
        volunteer_data[row['full_name']].append(row)

    # Prepare CSV content
    csv_buffer = StringIO()
    csv_writer = csv.writer(csv_buffer)

    # Write CSV header
    csv_writer.writerow(['Volunteer', 'Event Name', 'Status', 'Hours', 'Feedback'])

    # Write data for each volunteer
    for volunteer, events in volunteer_data.items():
        total_hours = 0
        for row in events:
            event_name = row['event_name'] or "No Events"
            status = row['participation_status'] or "N/A"
            hours = row['hours_volunteered'] or 0
            feedback = row['feedback'] or "N/A"

            # Accumulate total hours
            if row['hours_volunteered']:
                total_hours += hours

            csv_writer.writerow([volunteer, event_name, status, hours, feedback])

        # Write total hours for the volunteer
        csv_writer.writerow([volunteer, "Total Hours Volunteered", "", total_hours, ""])

    # Reset buffer position
    csv_buffer.seek(0)

    # Send CSV file as a response
    return send_file(
        BytesIO(csv_buffer.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='Volunteer_Participation_Report.csv'
    )

# Report Generation: Event Assignments PDF
@app.route('/generate_event_assignments_report')
def generate_event_assignments_report():
    # Query to fetch event details along with volunteer assignments
    query = """
        SELECT Events.id AS event_id, Events.event_name, Events.event_description, Events.location, 
               Events.required_skills, Events.urgency, Events.event_date, 
               Users.full_name AS volunteer_name, VolunteerAssignments.status AS assignment_status,
               VolunteerAssignments.cancelled AS assignment_cancelled
        FROM Events
        LEFT JOIN VolunteerAssignments ON Events.id = VolunteerAssignments.event_id
        LEFT JOIN Users ON VolunteerAssignments.user_id = Users.id
        ORDER BY Events.event_date, Events.event_name, Users.full_name
    """
    with engine.connect() as conn:
        result = conn.execute(text(query)).mappings()
        data = [dict(row) for row in result]

    # Initialize PDF document
    pdf_buffer = BytesIO()
    pdf_canvas = canvas.Canvas(pdf_buffer, pagesize=letter)
    pdf_canvas.setTitle("Event Details and Volunteer Assignments Report")

    # Title
    pdf_canvas.setFont("Helvetica-Bold", 16)
    pdf_canvas.drawString(180, 750, "Event Details and Volunteer Assignments")

    # Set starting positions
    y_position = 700
    pdf_canvas.setFont("Helvetica", 10)

    # Track the current event
    current_event_id = None

    for row in data:
        # Check if we are still on the same event or a new one
        if current_event_id != row['event_id']:
            # Add space between events
            if current_event_id is not None:
                y_position -= 20

            # Print event details
            current_event_id = row['event_id']
            pdf_canvas.setFont("Helvetica-Bold", 12)
            pdf_canvas.drawString(80, y_position, f"Event: {row['event_name']}")
            y_position -= 20

            pdf_canvas.setFont("Helvetica", 10)
            pdf_canvas.drawString(80, y_position, f"Description: {row['event_description']}")
            y_position -= 20
            pdf_canvas.drawString(80, y_position, f"Location: {row['location']}")
            y_position -= 20
            pdf_canvas.drawString(80, y_position, f"Required Skills: {row['required_skills']}")
            y_position -= 20
            pdf_canvas.drawString(80, y_position, f"Urgency: {row['urgency']}")
            y_position -= 20
            pdf_canvas.drawString(80, y_position, f"Date: {row['event_date']}")
            y_position -= 20
            pdf_canvas.drawString(80, y_position, "Assigned Volunteers:")
            y_position -= 20

        # Only display volunteers with active, non-cancelled assignments
        if row['assignment_status'] == 'active' and row['assignment_cancelled'] == 0:
            volunteer_name = row['volunteer_name'] if row['volunteer_name'] else "No volunteers assigned"
            pdf_canvas.drawString(100, y_position, f"- {volunteer_name}")
            y_position -= 20

        # If no volunteers were found for the current event, indicate that
        elif row['volunteer_name'] is None:
            pdf_canvas.drawString(100, y_position, "- No volunteers assigned")
            y_position -= 20

        # Add page break if space is running out
        if y_position < 50:
            pdf_canvas.showPage()
            y_position = 750

    pdf_canvas.save()

    # Move PDF buffer to start
    pdf_buffer.seek(0)

    return send_file(pdf_buffer, as_attachment=True, download_name="Event_Assignments_Report.pdf", mimetype='application/pdf')
@app.route('/generate_csv_assignments_report', methods=['GET'])
def generate_csv_assignments_report():
    query = """
        SELECT Events.id AS event_id, Events.event_name, Events.event_description, Events.location, 
               Events.required_skills, Events.urgency, Events.event_date, 
               Users.full_name AS volunteer_name, VolunteerAssignments.status AS assignment_status,
               VolunteerAssignments.cancelled AS assignment_cancelled
        FROM Events
        LEFT JOIN VolunteerAssignments ON Events.id = VolunteerAssignments.event_id
        LEFT JOIN Users ON VolunteerAssignments.user_id = Users.id
        ORDER BY Events.event_date, Events.event_name, Users.full_name
    """
    with engine.connect() as conn:
        result = conn.execute(text(query)).mappings()
        data = [dict(row) for row in result]
    
    # Prepare CSV content
    csv_buffer = StringIO()
    csv_writer = csv.writer(csv_buffer)
    
    # Write CSV header
    csv_writer.writerow(['Event Name', 'Description', 'Location', 'Required Skills', 'Urgency', 'Event Date', 'Volunteer Name'])
    
    # Group data by event
    from collections import defaultdict
    events = defaultdict(list)
    for row in data:
        events[row['event_id']].append(row)
    
    # Write data for each event
    for event_id, event_rows in events.items():
        # Get event details from the first row
        first_row = event_rows[0]
        event_details = [
            first_row['event_name'],
            first_row['event_description'],
            first_row['location'],
            first_row['required_skills'],
            first_row['urgency'],
            first_row['event_date'],
        ]
        # Get volunteers assigned to this event
        volunteers = []
        for row in event_rows:
            if row['assignment_status'] == 'active' and row['assignment_cancelled'] == 0:
                volunteer_name = row['volunteer_name'] if row['volunteer_name'] else "No volunteers assigned"
                volunteers.append(volunteer_name)
    
        # If no active, non-cancelled volunteers assigned
        if not volunteers:
            volunteers = ["No volunteers assigned"]
    
        # Write a row for each volunteer
        for volunteer in volunteers:
            csv_writer.writerow(event_details + [volunteer])
    
    # Reset buffer position
    csv_buffer.seek(0)
    
    # Send CSV file as a response
    return send_file(
        BytesIO(csv_buffer.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='Event_Assignments_Report.csv'
    )


if __name__ == '__main__':
    app.run(debug=True)

