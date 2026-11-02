"""Cálculos de CO₂ evitado. No sabe nada de Flask ni de HTML."""


def log_co2(log):
    """kg de CO₂ de un registro, o None si su acción todavía no tiene factor.

    Devolvemos None (y no 0) porque "no sabemos" no es lo mismo que "cero".
    """
    factor = log.action.co2_kg_per_unit
    if factor is None:
        return None
    return log.quantity * factor


def total_co2(logs):
    """Suma el CO₂ de varios registros. Los que no tienen factor no suman."""
    total = 0
    for log in logs:
        co2 = log_co2(log)
        if co2 is not None:
            total += co2
    return total


def count_pending(logs):
    """Cuántos registros tienen el factor en verificación (no están incluidos en el total)."""
    return sum(1 for log in logs if log_co2(log) is None)
