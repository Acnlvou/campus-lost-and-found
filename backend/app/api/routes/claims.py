from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...db.models import Claim, Item
from ...db.serializers import claim_dict
from ...modules.claims.service import review_claim, submit_claim
from ..deps import get_db, login_required
from ..schemas import ClaimRequest, ReviewRequest

router = APIRouter()


@router.post("/items/{item_id}/claims", status_code=201)
def claim(item_id: int, body: ClaimRequest, user=Depends(login_required), db: Session = Depends(get_db)):
    claim_id = submit_claim(db, user.id, item_id, body.note)
    return {"id": claim_id, "redirect": f"/items/{item_id}"}


@router.post("/claims/{claim_id}/review")
def review(claim_id: int, body: ReviewRequest, user=Depends(login_required), db: Session = Depends(get_db)):
    review_claim(db, user.id, claim_id, body.decision)
    return {"message": "审核已保存", "reload": True}


@router.get("/applications")
def applications(user=Depends(login_required), db: Session = Depends(get_db)):
    rows = (
        db.query(Claim, Item.title, Item.location)
        .join(Item, Item.id == Claim.item_id)
        .filter(Claim.applicant_id == user.id)
        .order_by(Claim.id.desc())
        .all()
    )
    return {"claims": [claim_dict(c, title=t, location=l) for c, t, l in rows]}
