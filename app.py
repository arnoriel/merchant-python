# app.py
from flask import Flask, jsonify, render_template, redirect, url_for, request
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from datetime import timedelta
from auth import auth_bp, load_data  # Pastikan fungsi load_data diimpor dari auth
from transaction import transaction_bp

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = 'super-secret'  # Ganti ini pada production
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=12)  # Token expire 12 jam
app.config['JWT_TOKEN_LOCATION'] = ['cookies']
app.config['JWT_ACCESS_COOKIE_NAME'] = 'access_token'
app.config['JWT_COOKIE_CSRF_PROTECT'] = False  # Nonaktifkan CSRF hanya untuk pengembangan
app.config['SECRET_KEY'] = 'your_secret_key_here'  # Gunakan kunci yang panjang dan acak di production
jwt = JWTManager(app)

# Register the authentication blueprint
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(transaction_bp, url_prefix='/transaction')

# Halaman Utama
@app.route('/')
def index():
    return render_template('index.html')

# Protected route untuk verifikasi token
@app.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    current_user = get_jwt_identity()  # Get the identity from the token
    return jsonify(logged_in_as=current_user), 200

if __name__ == '__main__':
    app.run(debug=True)

@app.before_request
def redirect_logged_in_user():
    if request.path == url_for("auth.login"):
        access_token = request.cookies.get("access_token")
        if access_token:
            try:
                user_id = get_jwt_identity()
                if user_id:
                    # Alihkan pengguna ke halaman sesuai perannya
                    users = load_data()["users"]
                    user = next((u for u in users if u["id"] == user_id), None)
                    if user:
                        return redirect(url_for(f"auth.{user['role']}"))
            except Exception:
                pass
