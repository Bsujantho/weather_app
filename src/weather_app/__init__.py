"""Fetch a daily weather forecast from Open-Meteo, print it, and save a chart."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # render to file without needing a display

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
import requests

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT = 10

COLUMNS = {
    "time": "Date",
    "temperature_2m_max": "High (°C)",
    "temperature_2m_min": "Low (°C)",
    "precipitation_sum": "Rain (mm)",
    "precipitation_probability_max": "Rain chance (%)",
}


@dataclass
class Location:
    name: str
    latitude: float
    longitude: float
    timezone: str


def geocode(city: str) -> Location:
    resp = requests.get(
        GEOCODE_URL, params={"name": city, "count": 1}, timeout=TIMEOUT
    )
    resp.raise_for_status()
    results = resp.json().get("results")
    if not results:
        raise ValueError(f"Could not find a location called {city!r}")
    r = results[0]
    label = ", ".join(p for p in (r["name"], r.get("country")) if p)
    return Location(label, r["latitude"], r["longitude"], r.get("timezone", "auto"))


def fetch_forecast(loc: Location, days: int) -> pd.DataFrame:
    params = {
        "latitude": loc.latitude,
        "longitude": loc.longitude,
        "daily": ",".join(k for k in COLUMNS if k != "time"),
        "timezone": loc.timezone,
        "forecast_days": days,
    }
    resp = requests.get(FORECAST_URL, params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    df = pd.DataFrame(resp.json()["daily"]).rename(columns=COLUMNS)
    df["Date"] = pd.to_datetime(df["Date"])
    return df[list(COLUMNS.values())]


def plot_forecast(df: pd.DataFrame, title: str, out: str) -> None:
    fig, ax = plt.subplots(figsize=(10, 4.5))

    # Rain as bars on a secondary axis, drawn behind the temperature lines.
    ax_rain = ax.twinx()
    ax_rain.bar(df["Date"], df["Rain (mm)"], width=0.6, color="tab:blue",
                alpha=0.25, label="Rain (mm)")
    ax_rain.set_ylabel("Rain (mm)")
    ax_rain.set_ylim(0, max(5, df["Rain (mm)"].max() * 1.3))
    ax.set_zorder(ax_rain.get_zorder() + 1)
    ax.patch.set_visible(False)

    ax.plot(df["Date"], df["High (°C)"], marker="o", color="tab:red", label="High")
    ax.plot(df["Date"], df["Low (°C)"], marker="o", color="tab:cyan", label="Low")
    ax.fill_between(df["Date"], df["Low (°C)"], df["High (°C)"],
                    color="tab:orange", alpha=0.12)
    for d, hi, lo in zip(df["Date"], df["High (°C)"], df["Low (°C)"]):
        ax.annotate(f"{hi:.0f}°", (d, hi), textcoords="offset points",
                    xytext=(0, 7), ha="center", fontsize=8)
        ax.annotate(f"{lo:.0f}°", (d, lo), textcoords="offset points",
                    xytext=(0, -13), ha="center", fontsize=8)

    ax.set_title(title)
    ax.set_ylabel("Temperature (°C)")
    ax.xaxis.set_major_locator(mdates.DayLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%a %d %b"))
    ax.grid(axis="y", alpha=0.3)
    lo_min, hi_max = df["Low (°C)"].min(), df["High (°C)"].max()
    ax.set_ylim(lo_min - 3, hi_max + 3)

    lines, labels = ax.get_legend_handles_labels()
    bars, bar_labels = ax_rain.get_legend_handles_labels()
    ax.legend(lines + bars, labels + bar_labels, loc="upper left", fontsize=8)

    fig.autofmt_xdate()
    fig.tight_layout()
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150)
    plt.close(fig)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Daily weather forecast from Open-Meteo.")
    p.add_argument("city", nargs="?", default="Newcastle upon Tyne",
                   help="place name to look up (default: %(default)s)")
    p.add_argument("-d", "--days", type=int, default=7, choices=range(1, 17),
                   metavar="1-16", help="number of days (default: %(default)s)")
    p.add_argument("-o", "--out", default="forecast.png",
                   help="chart output path (default: %(default)s)")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        loc = geocode(args.city)
        df = fetch_forecast(loc, args.days)
    except (requests.RequestException, ValueError, KeyError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print(f"{loc.name} — next {args.days} days\n")
    print(df.to_string(index=False, formatters={"Date": lambda d: d.strftime("%a %d %b")}))

    plot_forecast(df, f"{loc.name}: next {args.days} days", args.out)
    print(f"\nSaved {args.out}")
    return 0
