"""Authentication API endpoints: register, login, current user, logout."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from server.config import ACCESS_TOKEN_EXPIRE_DAYS
from server.database import get_db
from server.deps import require_authenticated_user
from server.models import Roadmap, SprintTask, User
from server.schemas import AuthResponse, AuthUser, LoginRequest, RegisterRequest
from server.services import insights, planner, scoring
from server.utils.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

DEFAULT_SPRINT_TASKS = [
    (1, 1, "Syntax", "Bài 01: Vị trí 4 loại từ cốt lõi (Word Forms) & 5 câu bài tập", False),
    (1, 1, "Vocab", "Kích hoạt SRS Flashcards, bắt đầu 15 thẻ từ vựng mỗi ngày", False),
    (1, 2, "Listening", "Dictation 10 câu hỏi Part 2 (Dạng Who/Where/When) để xóa bẫy âm thanh", False),
    (1, 2, "Syntax", "Bài 02 (Liên từ vs Giới từ) & Bài 03 (Dạng động từ To-V / V-ing)", False),
    (1, 3, "Syntax", "Bài 04: Câu Bị động (Passive Voice) & Cách nhận diện trong 10 giây", False),
    (1, 4, "Syntax", "Bài 05 (Hòa hợp Chủ-Vị) & Bài 06 (6 Thì thời gian trọng tâm)", False),
    (1, 6, "Vocab", "Hoàn thành 300 từ vựng kinh doanh cốt lõi ETS", False),
    (1, 8, "Test", "Mini-Test chốt Phase 1: Mục tiêu đạt chuẩn nền tảng", False),
    (2, 9, "Listening", "Kỹ thuật 'Đi trước băng 30s' cho Part 3 & 4; Shadowing tốc độ 1.0x", False),
    (2, 11, "Reading", "Rút ngắn thời gian Part 5 xuống dưới 12 phút", False),
    (2, 13, "Reading", "Kỹ thuật 3-Pass Scanning cho Part 7 đoạn đơn (Email, Memo, Notice)", False),
    (2, 15, "Reading", "Làm chủ câu hỏi ngụ ý (Inference) và kho Paraphrase Vault", False),
    (2, 16, "Test", "Mini-Test chốt Phase 2: Đánh giá mốc 700 - 750+", False),
    (3, 17, "Test", "Full Test 1 ETS 2024 (120 phút áp lực thật). Ghi nhật ký lỗi sai RCA", False),
    (3, 19, "Reading", "Khắc phục điểm yếu Triple Passages (Đoạn 3), tối ưu thời gian Part 7", False),
    (3, 21, "Test", "Full Test 2 & 3: Tối ưu phong độ ổn định", False),
    (3, 23, "Vocab", "Ôn lại toàn bộ Error Log và 150 cặp từ Paraphrase Vault", False),
    (3, 24, "Test", "Sẵn sàng đăng ký thi thật IIG! Mục tiêu đạt chuẩn mục tiêu", False),
]


def _format_auth_user(user: User) -> AuthUser:
    code, label, _ = scoring.cefr_for(user.target_score or 800)
    return AuthUser(
        id=user.id,
        username=user.username,
        email=user.email,
        display_name=user.display_name or user.username,
        headline=user.headline,
        target_score=user.target_score or 800,
        target_cefr=f"{code} - {label}",
        role=user.role or "learner",
        avatar_url=user.avatar_url,
        created_at=user.created_at,
    )


def _init_user_workspace(db: Session, user: User) -> None:
    """Initialize fresh personalized environment for a newly created or onboarded user."""
    # 1. Seed personal SRS Flashcard queue
    insights.ensure_srs_records(db, user.id)

    # 2. Seed personal 24-week Roadmap if missing
    roadmap = db.query(Roadmap).filter_by(user_id=user.id).first()
    if not roadmap:
        roadmap = Roadmap(
            user_id=user.id,
            title=f"Lộ trình 24 tuần Chinh phục TOEIC {user.target_score or 800}+",
            total_weeks=24,
            current_week=1,
        )
        db.add(roadmap)
        db.commit()
        db.refresh(roadmap)

        for phase, week, cat, title, done in DEFAULT_SPRINT_TASKS:
            db.add(
                SprintTask(
                    roadmap_id=roadmap.id,
                    phase=phase,
                    week_number=week,
                    category=cat,
                    title=title,
                    is_completed=done,
                )
            )
        db.commit()

    # 3. Generate initial 7-day study plan
    try:
        planner.ensure_plan(db, user.id, force=True)
    except Exception:
        pass


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    clean_username = payload.username.strip().lower()
    clean_email = payload.email.strip().lower()

    # 1. Uniqueness checks
    if db.query(User).filter(func.lower(User.username) == clean_username).first():
        raise HTTPException(status_code=400, detail="Tên đăng nhập đã tồn tại")

    if db.query(User).filter(func.lower(User.email) == clean_email).first():
        raise HTTPException(status_code=400, detail="Email này đã được đăng ký tài khoản")

    # 2. Create user with hashed password
    user = User(
        username=clean_username,
        email=clean_email,
        hashed_password=hash_password(payload.password),
        display_name=payload.display_name.strip() if payload.display_name else payload.username,
        target_score=payload.target_score,
        daily_goal_minutes=60,
        is_active=True,
        role="learner",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # 3. Provision personal workspace
    _init_user_workspace(db, user)

    # 4. Issue token and set cookie
    token = create_access_token(user.id, user.username)
    response.set_cookie(
        key="access_token",
        value=token,
        max_age=ACCESS_TOKEN_EXPIRE_DAYS * 86400,
        httponly=True,
        samesite="lax",
        path="/",
    )

    return AuthResponse(access_token=token, token_type="bearer", user=_format_auth_user(user))


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    identifier = payload.username_or_email.strip().lower()
    user = (
        db.query(User)
        .filter(or_(func.lower(User.username) == identifier, func.lower(User.email) == identifier))
        .first()
    )

    if not user:
        raise HTTPException(status_code=400, detail="Tên đăng nhập / email hoặc mật khẩu không chính xác")

    # If the default learner has no password set yet, allow logging in with any password or set it
    if user.hashed_password is None:
        user.hashed_password = hash_password(payload.password)
        db.commit()
    elif not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Tên đăng nhập / email hoặc mật khẩu không chính xác")

    # Ensure personal workspace is ready
    _init_user_workspace(db, user)

    token = create_access_token(user.id, user.username)
    response.set_cookie(
        key="access_token",
        value=token,
        max_age=ACCESS_TOKEN_EXPIRE_DAYS * 86400,
        httponly=True,
        samesite="lax",
        path="/",
    )

    return AuthResponse(access_token=token, token_type="bearer", user=_format_auth_user(user))


@router.get("/me", response_model=AuthUser)
def get_current_user_profile(user: User = Depends(require_authenticated_user)):
    return _format_auth_user(user)


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(key="access_token", path="/")
    return {"message": "Đăng xuất thành công"}
