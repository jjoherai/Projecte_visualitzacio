import pandas as pd
import os

os.makedirs("processed", exist_ok=True)

df = pd.read_csv(
    "data/flights_sample_3m.csv",
    parse_dates=["FL_DATE"],
    dtype={
        "AIRLINE": str,
        "ORIGIN": str,
        "DEST": str,
        "CANCELLED": float,
        "CANCELLATION_CODE": str,
        "DISTANCE": float,
        "ARR_DELAY": float,
        "DELAY_DUE_CARRIER": float,
        "DELAY_DUE_WEATHER": float,
        "DELAY_DUE_NAS": float,
        "DELAY_DUE_SECURITY": float,
        "DELAY_DUE_LATE_AIRCRAFT": float
    }
)

df["Year"] = df["FL_DATE"].dt.year
df["Month"] = df["FL_DATE"].dt.month

df["CANCELLED"] = df["CANCELLED"].fillna(0).astype(int)

delay_cols = ["DELAY_DUE_WEATHER", "DELAY_DUE_CARRIER", "DELAY_DUE_NAS",
              "DELAY_DUE_SECURITY", "DELAY_DUE_LATE_AIRCRAFT", "ARR_DELAY"]
for col in delay_cols:
    df[col] = pd.to_numeric(df[col].fillna(0), errors="coerce")

df["TotalDelay"] = df["DELAY_DUE_WEATHER"] \
                 + df["DELAY_DUE_CARRIER"] \
                 + df["DELAY_DUE_NAS"] \
                 + df["DELAY_DUE_SECURITY"] \
                 + df["DELAY_DUE_LATE_AIRCRAFT"]

monthly_delays = (
    df.groupby(["Year", "Month"])["TotalDelay"]
      .mean()
      .reset_index(name="AvgDelay")
)
monthly_delays["Date"] = pd.to_datetime(dict(
    year=monthly_delays.Year,
    month=monthly_delays.Month,
    day=1
))
monthly_delays = monthly_delays.sort_values("Date")

cancel_weather = df[df["CANCELLATION_CODE"] == "B"].copy()

total_flights = df.groupby(["Year", "AIRLINE"]).size().reset_index(name="TotalFlights")
weather_cancels = cancel_weather.groupby(["Year", "AIRLINE"]).size().reset_index(name="WeatherCancels")

merged1 = pd.merge(total_flights, weather_cancels,
                   on=["Year", "AIRLINE"], how="left")
merged1["WeatherCancels"] = merged1["WeatherCancels"].fillna(0).astype(int)
merged1["CancelPct"] = (
    merged1["WeatherCancels"] / merged1["TotalFlights"] * 100
).round(2)

cols_air = [
    "AirportID", "Name", "City", "Country",
    "IATA", "ICAO", "Latitude", "Longitude",
    "Altitude", "Timezone", "DST",
    "TzDatabase", "Type", "Source"
]
airports = pd.read_csv(
    "data/airports.txt",
    header=None,
    names=cols_air,
    usecols=["IATA", "Latitude", "Longitude"],
    quotechar='"',
    dtype={"IATA": str, "Latitude": float, "Longitude": float}
)

origin_delays = (
    df.groupby("ORIGIN")["TotalDelay"]
      .mean()
      .reset_index(name="AvgDelayOrigin")
)
origin_delays.rename(columns={"ORIGIN": "IATA"}, inplace=True)

airport_map = pd.merge(
    origin_delays,
    airports,
    on="IATA",
    how="left"
).dropna(subset=["Latitude", "Longitude"])

merged1.to_json("processed/cancellations_by_airline_year.json", orient="records")
monthly_delays.to_json("processed/monthly_delays.json", orient="records")
airport_map.to_json("processed/airport_delays.json", orient="records")

