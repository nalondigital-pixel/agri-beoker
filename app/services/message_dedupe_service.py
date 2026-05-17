from app.db.supabase_client import supabase


def has_processed_message(message_id: str):
    if not message_id:
        return False

    response = (
        supabase.table("processed_whatsapp_messages")
        .select("id")
        .eq("id", message_id)
        .limit(1)
        .execute()
    )

    return bool(response.data)


def mark_message_processed(message_id: str, from_phone: str):
    if not message_id:
        return None

    try:
        response = (
            supabase.table("processed_whatsapp_messages")
            .insert({
                "id": message_id,
                "from_phone": from_phone,
            })
            .execute()
        )

        return response.data

    except Exception as e:
        print("Message dedupe insert error:", e)
        return None