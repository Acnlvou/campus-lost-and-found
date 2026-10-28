def user_dict(user) -> dict:
    return {"id": user.id, "username": user.username, "name": user.name, "role": user.role}


def item_dict(item, owner_name=None) -> dict:
    data = {
        "id": item.id,
        "owner_id": item.owner_id,
        "kind": item.kind,
        "title": item.title,
        "category": item.category,
        "location": item.location,
        "event_time": item.event_time,
        "description": item.description,
        "status": item.status,
        "pub_status": item.pub_status,
        "created_at": item.created_at,
    }
    if owner_name is not None:
        data["owner_name"] = owner_name
    return data


def claim_dict(claim, applicant_name=None, title=None, location=None) -> dict:
    data = {
        "id": claim.id,
        "item_id": claim.item_id,
        "applicant_id": claim.applicant_id,
        "note": claim.note,
        "status": claim.status,
        "created_at": claim.created_at,
        "updated_at": claim.updated_at,
    }
    if applicant_name is not None:
        data["applicant_name"] = applicant_name
    if title is not None:
        data["title"] = title
    if location is not None:
        data["location"] = location
    return data


def audit_dict(row) -> dict:
    return {
        "id": row.id,
        "actor_id": row.actor_id,
        "action": row.action,
        "item_id": row.item_id,
        "detail": row.detail,
        "created_at": row.created_at,
    }
