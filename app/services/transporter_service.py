from app.db.supabase_client import supabase
from app.services.location_pin_service import haversine_distance_km
from app.services.location_normalizer_service import normalize_location_name
from app.services.whatsapp_service import send_whatsapp_buttons, send_whatsapp_message


TRANSPORTER_MATCH_RADIUS_KM = 80


def normalize_phone(phone: str):
    return str(phone or "").replace("+", "").replace(" ", "").strip()


def register_or_update_transporter(
    phone: str,
    name: str,
    base_location: str,
    vehicle_type: str,
    vehicle_capacity,
    capacity_unit: str = "kg",
    latitude=None,
    longitude=None,
    is_verified: bool = False,
):
    phone = normalize_phone(phone)
    base_location = normalize_location_name(base_location)

    existing = (
        supabase.table("verified_transporters")
        .select("*")
        .eq("phone", phone)
        .limit(1)
        .execute()
    )

    payload = {
        "phone": phone,
        "name": name,
        "base_location": base_location,
        "vehicle_type": vehicle_type,
        "vehicle_capacity": vehicle_capacity,
        "capacity_unit": capacity_unit or "kg",
        "latitude": latitude,
        "longitude": longitude,
        "is_verified": is_verified,
        "is_active": True,
    }

    if existing.data:
        response = (
            supabase.table("verified_transporters")
            .update(payload)
            .eq("phone", phone)
            .execute()
        )
    else:
        response = (
            supabase.table("verified_transporters")
            .insert(payload)
            .execute()
        )

    if response.data:
        return response.data[0]

    return None


def get_transporter_by_phone(phone: str):
    phone = normalize_phone(phone)

    response = (
        supabase.table("verified_transporters")
        .select("*")
        .eq("phone", phone)
        .limit(1)
        .execute()
    )

    if response.data:
        return response.data[0]

    return None


def get_active_verified_transporters(limit: int = 100):
    response = (
        supabase.table("verified_transporters")
        .select("*")
        .eq("is_active", True)
        .eq("is_verified", True)
        .limit(limit)
        .execute()
    )

    return response.data or []


def transporter_capacity_ok(transporter: dict, total_quantity, unit: str):
    try:
        total_quantity = float(total_quantity or 0)
        capacity = float(transporter.get("vehicle_capacity") or 0)
    except Exception:
        return True

    if total_quantity <= 0 or capacity <= 0:
        return True

    transporter_unit = str(transporter.get("capacity_unit") or "").lower().strip()
    load_unit = str(unit or "").lower().strip()

    # If both are kg-compatible, compare.
    kg_units = ["kg", "kgs", "kilogram", "kilograms"]

    if transporter_unit in kg_units and load_unit in kg_units:
        return capacity >= total_quantity

    # If units are different/unknown, do not block automatically.
    return True


def transporter_route_matches(transporter: dict, suggestion: dict):
    origin = normalize_location_name(suggestion.get("origin_area") or "")
    destination = normalize_location_name(suggestion.get("destination") or "")

    routes_served = transporter.get("routes_served") or []

    route_text = " ".join([str(item).lower() for item in routes_served])

    if route_text:
        origin_ok = origin.lower() in route_text if origin else True
        destination_ok = destination.lower() in route_text if destination else True

        if origin_ok or destination_ok:
            return True

    base_location = normalize_location_name(transporter.get("base_location") or "")

    if base_location:
        if origin and base_location.lower() in origin.lower():
            return True

        if destination and base_location.lower() in destination.lower():
            return True

    # GPS matching if transporter has coordinates and suggestion has approximate origin coords later.
    # For now this is text-first because suggestions store origin/destination names.
    return False


def find_matching_transporters_for_suggestion(suggestion: dict):
    transporters = get_active_verified_transporters()
    matches = []

    for transporter in transporters:
        if not transporter_capacity_ok(
            transporter,
            suggestion.get("total_quantity"),
            suggestion.get("unit"),
        ):
            continue

        if transporter_route_matches(transporter, suggestion):
            matches.append(transporter)

    return matches


def create_transporter_job_request(transporter: dict, suggestion: dict):
    phone = transporter.get("phone")

    response = (
        supabase.table("transporter_job_requests")
        .insert({
            "transporter_phone": phone,
            "suggestion_id": suggestion.get("id"),
            "origin": suggestion.get("origin_area"),
            "destination": suggestion.get("destination"),
            "total_quantity": suggestion.get("total_quantity"),
            "unit": suggestion.get("unit"),
            "status": "pending",
        })
        .execute()
    )

    if response.data:
        return response.data[0]

    return None


def notify_transporter_about_pool(transporter: dict, suggestion: dict):
    job = create_transporter_job_request(transporter, suggestion)

    if not job:
        return None

    phone = transporter.get("phone")
    origin = suggestion.get("origin_area") or "Unknown origin"
    destination = suggestion.get("destination") or "Unknown destination"
    total_quantity = suggestion.get("total_quantity") or 0
    unit = suggestion.get("unit") or ""

    send_whatsapp_buttons(
        phone,
        (
            "🚚 Transport Job Opportunity\n\n"
            f"Route: {str(origin).title()} → {str(destination).title()}\n"
            f"Load: {total_quantity} {unit}\n\n"
            "Are you available for this job?"
        ),
        [
            {
                "id": f"transporter_accept_{job.get('id')}",
                "title": "Available",
            },
            {
                "id": f"transporter_decline_{job.get('id')}",
                "title": "Not Available",
            },
        ],
    )

    return job


def notify_matching_transporters_for_suggestion(suggestion: dict):
    matches = find_matching_transporters_for_suggestion(suggestion)

    if not matches:
        return {
            "status": "no_matching_transporters",
            "count": 0,
        }

    sent_jobs = []

    for transporter in matches[:5]:
        job = notify_transporter_about_pool(transporter, suggestion)

        if job:
            sent_jobs.append(job)

    return {
        "status": "transporters_notified",
        "count": len(sent_jobs),
        "jobs": sent_jobs,
    }


def get_transporter_job(job_id: str):
    response = (
        supabase.table("transporter_job_requests")
        .select("*")
        .eq("id", job_id)
        .limit(1)
        .execute()
    )

    if response.data:
        return response.data[0]

    return None


def get_pool_suggestion(suggestion_id: str):
    response = (
        supabase.table("transport_pool_suggestions")
        .select("*")
        .eq("id", suggestion_id)
        .limit(1)
        .execute()
    )

    if response.data:
        return response.data[0]

    return None


def mark_transporter_job(job_id: str, status: str):
    response = (
        supabase.table("transporter_job_requests")
        .update({"status": status})
        .eq("id", job_id)
        .execute()
    )

    if response.data:
        return response.data[0]

    return None


def handle_transporter_accept(phone: str, job_id: str):
    job = get_transporter_job(job_id)

    if not job:
        send_whatsapp_message(phone, "This transport job was not found or has expired.")
        return {"handled": True, "status": "job_not_found"}

    transporter = get_transporter_by_phone(phone)

    if not transporter:
        send_whatsapp_message(phone, "You are not registered as a verified transporter yet.")
        return {"handled": True, "status": "transporter_not_found"}

    mark_transporter_job(job_id, "accepted")

    suggestion = get_pool_suggestion(job.get("suggestion_id"))

    send_whatsapp_message(
        phone,
        (
            "✅ Availability received.\n\n"
            "Your contact will be shared with the interested users for this transport route."
        ),
    )

    if suggestion:
        interested_phones = suggestion.get("interested_phones") or []

        transporter_name = transporter.get("name") or "Verified transporter"
        transporter_phone = transporter.get("phone")
        vehicle_type = transporter.get("vehicle_type") or "vehicle"
        vehicle_capacity = transporter.get("vehicle_capacity") or ""
        capacity_unit = transporter.get("capacity_unit") or ""

        for user_phone in interested_phones:
            send_whatsapp_message(
                user_phone,
                (
                    "🚚 Verified Transporter Available\n\n"
                    f"Name: {transporter_name}\n"
                    f"Phone: +{transporter_phone}\n"
                    f"Vehicle: {vehicle_type}\n"
                    f"Capacity: {vehicle_capacity} {capacity_unit}\n\n"
                    f"Chat: https://wa.me/{transporter_phone}"
                ),
            )

    return {"handled": True, "status": "accepted"}


def handle_transporter_decline(phone: str, job_id: str):
    job = get_transporter_job(job_id)

    if not job:
        send_whatsapp_message(phone, "This transport job was not found or has expired.")
        return {"handled": True, "status": "job_not_found"}

    mark_transporter_job(job_id, "declined")

    send_whatsapp_message(
        phone,
        "No problem. We marked you as not available for this transport job.",
    )

    return {"handled": True, "status": "declined"}