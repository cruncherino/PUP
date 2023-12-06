from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import requests

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.secret_key = 'bigLun@3000'
db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.init_app(app)

# Model for saved pets
class SavedPet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    pet_id = db.Column(db.String(50), nullable=False)

# Model for users
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    saved_pets = db.relationship('SavedPet', backref='user', lazy=True)

    def __init__(self, username, password):
        self.username = username
        self.password = password

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# API Key and Secret
api_key = "euh8itVWayyKsKr3ofZiSUlwFRV9umv1WxkDoZTgtgjcjWw1fV"
secret = "xIurjWkpPAi1T2So1C0cDpoYtWkhiYjQ7GNSMqWR"

# Obtain the access token
url = "https://api.petfinder.com/v2/oauth2/token"
data = {
    "grant_type": "client_credentials",
    "client_id": api_key,
    "client_secret": secret
}
response = requests.post(url, data=data)
token = response.json().get('access_token')

animals_url = "https://api.petfinder.com/v2/animals"
headers = {
    "Authorization": f"Bearer {token}"
}

# Initial route
@app.route('/')
def welcome():
    return render_template('initial.html')

# Search route
@app.route('/index', methods=['POST'])
def search():
    if request.method == 'POST':
        search_term = request.form['search']

        # Make a request to the Petfinder API to get animals
        params = {'type': search_term, 'sort': 'random', 'limit': 50}
        animals_response = requests.get(animals_url, headers=headers, params=params)

        if animals_response.status_code == 200:
            animals_data = animals_response.json()

            # Check if there is a key that contains the list of pets
            if 'animals' in animals_data:
                # Filter out pets without photos
                pets_with_photos = [pet for pet in animals_data['animals'] if pet.get('photos')]

                if pets_with_photos:
                    return render_template('index.html', pets=pets_with_photos)

    # Display an error message when there's an issue with fetching pet data
    return render_template('initial.html', error_message="We don't have that friend yet!")

# Home Button route
@app.route('/home')
def home():
    return render_template('initial.html')

@app.route('/dog')
def dog():
    # Fetch the state query parameter from the URL
    selected_state = request.args.get('state')

    # Fetch dog data using the Petfinder API with specific parameters
    params = {'type': 'dog', 'sort': 'random', 'limit': 50, 'location': selected_state}
    dogs_response = requests.get(animals_url, headers=headers, params=params)

    if dogs_response.status_code == 200:
        dogs_data = dogs_response.json()

        if 'animals' in dogs_data:
            dogs_with_photos = [dog for dog in dogs_data['animals'] if dog.get('photos')]

            if dogs_with_photos:
                return render_template('dog.html', dogs=dogs_with_photos)

    return render_template('initial.html', error_message="We don't have that friend yet!")

@app.route('/cat')
def cat():
    # Fetch the state query parameter from the URL
    selected_state = request.args.get('state')

    # Fetch cat data using the Petfinder API with parameters
    params = {'type': 'cat', 'sort': 'random', 'limit': 50, 'location': selected_state}
    cats_response = requests.get(animals_url, headers=headers, params=params)

    if cats_response.status_code == 200:
        cats_data = cats_response.json()

        if 'animals' in cats_data:
            cats_with_photos = [cat for cat in cats_data['animals'] if cat.get('photos')]

            if cats_with_photos:
                return render_template('cat.html', cats=cats_with_photos)

    return render_template('initial.html', error_message="We don't have that friend yet!")

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            # Redirect to the profile page with the username as a parameter
            login_user(user)
            return redirect(url_for('profile', username=username))
        else:
            flash('Login unsuccessful. Please check your username and password.')

    return render_template('login.html')

@app.route('/profile/<username>')
@login_required
def profile(username):
    user = User.query.filter_by(username=username).first()

    if user:
        saved_pets = SavedPet.query.filter_by(user_id=user.id).all()

        for saved_pet in saved_pets:
            # Make API request to Petfinder using the saved_pet.pet_id
            pet_id = saved_pet.pet_id
            pet_details = fetch_pet_details_from_api(pet_id)

            # Update saved_pet with details for profile
            if pet_details:
                # Store name
                saved_pet.name = pet_details.get('name')
                # Store age
                saved_pet.age = pet_details.get('age')
                # Store contact information
                saved_pet.contact = pet_details.get('contact', {})
                # Store address information
                saved_pet.address = pet_details.get('address', {})
                # Store photo URLs
                saved_pet.photos = pet_details.get('photos', [])

        return render_template('profile.html', user=user, saved_pets=saved_pets)

    else:
        flash('User not found.')
        return redirect(url_for('login'))

def fetch_pet_details_from_api(pet_id):
    # Make API request to Petfinder using the provided pet_id
    url = f'https://api.petfinder.com/v2/animals/{pet_id}'
    headers = {'Authorization': f'Bearer {token}'}

    try:
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            pet_details = response.json().get('animal', {})

            # Extract photo URLs
            photos = pet_details.get('photos', [])
            photo_urls = [photo['medium'] for photo in photos]

            additional_details = {
                'name': pet_details.get('name'),
                'age': pet_details.get('age'),
                'contact': pet_details.get('contact', {}),
                'address': pet_details.get('contact', {}).get('address', {}),
                'photos': photo_urls,
            }

            return additional_details

        else:
            print(f"Error fetching pet details: {response.text}")

    except Exception as e:
        print(f"Error fetching pet details: {e}")

    return None

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/check_auth')
def check_auth():
    return {'authenticated': current_user.is_authenticated}

# Signup route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_password)

        db.session.add(new_user)
        db.session.commit()

        flash('Account created successfully! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/pet_details/<pet_id>')
def pet_details(pet_id):
    pet_details_url = f"https://api.petfinder.com/v2/animals/{pet_id}"
    pet_details_response = requests.get(pet_details_url, headers=headers)

    if pet_details_response.status_code == 200:
        pet_details_data = pet_details_response.json().get('animal')

        return render_template('pet_details.html', pet=pet_details_data)

    return "Error fetching pet details"

@app.route('/save_pet/<pet_id>', methods=['POST'])
@login_required
def save_pet(pet_id):
    # Check if the pet is already saved by the user
    existing_saved_pet = SavedPet.query.filter_by(user_id=current_user.id, pet_id=pet_id).first()

    if existing_saved_pet:
        # Pet is already saved, remove it from the user's saved pets
        db.session.delete(existing_saved_pet)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Pet removed from saved pets'})
    else:
        # Save the pet to the user's saved pets
        new_saved_pet = SavedPet(user_id=current_user.id, pet_id=pet_id)
        db.session.add(new_saved_pet)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Pet saved successfully'})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        app.run(debug=True, host='0.0.0.0')
