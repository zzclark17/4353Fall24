from flask import Flask, render_template, request
import pandas as pd
from sqlalchemy import create_engine

app = Flask(__name__)

engine = create_engine('sqlite:///database.db')

@app.route("/")
def splash_screen():
    return render_template('index.html')

@app.route("/register", methods=['GET', 'POST'])
def register():
     if request.method == 'POST':
         # Extract form data
        email = request.form['email']
        password = request.form['password']  # In production, make sure to hash this!
        full_name = request.form['full_name']
        address_1 = request.form['address_1']
        address_2 = request.form.get('address_2', '')  # Optional
        city = request.form['city']
        state = request.form['state']
        zip_code = request.form['zip_code']
        role = request.form['role']  # Either 'volunteer' or 'admin'

        user_data = pd.DataFrame({
        'email': [email],
        'password': [password],  # Remember to hash the password in production!
        'full_name': [full_name],
        'address_1': [address_1],
        'address_2': [address_2],
        'city': [city],
        'state': [state],
        'zip_code': [zip_code],
        'role': [role]
            })

        user_data.to_sql('Users', engine, if_exists='append', index=False)

        return "Registration successful!"

     else:
        return render_template('registration.html')

if __name__ == '__main__':
    app.run(debug=True)

