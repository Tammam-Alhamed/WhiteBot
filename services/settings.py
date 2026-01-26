import json
import os

SETTINGS_FILE = "settings.json"


def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        default_data = {
            "exchange_rate": 15000,
            "margins": {"default": 1.0}  # الافتراضي 1.0 (بدون ربح)
        }
        save_settings(default_data)
        return default_data
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def save_settings(data):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def get_setting(key, default=None):
    data = load_settings()
    return data.get(key, default)


def update_setting(key, value):
    data = load_settings()
    data[key] = value
    save_settings(data)


# --- دوال النسب الجديدة ---
def get_margin_for_category(category_name):
    data = load_settings()
    margins = data.get("margins", {})

    # إذا بحثنا عن فئة موجودة نرجع قيمتها
    if category_name in margins:
        return float(margins[category_name])

    # إذا لم نجدها، نرجع "العام" (default)
    # إذا لم يوجد "العام"، نرجع 1.0 (بدون ربح)
    return float(margins.get("default", 1.0))


def set_category_margin(category_name, value):
    data = load_settings()
    if "margins" not in data: data["margins"] = {}
    data["margins"][category_name] = float(value)
    save_settings(data)
