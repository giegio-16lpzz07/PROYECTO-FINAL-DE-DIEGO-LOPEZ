"""Rutas de la aplicación web ClimaPTY."""

from flask import Flask, abort, render_template

from services.climate import CITIES, ClimateDataError, get_city_climate

app = Flask(__name__)


@app.route("/")
def index():
    """Página de inicio: lista de ciudades."""
    return render_template("index.html", cities=CITIES.values())


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


@app.errorhandler(404)
def page_not_found(error):
    """Página amigable cuando la dirección no existe."""
    return render_template("404.html", cities=CITIES.values()), 404


if __name__ == "__main__":
    # Puerto 5001 porque en macOS el 5000 lo usa el "Receptor AirPlay".
    app.run(debug=True, port=5001)
