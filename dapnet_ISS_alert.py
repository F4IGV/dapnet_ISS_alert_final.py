#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script DAPNET ISS By F4IGV et Chat GPT - Version DEBUG COMPLETE (ASCII ONLY)
-------------------------------------------------------

- Pas de lettres accentuees (compatible pager POCSAG)
- Calcul astro en UTC (Skyfield)
- Stockage passe en UTC
- Logs heure locale + heure UTC
- Messages envoyes en heure locale
- Prealerte = azimut seul
- Debut / Peak / Fin = azimut + elevation
"""

import os
import json
import time
from datetime import datetime, timedelta, timezone

import requests
from skyfield.api import load, wgs84, EarthSatellite

# =====================================================
# CHEMINS
# =====================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(SCRIPT_DIR, "iss_state.json")
LOG_FILE = os.path.join(SCRIPT_DIR, "iss_debug.log")

# =====================================================
# CONFIG DAPNET
# =====================================================
DAPNET_USER = "YourCall"
DAPNET_PASS = "YourPassword"   # Remplace si besoin
CALLSIGNS = ["Call", "Call"]   #choose the call where you want to send message
TX_GROUP = "TxEmitersGroup"    #Choose you Tx emiters group where you want to send message
DAPNET_URL = "https://hampager.de/api/calls"

# =====================================================
# POSITION OBSERVATEUR
# =====================================================
LAT = 48.1173          #You can change LAT and LON for choose your QTH
LON = -1.6778
ALT = 60  # metres     #Elevation of your QTH

# =====================================================
# PARAMETRES PASSE
# =====================================================
MIN_ELEV = 5.0
WINDOW_SEC = 45
PREPASS_MIN = 15
PASS_EXPIRE_MIN = 10

# =====================================================
# SOURCES TLE
# =====================================================
TLE_SOURCES = [
    "https://www.amsat.org/amsat/ftp/keps/current/nasa.all",
    "https://celestrak.org/NORAD/elements/stations.txt",
]

# =====================================================
# ETAT JSON
# =====================================================
DEFAULT_STATE = {
    "ISS": {
        "pass_prealert": "",
        "pass_start": "",
        "pass_peak": "",
        "pass_end": "",
        "sent_pre": False,
        "sent_start": False,
        "sent_peak": False,
        "sent_end": False
    }
}

# =====================================================
# LOGGING
# =====================================================
def log(msg: str):
    now_local = datetime.now()
    stamp = now_local.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[LOCAL {stamp}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf8") as f:
        f.write(line + "\n")


def log_debug_time(event_name, now_utc, evt_utc):
    now_local = now_utc.astimezone()
    evt_local = evt_utc.astimezone()
    diff = (now_utc - evt_utc).total_seconds()

    log(
        f"[{event_name}] now_local={now_local.strftime('%H:%M:%S')} "
        f"now_utc={now_utc.strftime('%H:%M:%S')} "
        f"evt_local={evt_local.strftime('%H:%M:%S')} "
        f"evt_utc={evt_utc.strftime('%H:%M:%S')} "
        f"diff={diff:.1f}s"
    )

# =====================================================
# JSON STATE MANAGEMENT
# =====================================================
def load_state():
    if not os.path.exists(STATE_FILE):
        save_state(DEFAULT_STATE)
        return json.loads(json.dumps(DEFAULT_STATE))

    try:
        with open(STATE_FILE, "r", encoding="utf8") as f:
            data = json.load(f)
    except:
        save_state(DEFAULT_STATE)
        return json.loads(json.dumps(DEFAULT_STATE))

    if "ISS" not in data:
        data["ISS"] = json.loads(json.dumps(DEFAULT_STATE["ISS"]))

    for k, v in DEFAULT_STATE["ISS"].items():
        if k not in data["ISS"]:
            data["ISS"][k] = v

    return data


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf8") as f:
        json.dump(state, f, indent=4)


def reset_iss_state(state):
    state["ISS"] = json.loads(json.dumps(DEFAULT_STATE["ISS"]))
    log("[STATE] Reset passe ISS")

# =====================================================
# TLE
# =====================================================
def get_iss_tle():
    for url in TLE_SOURCES:
        log(f"[TLE] Telechargement depuis {url}")
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            lines = r.text.splitlines()
            for i, line in enumerate(lines):
                up = line.strip().upper()
                if "ISS" in up or up.endswith("25544"):
                    log("[TLE] TLE ISS trouve")
                    return lines[i], lines[i+1], lines[i+2]
        except Exception as e:
            log(f"[TLE] ERREUR {e}")
        time.sleep(1)
    log("[TLE] ECHEC total.")
    return None

# =====================================================
# CALCUL AZIMUT/ELEVATION
# =====================================================
def get_az_el(ts, sat, obs, event_time_utc):
    t_evt = ts.from_datetime(event_time_utc.replace(tzinfo=timezone.utc))
    diff = sat - obs
    topo = diff.at(t_evt)
    alt, az, dist = topo.altaz()
    return alt.degrees, az.degrees

# =====================================================
# CALCUL PASSE
# =====================================================
def compute_pass_utc():
    tle = get_iss_tle()
    if not tle:
        return None

    ts = load.timescale()
    sat = EarthSatellite(tle[1], tle[2], "ISS", ts)
    obs = wgs84.latlon(LAT, LON, ALT / 1000)

    now_utc = datetime.now(timezone.utc)
    t0 = ts.from_datetime(now_utc)
    t1 = ts.from_datetime(now_utc + timedelta(hours=2))

    t, ev = sat.find_events(obs, t0, t1, altitude_degrees=MIN_ELEV)

    for i in range(len(ev)):
        if ev[i] == 0 and i+2 < len(ev):
            if ev[i+1] == 1 and ev[i+2] == 2:
                start = t[i].utc_datetime().replace(tzinfo=timezone.utc)
                peak = t[i+1].utc_datetime().replace(tzinfo=timezone.utc)
                end = t[i+2].utc_datetime().replace(tzinfo=timezone.utc)
                pre = start - timedelta(minutes=PREPASS_MIN)

                log("[PASS] Nouvelle passe trouvee (UTC):")
                log(f"       prealert : {pre}")
                log(f"       debut    : {start}")
                log(f"       peak     : {peak}")
                log(f"       fin      : {end}")

                return pre, start, peak, end

    log("[PASS] Aucune passe trouvee.")
    return None

# =====================================================
# ENVOI DAPNET
# =====================================================
def send_dapnet(text):
    payload = {
        "text": text,
        "callSignNames": CALLSIGNS,
        "transmitterGroupNames": [TX_GROUP],
        "emergency": False,
    }
    log(f"[DAPNET] ENVOI : '{text}'")
    try:
        r = requests.post(
            DAPNET_URL,
            auth=(DAPNET_USER, DAPNET_PASS),
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload),
            timeout=10
        )
        r.raise_for_status()
        log("[DAPNET] OK")
    except Exception as e:
        log(f"[DAPNET] ERREUR : {e}")

# =====================================================
# OUTILS TEMPORELS
# =====================================================
def in_window(now_utc, evt_utc):
    diff = abs((now_utc - evt_utc).total_seconds())
    log(f"[DEBUG] diff={diff:.1f}s window={WINDOW_SEC}s")
    return diff <= WINDOW_SEC

def fmt_local_hm(dt_utc):
    return dt_utc.astimezone().strftime("%H:%M")

# =====================================================
# LOGIQUE ISS
# =====================================================
def process_iss(state):

    iss = state["ISS"]
    now_utc = datetime.now(timezone.utc)

    # 1) PASSE ABSENTE -> CALCUL
    if not iss["pass_start"]:
        log("[INFO] Aucune passe -> calcul")
        res = compute_pass_utc()
        if not res:
            return
        pre, start, peak, end = res

        iss["pass_prealert"] = pre.isoformat()
        iss["pass_start"] = start.isoformat()
        iss["pass_peak"] = peak.isoformat()
        iss["pass_end"] = end.isoformat()
        iss["sent_pre"] = False
        iss["sent_start"] = False
        iss["sent_peak"] = False
        iss["sent_end"] = False

        save_state(state)
        return

    # 2) PASSE ACTIVE
    pre_utc = datetime.fromisoformat(iss["pass_prealert"])
    start_utc = datetime.fromisoformat(iss["pass_start"])
    peak_utc = datetime.fromisoformat(iss["pass_peak"])
    end_utc = datetime.fromisoformat(iss["pass_end"])

    log("[INFO] Passe active (UTC):")
    log(f"       prealert={pre_utc}")
    log(f"       debut   ={start_utc}")
    log(f"       peak    ={peak_utc}")
    log(f"       fin     ={end_utc}")

    # Charger Skyfield pour calcul az/ele
    tle = get_iss_tle()
    if not tle:
        log("[ERROR] Impossible charger TLE pour az/el")
        return

    ts = load.timescale()
    sat = EarthSatellite(tle[1], tle[2], "ISS", ts)
    obs = wgs84.latlon(LAT, LON, ALT / 1000)

    # ---------------------------
    # PREALERTE
    # ---------------------------
    if not iss["sent_pre"]:
        log_debug_time("PREALERTE", now_utc, pre_utc)
        if in_window(now_utc, pre_utc):
            alt, az = get_az_el(ts, sat, obs, start_utc)
            msg = (
                f"ISS dans 15 min {fmt_local_hm(start_utc)} "
                f"- Azimut {az:.0f}"
            )
            send_dapnet(msg)
            iss["sent_pre"] = True

    # ---------------------------
    # DEBUT
    # ---------------------------
    if not iss["sent_start"]:
        log_debug_time("DEBUT", now_utc, start_utc)
        if in_window(now_utc, start_utc):
            alt, az = get_az_el(ts, sat, obs, start_utc)
            msg = (
                f"ISS visible {fmt_local_hm(start_utc)} "
                f"- Azimut {az:.0f} Elevation {alt:.0f}"
            )
            send_dapnet(msg)
            iss["sent_start"] = True

    # ---------------------------
    # PEAK
    # ---------------------------
    if not iss["sent_peak"]:
        log_debug_time("PEAK", now_utc, peak_utc)
        if in_window(now_utc, peak_utc):
            alt, az = get_az_el(ts, sat, obs, peak_utc)
            msg = (
                f"ISS zenith {fmt_local_hm(peak_utc)} "
                f"- Azimut {az:.0f} Elevation {alt:.0f}"
            )
            send_dapnet(msg)
            iss["sent_peak"] = True

    # ---------------------------
    # FIN
    # ---------------------------
    if not iss["sent_end"]:
        log_debug_time("FIN", now_utc, end_utc)
        if in_window(now_utc, end_utc):
            alt, az = get_az_el(ts, sat, obs, end_utc)
            msg = (
                f"ISS fin {fmt_local_hm(end_utc)} "
                f"- Azimut {az:.0f} Elevation {alt:.0f}"
            )
            send_dapnet(msg)
            iss["sent_end"] = True

    # ---------------------------
    # PURGE APRES FIN
    # ---------------------------
    if iss["sent_end"] and now_utc > end_utc + timedelta(minutes=PASS_EXPIRE_MIN):
        log("[INFO] Passe terminee -> reset")
        reset_iss_state(state)

    save_state(state)

# =====================================================
# MAIN LOOP
# =====================================================
def main():
    log("============= NOUVEAU CYCLE =============")
    state = load_state()
    process_iss(state)
    log("============== FIN CYCLE ===============\n")


if __name__ == "__main__":
    main()


