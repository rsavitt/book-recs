from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(..., min_length=8)
    display_name: str | None = None


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    display_name: str | None
    is_public: bool
    spice_preference: int | None
    prefers_ya: bool | None

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str
