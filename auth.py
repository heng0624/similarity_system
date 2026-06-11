from flask import Blueprint, request, jsonify, session,redirect,url_for,flash
from werkzeug.security import generate_password_hash, check_password_hash
from DB import db, Users
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
import re
import hashlib
import requests
from extensions import mail

serializer = URLSafeTimedSerializer("supersecret")

auth_bp = Blueprint('auth', __name__)



# -------------------- EMAIL VERIFY ROUTE --------------------
def is_valid_email(email):
    pattern = r'^[^@\s]+@[^@\s]+\.[^@\s]+$'
    return re.match(pattern, email) is not None
# -------------------- EMAIL FUNCTION --------------------
def send_verification_email(email):
    token = serializer.dumps(email, salt="email-verify")
    verify_link = f"http://localhost:5000/verify/{token}"

    msg = Message(
        subject="Verify Your Email",
        recipients=[email],
        body=f"Click this link to verify your email: {verify_link}"
    )
    mail.send(msg)

@auth_bp.route("/update_profile", methods=["POST"])
def update_profile():
    if not session.get("user_id"):
        return jsonify({"status": "error", "message": "Not logged in"})

    user = Users.query.get(session["user_id"])
    data = request.json

    # ---------- USERNAME ----------
    if "username" in data:
        user.username = data["username"]

    # ---------- EMAIL ----------
    if "email" in data:
        new_email = data["email"]

        # 1. Validate format
        if not is_valid_email(new_email):
            return jsonify({"status": "error", "message": "Invalid email format"})

        # 2. Check duplicate
        exists = Users.query.filter(
            Users.email == new_email,
            Users.user_id != user.user_id
        ).first()
        if exists:
            return jsonify({"status": "error", "message": "Email already in use"})

        # 3. Update email + reset verification
        user.email = new_email
        user.is_verified = False

        # 4. Send verification email
        send_verification_email(new_email)

    db.session.commit()

    session["username"] = user.username
    return jsonify({
        "status": "success",
        "message": "Profile updated. Please verify your new email."
 })



# ---------------- SIGNUP ----------------
@auth_bp.route("/signup", methods=["POST"])
def signup():
    data = request.form

    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not is_valid_email(email):
        return jsonify({"status": "error", "message": "Invalid email format!"})

    if Users.query.filter_by(email=email).first():
        return jsonify({"status": "error", "message": "Email already in use!"})

    if not is_strong_password(password):
        return jsonify({"status": "error", "message": "Password too weak!"})

    if is_pwned(password):
        return jsonify({"status": "error", "message": "Password leaked!"})

    # 🔴 CREATE USER BUT DO NOT LOGIN
    new_user = Users(
        username=username,
        email=email,
        role="student",
        is_verified=False
    )
    new_user.set_password(password)

    db.session.add(new_user)
    db.session.commit()

    # 🔴 SEND EMAIL ONLY
    send_verification_email(email)

    return jsonify({
        "status": "success",
        "message": "Signup successful! Please verify your email before login."
    })

def is_strong_password(password):
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"[0-9]", password):
        return False
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False
    return True

def is_pwned(password):
    sha1pwd = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
    prefix, suffix = sha1pwd[:5], sha1pwd[5:]

    res = requests.get(f"https://api.pwnedpasswords.com/range/{prefix}")
    
    if res.status_code != 200:
        return False  # API error → just ignore

    hashes = (line.split(":") for line in res.text.splitlines())

    for h, count in hashes:
        if h == suffix:
            return True  # password is found/leaked

    return False



@auth_bp.route("/verify/<token>")
def verify_email(token):
    try:
        # Decode email from token
        email = serializer.loads(token, salt="email-verify", max_age=3600)
    except:
        return "Verification link expired or invalid."

    # Find user
    user = Users.query.filter_by(email=email).first()
    if not user:
        return "User not found."

    # Mark as verified
    user.is_verified = True
    db.session.commit()

    # ------------------ AUTO LOGIN ------------------
    session['user_id'] = user.user_id
    session['username'] = user.username

    return redirect(url_for("home"))

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
