from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy import insert
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

app = Flask(__name__)


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
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password)

        # Automatically set role to 'volunteer' if it's not specified
        role = 'volunteer'

        # Check if the user already exists
        existing_user_query = "SELECT * FROM Users WHERE email = :email"
        existing_user_df = pd.read_sql(existing_user_query, engine, params={'email': email})
        if not existing_user_df.empty:
            return "Error: A user with this email already exists."

        # Save the new user's data
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

        event_date = datetime.strptime(event_date_str, '%Y-%m-%d').date()

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
            event_data.to_sql('Events',
                              engine,
                              if_exists='append',
                              index=False)
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

@app.route('/assigned_events')
def assigned_events():
    # Check if the user is logged in and is a volunteer
    if 'user_id' not in session or session.get('role') != 'volunteer':
        return redirect(url_for('splash_screen'))

    # SQL query to fetch assigned events for the logged-in volunteer
    assigned_events_query = """
        SELECT Events.event_name, Events.event_date, Events.location, VolunteerAssignments.role
        FROM VolunteerAssignments
        JOIN Events ON VolunteerAssignments.event_id = Events.id
        WHERE VolunteerAssignments.user_id = :user_id
        ORDER BY Events.event_date ASC
    """

    # Execute the query
    assigned_events_df = pd.read_sql(assigned_events_query, engine, params={'user_id': session['user_id']})

    # Convert DataFrame to a list of dictionaries for rendering in the template
    assigned_events = assigned_events_df.to_dict(orient='records')

    # Render the assigned events page
    return render_template('assigned_events.html', assigned_events=assigned_events)


@app.route('/notifications')
def notifications():
    if 'user_id' not in session:
        return redirect(url_for('splash_screen'))

    user_id = session['user_id']
    # Fetch notifications for the logged-in user, sorted by date
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

if __name__ == '__main__':
    app.run(debug=True)

