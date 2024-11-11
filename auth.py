# auth.py
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, JWTManager, get_jwt_identity
from utils import load_data, save_data
from flask import make_response
import uuid

auth_bp = Blueprint("auth", __name__)

logged_in_users = {}

# Register User
@auth_bp.route("/register", methods=["GET", "POST"])
@jwt_required()
def register():
    if request.method == "POST":
        data = request.form
        name = data.get("name")
        username = data.get("username")
        password = data.get("password")
        role = data.get("role")  # Expecting 'superadmin', 'admin', or 'cashier'
        tabung = int(data.get("tabung", 0))
        kecamatan = data.get("kecamatan")
        kelurahan = data.get("kelurahan")
        kode_pos = data.get("kode_pos")

        data_json = load_data()
        users = data_json["users"]
        if any(user["username"] == username for user in users):
            return jsonify({"msg": "User already exists"}), 400

        hashed_password = generate_password_hash(password)
        new_user = {
            "id": str(uuid.uuid4()),
            "name": name,
            "username": username,
            "password": hashed_password,
            "role": role,  # Store role as string
            "tabung": tabung,
            "kecamatan": kecamatan,
            "kelurahan": kelurahan,
            "kode_pos": kode_pos,
        }
        users.append(new_user)
        save_data(data_json)  # Save all data including users and customers
        
        # Directly redirect to the list of all users after registration
        return redirect(url_for("auth.get_all_users"))

    return render_template("users/register.html")

# Login User
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    # Cek jika pengguna sudah login
    access_token = request.cookies.get("access_token")
    if access_token:
        try:
            # Dapatkan identitas pengguna dari token
            user_id = get_jwt_identity()
            if user_id:
                # Alihkan pengguna ke halaman sesuai peran mereka
                users = load_data()["users"]
                user = next((u for u in users if u["id"] == user_id), None)
                if user:
                    return redirect(url_for(f"auth.{user['role']}"))

        except Exception as e:
            # Jika token tidak valid atau terjadi error, lanjut ke login
            pass

    if request.method == "POST":
        data = request.form
        username = data.get("username")
        password = data.get("password")

        users = load_data()["users"]
        user = next((u for u in users if u["username"] == username), None)
        if not user or not check_password_hash(user["password"], password):
            return jsonify({"msg": "Invalid username or password"}), 401

        # Cek apakah pengguna sudah login di perangkat lain
        if user["id"] in logged_in_users:
            return jsonify({"msg": "Already logged in on another device"}), 403

        # Buat token akses
        access_token = create_access_token(identity=user["id"])
        logged_in_users[user["id"]] = access_token

        # Tentukan halaman tujuan sesuai peran
        if user["role"] == "superadmin":
            response = redirect(url_for("auth.superadmin"))
        elif user["role"] == "admin":
            response = redirect(url_for("auth.admin"))
        elif user["role"] == "cashier":
            response = redirect(url_for("auth.cashier"))
        else:
            return jsonify({"msg": "Role not recognized"}), 403

        # Set token di cookie dan nonaktifkan cache untuk halaman login
        response.set_cookie("access_token", access_token)
        response.headers["Cache-Control"] = "no-store"
        return response

    # Atur no-store cache control untuk GET request login
    response = make_response(render_template("auth/login.html"))
    response.headers["Cache-Control"] = "no-store"
    return response

# Middleware untuk mengecek status login
@auth_bp.before_request
def check_login_status():
    if request.path == "/auth/login" and "access_token" in request.cookies:
        user_id = get_jwt_identity()
        users = load_data()["users"]
        user = next((u for u in users if u["id"] == user_id), None)
        
        # Alihkan pengguna sesuai dengan perannya jika sudah login
        if user:
            if user["role"] == "superadmin":
                return redirect(url_for("auth.superadmin"))
            elif user["role"] == "admin":
                return redirect(url_for("auth.admin"))
            elif user["role"] == "cashier":
                return redirect(url_for("auth.cashier"))

# Logout User
@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    current_user_id = get_jwt_identity()
    # Hapus pengguna dari daftar pengguna yang sedang login
    logged_in_users.pop(current_user_id, None)
    
    response = redirect(url_for("index"))
    response.delete_cookie("access_token")
    return response

# Get All Users
@auth_bp.route("/users", methods=["GET"])
def get_all_users():
    users = load_data()["users"]
    return render_template("users/users.html", users=users)

@auth_bp.route("/aturproduk", methods=["GET"])
@jwt_required()
def atur_produk():
    # Mengambil data pengguna dari file JSON atau database
    data_json = load_data()
    users = data_json["users"]

    # Mengambil ID dari token yang sedang login
    current_user_id = get_jwt_identity()
    logged_in_user = next((user for user in users if user["id"] == current_user_id), None)
    
    if logged_in_user:
        return render_template("userpages/aturproduk.html", current_user=logged_in_user)
    else:
        return jsonify({"msg": "User not found"}), 404

# Update User
@auth_bp.route("/users/update/<id>", methods=["GET", "POST"])
def update_user(id):
    data_json = load_data()
    users = data_json["users"]
    user = next((u for u in users if u["id"] == id), None)

    if not user:
        return jsonify({"msg": "User not found"}), 404

    if request.method == "POST":
        data = request.form
        user["name"] = data.get("name", user["name"])
        user["username"] = data.get("username", user["username"])
        if data.get("password"):
            user["password"] = generate_password_hash(data.get("password"))
        user["role"] = data.get("role", user["role"])
        user["tabung"] = int(data.get("tabung", user["tabung"]))
        user["kecamatan"] = data.get("kecamatan", user["kecamatan"])
        user["kelurahan"] = data.get("kelurahan", user["kelurahan"])
        user["kode_pos"] = data.get("kode_pos", user["kode_pos"])

        save_data(data_json)  # Save all data including users and customers
        return redirect(url_for("auth.get_all_users"))

    return render_template("users/update_user.html", user=user)

# Delete Users
@auth_bp.route("/users/delete/<id>", methods=["POST"])
def delete_user(id):
    data_json = load_data()
    data_json["users"] = [u for u in data_json["users"] if u["id"] != id]

    save_data(data_json)  # Save all data including users and customers
    return redirect(url_for("auth.get_all_users"))

#View Users Profile
@auth_bp.route("/profile", methods=["GET"])
@jwt_required()
def profile():
    data_json = load_data()
    users = data_json["users"]
    
    # Get the ID of the logged-in user from the JWT
    current_user_id = get_jwt_identity()
    user = next((u for u in users if u["id"] == current_user_id), None)
    
    if user:
        return render_template("userpages/profile.html", user=user)
    else:
        return jsonify({"msg": "User not found"}), 404

# Auth Page Routes
@auth_bp.route("/superadmin")
@jwt_required()
def superadmin():
    return render_template("userpages/superadmin.html")

@auth_bp.route("/admin")
@jwt_required()
def admin():
    return render_template("userpages/admin.html")

@auth_bp.route("/cashier")
@jwt_required()
def cashier():
    return render_template("userpages/cashier.html")

# Route untuk halaman daftar Customers
@auth_bp.route("/customers", methods=["GET"])
def get_all_customers():
    # Data customers (sesuaikan dengan data sebenarnya)
    customers = load_data()[
        "customers"
    ]  # Pastikan load_data() memuat data dari data.json
    return render_template("customers/customers.html", customers=customers)

# Create Customer
@auth_bp.route("/customers/create", methods=["GET", "POST"])
def create_customer():
    if request.method == "POST":
        data_json = load_data()
        customers = data_json["customers"]
        new_customer = {
            "id": str(uuid.uuid4()),
            "nik": request.form["nik"],
            "name": request.form["name"],
            "tabung": 0,
            "max_tabung": int(request.form["max_tabung"]),
            "jenis_pengguna": request.form["jenis_pengguna"]  # Tambahkan jenis_pengguna
        }
        customers.append(new_customer)
        save_data(data_json)
        return redirect(url_for("auth.get_all_customers"))
    return render_template("customers/create_customer.html")

# Edit Customer
@auth_bp.route("/customers/edit/<id>", methods=["GET", "POST"])
def edit_customer(id):
    data = load_data()
    customers = data["customers"]
    customer = next((c for c in customers if c["id"] == id), None)
    if not customer:
        return jsonify({"msg": "Customer not found"}), 404

    if request.method == "POST":
        customer["nik"] = request.form["nik"]
        customer["name"] = request.form["name"]
        customer["max_tabung"] = int(request.form["max_tabung"])
        customer["jenis_pengguna"] = request.form["jenis_pengguna"]  # Update jenis_pengguna
        save_data(data)
        return redirect(url_for("auth.get_all_customers"))

    return render_template("customers/edit_customer.html", customer=customer)

# Delete Customer
@auth_bp.route("/customers/delete/<id>", methods=["POST"])
def delete_customer(id):
    data_json = load_data()
    data_json["customers"] = [c for c in data_json["customers"] if c["id"] != id]

    save_data(data_json)  # Save all data including users and customers
    return redirect(url_for("auth.get_all_customers"))

# Edit Customer - Update Tabung Only
@auth_bp.route("/customers/edit_tabung/<id>", methods=["GET", "POST"])
def edit_customer_tabung(id):
    data = load_data()
    customers = data["customers"]
    customer = next((c for c in customers if c["id"] == id), None)
    if not customer:
        return jsonify({"msg": "Customer not found"}), 404

    if request.method == "POST":
        # Only update the 'tabung' field
        customer["tabung"] = int(request.form["tabung"])
        save_data(data)
        return redirect(url_for("auth.get_all_customers"))

    return render_template("customers/edit_customer_tabung.html", customer=customer)