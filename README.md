# ClimaPTY 🇵🇦

**El cambio climático no es abstracto en Panamá. Ya pasó aquí.**

## El problema

El cambio climático se siente lejano para la mayoría de la gente: gráficos globales, osos polares, cifras abstractas. Pero en Panamá ya tiene consecuencias concretas: la sequía de 2023-2024 obligó a restringir los tránsitos por el Canal, que depende de la lluvia para llenar el lago Gatún, y la comunidad de Gardi Sugdub en Guna Yala tuvo que reubicarse por la subida del nivel del mar. Cuando el problema se siente lejano, nadie cambia su comportamiento.

## La solución

ClimaPTY conecta datos reales con acciones medibles:

1. **Lo que le pasó a tu Panamá:** eliges tu ciudad y ves cómo cambiaron la temperatura y la lluvia desde 1940, con datos históricos reales (Open-Meteo / reanálisis ERA5).
2. **Tu compromiso:** te registras, eliges acciones pensadas para Panamá (aire acondicionado, transporte, alimentación) y las registras. El sistema calcula el CO₂ evitado con factores de emisión citados.
3. **Impacto colectivo:** un contador público muestra el CO₂ total evitado por todos los usuarios.

## ¿Cómo contribuye a frenar el cambio climático?

El proyecto no "informa" solamente: convierte la información local en compromisos concretos y mide el resultado. El impacto se reporta con números reales de usuarios reales, no con estimaciones teóricas.

## Tecnologías

Python, Flask, SQLite, Flask-Login, Chart.js, API de Open-Meteo.

## Estado del proyecto

- [x] Día 1: estructura, datos históricos por ciudad
- [ ] Día 2: usuarios y compromisos
- [ ] Día 3: cálculo de CO₂ con fuentes, contador público
- [ ] Día 4: publicación en internet y primeros usuarios
- [ ] Día 5: pruebas y presentación

## Cómo ejecutarlo

Requisitos: Python 3.11 o superior y conexión a internet (la primera visita a cada ciudad descarga sus datos).

```bash
# 1. Clonar el repositorio y entrar en la carpeta
git clone <url-del-repositorio>
cd <carpeta-del-proyecto>

# 2. Crear y activar el entorno virtual
python3 -m venv venv
source venv/bin/activate        # En Windows: venv\Scripts\activate

# 3. Instalar las dependencias
pip install -r requirements.txt

# 4. Ejecutar la aplicación
python app.py
```

Luego abre <http://localhost:5001> en el navegador. (Usamos el puerto 5001 porque en macOS el 5000 lo ocupa el Receptor AirPlay.)

La primera vez que abres una ciudad, la app descarga más de 80 años de datos diarios y tarda unos segundos. Después se guardan en `data/cache/` y las siguientes visitas son instantáneas.

## Fuentes

- ONU, La crisis climática: <https://www.un.org/es/un75/climate-crisis-race-we-can-win>
- ONU, Causas y efectos del cambio climático: <https://www.un.org/es/climatechange/science/causes-effects-climate-change>
- Open-Meteo Historical Weather API: <https://open-meteo.com/en/docs/historical-weather-api>
