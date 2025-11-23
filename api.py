import asyncio
from datetime import datetime, timedelta
from typing import Annotated, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import Base, engine, get_db
from models import (
    Category,
    Comment,
    Favorite,
    ModelTag,
    Subscription,
    User,
    Video,
    VideoLike,
    WatchLater,
)
from schemas import (
    CategoryRead,
    CommentCreate,
    CommentRead,
    ModelTagRead,
    ProfileUpdate,
    Token,
    UserCreate,
    UserRead,
    VideoCreate,
    VideoRead,
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

app = FastAPI(title="Video Hosting API")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


async def init_models() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.on_event("startup")
async def on_startup() -> None:
    await init_models()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.JWT_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm="HS256")
    return encoded_jwt


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def get_user_by_login(db: AsyncSession, login: str) -> Optional[User]:
    result = await db.execute(select(User).where(or_(User.username == login, User.email == login)))
    return result.scalar_one_or_none()


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], db: Annotated[AsyncSession, Depends(get_db)]
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = await get_user_by_username(db, username)
    if user is None:
        raise credentials_exception
    return user


@app.post("/auth/register", response_model=UserRead)
async def register(payload: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    existing_user = await get_user_by_username(db, payload.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        username=payload.username,
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        display_name=payload.display_name,
        avatar_url=str(payload.avatar_url) if payload.avatar_url else None,
        bio=payload.bio,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@app.post("/auth/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    user = await get_user_by_login(db, form_data.username)
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    access_token = create_access_token(data={"sub": user.username})
    return Token(access_token=access_token)


@app.get("/me", response_model=UserRead)
async def get_me(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user


@app.patch("/me", response_model=UserRead)
async def update_profile(
    update: ProfileUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    if update.display_name is not None:
        current_user.display_name = update.display_name
    if update.avatar_url is not None:
        current_user.avatar_url = str(update.avatar_url)
    if update.bio is not None:
        current_user.bio = update.bio
    await db.commit()
    await db.refresh(current_user)
    return current_user


@app.post("/videos", response_model=VideoRead)
async def upload_video(
    payload: VideoCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    video = Video(
        owner_id=current_user.id,
        title=payload.title,
        description=payload.description,
        video_url=str(payload.video_url),
        thumbnail_url=str(payload.thumbnail_url) if payload.thumbnail_url else None,
        category_id=payload.category_id,
        model_tag_id=payload.model_tag_id,
        is_public=payload.is_public,
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)
    return await _hydrate_video(db, video)


@app.get("/videos", response_model=List[VideoRead])
async def list_videos(
    category_id: Optional[int] = None,
    model_tag_id: Optional[int] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = Depends(),
):
    query = select(Video)
    if category_id:
        query = query.where(Video.category_id == category_id)
    if model_tag_id:
        query = query.where(Video.model_tag_id == model_tag_id)
    result = await db.execute(query.order_by(Video.created_at.desc()))
    videos = result.scalars().all()
    return [await _hydrate_video(db, v) for v in videos]


@app.get("/videos/{video_id}", response_model=VideoRead)
async def get_video(video_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    video = await _get_video_or_404(db, video_id)
    return await _hydrate_video(db, video)


@app.post("/videos/{video_id}/comments", response_model=CommentRead)
async def add_comment(
    video_id: int,
    payload: CommentCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    await _get_video_or_404(db, video_id)
    comment = Comment(video_id=video_id, author_id=current_user.id, content=payload.content)
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return comment


@app.post("/videos/{video_id}/like", response_model=VideoRead)
async def like_video(
    video_id: int,
    is_like: bool = True,
    db: Annotated[AsyncSession, Depends(get_db)] = Depends(),
    current_user: Annotated[User, Depends(get_current_user)] = Depends(),
):
    video = await _get_video_or_404(db, video_id)
    existing = await db.execute(
        select(VideoLike).where(VideoLike.video_id == video_id, VideoLike.user_id == current_user.id)
    )
    like = existing.scalar_one_or_none()
    if like:
        like.is_like = is_like
    else:
        like = VideoLike(video_id=video_id, user_id=current_user.id, is_like=is_like)
        db.add(like)
    await db.commit()
    return await _hydrate_video(db, video)


@app.post("/videos/{video_id}/favorite", response_model=VideoRead)
async def add_to_favorites(
    video_id: int,
    db: Annotated[AsyncSession, Depends(get_db)] = Depends(),
    current_user: Annotated[User, Depends(get_current_user)] = Depends(),
):
    video = await _get_video_or_404(db, video_id)
    existing = await db.execute(
        select(Favorite).where(Favorite.video_id == video_id, Favorite.user_id == current_user.id)
    )
    if not existing.scalar_one_or_none():
        db.add(Favorite(video_id=video_id, user_id=current_user.id))
        await db.commit()
    return await _hydrate_video(db, video)


@app.delete("/videos/{video_id}/favorite", response_model=VideoRead)
async def remove_from_favorites(
    video_id: int,
    db: Annotated[AsyncSession, Depends(get_db)] = Depends(),
    current_user: Annotated[User, Depends(get_current_user)] = Depends(),
):
    video = await _get_video_or_404(db, video_id)
    existing = await db.execute(
        select(Favorite).where(Favorite.video_id == video_id, Favorite.user_id == current_user.id)
    )
    favorite = existing.scalar_one_or_none()
    if favorite:
        await db.delete(favorite)
        await db.commit()
    return await _hydrate_video(db, video)


@app.post("/videos/{video_id}/watch-later", response_model=VideoRead)
async def add_watch_later(
    video_id: int,
    db: Annotated[AsyncSession, Depends(get_db)] = Depends(),
    current_user: Annotated[User, Depends(get_current_user)] = Depends(),
):
    video = await _get_video_or_404(db, video_id)
    existing = await db.execute(
        select(WatchLater).where(WatchLater.video_id == video_id, WatchLater.user_id == current_user.id)
    )
    if not existing.scalar_one_or_none():
        db.add(WatchLater(video_id=video_id, user_id=current_user.id))
        await db.commit()
    return await _hydrate_video(db, video)


@app.delete("/videos/{video_id}/watch-later", response_model=VideoRead)
async def remove_watch_later(
    video_id: int,
    db: Annotated[AsyncSession, Depends(get_db)] = Depends(),
    current_user: Annotated[User, Depends(get_current_user)] = Depends(),
):
    video = await _get_video_or_404(db, video_id)
    existing = await db.execute(
        select(WatchLater).where(WatchLater.video_id == video_id, WatchLater.user_id == current_user.id)
    )
    record = existing.scalar_one_or_none()
    if record:
        await db.delete(record)
        await db.commit()
    return await _hydrate_video(db, video)


@app.post("/creators/{creator_id}/subscribe", response_model=UserRead)
async def subscribe(
    creator_id: int,
    db: Annotated[AsyncSession, Depends(get_db)] = Depends(),
    current_user: Annotated[User, Depends(get_current_user)] = Depends(),
):
    if creator_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot subscribe to yourself")
    result = await db.execute(select(User).where(User.id == creator_id))
    creator = result.scalar_one_or_none()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")

    existing = await db.execute(
        select(Subscription).where(
            Subscription.creator_id == creator_id, Subscription.subscriber_id == current_user.id
        )
    )
    if not existing.scalar_one_or_none():
        db.add(Subscription(creator_id=creator_id, subscriber_id=current_user.id))
        await db.commit()
    return creator


@app.delete("/creators/{creator_id}/subscribe", response_model=UserRead)
async def unsubscribe(
    creator_id: int,
    db: Annotated[AsyncSession, Depends(get_db)] = Depends(),
    current_user: Annotated[User, Depends(get_current_user)] = Depends(),
):
    result = await db.execute(select(User).where(User.id == creator_id))
    creator = result.scalar_one_or_none()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")

    existing = await db.execute(
        select(Subscription).where(
            Subscription.creator_id == creator_id, Subscription.subscriber_id == current_user.id
        )
    )
    subscription = existing.scalar_one_or_none()
    if subscription:
        await db.delete(subscription)
        await db.commit()
    return creator


@app.get("/categories", response_model=List[CategoryRead])
async def list_categories(db: Annotated[AsyncSession, Depends(get_db)] = Depends()):
    result = await db.execute(select(Category).order_by(Category.name.asc()))
    return result.scalars().all()


@app.get("/models", response_model=List[ModelTagRead])
async def list_models(db: Annotated[AsyncSession, Depends(get_db)] = Depends()):
    result = await db.execute(select(ModelTag).order_by(ModelTag.name.asc()))
    return result.scalars().all()


async def _get_video_or_404(db: AsyncSession, video_id: int) -> Video:
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return video


async def _hydrate_video(db: AsyncSession, video: Video) -> VideoRead:
    like_counts = await db.execute(
        select(
            func.sum(case((VideoLike.is_like.is_(True), 1), else_=0)).label("likes"),
            func.sum(case((VideoLike.is_like.is_(False), 1), else_=0)).label("dislikes"),
        ).where(VideoLike.video_id == video.id)
    )
    likes, dislikes = like_counts.one_or_none() or (0, 0)
    return VideoRead(
        id=video.id,
        owner_id=video.owner_id,
        title=video.title,
        description=video.description,
        video_url=video.video_url,
        thumbnail_url=video.thumbnail_url,
        category_id=video.category_id,
        model_tag_id=video.model_tag_id,
        is_public=video.is_public,
        created_at=video.created_at,
        likes=likes or 0,
        dislikes=dislikes or 0,
    )


if __name__ == "__main__":
    import uvicorn

    asyncio.run(init_models())
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=False)
