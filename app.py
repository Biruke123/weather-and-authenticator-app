from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session
from pymongo import MongoClient
import bcrypt
import requests
import os


app = Flask(__name__)
app.secret_key = '%!1nte%*(ysbm+z9)lmxhz+pj0x#jvbh@qkr!=nvyr@=7l$6c3'

port = int(os.environ.get("PORT", 5000))
app.run(host='0.0.0.0', port=port)

mongo_uri = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
client = MongoClient(mongo_uri)
db = client.authDB
users = db.users

API_KEY = "701e97c509ff67b2b3b72ca208f16463"

@app.route('/signup', methods=['GET'])
def signup_page():
    return render_template("signup.html")

@app.route('/signup', methods=['POST'])
def register():
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')

    if not username or not email or not password:
        flash("All fields are required.")
        return redirect(url_for('signup_page'))

    if users.find_one({'email': email}):
        flash("User already exists. Please log in.")
        return redirect(url_for('login_page'))

    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    result = users.insert_one({
        'username': username,
        'email': email,
        'passwordHash': hashed_pw
    })

    session['user_id'] = str(result.inserted_id)
    session['username'] = username

    flash("signup successful. Welcome!")
    return redirect(url_for('index'))

@app.route('/login', methods=['GET'])
def login_page():
    return render_template("login.html")

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')

    user = users.find_one({'email': email})
    if not user:
        flash("User not found.")
        return redirect(url_for('login_page'))

    if bcrypt.checkpw(password.encode('utf-8'), user['passwordHash'].encode('utf-8')):
        session['user_id'] = str(user['_id'])
        session['username'] = user['username']
        flash(f"Welcome back, {user['username']}!")
        return redirect(url_for('index'))
    else:
        flash("Invalid password.")
        return redirect(url_for('login_page'))

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for('login_page'))


@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login_page'))
    return render_template("index.html", username=session.get('username'))


@app.route('/weather')
def get_weather():
    city = request.args.get('city')
    units = request.args.get('units', 'metric')
    if not city:
        return jsonify(error="City is required"), 400

    params = {"q": city, "appid": API_KEY, "units": units}
    try:
        weather_resp = requests.get("https://api.openweathermap.org/data/2.5/weather", params=params)
        weather_resp.raise_for_status()
    except requests.RequestException:
        return jsonify(error="Failed to fetch current weather"), 500

    weather_data = weather_resp.json()
    if weather_data.get("cod") != 200:
        return jsonify(error=weather_data.get("message", "City not found")), 404

    main = weather_data.get("main", {})
    wind = weather_data.get("wind", {})
    description = weather_data.get("weather", [{}])[0].get("main", "").lower()

    forecast_resp = requests.get("https://api.openweathermap.org/data/2.5/forecast", params=params)
    forecasts = []
    if forecast_resp.ok:
        fc = forecast_resp.json()
        entries = fc.get("list", [])[:40]
        for entry in entries[::8]:
            forecasts.append({
                "date": entry.get("dt_txt", "").split()[0],
                "temp": entry.get("main", {}).get("temp"),
                "description": entry.get("weather", [{}])[0].get("description", "")
            })

    return jsonify(
        city=city.title(),
        temperature=main.get("temp"),
        humidity=main.get("humidity"),
        wind_speed=wind.get("speed"),
        description=description,
        forecast=forecasts
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)