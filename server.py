from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
from sqlalchemy import create_engine
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta

app = Flask(__name__)

# Setup the connection to your SQLite database
engine = create_engine('sqlite:///database.db')

@app.route("/")
def splash_screen():
    return render_template('index.html')

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Retrieve form data
        email = request.form['email']
        password = request.form['password']
        full_name = request.form['full_name']
        address_1 = request.form['address_1']
        address_2 = request.form.get('address_2', '')
        city = request.form['city']
        state = request.form['state']
        zip_code = request.form['zip_code']
        role = request.form['role']
        preferences = request.form.get('preferences', '')  # Handle preferences
        
        # Handle the selected skills
        skills_list = request.form.getlist('skills[]')  # Get the list of selected skills
        skills = ','.join(skills_list)  # Convert the list to a comma-separated string

        # Hash the password
        hashed_password = generate_password_hash(password)

        # Prepare user data including preferences and skills
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
            'preferences': [preferences],  # Add preferences to user_data
            'skills': [skills]  # Store the comma-separated skills
        })

        try:
            # Insert user data into Users table
            user_data.to_sql('Users', engine, if_exists='append', index=False)
        except Exception as e:
            # Log the exception for debugging
            print(e)
            return "Error: A user with this email already exists."

        # Handle availability (same as before)
        start_date_str = request.form['start_date']
        end_date_str = request.form['end_date']

        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

        if end_date < start_date:
            return "Error: End date cannot be before start date."

        delta = end_date - start_date
        availability_list = [start_date + timedelta(days=i) for i in range(delta.days + 1)]

        availability_data = pd.DataFrame({
            'user_id': [user_id] * len(availability_list),
            'available_date': availability_list
        })

        availability_data.to_sql('Availability', engine, if_exists='append', index=False)

        return "Registration Successful!"
    else:
        return render_template('registration.html')


if __name__ == '__main__':
    app.run(debug=True)
