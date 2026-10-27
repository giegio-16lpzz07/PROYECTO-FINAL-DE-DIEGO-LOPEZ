"""Lógica de datos climáticos: descarga desde Open-Meteo, caché y cálculos.

Este archivo no sabe nada de Flask ni de HTML. Solo recibe un slug de ciudad
y devuelve un diccionario con números listos para mostrar.
"""

import json
import os
from datetime import date

import requests

# Documentación: https://open-meteo.com/en/docs/historical-weather-api
API_URL = "https://archive-api.open-meteo.com/v1/archive"

# ERA5 es el reanálisis que empieza en 1940 (el más antiguo disponible).
START_DATE = "1940-01-01"

# Carpeta donde guardamos las respuestas de la API (data/cache/ en la raíz del proyecto).
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(PROJECT_DIR, "data", "cache")

# Década de referencia para comparar.
BASELINE_START = 1950
BASELINE_END = 1959

# Coordenadas verificadas con el geocodificador de Open-Meteo (GeoNames).
# Gardi Sugdub también se escribe "Cartí Sugtupu"; coincide con Wikipedia (09°28′14″N 78°57′40″W).
CITIES = {
    "ciudad-de-panama": {
        "name": "Ciudad de Panamá",
        "slug": "ciudad-de-panama",
        "region": "Provincia de Panamá",
        "latitude": 8.9936,
        "longitude": -79.5197,
    },
    "colon": {
        "name": "Colón",
        "slug": "colon",
        "region": "Provincia de Colón",
        "latitude": 9.3603,
        "longitude": -79.9002,
    },
    "david": {
        "name": "David",
        "slug": "david",
        "region": "Provincia de Chiriquí",
        "latitude": 8.4273,
        "longitude": -82.4309,
    },
    "chitre": {
        "name": "Chitré",
        "slug": "chitre",
        "region": "Provincia de Herrera",
        "latitude": 7.9601,
        "longitude": -80.4288,
    },
    "gardi-sugdub": {
        "name": "Gardi Sugdub",
        "slug": "gardi-sugdub",
        "region": "Comarca Guna Yala",
        "latitude": 9.4707,
        "longitude": -78.9612,
    },
}


class ClimateDataError(Exception):
    """Error que se lanza cuando no podemos obtener o procesar los datos."""


def get_last_complete_year():
    """Devuelve el último año que ya terminó (si hoy es 2026, devuelve 2025)."""
    return date.today().year - 1


def get_last_complete_decade(last_year):
    """Devuelve (inicio, fin) de la última década completa.

    Ejemplo: si el último año completo es 2025, la década 2020-2029 aún no
    terminó, así que la última completa es 2010-2019.
    """
    decade_end = (last_year + 1) // 10 * 10 - 1
    decade_start = decade_end - 9
    return decade_start, decade_end


def fetch_daily_data(city, end_date):
    """Pide a la API los datos diarios de temperatura media y precipitación."""
    params = {
        "latitude": city["latitude"],
        "longitude": city["longitude"],
        "start_date": START_DATE,
        "end_date": end_date,
        "daily": "temperature_2m_mean,precipitation_sum",
        "timezone": "America/Panama",
        # Solo ERA5: la documentación lo recomienda para comparar décadas de forma consistente.
        "models": "era5",
    }
    try:
        response = requests.get(API_URL, params=params, timeout=60)
        # 429 = "demasiadas peticiones": la API gratuita tiene un límite por minuto.
        if response.status_code == 429:
            raise ClimateDataError(
                "Open-Meteo recibió demasiadas consultas en poco tiempo. Espera un minuto y recarga la página."
            )
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        raise ClimateDataError(
            "No pudimos conectarnos con Open-Meteo. Revisa tu conexión a internet e inténtalo de nuevo."
        )
    except ValueError:
        raise ClimateDataError("Open-Meteo respondió con datos que no pudimos leer.")


def load_daily_data(city):
    """Devuelve los datos diarios de una ciudad, usando la caché si sirve."""
    end_date = f"{get_last_complete_year()}-12-31"
    cache_path = os.path.join(CACHE_DIR, f"{city['slug']}.json")

    # 1. Si ya tenemos el archivo y llega hasta la fecha que necesitamos, lo usamos.
    if os.path.exists(cache_path):
        with open(cache_path, encoding="utf-8") as cache_file:
            cached = json.load(cache_file)
        if cached["daily"]["time"][-1] == end_date:
            return cached

    # 2. Si no, lo pedimos a la API y lo guardamos para la próxima vez.
    data = fetch_daily_data(city, end_date)
    if "daily" not in data:
        raise ClimateDataError("Open-Meteo no devolvió datos diarios para esta ciudad.")

    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as cache_file:
        json.dump(data, cache_file)
    return data


def aggregate_by_year(daily):
    """Convierte los datos diarios en una lista con un resumen por año.

    Cada elemento es: {"year": 1940, "avg_temp": 26.1, "total_rain": 2300.5}
    """
    totals = {}  # año -> sumas parciales
    for day, temp, rain in zip(daily["time"], daily["temperature_2m_mean"], daily["precipitation_sum"]):
        year = int(day[:4])  # "1940-01-01" -> 1940
        if year not in totals:
            totals[year] = {"temp_sum": 0, "temp_days": 0, "rain_sum": 0}
        # La API puede devolver None si falta un dato; en ese caso lo saltamos.
        if temp is not None:
            totals[year]["temp_sum"] += temp
            totals[year]["temp_days"] += 1
        if rain is not None:
            totals[year]["rain_sum"] += rain

    yearly = []
    for year in sorted(totals):
        values = totals[year]
        if values["temp_days"] == 0:
            continue
        yearly.append({
            "year": year,
            "avg_temp": values["temp_sum"] / values["temp_days"],
            "total_rain": values["rain_sum"],
        })
    return yearly


def decade_average(yearly, start_year, end_year, key):
    """Promedio de un campo ("avg_temp" o "total_rain") entre dos años, ambos incluidos."""
    values = [item[key] for item in yearly if start_year <= item["year"] <= end_year]
    if not values:
        raise ClimateDataError(f"No hay datos para el periodo {start_year}-{end_year}.")
    return sum(values) / len(values)


def get_city_climate(slug):
    """Función principal: devuelve todo lo que la página de la ciudad necesita."""
    city = CITIES[slug]
    data = load_daily_data(city)
    yearly = aggregate_by_year(data["daily"])

    recent_start, recent_end = get_last_complete_decade(get_last_complete_year())

    baseline_temp = decade_average(yearly, BASELINE_START, BASELINE_END, "avg_temp")
    recent_temp = decade_average(yearly, recent_start, recent_end, "avg_temp")
    baseline_rain = decade_average(yearly, BASELINE_START, BASELINE_END, "total_rain")
    recent_rain = decade_average(yearly, recent_start, recent_end, "total_rain")

    return {
        "baseline_label": f"{BASELINE_START}-{BASELINE_END}",
        "recent_label": f"{recent_start}-{recent_end}",
        "baseline_temp": baseline_temp,
        "recent_temp": recent_temp,
        "temp_diff": recent_temp - baseline_temp,
        "baseline_rain": baseline_rain,
        "recent_rain": recent_rain,
        "rain_change_pct": (recent_rain - baseline_rain) / baseline_rain * 100,
        # Listas para los gráficos (redondeadas para que el navegador no reciba 15 decimales).
        "years": [item["year"] for item in yearly],
        "temps": [round(item["avg_temp"], 2) for item in yearly],
        "rains": [round(item["total_rain"], 1) for item in yearly],
        # Coordenadas reales del punto de la cuadrícula ERA5 que usó la API.
        "grid_latitude": data["latitude"],
        "grid_longitude": data["longitude"],
    }
