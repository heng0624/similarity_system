import os
import requests,hashlib
import pickle
import numpy as np
import torch
import traceback
import torch.nn.functional as F
from PyPDF2 import PdfReader
from docx import Document
from flask_migrate import Migrate
import difflib
from werkzeug.utils import secure_filename
from datetime import datetime
from flask_mail import Mail, Message
from extensions import mail


from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from DB import init_db, db, Users, AnalysisHistory, FeatureCache
from auth import auth_bp
from utils.text_similarity import get_text_embedding 
from utils.code_similarity import ast_to_vector,compute_code_similarity  # <- changed from compute_code_similarity
from utils.image_similarity import get_image_embedding
import mimetypes
import csv
import re
from flask import send_from_directory
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from flask import send_file
from itsdangerous import URLSafeTimedSerializer
from bs4 import BeautifulSoup


app = Flask(__name__)
app.config["SECRET_KEY"] = "supersecret"
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = "zhengteckheng0624@gmail.com"
app.config["MAIL_PASSWORD"] = "jmjwinnawuawijyf"
app.config["MAIL_DEFAULT_SENDER"] = "zhengteckheng0624@gmail.com"


# Initialize email + serializer (now correct)
serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"])
mail.init_app(app)

# Initialize DB
init_db(app)
migrate = Migrate(app, db)
app.register_blueprint(auth_bp)

with app.app_context():
    db.create_all()

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def extract_pdf_text(path):
    try:
        reader = PdfReader(path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        print("PDF extraction failed:", e)
        return ""


# -------------------- UTILITY --------------------
def hash_file(filepath):
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        hasher.update(f.read())
    return hasher.hexdigest()


def get_or_cache_embedding(file_path, modality, embed_function):
    file_hash = hash_file(file_path)
    cached = FeatureCache.query.filter_by(file_hash=file_hash).first()
    if cached:
        cached.last_accessed = db.func.now()
        db.session.commit()
        return pickle.loads(cached.embedding)

    vector = embed_function(file_path)
    new_cache = FeatureCache(file_hash=file_hash, embedding=pickle.dumps(vector), modality=modality)
    db.session.add(new_cache)
    db.session.commit()
    return vector

def generate_diff_html(text_a, text_b, fromdesc="A", todesc="B"):
    # produce a side-by-side HTML diff
    a_lines = text_a.splitlines()
    b_lines = text_b.splitlines()
    hd = difflib.HtmlDiff(wrapcolumn=80)
    return hd.make_table(a_lines, b_lines, fromdesc, todesc, context=True, numlines=3)

# -------------------- ROUTES --------------------
@app.route("/")
def root():
    return redirect(url_for("home"))


@app.route("/home")
def home():
    return render_template("index.html")
from flask import send_file

@app.route("/view/<path:filename>")
def view_file(filename):
    full_path = os.path.join(UPLOAD_FOLDER, filename)

    if not os.path.exists(full_path):
        return "File not found", 404

    return send_from_directory(UPLOAD_FOLDER, filename)



@app.route("/history")
def history():
    if not session.get("user_id"):
        return redirect(url_for("home"))

    uid = session["user_id"]
    history = AnalysisHistory.query.filter_by(user_id=uid).order_by(AnalysisHistory.timestamp.desc()).all()
    return render_template("history.html", history=history)


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("home"))
    user = Users.query.get(session["user_id"])
    return render_template("profile.html", user=user)

@app.route("/report/<int:hid>")
def report(hid):
    history = AnalysisHistory.query.get_or_404(hid)

    return render_template("report.html", h=history)

@app.route("/download_report/<int:history_id>")
def download_report(history_id):
    h = AnalysisHistory.query.get_or_404(history_id)

    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=letter)
    width, height = letter
    y = height - 50

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "Similarity Analysis Report")
    y -= 30

    c.setFont("Helvetica", 12)
    c.drawString(50, y, f"Mode: {h.modality}")
    y -= 18
    c.drawString(50, y, f"File A: {h.file_a_name}")
    y -= 18
    c.drawString(50, y, f"File B: {h.file_b_name}")
    y -= 18
    c.drawString(50, y, f"Similarity Score: {h.similarity_score}%")
    y -= 18
    c.drawString(50, y, f"Date: {h.timestamp}")
    y -= 30

    # If text previews exist, print first N chars as plain text (avoid huge content)
    preview_limit = 2000
    if h.preview_a:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "File A excerpt:")
        y -= 14
        c.setFont("Helvetica", 10)
        text = (h.preview_a[:preview_limit] + ("..." if len(h.preview_a) > preview_limit else ""))
        for line in text.splitlines():
            if y < 80:
                c.showPage()
                y = height - 50
            c.drawString(50, y, line[:100])
            y -= 12

    c.showPage()
    c.save()
    pdf_buffer.seek(0)

    return send_file(pdf_buffer, as_attachment=True, download_name=f"report_{history_id}.pdf", mimetype="application/pdf")
@app.route("/view_text/<int:hid>/<part>")
def view_text(hid, part):
    h = AnalysisHistory.query.get_or_404(hid)
    
    if part == "a":
        content = h.text_a
        title = h.file_a_name or "Input A"
    else:
        content = h.text_b
        title = h.file_b_name or "Input B"
        
    if not content:
        return "No content to display.", 404
    
    return render_template("view_text.html", title=title, content=content)



@app.route("/forgot_password", methods=["POST"])
def forgot_password():
    email = request.json.get("email")
    user = Users.query.filter_by(email=email).first()

    if not user:
        return jsonify({"error": "Email not found"}), 404
    
    token = serializer.dumps(email, salt="password-reset")

    reset_url = url_for('reset_password', token=token, _external=True)

    msg = Message("Reset Your Password", sender="zhengteckheng0624@gmail.com", recipients=[email])
    msg.body = f"Click here to reset your password:\n{reset_url}"
    mail.send(msg)


    return jsonify({"message": "Reset link sent to your email"})

@app.route("/reset/<token>")
def reset_password(token):
    try:
        email = serializer.loads(token, salt="password-reset", max_age=3600)  # 1 hour validity
    except:
        return "Token expired or invalid", 400

    return render_template("reset_password.html", email=email, token=token)

@app.route("/reset_password", methods=["POST"])
def reset_password_submit():
    token = request.form["token"]
    new_pass = request.form["password"]

    try:
        email = serializer.loads(token, salt="password-reset", max_age=3600)
    except:
        return "Token invalid", 400

    user = Users.query.filter_by(email=email).first()
    user.set_password(new_pass)   # hash inside model
    db.session.commit()

    flash("Password updated successfully. Please log in.", "success")


    return redirect(url_for("home"))




ALLOWED_DOC_EXT = (".txt", ".md", ".csv",".pdf",".docx")
ALLOWED_CODE_EXT = (".py", ".js", ".java", ".cpp", ".c", ".cs", ".html", ".css", ".json")
ALLOWED_IMAGE_EXT = (".png", ".jpg", ".jpeg", ".bmp", ".gif","webp")


def allowed_file(filename, allowed_ext):
    return filename.lower().endswith(allowed_ext)

def fetch_url_content(url):
    """Fetch text content from a webpage."""
    try:
        r = requests.get(url, timeout=5)
        soup = BeautifulSoup(r.text, "html.parser")
        return soup.get_text(separator=" ")
    except:
        return ""

def extract_docx_text(path):
    doc = Document(path)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return "\n".join(full_text)


@app.route("/similarity", methods=["POST"])
def similarity():
    try:
        if not session.get("user_id"):
            return jsonify({"error": "Login required"}), 403
        user_id = session["user_id"]

        # ----------- INPUTS -----------
        file1 = request.files.get("file1")
        file2 = request.files.get("file2")

        mode = request.form.get("mode")

        user_text = request.form.get("user_text", "").strip()
        compare_text = request.form.get("compare_text", "").strip()

        user_url = request.form.get("user_url", "").strip()
        compare_url = request.form.get("compare_url", "").strip()

        preview_a = ""
        preview_b = ""
        diff_html = ""
        score = 0.0

        # ==================================================================
        # 1) CASE A: USER enters TEXT or URL instead of uploading files  
        # ==================================================================
        if (not file1) and (not file2):
            text_a = ""
            text_b = ""
            # ---- TEXT INPUT ----
            if user_text:
                text_a = user_text

            if compare_text:
                text_b = compare_text

            # ---- URL INPUT ----
            if user_url:
                text_a = fetch_url_content(user_url)

            if compare_url:
                text_b = fetch_url_content(compare_url)

            # Validate
            if not text_a or not text_b:
                return jsonify({"error": "Text/URL content cannot be empty."}), 400

            preview_a = text_a[:20000]
            preview_b = text_b[:20000]

            # Compute similarity
            v1 = torch.tensor(get_text_embedding(text_a)).unsqueeze(0)
            v2 = torch.tensor(get_text_embedding(text_b)).unsqueeze(0)
            score = float(F.cosine_similarity(v1, v2).item()) * 100
            mode= "text" if user_text or compare_text else "url"
            print("mode",mode)
            diff_html = generate_diff_html(text_a, text_b, "Input A", "Input B")

            h = AnalysisHistory(
                user_id=user_id,
                modality =mode,
                file_a_name="TEXT_OR_URL_A",
                file_b_name="TEXT_OR_URL_B",
                save_path_a=None,
                save_path_b=None,
                text_a = text_a,   # store the text content
                text_b = text_b,   # store the text content
                similarity_score=round(score, 2),
                preview_a=preview_a,
                preview_b=preview_b,
                diff_html=diff_html,

            )
            db.session.add(h)
            db.session.commit()

            return jsonify({
                "mode": mode,
                "score": round(score, 2),
                "preview_a": preview_a,
                "preview_b": preview_b,
                "history_id": h.analysis_id
            })

        # ==================================================================
        # 2) CASE B: NORMAL FILE BASED COMPARISON (original logic preserved)
        # ==================================================================

        if not file1 or not file2 or not mode:
            return jsonify({"error": "Missing inputs"}), 400

        # choose allowed extensions
        if mode == "document":
            allowed_ext = ALLOWED_DOC_EXT
        elif mode == "code":
            allowed_ext = ALLOWED_CODE_EXT
        elif mode == "image":
            allowed_ext = ALLOWED_IMAGE_EXT
        else:
            return jsonify({"error": "Invalid mode"}), 400

        # validate extensions
        if not allowed_file(file1.filename, allowed_ext) or not allowed_file(file2.filename, allowed_ext):
            return jsonify({"error": f"Invalid file type for {mode}. Allowed: {', '.join(allowed_ext)}"}), 400

        # save files
        fname1 = secure_filename(file1.filename)
        fname2 = secure_filename(file2.filename)

        save1 = os.path.join(UPLOAD_FOLDER, fname1)
        save2 = os.path.join(UPLOAD_FOLDER, fname2)

        # handle duplicate filenames
        if os.path.exists(save1):
            fname1 = f"{int(datetime.utcnow().timestamp())}_{fname1}"
            save1 = os.path.join(UPLOAD_FOLDER, fname1)

        if os.path.exists(save2):
            fname2 = f"{int(datetime.utcnow().timestamp())}_{fname2}"
            save2 = os.path.join(UPLOAD_FOLDER, fname2)

        file1.save(save1)
        file2.save(save2)

        # -------- DOCUMENT MODE --------
        if mode == "document":
            ext1 = os.path.splitext(save1)[1].lower()
            ext2 = os.path.splitext(save2)[1].lower()

            def read_text(path, ext):
                if ext == ".pdf":
                    return extract_pdf_text(path)
                if ext == ".docx":
                    return extract_docx_text(path)
                if ext == ".csv":
                    rows = []
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        r = csv.reader(f)
                        for row in r:
                            rows.append(", ".join(row))
                    return "\n".join(rows)
                try:
                    return open(path, "r", encoding="utf-8", errors="ignore").read()
                except:
                    return ""

            text1 = read_text(save1, ext1)
            text2 = read_text(save2, ext2)

            preview_a = text1[:20000]
            preview_b = text2[:20000]

            v1 = torch.tensor(get_text_embedding(text1)).unsqueeze(0)
            v2 = torch.tensor(get_text_embedding(text2)).unsqueeze(0)
            score = float(F.cosine_similarity(v1, v2).item()) * 100

            diff_html = generate_diff_html(text1, text2, "File A", "File B")

        # -------- CODE MODE --------
        elif mode == "code":
            code1 = open(save1, "r", encoding="utf-8", errors="ignore").read()
            code2 = open(save2, "r", encoding="utf-8", errors="ignore").read()

            preview_a = code1[:20000]
            preview_b = code2[:20000]

            score = float(compute_code_similarity(code1, code2)) * 100
            diff_html = generate_diff_html(code1, code2, "Code A", "Code B")

        # -------- IMAGE MODE --------
        elif mode == "image":
            v1 = get_or_cache_embedding(save1, "image", get_image_embedding)
            v2 = get_or_cache_embedding(save2, "image", get_image_embedding)

            v1t = torch.from_numpy(np.array(v1)) if not isinstance(v1, torch.Tensor) else v1
            v2t = torch.from_numpy(np.array(v2)) if not isinstance(v2, torch.Tensor) else v2

            score = float(F.cosine_similarity(v1t, v2t, dim=0).item()) * 100

            import base64
            preview_a = "data:image/*;base64," + base64.b64encode(open(save1, "rb").read()).decode()
            preview_b = "data:image/*;base64," + base64.b64encode(open(save2, "rb").read()).decode()

        score = round(score, 2)

        # Save analysis history
        h = AnalysisHistory(
            user_id=user_id,
            modality=mode,
            file_a_name=file1.filename,
            file_b_name=file2.filename,
            save_path_a=fname1,
            save_path_b=fname2,
            similarity_score=score,
            preview_a=preview_a,
            preview_b=preview_b,
            diff_html=diff_html
        )
        db.session.add(h)
        db.session.commit()

        return jsonify({
            "mode": mode,
            "score": score,
            "preview_a": preview_a,
            "preview_b": preview_b,
            "history_id": h.analysis_id
        })

    except Exception as e:
        print("ERROR:", e)
        traceback.print_exc()
        return jsonify({"error": "Server crashed", "details": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
