from flask import Blueprint, request, jsonify, session,redirect,url_for,flash
from werkzeug.security import generate_password_hash, check_password_hash
from DB import db, Users

auth_bp = Blueprint('auth', __name__)

# ---------------- SIGNUP ----------------
@auth_bp.route("/signup", methods=["POST"])
def signup():
    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "").strip()
    role = request.form.get("role", "student")

    if not username or not email or not password:
        return jsonify({"status": "error", "message": "All fields are required!"})

    # Case-insensitive check
    existing_user = Users.query.filter(
        (db.func.lower(Users.username) == username.lower()) |
        (db.func.lower(Users.email) == email.lower())
    ).first()
    if existing_user:
        return jsonify({"status": "error", "message": "Username or email already exists!"})

    hashed_password = generate_password_hash(password)
    new_user = Users(username=username, email=email, password=hashed_password, role=role)
    db.session.add(new_user)
    db.session.commit()

    session['user_id'] = new_user.user_id
    session['username'] = new_user.username

    return jsonify({"status": "success", "message": "Signup successful!"})

# ---------------- LOGIN ----------------
@auth_bp.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    if not username or not password:
        return jsonify({"status": "error", "message": "Both fields are required!"})

    user = Users.query.filter(db.func.lower(Users.username) == username.lower()).first()
    if user and check_password_hash(user.password, password):
        session['user_id'] = user.user_id
        session['username'] = user.username
        return jsonify({"status": "success", "message": "Login successful!"})

    return jsonify({"status": "error", "message": "Invalid username or password!"})

# ---------------- LOGOUT ----------------
@auth_bp.route("/logout")
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect(url_for("home"))
