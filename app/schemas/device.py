from pydantic import BaseModel


class DeviceResponse(BaseModel):
    id: str
    name: str
    created_at: int
    last_seen: int
    current: bool


class DeviceLinkStartResponse(BaseModel):
    pairing_token: str
    code: str
    expires_at: int


class DeviceLinkCompleteRequest(BaseModel):
    code: str
    identity_pub: str
    device_name: str


class DeviceLinkCompleteResponse(BaseModel):
    access: str
    refresh: str
    device_id: str
