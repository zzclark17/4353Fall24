from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
from sqlalchemy import create_engine
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

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
        full_name = request.form['full_name']
        address_1 = request.form['address_1']
        address_2 = request.form.get('address_2', '')
        city = request.form['city']
        state = request.form['state']
        zip_code = request.form['zip_code']
        role = request.form['role']
        start_date_str = request.form['start_date']
        end_date_str = request.form['end_date']
        preferences = request.form.get('preferences', '')
        skills_list = request.form.getlist('skills[]')
        skills = ','.join(skills_list)
        hashed_password = generate_password_hash(password)

        existing_user_query = "SELECT * FROM Users WHERE email = :email"
        existing_user_df = pd.read_sql(existing_user_query, engine, params={'email': email})
        if not existing_user_df.empty:
            return "Error: A user with this email already exists."

        user_data = pd.DataFrame({
            'email': [email],
            'password': [hashed_password],
            'full_name': [full_name],
            'address_1': [address_1],
            'address_2': [address_2],
            'city': [city],
            'state': [state],
            'zip_code': [zip_code],
            'role': [role],
            'preferences': [preferences],
            'availability_start': [start_date_str],
            'availability_end': [end_date_str],
            'skills': [skills]
        })

        user_data.to_sql('Users', engine, if_exists='append', index=False)

        new_user_query = "SELECT id FROM Users WHERE email = :email"
        new_user_df = pd.read_sql(new_user_query, engine, params={'email': email})
        user_id = new_user_df['id'].iloc[0]

        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

        if end_date < start_date:
            return "Error: End date cannot be before start date."

        delta = end_date - start_date
        availability_list = [start_date + timedelta(days=i) for i in range(delta.days + 1)]
        availability_list_str = [date.strftime('%Y-%m-%d') for date in availability_list]

        availability_data = pd.DataFrame({
            'user_id': [user_id] * len(availability_list_str),
            'available_date': availability_list_str
        })

        availability_data.to_sql('Availability', engine, if_exists='append', index=False)

        return "Registration Successful!"
    else:
        return render_template('registration.html')

@app.route("/login", methods=['POST'])
def login():
    email_or_username = request.form['username']
    password = request.form['password']

    user_query = "SELECT * FROM Users WHERE email = :email"
    user_df = pd.read_sql(user_query, engine, params={'email': email_or_username})

    if user_df.empty:
        return "Invalid username or password."

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
        return "Invalid username or password."


@app.route('/admin_profile')
def admin_profile():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('splash_screen'))

    return render_template('admin_profile.html', full_name=session.get('full_name'))

@app.route('/volunteer_profile')
def volunteer_profile():
    if 'user_id' not in session or session.get('role') != 'volunteer':
        return redirect(url_for('splash_screen'))

    return render_template('volunteer_profile.html', full_name=session.get('full_name'))

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
            event_data.to_sql('Events', engine, if_exists='append', index=False)
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
    
    user = user_df.iloc[0]
    return render_template('profile_info.html', user=user)

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
        update_query = """
            UPDATE Events
            SET event_name = :event_name,
                event_description = :event_description,
                location = :location,
                required_skills = :required_skills,
                urgency = :urgency,
                event_date = :event_date
            WHERE id = :event_id
        """

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
                conn.execute(update_query, params)
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

    delete_query = "DELETE FROM Events WHERE id = :event_id"
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


    users_query = "SELECT * FROM Users WHERE role = 'volunteer'"
    users_df = pd.read_sql(users_query, engine)

    if 'skills' not in users_df.columns:
        users_df['skills'] = ''

    matching_volunteers = []

    for idx, user in users_df.iterrows():
        user_skills = set()

        if pd.notnull(user.get('skills')):
            user_skills = set(user['skills'].split(','))

        if not required_skills or required_skills.issubset(user_skills):
            availability_query = """
                SELECT * FROM Availability
                WHERE user_id = :user_id AND available_date = :event_date
            """
            availability_df = pd.read_sql(availability_query, engine, params={'user_id': user['id'], 'event_date': event_date})

            if not availability_df.empty:
                matching_volunteers.append(user)

    if request.method == 'POST':
        selected_volunteer_ids = request.form.getlist('volunteer_ids')
        assignment_data = pd.DataFrame({
            'event_id': [event_id] * len(selected_volunteer_ids),
            'user_id': selected_volunteer_ids
        })
        try:
            assignment_data.to_sql('VolunteerAssignments', engine, if_exists='append', index=False)
        except Exception as e:
            print(e)
            return "Error: Failed to assign volunteers."
        return redirect(url_for('manage_events'))

    else:
        volunteers = [vol.to_dict() for vol in matching_volunteers]
        return render_template('match_volunteers.html', event=event, volunteers=volunteers)
    
#Cholponai
@app.route('/show_history')
def show_history():
    # Render the volunteer history page without any predefined data
    return render_template('volunteer_history.html')

@app.route('/notifications')
def notifications():
    return render_template('notifications.html')

if __name__ == '__main__':
    app.run(debug=True)
