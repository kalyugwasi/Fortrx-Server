import json

from sqlalchemy import text
from sqlalchemy.orm import Session
from fastapi import HTTPException,status
from app.models import KeyBundle, User
from app.repositories import get_bundle_by_user_id,create_bundle,update_bundle
from app.schemas import KeyBundleUpload,KeyBundleResponse

def _deserialize_bundle_otpks(bundle):
    """Ensure bundle.one_time_prekeys is always a Python list, never a raw JSON string."""
    if isinstance(bundle.one_time_prekeys, str):
        keys = json.loads(bundle.one_time_prekeys)
    else:
        keys = bundle.one_time_prekeys or []
    # normalize back onto the instance so callers see a list
    bundle.one_time_prekeys = keys
    return bundle

def upload_key_bundle(db:Session,user_id:int,payload:KeyBundleUpload):
    # SQLite Text column cannot store a Python list — serialize to JSON string
    one_time_prekeys_json = json.dumps(payload.one_time_prekeys)
    bundle = get_bundle_by_user_id(db,user_id)
    if bundle:
        bundle = update_bundle(
            db,bundle,
            identity_key=payload.identity_key,
            signing_public=payload.signing_public,
            signed_prekey=payload.signed_prekey,
            signed_prekey_signature=payload.signed_prekey_signature,
            prekey_id=payload.prekey_id,
            one_time_prekeys=one_time_prekeys_json,
            kyber_prekey_public=payload.kyber_prekey_public,
            kyber_prekey_signature=payload.kyber_prekey_signature)
    else:
        bundle = create_bundle(
            db,
            user_id=user_id,
            identity_key=payload.identity_key,
            signing_public=payload.signing_public,
            signed_prekey=payload.signed_prekey,
            signed_prekey_signature=payload.signed_prekey_signature,
            prekey_id=payload.prekey_id,
            one_time_prekeys=one_time_prekeys_json,
            kyber_prekey_public=payload.kyber_prekey_public,
            kyber_prekey_signature=payload.kyber_prekey_signature
            )

    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.identity_public_key = payload.identity_key
        db.commit()
    return bundle

def fetch_key_bundle(db:Session,user_id:int):
    if db.bind.dialect.name == "sqlite":
        db.execute(text("BEGIN IMMEDIATE"))
        bundle = db.query(KeyBundle).filter(KeyBundle.user_id == user_id).first()
    else:
        bundle = (
            db.query(KeyBundle)
            .filter(KeyBundle.user_id == user_id)
            .with_for_update()
            .first()
        )
    if not bundle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Key Bundle not found")
    # Deserialize stored JSON string back to list before repo operates on it
    _deserialize_bundle_otpks(bundle)
    if not bundle.one_time_prekeys:
        otp = None
    else:
        otp = bundle.one_time_prekeys.pop(0)
        if isinstance(otp,bytes):
            otp = otp.decode()
        bundle.one_time_prekeys = json.dumps(bundle.one_time_prekeys)
        db.add(bundle)
    db.commit()
    return KeyBundleResponse(
        user_id=bundle.user_id,
        identity_key=bundle.identity_key,
        signing_public=bundle.signing_public,
        signed_prekey=bundle.signed_prekey,
        signed_prekey_signature=bundle.signed_prekey_signature,
        prekey_id=bundle.prekey_id,
        one_time_prekey=otp,
        kyber_prekey_public=bundle.kyber_prekey_public,
        kyber_prekey_signature=bundle.kyber_prekey_signature
    )
