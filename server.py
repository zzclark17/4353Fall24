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
        email = request.form['email']
        password = request.form['password']
        full_name = request.form['full_name']
        address_1 = request.form['address_1']
        address_2 = request.form.get('address_2', '')
        city = request.form['city']
        state = request.form['state']
        zip_code = request.form['zip_code']
        role = request.form['role']

        hashed_password = generate_password_hash(password)

        user_data = pd.DataFrame({
            'email': [email],
            'password': [hashed_password],
            'full_name': [full_name],
            'address_1': [address_1],
            'address_2': [address_2],
            'city': [city],
            'state': [state],
            'zip_code': [zip_code],
            'role': [role]
        })

        try:
            user_data.to_sql('Users', engine, if_exists='append', index=False)
        except Exception:
            return "Error: A user with this email already exists."

        user_id_query = "SELECT id FROM Users WHERE email = ?"
        user_id = pd.read_sql(user_id_query, engine, params=[email]).iloc[0]['id']

        skills = request.form.getlist('skills[]')
        for skill_name in skills:
            skill_id_query = "SELECT id FROM Skills WHERE skill_name = ?"
            skill_df = pd.read_sql(skill_id_query, engine, params=[skill_name])
            if skill_df.empty:
                skill_data = pd.DataFrame({'skill_name': [skill_name]})
                skill_data.to_sql('Skills', engine, if_exists='append', index=False)
                skill_id = pd.read_sql(skill_id_query, engine, params=[skill_name]).iloc[0]['id']
            else:
                skill_id = skill_df.iloc[0]['id']

            volunteer_skill_data = pd.DataFrame({
                'user_id': [user_id],
                'skill_id': [skill_id]
            })
            volunteer_skill_data.to_sql('Volunteer_Skills', engine, if_exists='append', index=False)

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

        return redirect(url_for('splash_screen'))
    else:
        return render_template('registration.html')

if __name__ == '__main__':
    app.run(debug=True)

