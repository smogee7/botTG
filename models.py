from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Boolean, func
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime

from database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String, nullable=True)
    bio: Mapped[str | None] = mapped_column(String, nullable=True)
    balance: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    login_tokens: Mapped[list["LoginToken"]] = relationship("LoginToken", back_populates="user")
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="user")
    videos: Mapped[list["Video"]] = relationship("Video", back_populates="owner")
    comments: Mapped[list["Comment"]] = relationship("Comment", back_populates="author")
    likes: Mapped[list["VideoLike"]] = relationship("VideoLike", back_populates="user")
    favorites: Mapped[list["Favorite"]] = relationship("Favorite", back_populates="user")
    watch_later_items: Mapped[list["WatchLater"]] = relationship("WatchLater", back_populates="user")
    subscriptions: Mapped[list["Subscription"]] = relationship(
        "Subscription", back_populates="subscriber", foreign_keys="Subscription.subscriber_id"
    )
    subscribers: Mapped[list["Subscription"]] = relationship(
        "Subscription", back_populates="creator", foreign_keys="Subscription.creator_id"
    )


class LoginToken(Base):
    __tablename__ = "login_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    token: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="login_tokens")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String, default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="orders")
    deals: Mapped[list["Deal"]] = relationship("Deal", back_populates="order")


class Deal(Base):
    __tablename__ = "deals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"))
    buyer_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    order: Mapped["Order"] = relationship("Order", back_populates="deals")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    videos: Mapped[list["Video"]] = relationship("Video", back_populates="category")


class ModelTag(Base):
    __tablename__ = "model_tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    videos: Mapped[list["Video"]] = relationship("Video", back_populates="model_tag")


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    video_url: Mapped[str] = mapped_column(String, nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(String, nullable=True)
    category_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("categories.id"))
    model_tag_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("model_tags.id"))
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    owner: Mapped["User"] = relationship("User", back_populates="videos")
    category: Mapped["Category"] = relationship("Category", back_populates="videos")
    model_tag: Mapped["ModelTag"] = relationship("ModelTag", back_populates="videos")
    comments: Mapped[list["Comment"]] = relationship("Comment", back_populates="video")
    likes: Mapped[list["VideoLike"]] = relationship("VideoLike", back_populates="video")
    favorites: Mapped[list["Favorite"]] = relationship("Favorite", back_populates="video")
    watch_later_items: Mapped[list["WatchLater"]] = relationship("WatchLater", back_populates="video")


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    video_id: Mapped[int] = mapped_column(Integer, ForeignKey("videos.id"))
    author_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    content: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    video: Mapped["Video"] = relationship("Video", back_populates="comments")
    author: Mapped["User"] = relationship("User", back_populates="comments")


class VideoLike(Base):
    __tablename__ = "video_likes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    video_id: Mapped[int] = mapped_column(Integer, ForeignKey("videos.id"))
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    is_like: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    video: Mapped["Video"] = relationship("Video", back_populates="likes")
    user: Mapped["User"] = relationship("User", back_populates="likes")


class Favorite(Base):
    __tablename__ = "favorites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    video_id: Mapped[int] = mapped_column(Integer, ForeignKey("videos.id"))
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    video: Mapped["Video"] = relationship("Video", back_populates="favorites")
    user: Mapped["User"] = relationship("User", back_populates="favorites")


class WatchLater(Base):
    __tablename__ = "watch_later"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    video_id: Mapped[int] = mapped_column(Integer, ForeignKey("videos.id"))
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    video: Mapped["Video"] = relationship("Video", back_populates="watch_later_items")
    user: Mapped["User"] = relationship("User", back_populates="watch_later_items")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    subscriber_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    creator_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    subscriber: Mapped["User"] = relationship(
        "User", back_populates="subscriptions", foreign_keys=[subscriber_id]
    )
    creator: Mapped["User"] = relationship("User", back_populates="subscribers", foreign_keys=[creator_id])
