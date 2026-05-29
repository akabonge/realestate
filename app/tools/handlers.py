"""
Tool execution handlers for Rappahannock Realty Group.
Each function maps to one tool definition and returns a plain dict.
"""
from app.tools.mock_db import (
    search_listings,
    get_listing,
    get_showing_slots,
    create_showing,
    estimate_mortgage,
)


def handle_search_listings(min_price: int = 0, max_price: int = 9999999,
                            bedrooms: int = 0, bathrooms: float = 0.0,
                            city: str = "", min_sqft: int = 0) -> dict:
    results = search_listings(min_price, max_price, bedrooms, bathrooms, city, min_sqft)
    if not results:
        return {
            "found": False,
            "message": "No active listings match those criteria. Try widening the price range or removing filters.",
        }
    # Return a summary view to keep token usage manageable
    summary = [
        {
            "id": r["id"],
            "address": f"{r['address']}, {r['city']}, {r['state']}",
            "price": r["price"],
            "beds": r["bedrooms"],
            "baths": r["bathrooms"],
            "sqft": r["sqft"],
            "year_built": r["year_built"],
            "description": r["description"][:120] + "..." if len(r["description"]) > 120 else r["description"],
        }
        for r in results[:6]  # cap at 6 results
    ]
    return {"found": True, "count": len(results), "listings": summary}


def handle_get_listing_details(listing_id: str) -> dict:
    listing = get_listing(listing_id)
    if not listing:
        return {"found": False, "message": f"No listing found with ID {listing_id}."}
    return {"found": True, "listing": dict(listing)}


def handle_schedule_showing(listing_id: str, name: str, email: str,
                             preferred_date: str, preferred_time: str,
                             phone: str = "") -> dict:
    # Validate slot
    available = get_showing_slots(preferred_date)
    if not available:
        return {
            "success": False,
            "error": f"No showing slots available on {preferred_date}. We schedule Monday to Saturday.",
        }
    if preferred_time not in available:
        return {
            "success": False,
            "error": f"{preferred_time} is not available on {preferred_date}. Open slots: {available}.",
        }
    result = create_showing(listing_id, name, email, phone, preferred_date, preferred_time)
    if result.get("success"):
        result["message"] = (
            f"Showing confirmed for {name} at {result['address']} on {preferred_date} at {preferred_time}. "
            f"Confirmation: {result['confirmation_code']}. An agent will meet you there."
        )
    return result


def handle_estimate_mortgage(home_price: int, down_payment_pct: float = 20.0,
                               term_years: int = 30, rate: float = 6.75) -> dict:
    return estimate_mortgage(home_price, down_payment_pct, term_years, rate)


def execute_tool(name: str, inputs: dict) -> dict:
    """Dispatch tool call by name."""
    if name == "search_listings":
        return handle_search_listings(
            min_price=inputs.get("min_price", 0),
            max_price=inputs.get("max_price", 9999999),
            bedrooms=inputs.get("bedrooms", 0),
            bathrooms=inputs.get("bathrooms", 0.0),
            city=inputs.get("city", ""),
            min_sqft=inputs.get("min_sqft", 0),
        )
    if name == "get_listing_details":
        return handle_get_listing_details(listing_id=inputs["listing_id"])
    if name == "schedule_showing":
        return handle_schedule_showing(
            listing_id=inputs["listing_id"],
            name=inputs["name"],
            email=inputs["email"],
            preferred_date=inputs["preferred_date"],
            preferred_time=inputs["preferred_time"],
            phone=inputs.get("phone", ""),
        )
    if name == "estimate_mortgage":
        return handle_estimate_mortgage(
            home_price=inputs["home_price"],
            down_payment_pct=inputs.get("down_payment_pct", 20.0),
            term_years=inputs.get("term_years", 30),
            rate=inputs.get("rate", 6.75),
        )
    return {"error": f"Unknown tool: {name}"}
