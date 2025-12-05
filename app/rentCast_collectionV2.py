import requests
import json
import csv

API_KEY = "8355e5b44e76466296525f90b9523f35"  # Remove our API Key later

#   "Active"   -> only active listings
#   "Inactive" -> only inactive (off-market) listings
#   None       -> no filter (both, if API returns them)

# Here is where the wesite input would have to be placed (IMPORTANT)
LISTING_STATUS = None


def build_range(min_value, max_value):
    """Build RentCast-style range strings like 'min:max', '*:max', 'min:*'."""
    # By using min and max values we can build a range for the API to filter results.
    if min_value is None and max_value is None:
        return None
    lo = str(min_value) if min_value is not None else "*"
    hi = str(max_value) if max_value is not None else "*"
    return f"{lo}:{hi}"


def fetch_listings(
    listing_type="sale",      # "sale" or "rental" But we are focused on Sale for now
    zip_code=None,
    city=None,
    state=None,
    # e.g. "Single Family", "Condo". We will use filters in our other program for this.
    property_type=None,
    min_bedrooms=None,
    max_bedrooms=None,
    min_bathrooms=None,
    max_bathrooms=None,
    min_price=None,
    max_price=None,
    min_sqft=None,
    max_sqft=None,
    min_lot=None,
    max_lot=None,
    min_year=None,
    max_year=None,
    min_days_old=None,
    max_days_old=None,
    # e.g. "Active" or "Inactive" Basiclly is it on the market or not.
    status=None,
    limit=100,
    offset=0,
    include_total=False
):
    # 1. Choose endpoint, based on what we need on filters
    if listing_type == "sale":
        base_url = "https://api.rentcast.io/v1/listings/sale"
    elif listing_type == "rental":
        base_url = "https://api.rentcast.io/v1/listings/rental/long-term"
    else:
        raise ValueError("listing_type must be 'sale' or 'rental'")

    # 2. Base params for project script I added
    params = {
        "limit": limit,
        "offset": offset,
        "includeTotalCount": str(include_total).lower()
    }

    # 3. Location of properties
    if zip_code:
        params["zipCode"] = zip_code
    else:
        if city:
            params["city"] = city
        if state:
            params["state"] = state

    # 4. Property type
    if property_type:
        params["propertyType"] = property_type

    # 5. Ranged filters
    beds_range = build_range(min_bedrooms, max_bedrooms)
    if beds_range:
        params["bedrooms"] = beds_range

    baths_range = build_range(min_bathrooms, max_bathrooms)
    if baths_range:
        params["bathrooms"] = baths_range

    sqft_range = build_range(min_sqft, max_sqft)
    if sqft_range:
        params["squareFootage"] = sqft_range

    lot_range = build_range(min_lot, max_lot)
    if lot_range:
        params["lotSize"] = lot_range

    year_range = build_range(min_year, max_year)
    if year_range:
        params["yearBuilt"] = year_range

    price_range = build_range(min_price, max_price)
    if price_range:
        params["price"] = price_range

    days_old_range = build_range(min_days_old, max_days_old)
    if days_old_range:
        params["daysOld"] = days_old_range

    # 6. Status filter (Active / Inactive)
    if status:
        params["status"] = status

    headers = {
        "Accept": "application/json",
        "X-Api-Key": API_KEY
    }

    # 7. Call API which is RentCast
    response = requests.get(base_url, params=params, headers=headers)

    if response.status_code != 200:
        print("Request failed:", response.status_code, response.text)
        return None

    data = response.json()

    # Some APIs wrap results in a "listings" field. Handle that just in case.
    if isinstance(data, dict) and "listings" in data:
        data = data["listings"]

    # _______________Sort listings so that they are in close proximity based on latitude and longitude__________________________________
    coords = [
        (d.get("latitude"), d.get("longitude"))
        for d in data
        if d.get("latitude") is not None and d.get("longitude") is not None
    ]

    if coords:
        center_lat = sum(lat for lat, _ in coords) / len(coords)
        center_lon = sum(lon for _, lon in coords) / len(coords)

        def squared_distance_to_center(d):
            lat = d.get("latitude")
            lon = d.get("longitude")
            if lat is None or lon is None:
                return float("inf")
            return (lat - center_lat) ** 2 + (lon - center_lon) ** 2

        data = sorted(data, key=squared_distance_to_center)
    # _________________End of the proximity for sorts____________________________________________________

    # Show the keys of the first listing
    if data:
        print("First listing keys:", list(data[0].keys()))

    # prints a quick summary (now in sorted order) honestly useful
    print("\nSummary of listings (sorted by proximity):")
    for i, listing in enumerate(data, start=1):
        addr = listing.get("formattedAddress")
        price = listing.get("price")
        beds = listing.get("bedrooms")
        baths = listing.get("bathrooms")
        sqft = listing.get("squareFootage")
        status_val = listing.get("status")
        print(
            f"{i}. {addr} | ${price} | {beds} bd / {baths} ba | {sqft} sqft | {status_val}")

    return data


def save_listings_to_csv(listings, filename="listings.csv"):
    """Save a list of listing dicts to a CSV file (includes ALL top-level fields)."""
    if not listings:
        print("No listings to save.")
        return

    # Collect all keys across all listings so we don't miss any field
    fieldnames = sorted(
        {key for listing in listings for key in listing.keys()})

    # Adds latitude/longitude columns even if some listings don't have them
    for key in ("latitude", "longitude"):
        if key not in fieldnames:
            fieldnames.append(key)

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for listing in listings:
            writer.writerow(listing)

    print(f"\nSaved {len(listings)} listings to {filename}")


if __name__ == "__main__":  # Here is where we can enter the parameters for our search within the API
    listings = fetch_listings(
        listing_type="sale",
        city="Los Angeles",
        zip_code=None,
        property_type=None,
        min_price=None,
        max_price=None,
        min_bedrooms=None,
        min_bathrooms=None,
        limit=500,
        status=LISTING_STATUS
    )

    save_listings_to_csv(listings, filename="data/listings_RentCastAPI.csv")
