"""Modelos de la base de datos (tablas de SQLite)."""

from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """Una persona registrada. UserMixin agrega lo que Flask-Login necesita (is_authenticated, get_id...)."""

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)  # nunca guardamos la contraseña real
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
