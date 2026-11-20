"""Shared settings, database and helpers for the A Square store (app.py) and admin (admin.py)."""
import json
import os
import sqlite3
import urllib.parse
import uuid
from datetime import date, datetime

import streamlit as st

# ----------------------------------------------------------------------------
# CONFIG - edit these for your business
# ----------------------------------------------------------------------------
BRAND = "A Square"
TAGLINE = "Wear Your Own Fashion"
WHATSAPP_NUMBER = "919999999999"  # country code + number, no + sign
CURRENCY = "₹"
CATEGORIES = ["Men", "Women", "Kids", "Ethnic", "Western", "Accessories", "Footwear"]
SIZES = ["XS", "S", "M", "L", "XL", "XXL", "Free Size", "Kids 2-4Y", "Kids 5-8Y"]

def _get_admin_password():
    if os.environ.get("ADMIN_PASSWORD"):
        return os.environ["ADMIN_PASSWORD"]
    try:
        return st.secrets["ADMIN_PASSWORD"]
    except Exception:  # no secrets.toml or key missing
        return "asquare123"


ADMIN_PASSWORD = _get_admin_password()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(BASE_DIR, "product_images")
DB_PATH = os.path.join(BASE_DIR, "asquare.db")
os.makedirs(IMG_DIR, exist_ok=True)


# ----------------------------------------------------------------------------
# DATABASE
# ----------------------------------------------------------------------------
def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def run(sql, params=(), fetch=False):
    con = db()
    cur = con.execute(sql, params)
    rows = [dict(r) for r in cur.fetchall()] if fetch else None
    con.commit()
    con.close()
    return rows


def init_db():
    run("""CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, category TEXT,
        price REAL, mrp REAL, sizes TEXT, colors TEXT, stock INTEGER,
        description TEXT, images TEXT, featured INTEGER DEFAULT 0,
        active INTEGER DEFAULT 1, created TEXT)""")
    run("""CREATE TABLE IF NOT EXISTS offers(
        id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, subtitle TEXT,
        code TEXT, discount_pct INTEGER, min_order REAL DEFAULT 0,
        valid_till TEXT, color TEXT, active INTEGER DEFAULT 1)""")
    run("""CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT, customer TEXT, phone TEXT,
        address TEXT, items TEXT, total REAL, coupon TEXT,
        status TEXT DEFAULT 'New', created TEXT)""")


init_db()


def save_images(files):
    names = []
    for f in files or []:
        ext = os.path.splitext(f.name)[1].lower() or ".jpg"
        name = f"{uuid.uuid4().hex}{ext}"
        with open(os.path.join(IMG_DIR, name), "wb") as out:
            out.write(f.getbuffer())
        names.append(name)
    return names


def img_paths(p):
    out = []
    for n in (p.get("images") or "").split(","):
        path = os.path.join(IMG_DIR, n.strip())
        if n.strip() and os.path.exists(path):
            out.append(path)
    return out


def active_offers():
    today = date.today().isoformat()
    return run(
        "SELECT * FROM offers WHERE active=1 AND (valid_till IS NULL OR valid_till='' OR valid_till>=?) ORDER BY id DESC",
        (today,), fetch=True,
    )


def money(x):
    return f"{CURRENCY}{x:,.0f}"


def discount_pct(p):
    return round((p["mrp"] - p["price"]) * 100 / p["mrp"]) if p["mrp"] and p["mrp"] > p["price"] else 0



INK, PLUM, GOLD, SALE, GREEN, MIST = "#1d1530", "#4a2c6d", "#f5b324", "#e5334f", "#1b9e5a", "#f4f3f8"

PALETTE = {"plum": f"linear-gradient(110deg,{PLUM},#8a4fbf)",
           "sunset": f"linear-gradient(110deg,{SALE},#ff8a3d)",
           "ink": f"linear-gradient(110deg,{INK},#3b2f63)",
           "green": f"linear-gradient(110deg,#0d7a47,#35c48a)",
           "gold": f"linear-gradient(110deg,#c98a00,{GOLD})"}



def apply_style():
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=Playfair+Display:ital,wght@1,600&display=swap');
    html, body, [class*="css"], .stApp {{ font-family: 'Outfit', sans-serif; }}
    .stApp {{ background: {MIST}; }}
    header[data-testid="stHeader"] {{ display:none; }}
    .block-container {{ padding-top: 0 !important; max-width: 1250px; }}

    .topbar {{ background:{INK}; margin:0 -9999px; padding:14px 9999px; color:#fff;
      display:flex; align-items:center; gap:18px; }}
    .logo {{ font-size:30px; font-weight:700; letter-spacing:-0.5px; line-height:1; }}
    .logo span {{ color:{GOLD}; }}
    .tag {{ font-family:'Playfair Display',serif; font-style:italic; color:{GOLD}; font-size:15px; margin-top:2px; }}
    .strip {{ background:#fff; margin:0 -9999px 16px; padding:8px 9999px; border-bottom:1px solid #e4e1ec;
      font-weight:500; color:#333; }}

    .hero {{ border-radius:10px; padding:28px 34px; color:#fff; margin-bottom:10px; }}
    .hero h2 {{ margin:0; font-size:34px; font-weight:700; }}
    .hero p {{ margin:6px 0 0; font-size:16px; opacity:.92; }}
    .code {{ display:inline-block; margin-top:12px; border:1.5px dashed #fff; padding:4px 14px;
      border-radius:6px; font-weight:600; letter-spacing:2px; }}

    .sec {{ font-size:22px; font-weight:700; color:{INK}; margin:18px 0 8px; }}
    .pname {{ font-weight:500; color:#222; font-size:15px; height:22px; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; }}
    .pcat {{ color:#777; font-size:12px; }}
    .price {{ font-size:19px; font-weight:700; color:{INK}; }}
    .mrp {{ color:#888; text-decoration:line-through; margin-left:6px; font-size:13px; }}
    .off {{ color:{GREEN}; font-weight:600; margin-left:6px; font-size:13px; }}
    .badge {{ background:{SALE}; color:#fff; padding:2px 8px; border-radius:4px; font-size:12px; font-weight:600; }}
    .low {{ color:{SALE}; font-size:12px; font-weight:500; }}
    .noimg {{ background:#e9e6f2; border-radius:8px; height:230px; display:flex; align-items:center;
      justify-content:center; color:#8a82a3; font-size:14px; }}
    .footer {{ margin:40px -9999px 0; padding:26px 9999px; background:{INK}; color:#cfc8e0; text-align:center; }}
    div[data-testid="stImage"] img {{ border-radius:8px; object-fit:cover; }}
    .stButton > button[kind="primary"] {{ background:{PLUM}; border:none; }}
    </style>
    """, unsafe_allow_html=True)
