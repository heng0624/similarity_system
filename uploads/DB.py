from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

def init_db(app):
    app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:@localhost/similarity_app"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

# ---------------- USERS TABLE ----------------
class Users(db.Model):
    __tablename__ = 'users'

    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum('admin', 'lecturer', 'student'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

# ---------------- HISTORY TABLE ----------------
class AnalysisHistory(db.Model):
    __tablename__ = 'analysishistory'

    analysis_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    modality = db.Column(db.Enum('document', 'image', 'code'), nullable=False)
    file_a_name = db.Column(db.Text, nullable=False)
    file_b_name = db.Column(db.Text, nullable=False)
    similarity_score = db.Column(db.Float, nullable=False)
    report_url = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

# ---------------- CACHE TABLE ----------------
class FeatureCache(db.Model):
    __tablename__ = 'featurecache'

    cache_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    file_hash = db.Column(db.String(64), unique=True, nullable=False)
    embedding = db.Column(db.LargeBinary, nullable=False)
    modality = db.Column(db.Enum('document', 'image', 'code'), nullable=False)
    last_accessed = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
