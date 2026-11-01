import requests
import pandas as pd
import matplotlib.pyplot as plt

URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude=54.97&longitude=-1.61"
    "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum"
    "&timezone=Europe/London"
)

data = requests.get(URL, timeout=10).json()["daily"]
df = pd.DataFrame(data)
df["time"] = pd.to_datetime(df["time"])
df.columns = ["Date", "High (°C)", "Low (°C)", "Rain (mm)"]
print(df.to_string(index=False))

fig, ax = plt.subplots(figsize=(9, 4))
ax.plot(df["Date"], df["High (°C)"], marker="o", label="High")
ax.plot(df["Date"], df["Low (°C)"], marker="o", label="Low")
ax.fill_between(df["Date"], df["Low (°C)"], df["High (°C)"], alpha=0.15)
ax.set_title("Newcastle: next 7 days")
ax.set_ylabel("°C")
ax.legend()
fig.autofmt_xdate()
fig.tight_layout()
fig.savefig("forecast.png", dpi=150)
print("\nSaved forecast.png")
