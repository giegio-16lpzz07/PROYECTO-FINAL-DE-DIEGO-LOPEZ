"""Rutas de la aplicación web ClimaPTY."""

import os
from datetime import date

from dotenv import load_dotenv
from flask import Flask, abort, flash, redirect, render_template, request, url_for
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from models import Action, ActionLog, User, db
from services.climate import CITIES, ClimateDataError, get_city_climate
from services.impact import count_pending, log_co2, total_co2

# Lee el archivo .env y pone sus valores en las variables de entorno.
load_dotenv()

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
if not app.config["SECRET_KEY"]:
    raise RuntimeError("Falta SECRET_KEY. Copia .env.example como .env y pon una clave.")

# Ruta relativa: Flask-SQLAlchemy la guarda en la carpeta instance/ (instance/climapty.db).
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///climapty.db"
db.init_app(app)

# Crea las tablas si todavía no existen.
with app.app_context():
    db.create_all()

# Flask-Login: si alguien sin sesión entra a una página protegida, lo manda a "login".
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Inicia sesión para ver esa página."

MIN_PASSWORD_LENGTH = 8

PENDING_FACTOR_NOTE = (
    "Factor en verificación: usaremos el factor oficial de la red eléctrica de Panamá "
    "(Secretaría Nacional de Energía)."
)

# Las acciones que crea "flask seed". El slug es el identificador fijo de cada una.
SEED_ACTIONS = [
    {
        "slug": "aire-25-grados",
        "name": "Subir el aire acondicionado a 25°C o más",
        "unit_label": "día",
        "co2_kg_per_unit": None,
        "source_url": None,
        "assumptions": PENDING_FACTOR_NOTE,
    },
    {
        "slug": "aire-apagado-4-horas",
        "name": "Apagar el aire acondicionado al menos 4 horas",
        "unit_label": "día",
        "co2_kg_per_unit": None,
        "source_url": None,
        "assumptions": PENDING_FACTOR_NOTE,
    },
    {
        "slug": "metro-o-bus",
        "name": "Usar Metro o bus en vez de carro",
        "unit_label": "km",
        "co2_kg_per_unit": 0.249,
        "source_url": "https://www.epa.gov/greenvehicles/greenhouse-gas-emissions-typical-passenger-vehicle",
        "assumptions": (
            "EPA: ~400 g CO₂ por milla de un carro promedio (≈0.249 kg/km). "
            "No restamos las emisiones del bus o Metro, así que es un máximo."
        ),
    },
    {
        "slug": "porcion-carne-res",
        "name": "Porción de carne de res que no comí",
        "unit_label": "porción de 150 g",
        "co2_kg_per_unit": 14.92,
        "source_url": "https://ourworldindata.org/grapher/ghg-per-kg-poore",
        "assumptions": (
            "Poore & Nemecek (2018): 99.48 kg CO₂e por kg de carne de res (ganado de carne). "
            "Asume que no se reemplaza por otra proteína, así que es un máximo."
        ),
    },
    {
        "slug": "ropa-al-aire",
        "name": "Secar la ropa al aire en vez de secadora",
        "unit_label": "carga",
        "co2_kg_per_unit": None,
        "source_url": None,
        "assumptions": PENDING_FACTOR_NOTE,
    },
]


@login_manager.user_loader
def load_user(user_id):
    """Flask-Login guarda solo el id en la cookie; con esta función recupera al usuario completo."""
    return db.session.get(User, int(user_id))


def is_safe_next_url(url):
    """Solo permitimos volver a páginas de nuestro propio sitio (evita redirigir a sitios externos)."""
    return bool(url) and url.startswith("/") and not url.startswith("//") and "\\" not in url


@app.cli.command("seed")
def seed():
    """Crea o actualiza las acciones. Se puede correr varias veces sin duplicar."""
    for data in SEED_ACTIONS:
        action = Action.query.filter_by(slug=data["slug"]).first()
        if action is None:
            action = Action(slug=data["slug"])
            db.session.add(action)
            print(f"Creada: {data['name']}")
        else:
            print(f"Actualizada: {data['name']}")
        # Copiamos (o sobrescribimos) cada campo con el valor del seed.
        action.name = data["name"]
        action.unit_label = data["unit_label"]
        action.co2_kg_per_unit = data["co2_kg_per_unit"]
        action.source_url = data["source_url"]
        action.assumptions = data["assumptions"]
    db.session.commit()
    print(f"Listo: {Action.query.count()} acciones en la base de datos.")


@app.route("/")
def index():
    """Página de inicio: lista de ciudades y contador público."""
    all_logs = ActionLog.query.all()
    return render_template(
        "index.html",
        cities=CITIES.values(),
        global_co2=total_co2(all_logs),
        global_actions=len(all_logs),
    )


@app.route("/ciudad/<slug>")
def city_detail(slug):
    """Página con los datos históricos de una ciudad."""
    if slug not in CITIES:
        abort(404)

    city = CITIES[slug]
    try:
        climate = get_city_climate(slug)
    except ClimateDataError as error:
        # Mostramos la página con un mensaje en vez de romper la app.
        # 503 = "servicio no disponible por ahora".
        return render_template("city.html", city=city, error=str(error)), 503

    return render_template("city.html", city=city, climate=climate)


@app.route("/mi-impacto", methods=["GET", "POST"])
@login_required
def my_impact():
    """Registrar acciones y ver el impacto propio. Solo con sesión iniciada."""
    if request.method == "POST":
        # type=int convierte el texto a número; si no es un entero válido, devuelve None.
        action_id = request.form.get("action_id", type=int)
        quantity = request.form.get("quantity", type=int)
        action = None
        if action_id is not None:
            action = db.session.get(Action, action_id)

        if action is None:
            flash("Esa acción no existe.", "error")
        elif quantity is None or quantity < 1:
            flash("La cantidad debe ser un número entero de 1 o más.", "error")
        else:
            log = ActionLog(user_id=current_user.id, action_id=action.id, date=date.today(), quantity=quantity)
            db.session.add(log)
            db.session.commit()
            flash(f"Registrado: {action.name} ({quantity} {action.unit_label}).", "success")
        # Redirigimos para que recargar la página no repita el registro.
        return redirect(url_for("my_impact"))

    actions = Action.query.order_by(Action.id).all()
    # Solo los registros de este usuario, lo más reciente primero.
    logs = (
        ActionLog.query.filter_by(user_id=current_user.id)
        .order_by(ActionLog.created_at.desc(), ActionLog.id.desc())
        .all()
    )
    history = [{"log": log, "co2": log_co2(log)} for log in logs]
    return render_template(
        "my_impact.html",
        actions=actions,
        history=history,
        user_co2=total_co2(logs),
        pending_count=count_pending(logs),
    )


@app.route("/registro", methods=["GET", "POST"])
def register():
    """Formulario para crear una cuenta."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username:
            flash("Escribe un nombre de usuario.", "error")
        elif len(password) < MIN_PASSWORD_LENGTH:
            flash(f"La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres.", "error")
        elif User.query.filter_by(username=username).first():
            flash("Ese nombre de usuario ya existe. Elige otro.", "error")
        else:
            user = User(username=username, password_hash=generate_password_hash(password))
            db.session.add(user)
            db.session.commit()
            flash("Cuenta creada. Ya puedes iniciar sesión.", "success")
            return redirect(url_for("login"))

        # Si hubo un error, volvemos a mostrar el formulario con el nombre que escribió.
        return render_template("register.html", username=username), 400

    return render_template("register.html", username="")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Formulario para iniciar sesión."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()

        # Mismo mensaje si el usuario no existe o si la contraseña está mal:
        # así nadie puede averiguar qué usuarios existen.
        if user is None or not check_password_hash(user.password_hash, password):
            flash("Usuario o contraseña incorrectos.", "error")
            return render_template("login.html", username=username), 401

        login_user(user)
        next_url = request.args.get("next")
        if is_safe_next_url(next_url):
            return redirect(next_url)
        return redirect(url_for("index"))

    return render_template("login.html", username="")


@app.route("/logout")
def logout():
    """Cierra la sesión."""
    logout_user()
    flash("Sesión cerrada.", "success")
    return redirect(url_for("index"))


@app.errorhandler(404)
def page_not_found(error):
    """Página amigable cuando la dirección no existe."""
    return render_template("404.html", cities=CITIES.values()), 404


if __name__ == "__main__":
    # Puerto 5001 porque en macOS el 5000 lo usa el "Receptor AirPlay".
    app.run(debug=True, port=5001)
