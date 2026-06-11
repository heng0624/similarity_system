from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from DB import init_db, db, Users, AnalysisHistory, FeatureCache
from auth import auth_bp
from utils.text_similarity import compute_text_similarity
from utils.image_similarity import compute_image_similarity
from utils.code_similarity import compute_code_similarity
import os, hashlib, pickle
from sentence_transformers import util
import numpy as np
import torch.nn.functional as F

from utils.text_similarity import get_text_embedding
from utils.image_similarity import get_image_embedding
from utils.code_similarity import get_code_embedding


app = Flask(__name__)
app.config["SECRET_KEY"] = "supersecret"

# Initialize DB
init_db(app)
app.register_blueprint(auth_bp)

with app.app_context():
    db.create_all()

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)




# --------------------------------------------------------
# 🔥 UTILITY: HASH FILE (for FeatureCache)
# --------------------------------------------------------
def hash_file(filepath):
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        hasher.update(f.read())
    return hasher.hexdigest()



# --------------------------------------------------------
# 🔥 FEATURE CACHE SYSTEM
# --------------------------------------------------------
def get_or_cache_embedding(file_path, modality, embed_function):
    """
    embed_function(file_path) → returns embedding (vector)
    """

    file_hash = hash_file(file_path)

    # Check cache
    cached = FeatureCache.query.filter_by(file_hash=file_hash).first()
    if cached:
        cached.last_accessed = db.func.now()
        db.session.commit()
        return pickle.loads(cached.embedding)

    # Compute new embedding
    vector = embed_function(file_path)

    # Store in DB
    new_cache = FeatureCache(
        file_hash=file_hash,
        embedding=pickle.dumps(vector),
        modality=modality
    )
    db.session.add(new_cache)
    db.session.commit()

    return vector



# --------------------------------------------------------
# 🔥 Web Routes
# --------------------------------------------------------
@app.route("/")
def root():
    return redirect(url_for("home"))


@app.route("/home")
def home():
    return render_template("index.html")


@app.route("/history")
def history():
    if not session.get("user_id"):
        return redirect(url_for("home"))

    uid = session["user_id"]
    history = AnalysisHistory.query.filter_by(user_id=uid).order_by(
        AnalysisHistory.timestamp.desc()
    ).all()

    return render_template("history.html", history=history)



@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("home"))
    user = Users.query.get(session["user_id"])
    return render_template("profile.html", user=user)



@app.route("/update_profile", methods=["POST"])
def update_profile():
    if not session.get("user_id"):
        return jsonify({"status": "error", "msg": "Not logged in"})

    user = Users.query.get(session["user_id"])
    data = request.json

    if "username" in data:
        user.username = data["username"]
    if "email" in data:
        user.email = data["email"]

    db.session.commit()
    session["username"] = user.username

    return jsonify({"status": "success", "msg": "Profile updated successfully"})




# --------------------------------------------------------
# 🔥 SIMILARITY API (with DB save + cache + user history)
# --------------------------------------------------------
@app.route("/similarity", methods=["POST"])
@app.route("/similarity", methods=["POST"])
def similarity():
    try:
        if not session.get("user_id"):
            return jsonify({"error": "Login required"}), 403

        user_id = session["user_id"]

        file1 = request.files.get("file1")
        file2 = request.files.get("file2")
        mode = request.form.get("mode")

        if not file1 or not file2 or not mode:
            return jsonify({"error": "Missing inputs"}), 400

        # Save files
        p1 = os.path.join(UPLOAD_FOLDER, file1.filename)
        p2 = os.path.join(UPLOAD_FOLDER, file2.filename)
        file1.save(p1)
        file2.save(p2)

        # ------------------------------
        # TEXT
        # ------------------------------
        if mode == "document":
            text1 = open(p1, "r", encoding="utf-8", errors="ignore").read()
            text2 = open(p2, "r", encoding="utf-8", errors="ignore").read()

            v1 = get_or_cache_embedding(p1, "text", lambda _: get_text_embedding(text1))
            v2 = get_or_cache_embedding(p2, "text", lambda _: get_text_embedding(text2))

            score = util.cos_sim(v1, v2).item()

        # ------------------------------
        # CODE
        # ------------------------------
        elif mode == "code":
            code1 = open(p1, "r", encoding="utf-8", errors="ignore").read()
            code2 = open(p2, "r", encoding="utf-8", errors="ignore").read()

            v1 = get_or_cache_embedding(p1, "code", lambda _: get_code_embedding(code1))
            v2 = get_or_cache_embedding(p2, "code", lambda _: get_code_embedding(code2))

            # cosine similarity of numpy vectors
            score = float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))

        # ------------------------------
        # IMAGE
        # ------------------------------
        elif mode == "image":
            v1 = get_or_cache_embedding(p1, "image", get_image_embedding)
            v2 = get_or_cache_embedding(p2, "image", get_image_embedding)

            score = F.cosine_similarity(v1, v2, dim=0).item()

        else:
            return jsonify({"error": "Invalid mode"}), 400

        score = round(score * 100, 2)

        # Save History
        history = AnalysisHistory(
            user_id=user_id,
            modality=mode,
            file_a_name=file1.filename,
            file_b_name=file2.filename,
            similarity_score=score,
        )
        db.session.add(history)
        db.session.commit()

        return jsonify({"mode": mode, "score": score})

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"error": "Server crashed", "details": str(e)}), 500

# --------------------------------------------------------
# RUN
# --------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
