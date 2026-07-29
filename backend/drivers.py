"""
Generated driver profiles from teammate-delta methodology.
See DRIVER_DATA_METHODOLOGY.md for details on how these values were derived.
"""

DRIVER_PROFILES = {
    "generic": {
        "name": "Generic Driver",
        "team": "None",
        "pace_offset": 0.0,
        "consistency": 0.15,
        "data_confidence": "Low"
    },
    "ver": {
        "name": "Max Verstappen",
        "team": "Red Bull Racing",
        "pace_offset": -0.15,
        "consistency": 0.08,
        "data_confidence": "High"
    },
    "per": {
        "name": "Sergio Pérez",
        "team": "Red Bull Racing",
        "pace_offset": 0.15,
        "consistency": 0.14,
        "data_confidence": "High"
    },
    "ham": {
        "name": "Lewis Hamilton",
        "team": "Mercedes",
        "pace_offset": -0.05,
        "consistency": 0.09,
        "data_confidence": "High"
    },
    "rus": {
        "name": "George Russell",
        "team": "Mercedes",
        "pace_offset": 0.05,
        "consistency": 0.11,
        "data_confidence": "High"
    },
    "lec": {
        "name": "Charles Leclerc",
        "team": "Ferrari",
        "pace_offset": -0.08,
        "consistency": 0.12,
        "data_confidence": "High"
    },
    "sai": {
        "name": "Carlos Sainz",
        "team": "Ferrari",
        "pace_offset": 0.08,
        "consistency": 0.11,
        "data_confidence": "High"
    },
    "nor": {
        "name": "Lando Norris",
        "team": "McLaren",
        "pace_offset": -0.1,
        "consistency": 0.1,
        "data_confidence": "High"
    },
    "pia": {
        "name": "Oscar Piastri",
        "team": "McLaren",
        "pace_offset": 0.1,
        "consistency": 0.13,
        "data_confidence": "Medium" # Rookie season variance
    },
    "alo": {
        "name": "Fernando Alonso",
        "team": "Aston Martin",
        "pace_offset": -0.12,
        "consistency": 0.09,
        "data_confidence": "High"
    },
    "str": {
        "name": "Lance Stroll",
        "team": "Aston Martin",
        "pace_offset": 0.12,
        "consistency": 0.18,
        "data_confidence": "Medium"
    },
    "gas": {
        "name": "Pierre Gasly",
        "team": "Alpine",
        "pace_offset": -0.02,
        "consistency": 0.12,
        "data_confidence": "High"
    },
    "oco": {
        "name": "Esteban Ocon",
        "team": "Alpine",
        "pace_offset": 0.02,
        "consistency": 0.13,
        "data_confidence": "High"
    },
    "alb": {
        "name": "Alexander Albon",
        "team": "Williams",
        "pace_offset": -0.2,
        "consistency": 0.11,
        "data_confidence": "High"
    },
    "sar": {
        "name": "Logan Sargeant",
        "team": "Williams",
        "pace_offset": 0.2,
        "consistency": 0.22,
        "data_confidence": "Low" # High variance, rookie season
    },
    "tsu": {
        "name": "Yuki Tsunoda",
        "team": "AlphaTauri",
        "pace_offset": -0.05,
        "consistency": 0.14,
        "data_confidence": "High"
    },
    "ric": {
        "name": "Daniel Ricciardo",
        "team": "AlphaTauri",
        "pace_offset": 0.05,
        "consistency": 0.13,
        "data_confidence": "Low" # Partial season
    },
    "bot": {
        "name": "Valtteri Bottas",
        "team": "Alfa Romeo",
        "pace_offset": -0.05,
        "consistency": 0.12,
        "data_confidence": "High"
    },
    "zho": {
        "name": "Guanyu Zhou",
        "team": "Alfa Romeo",
        "pace_offset": 0.05,
        "consistency": 0.14,
        "data_confidence": "High"
    },
    "mag": {
        "name": "Kevin Magnussen",
        "team": "Haas F1 Team",
        "pace_offset": 0.0,
        "consistency": 0.15,
        "data_confidence": "Medium"
    },
    "hul": {
        "name": "Nico Hülkenberg",
        "team": "Haas F1 Team",
        "pace_offset": 0.0,
        "consistency": 0.14,
        "data_confidence": "Medium"
    }
}

def get_driver(driver_id) -> dict:
    if not driver_id or not isinstance(driver_id, str):
        return DRIVER_PROFILES["generic"]
    driver_id = driver_id.lower()
    if driver_id not in DRIVER_PROFILES:
        return DRIVER_PROFILES["generic"]
    return DRIVER_PROFILES[driver_id]
