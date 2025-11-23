from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy import desc
from sqlalchemy.orm import selectinload
from app.models.post import Post
from app.schemas.post import PostCreate, PostResponse
from app.core.database import get_db
from app.core.security import get_password_hash, verify_password, create_access_token
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, Token
from sqlalchemy import delete, and_
from app.models.post import Post, likes_table, Comment
from app.schemas.post import PostCreate, PostResponse, CommentCreate, CommentResponse
import shutil
from fastapi import UploadFile, File
from app.models.post import PostMedia
from app.schemas.post import MediaResponse
import uuid
import redis.asyncio as redis

router = APIRouter()


@router.post("/auth/register", response_model=UserResponse)
async def register(user_in: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    stmt = select(User).where(
        (User.username == user_in.username) | (User.email == user_in.email)
    )
    result = await db.execute(stmt)
    if result.scalars().first():
        raise HTTPException(
            status_code=400, detail="Username or Email already registered"
        )

    new_user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        bio=user_in.bio,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.post("/auth/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    stmt = select(User).where(User.username == form_data.username)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    access_token = create_access_token(subject=user.username)
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/users/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/users/{username}/follow")
async def follow_user(
    username: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(User).where(User.username == username)
    result = await db.execute(stmt)
    target_user = result.scalars().first()

    if not target_user:
        raise HTTPException(404, "User not found")

    if target_user.id == current_user.id:
        raise HTTPException(400, "You cannot follow yourself")

    stmt_user = (
        select(User)
        .options(selectinload(User.following))
        .where(User.id == current_user.id)
    )
    result_user = await db.execute(stmt_user)
    user_with_following = result_user.scalars().first()

    if target_user in user_with_following.following:
        return {"message": f"Already following {username}"}

    user_with_following.following.append(target_user)
    await db.commit()

    return {"message": f"Successfully followed {username}"}


redis_client = redis.from_url(
    "redis://redis:6379", encoding="utf-8", decode_responses=True
)


async def check_rate_limit(user: User = Depends(get_current_user)):
    key = f"rate_limit:{user.id}"

    current_count = await redis_client.incr(key)

    if current_count == 1:
        await redis_client.expire(key, 60)

    if current_count > 5:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded: 5 posts per minute",
        )


@router.post("/posts", response_model=PostResponse)
async def create_post(
    post_in: PostCreate,
    _=Depends(check_rate_limit),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    print(f"DEBUG: Attempting to create post. Content: {post_in.content}")
    print(f"DEBUG: Received Media IDs: {post_in.media_ids}")

    if post_in.media_ids:
        stmt = select(PostMedia).where(PostMedia.id.in_(post_in.media_ids))
        result = await db.execute(stmt)
        found_media = result.scalars().all()

        print(f"DEBUG: Found {len(found_media)} media items in DB")

        if len(found_media) != len(post_in.media_ids):
            found_ids = [str(m.id) for m in found_media]
            missing = set(str(i) for i in post_in.media_ids) - set(found_ids)
            print(f"DEBUG: Missing IDs: {missing}")
            raise HTTPException(
                404,
                f"Media with IDs {missing} not found in DB. Did you upload them first?",
            )
    else:
        found_media = []

    new_post = Post(content=post_in.content, user_id=current_user.id)
    db.add(new_post)
    await db.commit()
    await db.refresh(new_post)

    if found_media:
        for m in found_media:
            m.post_id = new_post.id
            db.add(m)

        await db.commit()
        print("DEBUG: Media linked successfully")

    stmt = select(Post).where(Post.id == new_post.id).options(selectinload(Post.media))
    result = await db.execute(stmt)
    final_post = result.scalars().first()

    media_urls = [f"/static/{m.filename}" for m in final_post.media]
    print(f"DEBUG: Final Post Media URLs: {media_urls}")

    return PostResponse(
        id=final_post.id,
        content=final_post.content,
        created_at=final_post.created_at,
        author_username=current_user.username,
        media=[
            MediaResponse(id=m.id, url=f"/static/{m.filename}")
            for m in final_post.media
        ],
    )


@router.get("/feed", response_model=list[PostResponse])
async def get_feed(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    stmt_following = (
        select(User.following)
        .where(User.id == current_user.id)
        .options(selectinload(User.following))
    )

    q = (
        select(User)
        .where(User.id == current_user.id)
        .options(selectinload(User.following))
    )
    res = await db.execute(q)
    user_with_subs = res.scalars().first()

    following_ids = [u.id for u in user_with_subs.following]
    following_ids.append(current_user.id)

    if not following_ids:
        return []

    stmt = (
        select(Post)
        .where(Post.user_id.in_(following_ids))
        .order_by(desc(Post.created_at))
        .limit(limit)
        .options(selectinload(Post.author), selectinload(Post.media))
    )

    result = await db.execute(stmt)
    posts = result.scalars().all()

    response = []
    for p in posts:
        response.append(
            PostResponse(
                id=p.id,
                content=p.content,
                created_at=p.created_at,
                author_username=p.author.username,
                media=[
                    MediaResponse(id=m.id, url=f"/static/{m.filename}") for m in p.media
                ],
            )
        )

    return response


@router.post("/posts/{post_id}/like")
async def like_post(
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    post = await db.get(Post, post_id)
    if not post:
        raise HTTPException(404, "Post not found")

    stmt = select(likes_table).where(
        and_(likes_table.c.user_id == current_user.id, likes_table.c.post_id == post_id)
    )
    result = await db.execute(stmt)
    if result.first():
        return {"message": "Already liked"}

    stmt_ins = likes_table.insert().values(user_id=current_user.id, post_id=post_id)
    await db.execute(stmt_ins)
    await db.commit()

    return {"message": "Post liked"}


@router.delete("/posts/{post_id}/like")
async def unlike_post(
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = delete(likes_table).where(
        and_(likes_table.c.user_id == current_user.id, likes_table.c.post_id == post_id)
    )
    await db.execute(stmt)
    await db.commit()

    return {"message": "Post unliked"}


@router.post("/posts/{post_id}/comments", response_model=CommentResponse)
async def create_comment(
    post_id: str,
    comment_in: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    post = await db.get(Post, post_id)
    if not post:
        raise HTTPException(404, "Post not found")

    new_comment = Comment(
        content=comment_in.content, user_id=current_user.id, post_id=post_id
    )
    db.add(new_comment)
    await db.commit()
    await db.refresh(new_comment)

    return CommentResponse(
        id=new_comment.id,
        content=new_comment.content,
        author_username=current_user.username,
        created_at=new_comment.created_at,
    )


@router.get("/posts/{post_id}/comments", response_model=list[CommentResponse])
async def get_comments(post_id: str, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Comment)
        .where(Comment.post_id == post_id)
        .order_by(Comment.created_at)
        .options(selectinload(Comment.author))
    )
    result = await db.execute(stmt)
    comments = result.scalars().all()

    resp = []
    for c in comments:
        resp.append(
            CommentResponse(
                id=c.id,
                content=c.content,
                author_username=c.author.username,
                created_at=c.created_at,
            )
        )
    return resp


@router.post("/media/upload", response_model=MediaResponse)
async def upload_media(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    file_ext = file.filename.split(".")[-1]
    unique_name = f"{uuid.uuid4()}.{file_ext}"
    file_path = f"uploaded_files/{unique_name}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    media = PostMedia(file_path=file_path, filename=unique_name)
    db.add(media)
    await db.commit()
    await db.refresh(media)

    return MediaResponse(id=media.id, url=f"/static/{unique_name}")


@router.delete("/posts/{post_id}")
async def delete_post(
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    post = await db.get(Post, post_id)
    if not post:
        raise HTTPException(404, "Post not found")

    if post.user_id != current_user.id:
        raise HTTPException(403, "Not enough permissions to delete this post")

    await db.delete(post)
    await db.commit()

    return {"message": "Post deleted"}


@router.get("/search", response_model=list[PostResponse])
async def search_posts(q: str, limit: int = 20, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Post)
        .where(Post.content.ilike(f"%{q}%"))
        .order_by(desc(Post.created_at))
        .limit(limit)
        .options(selectinload(Post.author), selectinload(Post.media))
    )

    result = await db.execute(stmt)
    posts = result.scalars().all()

    response = []
    for p in posts:
        response.append(
            PostResponse(
                id=p.id,
                content=p.content,
                created_at=p.created_at,
                author_username=p.author.username,
                media=[
                    MediaResponse(id=m.id, url=f"/static/{m.filename}") for m in p.media
                ],
            )
        )
    return response
