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


class Action(db.Model):
    """Una acción que se puede registrar (ej. "Usar Metro o bus en vez de carro")."""

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    unit_label = db.Column(db.String(50), nullable=False)    # ej. "km", "porción de 150 g"
    co2_kg_per_unit = db.Column(db.Float, nullable=True)     # None = factor en verificación
    source_url = db.Column(db.String(300), nullable=True)
    assumptions = db.Column(db.Text, nullable=True)


class ActionLog(db.Model):
    """Un registro: un usuario hizo una acción cierta cantidad de veces en una fecha."""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    action_id = db.Column(db.Integer, db.ForeignKey("action.id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)  # entero >= 1 (se valida en la ruta)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)

    # Permite escribir log.action para llegar a la acción (y su factor) desde el registro.
    action = db.relationship("Action")
