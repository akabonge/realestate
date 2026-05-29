"""
SQLite mock database for Rappahannock Realty Group.
Contains 14 realistic Fredericksburg-area listings and a showings table.
"""
import sqlite3
import random
import string
from datetime import date, datetime, timedelta
from pathlib import Path

_DB_PATH = Path(__file__).parent.parent.parent / "realty.db"

# Showing slots: Mon-Sat 9am-5pm, every 60 min
_SHOW_DAYS = {0, 1, 2, 3, 4, 5}  # 0=Mon ... 5=Sat, 6=Sun closed
_SHOW_TIMES = ["09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00"]

_LISTINGS = [
    ("RRG-1001", "214 Fall Hill Ave", "Fredericksburg", "VA", 399000, 3, 2.0, 1850, 2002,
     "Traditional brick colonial in the heart of Fredericksburg. Hardwood floors throughout, updated kitchen, large deck. Walk to VRE."),
    ("RRG-1002", "89 Breckenridge Ln", "Stafford", "VA", 519000, 4, 3.0, 2640, 2015,
     "Move-in ready craftsman in sought-after Embrey Mill. Open floor plan, chef's kitchen, main-level office. HOA pool and trails."),
    ("RRG-1003", "3301 Lakeview Pkwy", "Spotsylvania", "VA", 289000, 3, 2.0, 1420, 1998,
     "Affordable rancher on quiet cul-de-sac. New HVAC 2023, updated bathrooms, large flat backyard. Minutes to I-95."),
    ("RRG-1004", "701 Prince Edward St", "Fredericksburg", "VA", 625000, 4, 3.5, 3100, 1890,
     "Beautifully restored historic townhouse in Old Town. Original heart pine floors, exposed brick, modern kitchen. Steps from the Rappahannock."),
    ("RRG-1005", "12 Copper Mill Dr", "Stafford", "VA", 459000, 4, 2.5, 2380, 2019,
     "Like-new craftsman in Aquia Harbour. Quartz counters, SS appliances, finished basement. Gated community with marina access."),
    ("RRG-1006", "5500 Plank Rd", "Spotsylvania", "VA", 349000, 3, 2.0, 1680, 2007,
     "Low-maintenance colonial with solar panels. Energy bills average under $60/month. Two-car garage, fenced yard, cul-de-sac."),
    ("RRG-1007", "44 River Heights Dr", "King George", "VA", 385000, 4, 3.0, 2100, 2011,
     "Spacious colonial with river views. Large owner's suite, screened porch, community boat ramp. 30 min to Dahlgren NSWC."),
    ("RRG-1008", "2200 Mine Rd", "Fredericksburg", "VA", 749000, 5, 4.0, 4200, 2018,
     "Luxury estate on 1.2 acres. Gourmet kitchen, home theater, 3-car garage, saltwater pool. No HOA, private setting."),
    ("RRG-1009", "301 Stafford Lakes Pkwy", "Stafford", "VA", 319000, 3, 2.0, 1540, 2001,
     "Updated townhome in Stafford Lakes. New roof 2022, renovated kitchen, community pool. Easy commute on Rt 1."),
    ("RRG-1010", "18 Wilderness Rd", "Spotsylvania", "VA", 279000, 2, 2.0, 1100, 1995,
     "Cozy patio home ideal for first-time buyers or downsizers. HOA covers lawn care and exterior. Quiet 55+ community."),
    ("RRG-1011", "90 White Oak Rd", "King George", "VA", 425000, 4, 2.5, 2250, 2014,
     "Colonial on half-acre lot with three-season porch. Updated owner's suite bath, new appliances, two sheds. Minutes to Dahlgren gate."),
    ("RRG-1012", "608 George St", "Fredericksburg", "VA", 569000, 3, 2.5, 2050, 1940,
     "Renovated Victorian in Sophia Street corridor. Chef's kitchen, original moldings restored, rooftop deck with river view."),
    ("RRG-1013", "7700 Harrison Rd", "Fredericksburg", "VA", 189000, 2, 1.0, 920, 1975,
     "Investor special — priced to sell. Needs cosmetic updates. Strong rental area; comps support $1,400-$1,600/month."),
    ("RRG-1014", "155 Celebrate Virginia Pkwy", "Stafford", "VA", 685000, 5, 4.5, 3800, 2021,
     "Nearly new luxury home in Celebrate Virginia North. Main-level primary suite, loft, 3-car tandem garage. Resort-style HOA amenities."),
]


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _gen_code() -> str:
    return "RRG-S" + "".join(random.choices(string.digits, k=4))


def init_db() -> None:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS listings (
            id TEXT PRIMARY KEY,
            address TEXT NOT NULL,
            city TEXT NOT NULL,
            state TEXT NOT NULL,
            price INTEGER NOT NULL,
            bedrooms INTEGER NOT NULL,
            bathrooms REAL NOT NULL,
            sqft INTEGER NOT NULL,
            year_built INTEGER NOT NULL,
            description TEXT NOT NULL,
            status TEXT DEFAULT 'active'
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS showings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            listing_id TEXT NOT NULL,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT DEFAULT '',
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            confirmed_at TEXT NOT NULL,
            confirmation_code TEXT NOT NULL UNIQUE
        )
    """)

    if cur.execute("SELECT COUNT(*) FROM listings").fetchone()[0] == 0:
        cur.executemany("""
            INSERT INTO listings (id, address, city, state, price, bedrooms, bathrooms, sqft, year_built, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, _LISTINGS)

    conn.commit()
    conn.close()


def search_listings(min_price: int = 0, max_price: int = 9999999,
                    bedrooms: int = 0, bathrooms: float = 0.0,
                    city: str = "", min_sqft: int = 0) -> list[dict]:
    conn = get_conn()
    cur = conn.cursor()
    query = """
        SELECT * FROM listings
        WHERE price BETWEEN ? AND ?
          AND bedrooms >= ?
          AND bathrooms >= ?
          AND sqft >= ?
          AND status = 'active'
    """
    params = [min_price, max_price, bedrooms, bathrooms, min_sqft]
    if city:
        query += " AND LOWER(city) = LOWER(?)"
        params.append(city)
    query += " ORDER BY price"
    rows = cur.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_listing(listing_id: str) -> dict | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM listings WHERE id = ?", (listing_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_showing_slots(for_date: str) -> list[str]:
    try:
        d = date.fromisoformat(for_date)
    except ValueError:
        return []
    if d.weekday() not in _SHOW_DAYS:
        return []
    conn = get_conn()
    booked = {row["time"] for row in conn.execute(
        "SELECT time FROM showings WHERE date = ?", (for_date,)
    ).fetchall()}
    conn.close()
    return [t for t in _SHOW_TIMES if t not in booked]


def create_showing(listing_id: str, name: str, email: str, phone: str,
                   for_date: str, time: str) -> dict:
    code = _gen_code()
    conn = get_conn()
    try:
        conn.execute("""
            INSERT INTO showings (listing_id, name, email, phone, date, time, confirmed_at, confirmation_code)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (listing_id, name, email, phone, for_date, time,
              datetime.now().isoformat(), code))
        conn.commit()
        listing = get_listing(listing_id)
        address = listing["address"] if listing else listing_id
        return {
            "success": True,
            "confirmation_code": code,
            "listing_id": listing_id,
            "address": address,
            "date": for_date,
            "time": time,
            "name": name,
        }
    except sqlite3.IntegrityError:
        return {"success": False, "error": "Duplicate confirmation code — please retry."}
    finally:
        conn.close()


def estimate_mortgage(home_price: int, down_pct: float = 20.0,
                      term_years: int = 30, rate: float = 6.75) -> dict:
    down = home_price * (down_pct / 100)
    principal = home_price - down
    monthly_rate = rate / 100 / 12
    n = term_years * 12
    if monthly_rate == 0:
        payment = principal / n
    else:
        payment = principal * (monthly_rate * (1 + monthly_rate) ** n) / ((1 + monthly_rate) ** n - 1)
    return {
        "home_price": home_price,
        "down_payment": round(down),
        "loan_amount": round(principal),
        "interest_rate_pct": rate,
        "term_years": term_years,
        "estimated_monthly_payment": round(payment),
        "note": "Estimate only. Includes P&I; excludes taxes, insurance, and HOA.",
    }
