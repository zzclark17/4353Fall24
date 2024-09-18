from flask import Flask, render_template, request

app = Flask(__name__)

@app.route("/")
def splash_screen():
    return render_template('index.html')

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        #handle incoming data
        pass
    else:
        return render_template('registration.html')

if __name__ == '__main__':
    app.run(debug=True)

