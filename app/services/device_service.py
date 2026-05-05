import hashlib
from hmac import compare_digest
import secrets

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Device, KeyBundle, PairingCode, RefreshToken, User
from app.services.audit_service import write_audit_log
from app.services.auth_service import create_or_update_device, issue_login_tokens, now_ms


PAIRING_TTL_MS = 5 * 60 * 1000


def list_devices(db: Session, user: User, current_device_id: str | None) -> list[dict]:
    devices = (
        db.query(Device)
        .filter(Device.user_id == user.id, Device.revoked_at.is_(None))
        .order_by(Device.created_at.asc())
        .all()
    )
    return [
        {
            "id": device.id,
            "name": device.name,
            "created_at": device.created_at,
            "last_seen": device.last_seen,
            "current": device.id == current_device_id,
        }
        for device in devices
    ]


def revoke_device(db: Session, user: User, device_id: str) -> None:
    device = db.query(Device).filter(Device.id == device_id, Device.user_id == user.id).first()
    if device is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    now = now_ms()
    (
        db.query(RefreshToken)
        .filter(RefreshToken.user_id == user.id, RefreshToken.device_id == device_id, RefreshToken.revoked_at.is_(None))
        .update({"revoked_at": now}, synchronize_session=False)
    )
    db.query(KeyBundle).filter(KeyBundle.user_id == user.id, KeyBundle.device_id == device_id).delete(synchronize_session=False)
    device.revoked_at = now
    write_audit_log(db, actor=user.id, action="device_revoke", meta={"device_id": device_id})
    db.commit()


def start_device_link(db: Session, user: User) -> dict:
    raw_code = f"{secrets.randbelow(1_000_000):06d}"
    code_hash = hashlib.sha256(raw_code.encode("utf-8")).digest()
    row = PairingCode(
        code_hash=code_hash,
        user_id=user.id,
        expires_at=now_ms() + PAIRING_TTL_MS,
        used_at=None,
    )
    db.add(row)
    db.commit()
    return {
        "pairing_token": secrets.token_urlsafe(24),
        "code": f"{raw_code[:3]} {raw_code[3:]}",
        "expires_at": row.expires_at,
    }


def complete_device_link(db: Session, code: str, identity_pub: str, device_name: str) -> dict:
    normalized = "".join(ch for ch in code if ch.isdigit())
    submitted_hash = hashlib.sha256(normalized.encode("utf-8")).digest()
    now = now_ms()
    candidates = (
        db.query(PairingCode)
        .filter(PairingCode.used_at.is_(None), PairingCode.expires_at > now)
        .all()
    )
    matched = None
    for candidate in candidates:
        if compare_digest(candidate.code_hash, submitted_hash):
            matched = candidate
            break
    if matched is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid pairing code")

    user = db.query(User).filter(User.id == matched.user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    device = create_or_update_device(db, user, device_name=device_name, identity_pub=identity_pub)
    matched.used_at = now
    db.commit()
    tokens = issue_login_tokens(db, user, device_name=device.name, device_id=device.id, identity_pub=identity_pub)
    return {
        "access": tokens["access_token"],
        "refresh": tokens["refresh_token"],
        "device_id": tokens["device_id"],
    }
