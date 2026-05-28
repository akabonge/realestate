"""
One-time data ingestion script. Run this before starting the server.
Re-running is safe — it clears and rebuilds the collection.

Usage:
    python scripts/ingest_data.py
"""
import sys
import json
from pathlib import Path

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.rag.embedder import get_collection

DATA_DIR = Path(__file__).parent.parent / "data"


def load_json(filename: str) -> dict:
    with open(DATA_DIR / filename, "r", encoding="utf-8") as f:
        return json.load(f)


def build_documents() -> list[tuple[str, str, str]]:
    """Returns list of (id, text, source) tuples."""
    docs = []

    # Agency info
    info = load_json("agency_info.json")["agency"]
    docs.append((
        "agency/overview",
        f"Rappahannock Realty Group\n{info['about']}\n"
        f"Phone: {info['phone']}\nEmail: {info['email']}\nAddress: {info['address']}\n"
        f"Hours: Mon-Fri {info['hours']['monday_friday']}, Sat {info['hours']['saturday']}, Sun {info['hours']['sunday']}\n"
        f"Service areas: {', '.join(info['service_areas'])}\n"
        f"Specialties: {', '.join(info['specialties'])}",
        "agency/overview"
    ))

    for agent in info["agents"]:
        docs.append((
            f"agent/{agent['name'].replace(' ', '_')}",
            f"Agent: {agent['name']}, {agent['title']}\nPhone: {agent['phone']}\nEmail: {agent['email']}\nSpecialty: {agent['specialty']}",
            "agency/agents"
        ))

    docs.append((
        "agency/buyer_process",
        "Buyer process at Rappahannock Realty Group:\n" + "\n".join(info["buyer_process"]),
        "agency/process"
    ))

    docs.append((
        "agency/seller_process",
        "Seller process at Rappahannock Realty Group:\n" + "\n".join(info["seller_process"]),
        "agency/process"
    ))

    docs.append((
        "agency/commission",
        f"Commission: {info['commission']}\nAverage days on market: {info['average_days_on_market']}",
        "agency/commission"
    ))

    # Neighborhoods
    neighborhoods = load_json("neighborhoods.json")["neighborhoods"]
    for n in neighborhoods:
        highlights = "\n".join(f"- {h}" for h in n["highlights"])
        hoa_info = (
            f"HOA: Yes, ~${n.get('typical_hoa_fee', 'varies')}/month"
            if n.get("hoa_common") else "HOA: None"
        )
        doc = (
            f"Neighborhood: {n['name']}\n"
            f"County: {n['county']}\nType: {n['type']}\n"
            f"Price range: {n['price_range']}\nMedian price: ${n['median_home_price']:,}\n"
            f"Description: {n['description']}\n"
            f"Best for: {n['best_for']}\n"
            f"Schools: {n.get('schools', 'Varies by location')}\n"
            f"{hoa_info}\n"
            f"Highlights:\n{highlights}"
        )
        # Add commute info
        for key, val in n.items():
            if key.startswith("commute_"):
                destination = key.replace("commute_to_", "").replace("_", " ").title()
                doc += f"\nCommute to {destination}: {val}"
        docs.append((f"neighborhood/{n['name'].replace('/', '_')}", doc, f"neighborhoods/{n['name']}"))

    # Listings
    listings = load_json("listings.json")["listings"]
    for listing in listings:
        features = ", ".join(listing.get("features", []))
        hoa = f"HOA: ${listing['hoa_fee']}/month" if listing.get("hoa_fee") else "No HOA"
        doc = (
            f"Listing {listing['id']}: {listing['address']}\n"
            f"Neighborhood: {listing['neighborhood']} | County: {listing['county']}\n"
            f"Type: {listing['type']} | Status: {listing['status']}\n"
            f"Price: ${listing['price']:,} | {listing['bedrooms']} bed / {listing['bathrooms']} bath | {listing['sqft']:,} sqft\n"
            f"Year built: {listing['year_built']} | Lot: {listing['lot_size']} | Garage: {listing['garage']}\n"
            f"{hoa} | Annual taxes: ~${listing['taxes_annual']:,}\n"
            f"Schools: {listing.get('elementary', 'N/A')} / {listing.get('middle', 'N/A')} / {listing.get('high', 'N/A')}\n"
            f"Features: {features}\n"
            f"Description: {listing['description']}\n"
            f"Days on market: {listing['days_on_market']} | Agent: {listing['agent']}"
        )
        docs.append((f"listing/{listing['id']}", doc, f"listings/{listing['neighborhood']}"))

    # Market stats
    stats = load_json("listings.json")["market_stats"]
    metro = stats["fredericksburg_metro"]
    docs.append((
        "market/stats",
        f"Fredericksburg Metro Market Stats (as of {stats['as_of']}):\n"
        f"Median sale price: ${metro['median_sale_price']:,}\n"
        f"Average days on market: {metro['avg_days_on_market']} days\n"
        f"List-to-sale ratio: {metro['list_to_sale_ratio']}\n"
        f"Inventory: {metro['inventory_months']} months supply\n"
        f"Market condition: {metro['market_condition']}\n"
        f"Year-over-year price change: {metro['yoy_price_change']}\n"
        f"Mortgage rates (approx): 30yr fixed {stats['mortgage_rates']['30yr_fixed_approx']}, "
        f"15yr fixed {stats['mortgage_rates']['15yr_fixed_approx']}",
        "market/stats"
    ))

    # FAQs
    faqs = load_json("faqs.json")["faqs"]
    by_category: dict[str, list] = {}
    for faq in faqs:
        by_category.setdefault(faq["category"], []).append(faq)

    for category, items in by_category.items():
        text = f"FAQs — {category}:\n\n"
        text += "\n\n".join(f"Q: {item['question']}\nA: {item['answer']}" for item in items)
        safe_cat = category.replace(" ", "_").replace("/", "_").replace("&", "and")
        docs.append((f"faq/{safe_cat}", text, f"faqs/{category}"))

    return docs


def main():
    print("Connecting to ChromaDB...")
    collection = get_collection()

    docs = build_documents()
    print(f"Prepared {len(docs)} documents.")

    # Clear existing entries
    existing_ids = collection.get()["ids"]
    if existing_ids:
        collection.delete(ids=existing_ids)
        print(f"Cleared {len(existing_ids)} existing documents.")

    ids = [d[0] for d in docs]
    texts = [d[1] for d in docs]
    metadatas = [{"source": d[2]} for d in docs]

    print("Generating embeddings and storing...")
    collection.add(ids=ids, documents=texts, metadatas=metadatas)
    print(f"Done. {collection.count()} documents indexed.")


if __name__ == "__main__":
    main()
