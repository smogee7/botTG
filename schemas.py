from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, HttpUrl, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserBase(BaseModel):
    username: str
    email: EmailStr
    display_name: Optional[str] = None
    avatar_url: Optional[HttpUrl] = None
    bio: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(min_length=6)


class UserRead(UserBase):
    id: int

    class Config:
        from_attributes = True


class ProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    avatar_url: Optional[HttpUrl] = None
    bio: Optional[str] = None


class CategoryRead(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class ModelTagRead(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class VideoBase(BaseModel):
    title: str
    description: Optional[str] = None
    video_url: HttpUrl
    thumbnail_url: Optional[HttpUrl] = None
    category_id: Optional[int] = None
    model_tag_id: Optional[int] = None
    is_public: bool = True


class VideoCreate(VideoBase):
    pass


class VideoRead(VideoBase):
    id: int
    owner_id: int
    created_at: datetime
    likes: int
    dislikes: int

    class Config:
        from_attributes = True


class CommentCreate(BaseModel):
    content: str


class CommentRead(BaseModel):
    id: int
    video_id: int
    author_id: int
    content: str
    created_at: datetime

    class Config:
        from_attributes = True
