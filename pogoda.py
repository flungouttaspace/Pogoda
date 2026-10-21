import json
import math
import re
import sys
from datetime import date, timedelta
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen


CACHE_FILE = Path(__file__).with_name("wyniki_pogody.json")
TIMEZONE = "Europe/London"


def parse_date(text):
    text = text.strip()
    if not text:
        return (date.today() + timedelta(days=1)).isoformat()
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", text):
        raise ValueError("Podaj datę w formacie YYYY-mm-dd.")
    return date.fromisoformat(text).isoformat()


def read_coordinate(label, minimum, maximum):
    while True:
        try:
            value = float(input(label).strip().replace(",", "."))
            if math.isfinite(value) and minimum <= value <= maximum:
                return 0.0 if value == 0 else value
        except ValueError:
            pass
        print(f"Podaj liczbę od {minimum} do {maximum}.")


def rain_message(value):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        return "Nie wiem"
    return "Będzie padać" if value > 0 else "Nie będzie padać"


def fetch_rain(latitude, longitude, searched_date):
    params = urlencode({
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "rain",
        "daily": "rain_sum",
        "timezone": TIMEZONE,
        "start_date": searched_date,
        "end_date": searched_date,
    })
    try:
        with urlopen("https://api.open-meteo.com/v1/forecast?" + params,
                     timeout=20) as response:
            data = json.load(response)
        if not isinstance(data, dict) or data.get("error"):
            return None
        daily = data.get("daily")
        if not isinstance(daily, dict):
            return None
        dates = daily.get("time")
        values = daily.get("rain_sum")
        if not isinstance(dates, list) or not isinstance(values, list):
            return None
        index = dates.index(searched_date)
        value = values[index]
        if type(value) in (int, float) and math.isfinite(value):
            return value
    except (URLError, OSError, ValueError, IndexError) as error:
        print(f"Nie udało się pobrać wyniku: {error}", file=sys.stderr)
    return None


def check_weather(latitude, longitude, searched_date, cache_file=CACHE_FILE):
    cache_file = Path(cache_file)
    if cache_file.exists():
        # Nie nadpisujemy uszkodzonego pliku wcześniejszych wyników.
        cache = json.loads(cache_file.read_text(encoding="utf-8"))
        if not isinstance(cache, dict):
            raise ValueError("Plik wyników musi zawierać obiekt JSON.")
    else:
        cache = {}

    # Wynik dotyczy konkretnej lokalizacji, daty i strefy czasowej.
    key = f"{latitude}|{longitude}|{TIMEZONE}|{searched_date}"
    if key in cache:
        return rain_message(cache[key])

    rain = fetch_rain(latitude, longitude, searched_date)
    cache[key] = rain
    temporary_file = cache_file.with_suffix(".tmp")
    try:
        temporary_file.write_text(
            json.dumps(cache, ensure_ascii=False, indent=2, allow_nan=False),
            encoding="utf-8",
        )
        temporary_file.replace(cache_file)
    except OSError as error:
        print(f"Nie udało się zapisać wyniku: {error}", file=sys.stderr)
    return rain_message(rain)


def main():
    while True:
        try:
            searched_date = parse_date(input(
                "Podaj datę (YYYY-mm-dd; Enter = jutro): "
            ))
            break
        except ValueError:
            print("Nieprawidłowa data. Użyj formatu YYYY-mm-dd, np. 2026-09-24.")

    latitude = read_coordinate("Szerokość geograficzna (np. 52.2297): ", -90, 90)
    longitude = read_coordinate("Długość geograficzna (np. 21.0122): ", -180, 180)
    try:
        print(check_weather(latitude, longitude, searched_date))
    except (OSError, ValueError) as error:
        print(f"Nie można odczytać pliku wyników: {error}", file=sys.stderr)
        print("Nie wiem")


if __name__ == "__main__":
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        print("\nPrzerwano program.")
