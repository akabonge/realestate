"""Anthropic tool_use schemas for Rappahannock Realty Group."""

TOOLS = [
    {
        "name": "search_listings",
        "description": (
            "Search active property listings in the Fredericksburg, Stafford, Spotsylvania, "
            "and King George area. All parameters are optional — omit any you don't want to filter by."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "min_price": {"type": "integer", "description": "Minimum listing price in USD."},
                "max_price": {"type": "integer", "description": "Maximum listing price in USD."},
                "bedrooms": {"type": "integer", "description": "Minimum number of bedrooms."},
                "bathrooms": {"type": "number", "description": "Minimum number of bathrooms (e.g. 2.5)."},
                "city": {
                    "type": "string",
                    "description": "City to filter by: Fredericksburg, Stafford, Spotsylvania, or King George.",
                },
                "min_sqft": {"type": "integer", "description": "Minimum square footage."},
            },
            "required": [],
        },
    },
    {
        "name": "get_listing_details",
        "description": "Get full details on a specific property listing by its ID (e.g. RRG-1004).",
        "input_schema": {
            "type": "object",
            "properties": {
                "listing_id": {
                    "type": "string",
                    "description": "The listing ID from search results.",
                },
            },
            "required": ["listing_id"],
        },
    },
    {
        "name": "schedule_showing",
        "description": (
            "Schedule a property showing for a client. Always check listing details first. "
            "Showings are available Monday through Saturday, 9 AM to 5 PM."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "listing_id": {"type": "string", "description": "The listing ID to show."},
                "name": {"type": "string", "description": "Client's full name."},
                "email": {"type": "string", "description": "Client's email address."},
                "phone": {"type": "string", "description": "Client's phone number (optional)."},
                "preferred_date": {"type": "string", "description": "Preferred showing date YYYY-MM-DD."},
                "preferred_time": {
                    "type": "string",
                    "description": "Preferred time HH:MM (24-hour). Available on the hour from 09:00 to 16:00.",
                },
            },
            "required": ["listing_id", "name", "email", "preferred_date", "preferred_time"],
        },
    },
    {
        "name": "estimate_mortgage",
        "description": (
            "Calculate an estimated monthly mortgage payment for a given home price. "
            "Useful for helping buyers understand affordability."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "home_price": {"type": "integer", "description": "Purchase price in USD."},
                "down_payment_pct": {
                    "type": "number",
                    "description": "Down payment as a percentage (e.g. 20 for 20%). Defaults to 20.",
                },
                "term_years": {
                    "type": "integer",
                    "description": "Loan term in years — 15 or 30. Defaults to 30.",
                },
                "rate": {
                    "type": "number",
                    "description": "Annual interest rate as a percentage (e.g. 6.75). Defaults to current market average.",
                },
            },
            "required": ["home_price"],
        },
    },
]
