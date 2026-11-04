import csv
import hmac
import hashlib
import io
import logging
import os
import re
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from pathlib import Path

import httpx
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.billing import generate_slots, quote
from app.database import UPLOAD_DIR, SessionLocal, engine, get_db
from app.models import (
    Address,
    AvailabilitySlot,
    Base,
    Booking,
    BookingAssignment,
    BookingImage,
    Complaint,
    Coupon,
    Customer,
    Favorite,
    Invoice,
    Notification,
    PasswordReset,
    Payment,
    ProviderEarning,
    ProviderService,
    Review,
    Service,
    ServiceArea,
    ServiceCategory,
    ServiceProvider,
    SubscriptionPlan,
    Technician,
    User,
)
from app.security import REVOKED, create_token, decode_token, hash_password, rate_limit, verify_password
from app.seed import seed

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("homeserve")
bearer = HTTPBearer(auto_error=False)
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
UPLOAD_RE = re.compile(r"^/uploads/[A-Za-z0-9._-]+$")
CLOUDINARY_RE = re.compile(r"^https://res\.cloudinary\.com/[A-Za-z0-9_-]+/.+")
MAX_BYTES = 5 * 1024 * 1024
ALLOWED_EXT = {".jpg": ".jpg", ".jpeg": ".jpg", ".png": ".png", ".webp": ".webp", ".pdf": ".pdf"}
OPEN_STATUSES = ("Pending", "Confirmed", "Provider Assigned", "In Progress")


def iso(value):
    return value.isoformat() if value else None


def recent_months(count=6):
    today = date.today()
    year, month = today.year, today.month
    keys = []
    for _ in range(count):
        keys.append(f"{year}-{month:02d}")
        month -= 1
        if month == 0:
            month, year = 12, year - 1
    return list(reversed(keys))


def check_password(password: str):
    if len(password) < 8 or not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise HTTPException(400, "Password must be 8+ characters and include a letter and a number.")


def clean_email(value: str) -> str:
    email = (value or "").strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(400, "Enter a valid email address.")
    return email


def clean_phone(value: str) -> str:
    phone = re.sub(r"\D", "", value or "")
    if phone and len(phone) != 10:
        raise HTTPException(400, "Enter a 10-digit mobile number.")
    return phone


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "item"


def notify(db, user_id, title, body, ntype="info"):
    db.add(Notification(user_id=user_id, title=title, body=body, ntype=ntype))


def paid_sum(db, booking_id: int) -> float:
    rows = db.query(Payment).filter(Payment.booking_id == booking_id, Payment.status == "Paid").all()
    return round(sum(row.amount for row in rows), 2)


def refresh_payment_status(db, booking: Booking):
    paid = paid_sum(db, booking.id)
    if paid <= 0:
        booking.payment_status = "Pending"
    elif paid + 0.009 < booking.total:
        booking.payment_status = "Partial"
    else:
        booking.payment_status = "Paid"
        if not db.query(ProviderEarning).filter_by(booking_id=booking.id, status="accrued").first():
            db.add(ProviderEarning(
                provider_id=booking.provider_id,
                booking_id=booking.id,
                gross=booking.taxable,
                commission=booking.commission,
                net=booking.provider_earning,
                status="accrued",
            ))
    return paid


def recalc_rating(db, provider_id: int):
    rows = db.query(Review).filter(Review.provider_id == provider_id, Review.is_visible.is_(True)).all()
    provider = db.get(ServiceProvider, provider_id)
    if not provider:
        return
    provider.rating_count = len(rows)
    provider.rating_avg = round(sum(row.rating for row in rows) / len(rows), 1) if rows else 0


def customer_of(db, user: User) -> Customer:
    row = db.query(Customer).filter_by(user_id=user.id).first()
    if not row:
        raise HTTPException(403, "Customer profile not found.")
    return row


def provider_of(db, user: User) -> ServiceProvider:
    row = db.query(ServiceProvider).filter_by(user_id=user.id).first()
    if not row:
        raise HTTPException(403, "Provider profile not found.")
    return row


def technician_of(db, user: User) -> Technician:
    row = db.query(Technician).filter_by(user_id=user.id).first()
    if not row:
        raise HTTPException(403, "Technician profile not found.")
    return row


def can_view_booking(db, user: User, booking: Booking) -> bool:
    if user.role == "admin":
        return True
    if user.role == "customer":
        row = db.query(Customer).filter_by(user_id=user.id).first()
        return bool(row and booking.customer_id == row.id)
    if user.role == "provider":
        row = db.query(ServiceProvider).filter_by(user_id=user.id).first()
        return bool(row and booking.provider_id == row.id)
    if user.role == "technician":
        row = db.query(Technician).filter_by(user_id=user.id).first()
        return bool(row and booking.technician_id == row.id)
    return False


def load_booking(db, user: User, booking_id: int) -> Booking:
    booking = db.get(Booking, booking_id)
    if not booking or not can_view_booking(db, user, booking):
        raise HTTPException(404, "Booking not found.")
    return booking


def public_user(db, user: User) -> dict:
    data = {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "phone": user.phone or "",
        "role": user.role,
        "status": user.status,
        "created_at": iso(user.created_at),
    }
    if user.role == "customer":
        row = db.query(Customer).filter_by(user_id=user.id).first()
        data["customer_id"] = row.id if row else None
    elif user.role == "provider":
        row = db.query(ServiceProvider).filter_by(user_id=user.id).first()
        if row:
            plan = db.get(SubscriptionPlan, row.plan_id) if row.plan_id else None
            data.update({
                "provider_id": row.id,
                "business_name": row.business_name,
                "bio": row.bio or "",
                "experience_years": row.experience_years,
                "verification_status": row.verification_status,
                "document_url": row.document_url or "",
                "rejection_reason": row.rejection_reason or "",
                "commission_rate": row.commission_rate,
                "rating_avg": row.rating_avg,
                "rating_count": row.rating_count,
                "plan_id": row.plan_id,
                "plan_name": plan.name if plan else "",
            })
    elif user.role == "technician":
        row = db.query(Technician).filter_by(user_id=user.id).first()
        if row:
            provider = db.get(ServiceProvider, row.provider_id)
            data.update({
                "technician_id": row.id,
                "provider_id": row.provider_id,
                "business_name": provider.business_name if provider else "",
                "skills": row.skills or "",
            })
    return data


def category_json(row: ServiceCategory) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "slug": row.slug,
        "description": row.description or "",
        "icon": row.icon or "bolt",
        "parent_id": row.parent_id,
        "is_active": row.is_active,
    }


def service_summary(db, row: Service) -> dict:
    category = db.get(ServiceCategory, row.category_id)
    offers = (
        db.query(ProviderService)
        .join(ServiceProvider, ServiceProvider.id == ProviderService.provider_id)
        .filter(
            ProviderService.service_id == row.id,
            ProviderService.status == "active",
            ServiceProvider.verification_status == "approved",
        )
        .all()
    )
    prices = [offer.price for offer in offers]
    return {
        "id": row.id,
        "name": row.name,
        "description": row.description or "",
        "base_price": row.base_price,
        "duration_mins": row.duration_mins,
        "image_url": row.image_url or "",
        "status": row.status,
        "category_id": row.category_id,
        "category": category.name if category else "",
        "icon": category.icon if category else "bolt",
        "min_price": min(prices) if prices else row.base_price,
        "provider_count": len(offers),
    }


def provider_card(db, row: ServiceProvider) -> dict:
    user = db.get(User, row.user_id)
    areas = db.query(ServiceArea).filter_by(provider_id=row.id).all()
    offers = db.query(ProviderService).filter_by(provider_id=row.id, status="active").all()
    names = []
    for offer in offers[:4]:
        service = db.get(Service, offer.service_id)
        if service:
            names.append(service.name)
    prices = [offer.price for offer in offers]
    return {
        "id": row.id,
        "business_name": row.business_name,
        "bio": row.bio or "",
        "experience_years": row.experience_years,
        "verification_status": row.verification_status,
        "rating_avg": row.rating_avg,
        "rating_count": row.rating_count,
        "city": areas[0].city if areas else "",
        "areas": [{"city": area.city, "pincode": area.pincode} for area in areas],
        "services": names,
        "starting_price": min(prices) if prices else 0,
        "contact_name": user.full_name if user else "",
    }


def review_json(db, row: Review) -> dict:
    customer = db.get(Customer, row.customer_id)
    user = db.get(User, customer.user_id) if customer else None
    return {
        "id": row.id,
        "booking_id": row.booking_id,
        "provider_id": row.provider_id,
        "rating": row.rating,
        "comment": row.comment or "",
        "provider_response": row.provider_response or "",
        "customer_name": user.full_name if user else "Customer",
        "is_visible": row.is_visible,
        "created_at": iso(row.created_at),
    }


def booking_json(db, row: Booking) -> dict:
    customer = db.get(Customer, row.customer_id)
    customer_user = db.get(User, customer.user_id) if customer else None
    provider = db.get(ServiceProvider, row.provider_id)
    provider_user = db.get(User, provider.user_id) if provider else None
    service = db.get(Service, row.service_id)
    tech_user = None
    if row.technician_id:
        tech = db.get(Technician, row.technician_id)
        tech_user = db.get(User, tech.user_id) if tech else None
    images = db.query(BookingImage).filter_by(booking_id=row.id).all()
    review = db.query(Review).filter_by(booking_id=row.id).first()
    paid = paid_sum(db, row.id)
    return {
        "id": row.id,
        "booking_code": row.booking_code,
        "status": row.status,
        "payment_status": row.payment_status,
        "scheduled_date": row.scheduled_date,
        "scheduled_time": row.scheduled_time,
        "address": row.address_text,
        "city": row.city,
        "problem_note": row.problem_note or "",
        "remarks": row.remarks or "",
        "cancel_reason": row.cancel_reason or "",
        "subtotal": row.subtotal,
        "discount": row.discount,
        "gst": row.gst,
        "commission": row.commission,
        "total": row.total,
        "amount_paid": paid,
        "balance": round(max(row.total - paid, 0), 2),
        "coupon_code": row.coupon_code or "",
        "service_name": service.name if service else "",
        "provider_id": row.provider_id,
        "provider_name": provider.business_name if provider else "",
        "provider_phone": provider_user.phone if provider_user else "",
        "customer_name": customer_user.full_name if customer_user else "",
        "customer_phone": customer_user.phone if customer_user else "",
        "technician_id": row.technician_id,
        "technician_name": tech_user.full_name if tech_user else "",
        "technician_phone": tech_user.phone if tech_user else "",
        "images": [{"id": image.id, "url": image.url, "kind": image.kind} for image in images],
        "review": review_json(db, review) if review else None,
        "arrived_at": iso(row.arrived_at),
        "completed_at": iso(row.completed_at),
        "created_at": iso(row.created_at),
    }


def coupon_payload(row: Coupon) -> dict:
    return {
        "discount_type": row.discount_type,
        "value": row.value,
        "min_amount": row.min_amount or 0,
        "max_discount": row.max_discount,
    }


def active_coupon(db, code: str | None) -> Coupon | None:
    if not code:
        return None
    row = db.query(Coupon).filter(Coupon.code == code.strip().upper()).first()
    if not row or not row.is_active:
        raise HTTPException(400, "That coupon is not active.")
    if row.expires_on and row.expires_on < date.today().isoformat():
        raise HTTPException(400, "That coupon has expired.")
    return row


def hours_for(db, provider_id: int, day: date):
    rows = (
        db.query(AvailabilitySlot)
        .filter_by(provider_id=provider_id, day_of_week=day.weekday(), is_active=True)
        .all()
    )
    times = []
    for row in rows:
        for slot in generate_slots(row.start_time, row.end_time):
            if slot not in times:
                times.append(slot)
    return times


def new_code(db) -> str:
    for _ in range(6):
        code = "HS" + uuid.uuid4().hex[:6].upper()
        if not db.query(Booking).filter_by(booking_code=code).first():
            return code
    raise HTTPException(500, "Could not generate a booking id.")


def visible_bookings(db, user: User):
    query = db.query(Booking)
    if user.role == "customer":
        query = query.filter(Booking.customer_id == customer_of(db, user).id)
    elif user.role == "provider":
        query = query.filter(Booking.provider_id == provider_of(db, user).id)
    elif user.role == "technician":
        query = query.filter(Booking.technician_id == technician_of(db, user).id)
    return query


def frontend_dist() -> Path | None:
    candidates = []
    if os.getenv("FRONTEND_DIST"):
        candidates.append(Path(os.environ["FRONTEND_DIST"]))
    candidates.append(Path(__file__).resolve().parents[2] / "frontend" / "dist")
    candidates.append(Path("/app/frontend_dist"))
    for path in candidates:
        if (path / "index.html").is_file():
            return path
    return None


def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


init_db()


app = FastAPI(
    title="HomeServe API",
    version="1.0.0",
    description="Booking API for HomeServe Technologies.",
    lifespan=lifespan,
)

cors_raw = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
if cors_raw.strip() == "*":
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[item.strip() for item in cors_raw.split(",") if item.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.middleware("http")
async def log_requests(request: Request, call_next):
    try:
        response = await call_next(request)
    except Exception:
        log.exception("unhandled %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Something went wrong. Please try again."})
    log.info("%s %s -> %s", request.method, request.url.path, response.status_code)
    return response


def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer), db=Depends(get_db)) -> User:
    if creds is None:
        raise HTTPException(401, "Login required.")
    payload = decode_token(creds.credentials)
    if payload.get("jti") in REVOKED:
        raise HTTPException(401, "You have been logged out.")
    user = db.get(User, int(payload["sub"]))
    if not user or user.status != "active":
        raise HTTPException(401, "This account is not active.")
    return user


def require(*roles):
    def dependency(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, "You do not have access to this section.")
        return user
    return dependency


class RegisterIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: str
    phone: str = ""
    password: str
    role: str
    business_name: str = ""
    bio: str = ""
    experience_years: int = 1
    provider_id: int | None = None
    skills: str = ""
    city: str = ""
    pincode: str = ""


class LoginIn(BaseModel):
    email: str
    password: str


class ForgotIn(BaseModel):
    email: str


class ResetIn(BaseModel):
    email: str
    code: str
    password: str


class PasswordIn(BaseModel):
    old_password: str
    new_password: str


class ProfileIn(BaseModel):
    full_name: str | None = None
    phone: str | None = None


class ProviderProfileIn(BaseModel):
    business_name: str | None = None
    bio: str | None = None
    experience_years: int | None = None
    document_url: str | None = None


class AddressIn(BaseModel):
    label: str = "Home"
    line1: str
    city: str
    state: str = "Gujarat"
    pincode: str = ""
    is_default: bool = False


class BookingIn(BaseModel):
    provider_service_id: int
    scheduled_date: str
    scheduled_time: str
    address_id: int | None = None
    line1: str = ""
    city: str = ""
    state: str = "Gujarat"
    pincode: str = ""
    label: str = "Home"
    problem_note: str = ""
    coupon_code: str = ""


class RescheduleIn(BaseModel):
    scheduled_date: str
    scheduled_time: str


class ReasonIn(BaseModel):
    reason: str = ""


class AssignIn(BaseModel):
    technician_id: int


class CompleteIn(BaseModel):
    remarks: str = Field(min_length=3, max_length=500)


class ImageIn(BaseModel):
    url: str
    kind: str = "problem"


class CheckoutIn(BaseModel):
    booking_id: int
    mode: str = "full"


class VerifyIn(BaseModel):
    booking_id: int
    order_id: str
    outcome: str
    test_card: str = ""
    payment_id: str = ""
    signature: str = ""


class CouponPreview(BaseModel):
    code: str
    amount: float


class ReviewIn(BaseModel):
    booking_id: int
    rating: int = Field(ge=1, le=5)
    comment: str = ""


class RespondIn(BaseModel):
    response: str = Field(min_length=2, max_length=500)


class ComplaintIn(BaseModel):
    subject: str = Field(min_length=3, max_length=160)
    description: str = ""
    booking_id: int | None = None


class ComplaintUpdate(BaseModel):
    status: str
    admin_note: str = ""


class CategoryIn(BaseModel):
    name: str
    description: str = ""
    icon: str = "bolt"
    parent_id: int | None = None


class ServiceIn(BaseModel):
    category_id: int
    name: str
    description: str = ""
    base_price: float
    duration_mins: int = 60
    image_url: str = ""
    status: str = "active"


class ServicePatch(BaseModel):
    name: str | None = None
    description: str | None = None
    base_price: float | None = None
    duration_mins: int | None = None
    image_url: str | None = None
    status: str | None = None
    category_id: int | None = None


class OfferIn(BaseModel):
    service_id: int
    price: float
    description: str = ""


class OfferPatch(BaseModel):
    price: float | None = None
    description: str | None = None
    status: str | None = None


class SlotIn(BaseModel):
    day_of_week: int = Field(ge=0, le=6)
    start_time: str
    end_time: str


class AreaIn(BaseModel):
    city: str
    pincode: str = ""


class TechIn(BaseModel):
    full_name: str
    email: str
    phone: str = ""
    password: str
    skills: str = ""


class StatusIn(BaseModel):
    status: str


class VerifyProviderIn(BaseModel):
    status: str
    reason: str = ""


class CouponIn(BaseModel):
    code: str
    discount_type: str = "percent"
    value: float
    min_amount: float = 0
    max_discount: float | None = None
    expires_on: str = ""
    is_active: bool = True


class PlanIn(BaseModel):
    name: str
    price: float = 0
    commission_rate: float = 15
    description: str = ""
    features: str = ""
    is_active: bool = True


class PlanPick(BaseModel):
    plan_id: int


class AnnounceIn(BaseModel):
    title: str
    body: str
    audience: str = "all"


class ReviewHide(BaseModel):
    is_visible: bool


def auth_response(db, user: User):
    return {"token": create_token(user.id, user.role), "user": public_user(db, user)}


@app.get("/api/health", tags=["Meta"])
def health(db=Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"ok": True, "service": "homeserve", "database": engine.dialect.name}


@app.get("/api/public/stats", tags=["Catalog"])
def public_stats(db=Depends(get_db)):
    return {
        "providers": db.query(ServiceProvider).filter_by(verification_status="approved").count(),
        "categories": db.query(ServiceCategory).filter_by(is_active=True, parent_id=None).count(),
        "customers": db.query(Customer).count(),
        "bookings": db.query(Booking).count(),
    }


@app.post("/api/auth/register", tags=["Auth"])
def register(payload: RegisterIn, request: Request, db=Depends(get_db)):
    rate_limit(f"register:{request.client.host if request.client else 'x'}")
    if payload.role not in ("customer", "provider", "technician"):
        raise HTTPException(400, "Choose customer, provider or technician.")
    email = clean_email(payload.email)
    check_password(payload.password)
    phone = clean_phone(payload.phone)
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(400, "An account with this email already exists.")
    user = User(full_name=payload.full_name.strip(), email=email, phone=phone, role=payload.role, password_hash=hash_password(payload.password), status="active")
    db.add(user)
    db.flush()
    if payload.role == "customer":
        db.add(Customer(user_id=user.id))
    elif payload.role == "provider":
        if len(payload.business_name.strip()) < 2:
            raise HTTPException(400, "Add your business name.")
        plan = db.query(SubscriptionPlan).filter_by(name="Starter").first()
        provider = ServiceProvider(
            user_id=user.id,
            business_name=payload.business_name.strip(),
            bio=payload.bio.strip(),
            experience_years=max(payload.experience_years, 0),
            verification_status="pending",
            commission_rate=plan.commission_rate if plan else 20,
            plan_id=plan.id if plan else None,
        )
        db.add(provider)
        db.flush()
        for day in range(7):
            db.add(AvailabilitySlot(provider_id=provider.id, day_of_week=day, start_time="09:00", end_time="18:00"))
        if payload.city.strip():
            db.add(ServiceArea(provider_id=provider.id, city=payload.city.strip(), pincode=payload.pincode.strip()))
        admin = db.query(User).filter_by(role="admin").first()
        if admin:
            notify(db, admin.id, "New provider", f"{provider.business_name} is waiting for verification.", "admin")
    else:
        provider = db.get(ServiceProvider, payload.provider_id) if payload.provider_id else None
        if not provider or provider.verification_status != "approved":
            raise HTTPException(400, "Choose the approved provider you work with.")
        db.add(Technician(user_id=user.id, provider_id=provider.id, skills=payload.skills.strip(), status="active"))
        notify(db, provider.user_id, "Technician joined", f"{user.full_name} registered on your team.", "team")
    db.commit()
    db.refresh(user)
    return auth_response(db, user)


@app.post("/api/auth/login", tags=["Auth"])
def login(payload: LoginIn, request: Request, db=Depends(get_db)):
    email = clean_email(payload.email)
    rate_limit(f"login:{request.client.host if request.client else 'x'}:{email}")
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Email or password is incorrect.")
    if user.status != "active":
        raise HTTPException(403, "This account is suspended. Contact HomeServe support.")
    return auth_response(db, user)


@app.post("/api/auth/forgot", tags=["Auth"])
def forgot(payload: ForgotIn, request: Request, db=Depends(get_db)):
    rate_limit(f"forgot:{request.client.host if request.client else 'x'}", limit=5)
    email = clean_email(payload.email)
    user = db.query(User).filter(User.email == email).first()
    result = {"message": "If an account exists, a reset code is ready."}
    if user:
        code = f"{uuid.uuid4().int % 900000 + 100000}"
        db.add(PasswordReset(user_id=user.id, code=code, expires_at=datetime.utcnow() + timedelta(minutes=15), used=False))
        db.commit()
        if DEMO_MODE:
            result["demo_reset_code"] = code
    return result


@app.post("/api/auth/reset", tags=["Auth"])
def reset_password(payload: ResetIn, db=Depends(get_db)):
    email = clean_email(payload.email)
    check_password(payload.password)
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(400, "Reset code is invalid or expired.")
    row = (
        db.query(PasswordReset)
        .filter(PasswordReset.user_id == user.id, PasswordReset.code == payload.code.strip(), PasswordReset.used.is_(False))
        .order_by(PasswordReset.id.desc())
        .first()
    )
    if not row or row.expires_at < datetime.utcnow():
        raise HTTPException(400, "Reset code is invalid or expired.")
    row.used = True
    user.password_hash = hash_password(payload.password)
    db.commit()
    return {"message": "Password updated. You can log in now."}


@app.post("/api/auth/logout", tags=["Auth"])
def logout(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    if creds:
        try:
            REVOKED.add(decode_token(creds.credentials).get("jti"))
        except HTTPException:
            pass
    return {"ok": True}


@app.get("/api/auth/me", tags=["Auth"])
def me(user: User = Depends(current_user), db=Depends(get_db)):
    return public_user(db, user)


@app.post("/api/auth/change-password", tags=["Auth"])
def change_password(payload: PasswordIn, user: User = Depends(current_user), db=Depends(get_db)):
    if not verify_password(payload.old_password, user.password_hash):
        raise HTTPException(400, "Current password is incorrect.")
    check_password(payload.new_password)
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"message": "Password changed."}


@app.patch("/api/profile", tags=["Auth"])
def update_profile(payload: ProfileIn, user: User = Depends(current_user), db=Depends(get_db)):
    if payload.full_name is not None:
        if len(payload.full_name.strip()) < 2:
            raise HTTPException(400, "Name is too short.")
        user.full_name = payload.full_name.strip()
    if payload.phone is not None:
        user.phone = clean_phone(payload.phone)
    db.commit()
    return public_user(db, user)


@app.get("/api/categories", tags=["Catalog"])
def list_categories(db=Depends(get_db)):
    rows = db.query(ServiceCategory).filter_by(is_active=True).order_by(ServiceCategory.id).all()
    return [category_json(row) for row in rows]


@app.post("/api/categories", tags=["Admin"])
def create_category(payload: CategoryIn, _: User = Depends(require("admin")), db=Depends(get_db)):
    slug = slugify(payload.name)
    if db.query(ServiceCategory).filter_by(slug=slug).first():
        slug = f"{slug}-{uuid.uuid4().hex[:4]}"
    row = ServiceCategory(name=payload.name.strip(), slug=slug, description=payload.description.strip(), icon=payload.icon, parent_id=payload.parent_id, is_active=True)
    db.add(row)
    db.commit()
    db.refresh(row)
    return category_json(row)


@app.patch("/api/categories/{category_id}", tags=["Admin"])
def patch_category(category_id: int, payload: CategoryIn, _: User = Depends(require("admin")), db=Depends(get_db)):
    row = db.get(ServiceCategory, category_id)
    if not row:
        raise HTTPException(404, "Category not found.")
    row.name = payload.name.strip()
    row.description = payload.description.strip()
    row.icon = payload.icon
    row.parent_id = payload.parent_id
    db.commit()
    return category_json(row)


@app.get("/api/services", tags=["Catalog"])
def list_services(q: str = "", category_id: int | None = None, city: str = "", page: int = 1, page_size: int = 12, db=Depends(get_db)):
    page = max(page, 1)
    page_size = min(max(page_size, 1), 50)
    query = db.query(Service).filter(Service.status == "active")
    if category_id:
        query = query.filter(Service.category_id == category_id)
    if q.strip():
        like = f"%{q.strip().lower()}%"
        query = query.filter((Service.name.ilike(like)) | (Service.description.ilike(like)))
    if city.strip():
        area_ids = [area.provider_id for area in db.query(ServiceArea).filter(ServiceArea.city.ilike(city.strip())).all()]
        service_ids = [offer.service_id for offer in db.query(ProviderService).filter(ProviderService.provider_id.in_(area_ids or [0])).all()]
        query = query.filter(Service.id.in_(service_ids or [0]))
    total = query.count()
    rows = query.order_by(Service.id).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [service_summary(db, row) for row in rows], "total": total, "page": page, "page_size": page_size}


@app.get("/api/services/{service_id}", tags=["Catalog"])
def get_service(service_id: int, db=Depends(get_db)):
    row = db.get(Service, service_id)
    if not row or row.status != "active":
        raise HTTPException(404, "Service not found.")
    data = service_summary(db, row)
    offers = (
        db.query(ProviderService)
        .join(ServiceProvider, ServiceProvider.id == ProviderService.provider_id)
        .filter(ProviderService.service_id == row.id, ProviderService.status == "active", ServiceProvider.verification_status == "approved")
        .all()
    )
    providers = []
    for offer in offers:
        provider = db.get(ServiceProvider, offer.provider_id)
        card = provider_card(db, provider)
        card.update({"offer_id": offer.id, "price": offer.price, "offer_description": offer.description or ""})
        providers.append(card)
    data["providers"] = providers
    return data


@app.post("/api/services", tags=["Admin"])
def create_service(payload: ServiceIn, _: User = Depends(require("admin")), db=Depends(get_db)):
    if not db.get(ServiceCategory, payload.category_id):
        raise HTTPException(400, "Category not found.")
    row = Service(category_id=payload.category_id, name=payload.name.strip(), description=payload.description.strip(), base_price=payload.base_price, duration_mins=payload.duration_mins, image_url=payload.image_url, status=payload.status if payload.status in ("active", "inactive") else "active")
    db.add(row)
    db.commit()
    db.refresh(row)
    return service_summary(db, row)


@app.patch("/api/services/{service_id}", tags=["Admin"])
def patch_service(service_id: int, payload: ServicePatch, _: User = Depends(require("admin")), db=Depends(get_db)):
    row = db.get(Service, service_id)
    if not row:
        raise HTTPException(404, "Service not found.")
    for field in ("name", "description", "base_price", "duration_mins", "image_url", "status", "category_id"):
        value = getattr(payload, field)
        if value is not None:
            setattr(row, field, value.strip() if isinstance(value, str) else value)
    db.commit()
    return service_summary(db, row)


@app.get("/api/providers", tags=["Catalog"])
def list_providers(q: str = "", category_id: int | None = None, city: str = "", db=Depends(get_db)):
    rows = db.query(ServiceProvider).filter_by(verification_status="approved").all()
    if city.strip():
        ids = {area.provider_id for area in db.query(ServiceArea).filter(ServiceArea.city.ilike(city.strip())).all()}
        rows = [row for row in rows if row.id in ids]
    if category_id:
        service_ids = [service.id for service in db.query(Service).filter_by(category_id=category_id).all()]
        ids = {offer.provider_id for offer in db.query(ProviderService).filter(ProviderService.service_id.in_(service_ids or [0]), ProviderService.status == "active").all()}
        rows = [row for row in rows if row.id in ids]
    if q.strip():
        needle = q.strip().lower()
        rows = [row for row in rows if needle in row.business_name.lower() or needle in (row.bio or "").lower()]
    return [provider_card(db, row) for row in rows]


@app.get("/api/providers/{provider_id}", tags=["Catalog"])
def get_provider(provider_id: int, db=Depends(get_db)):
    row = db.get(ServiceProvider, provider_id)
    if not row or row.verification_status != "approved":
        raise HTTPException(404, "Provider not found.")
    data = provider_card(db, row)
    hours = db.query(AvailabilitySlot).filter_by(provider_id=row.id, is_active=True).order_by(AvailabilitySlot.day_of_week).all()
    offers = []
    for offer in db.query(ProviderService).filter_by(provider_id=row.id, status="active").all():
        service = db.get(Service, offer.service_id)
        if service and service.status == "active":
            offers.append({"offer_id": offer.id, "service_id": service.id, "name": service.name, "price": offer.price, "duration_mins": service.duration_mins, "description": offer.description or service.description})
    reviews = db.query(Review).filter(Review.provider_id == row.id, Review.is_visible.is_(True)).order_by(Review.id.desc()).all()
    data.update({
        "hours": [{"day_of_week": hour.day_of_week, "start_time": hour.start_time, "end_time": hour.end_time} for hour in hours],
        "offers": offers,
        "reviews": [review_json(db, review) for review in reviews],
    })
    return data


@app.get("/api/offers/{offer_id}", tags=["Catalog"])
def get_offer(offer_id: int, db=Depends(get_db)):
    offer = db.get(ProviderService, offer_id)
    if not offer or offer.status != "active":
        raise HTTPException(404, "Offer not found.")
    provider = db.get(ServiceProvider, offer.provider_id)
    service = db.get(Service, offer.service_id)
    if not provider or provider.verification_status != "approved" or not service or service.status != "active":
        raise HTTPException(404, "Offer not found.")
    return {
        "offer_id": offer.id,
        "price": offer.price,
        "description": offer.description or service.description,
        "service": service_summary(db, service),
        "provider": provider_card(db, provider),
        "commission_rate": provider.commission_rate,
    }


@app.get("/api/slots", tags=["Booking"])
def slots(provider_id: int, scheduled_date: str, db=Depends(get_db)):
    try:
        day = datetime.strptime(scheduled_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(400, "Use a date in YYYY-MM-DD format.")
    if day < date.today():
        raise HTTPException(400, "Choose today or a future date.")
    times = hours_for(db, provider_id, day)
    taken = {
        row.scheduled_time
        for row in db.query(Booking).filter(Booking.provider_id == provider_id, Booking.scheduled_date == scheduled_date, Booking.slot_key.isnot(None)).all()
    }
    return [{"time": item, "available": item not in taken} for item in times]


@app.post("/api/coupons/preview", tags=["Payments"])
def preview_coupon(payload: CouponPreview, _: User = Depends(current_user), db=Depends(get_db)):
    coupon = active_coupon(db, payload.code)
    priced = quote(payload.amount, coupon_payload(coupon) if coupon else None)
    if coupon and priced["discount"] <= 0:
        raise HTTPException(400, "This coupon does not apply to that amount.")
    return priced | {"code": coupon.code if coupon else ""}


@app.get("/api/customer/dashboard", tags=["Customer"])
def customer_dashboard(user: User = Depends(require("customer")), db=Depends(get_db)):
    customer = customer_of(db, user)
    rows = db.query(Booking).filter_by(customer_id=customer.id).order_by(Booking.scheduled_date.desc()).all()
    upcoming = [booking_json(db, row) for row in rows if row.status in OPEN_STATUSES and row.scheduled_date >= date.today().isoformat()]
    previous = [booking_json(db, row) for row in rows if row.status in ("Completed", "Cancelled", "Rejected")]
    pending_pay = [booking_json(db, row) for row in rows if row.payment_status not in ("Paid", "Refunded") and row.status not in ("Cancelled", "Rejected")]
    return {
        "upcoming": upcoming[:5],
        "previous_count": len(previous),
        "pending_payments": len(pending_pay),
        "favorites": db.query(Favorite).filter_by(customer_id=customer.id).count(),
        "recent": [booking_json(db, row) for row in rows[:6]],
    }


@app.get("/api/addresses", tags=["Customer"])
def list_addresses(user: User = Depends(require("customer")), db=Depends(get_db)):
    customer = customer_of(db, user)
    rows = db.query(Address).filter_by(customer_id=customer.id).all()
    return [{"id": row.id, "label": row.label, "line1": row.line1, "city": row.city, "state": row.state, "pincode": row.pincode, "is_default": row.is_default} for row in rows]


@app.post("/api/addresses", tags=["Customer"])
def create_address(payload: AddressIn, user: User = Depends(require("customer")), db=Depends(get_db)):
    customer = customer_of(db, user)
    if payload.is_default:
        for row in db.query(Address).filter_by(customer_id=customer.id).all():
            row.is_default = False
    row = Address(customer_id=customer.id, label=payload.label.strip() or "Home", line1=payload.line1.strip(), city=payload.city.strip(), state=payload.state.strip() or "Gujarat", pincode=payload.pincode.strip(), is_default=payload.is_default)
    if not row.line1 or not row.city:
        raise HTTPException(400, "Address and city are required.")
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id}


@app.patch("/api/addresses/{address_id}", tags=["Customer"])
def patch_address(address_id: int, payload: AddressIn, user: User = Depends(require("customer")), db=Depends(get_db)):
    customer = customer_of(db, user)
    row = db.get(Address, address_id)
    if not row or row.customer_id != customer.id:
        raise HTTPException(404, "Address not found.")
    if payload.is_default:
        for other in db.query(Address).filter_by(customer_id=customer.id).all():
            other.is_default = False
    row.label = payload.label.strip() or "Home"
    row.line1 = payload.line1.strip()
    row.city = payload.city.strip()
    row.state = payload.state.strip() or "Gujarat"
    row.pincode = payload.pincode.strip()
    row.is_default = payload.is_default
    db.commit()
    return {"ok": True}


@app.delete("/api/addresses/{address_id}", tags=["Customer"])
def delete_address(address_id: int, user: User = Depends(require("customer")), db=Depends(get_db)):
    customer = customer_of(db, user)
    row = db.get(Address, address_id)
    if not row or row.customer_id != customer.id:
        raise HTTPException(404, "Address not found.")
    db.delete(row)
    db.commit()
    return {"ok": True}


@app.get("/api/favorites", tags=["Customer"])
def list_favorites(user: User = Depends(require("customer")), db=Depends(get_db)):
    customer = customer_of(db, user)
    rows = db.query(Favorite).filter_by(customer_id=customer.id).all()
    cards = []
    for row in rows:
        provider = db.get(ServiceProvider, row.provider_id)
        if provider:
            cards.append(provider_card(db, provider))
    return cards


@app.post("/api/favorites/{provider_id}", tags=["Customer"])
def toggle_favorite(provider_id: int, user: User = Depends(require("customer")), db=Depends(get_db)):
    customer = customer_of(db, user)
    if not db.get(ServiceProvider, provider_id):
        raise HTTPException(404, "Provider not found.")
    existing = db.query(Favorite).filter_by(customer_id=customer.id, provider_id=provider_id).first()
    if existing:
        db.delete(existing)
        db.commit()
        return {"favorite": False}
    db.add(Favorite(customer_id=customer.id, provider_id=provider_id))
    db.commit()
    return {"favorite": True}


def place_booking(db, user: User, payload: BookingIn) -> Booking:
    customer = customer_of(db, user)
    offer = db.get(ProviderService, payload.provider_service_id)
    if not offer or offer.status != "active":
        raise HTTPException(404, "That service offer is not available.")
    provider = db.get(ServiceProvider, offer.provider_id)
    service = db.get(Service, offer.service_id)
    if not provider or provider.verification_status != "approved" or not service or service.status != "active":
        raise HTTPException(400, "This provider is not available for booking.")
    try:
        day = datetime.strptime(payload.scheduled_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(400, "Use a date in YYYY-MM-DD format.")
    if day < date.today():
        raise HTTPException(400, "Choose today or a future date.")
    if payload.scheduled_time not in hours_for(db, provider.id, day):
        raise HTTPException(400, "That time is outside the provider's working hours.")
    if payload.address_id:
        address = db.get(Address, payload.address_id)
        if not address or address.customer_id != customer.id:
            raise HTTPException(404, "Address not found.")
        line, city, pin = address.line1, address.city, address.pincode
    else:
        line, city, pin = payload.line1.strip(), payload.city.strip(), payload.pincode.strip()
        if not line or not city:
            raise HTTPException(400, "Add the visit address and city.")
        db.add(Address(customer_id=customer.id, label=payload.label or "Home", line1=line, city=city, state=payload.state or "Gujarat", pincode=pin, is_default=False))
    areas = db.query(ServiceArea).filter_by(provider_id=provider.id).all()
    if areas:
        city_ok = any(area.city.lower() == city.lower() for area in areas)
        pin_ok = bool(pin) and any(area.pincode == pin for area in areas)
        if not city_ok and not pin_ok:
            raise HTTPException(400, "This provider does not serve that area.")
    coupon = active_coupon(db, payload.coupon_code)
    priced = quote(offer.price, coupon_payload(coupon) if coupon else None, provider.commission_rate)
    if coupon and priced["discount"] <= 0:
        raise HTTPException(400, "This coupon does not apply to this booking.")
    slot_key = f"{provider.id}:{payload.scheduled_date}:{payload.scheduled_time}"
    if db.query(Booking).filter_by(slot_key=slot_key).first():
        raise HTTPException(409, "That slot was just taken. Pick another time.")
    booking = Booking(
        booking_code=new_code(db),
        customer_id=customer.id,
        provider_id=provider.id,
        service_id=service.id,
        provider_service_id=offer.id,
        address_text=f"{line}, {city} {pin}".strip(),
        city=city,
        scheduled_date=payload.scheduled_date,
        scheduled_time=payload.scheduled_time,
        status="Pending",
        payment_status="Pending",
        problem_note=payload.problem_note.strip(),
        subtotal=priced["subtotal"],
        discount=priced["discount"],
        taxable=priced["taxable"],
        gst=priced["gst"],
        commission=priced["commission"],
        provider_earning=priced["earning"],
        total=priced["total"],
        coupon_code=coupon.code if coupon else "",
        slot_key=slot_key,
    )
    db.add(booking)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "That slot was just taken. Pick another time.")
    notify(db, user.id, "Booking request sent", f"{booking.booking_code} for {service.name} on {booking.scheduled_date} at {booking.scheduled_time}.", "booking")
    notify(db, user.id, "Appointment reminder", f"Visit {booking.scheduled_date} at {booking.scheduled_time}. Address: {booking.address_text}.", "reminder")
    notify(db, provider.user_id, "New booking request", f"{user.full_name} requested {service.name} on {booking.scheduled_date} at {booking.scheduled_time}.", "booking")
    return booking


@app.post("/api/bookings", tags=["Booking"])
def create_booking(payload: BookingIn, user: User = Depends(require("customer")), db=Depends(get_db)):
    booking = place_booking(db, user, payload)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "That slot was just taken. Pick another time.")
    db.refresh(booking)
    return booking_json(db, booking)


@app.get("/api/bookings", tags=["Booking"])
def list_bookings(status: str = "", page: int = 1, page_size: int = 20, user: User = Depends(current_user), db=Depends(get_db)):
    page = max(page, 1)
    page_size = min(max(page_size, 1), 50)
    query = visible_bookings(db, user)
    if status.strip():
        query = query.filter(Booking.status == status.strip())
    total = query.count()
    rows = query.order_by(Booking.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [booking_json(db, row) for row in rows], "total": total, "page": page, "page_size": page_size}


@app.get("/api/bookings/{booking_id}", tags=["Booking"])
def get_booking(booking_id: int, user: User = Depends(current_user), db=Depends(get_db)):
    return booking_json(db, load_booking(db, user, booking_id))


@app.post("/api/bookings/{booking_id}/cancel", tags=["Booking"])
def cancel_booking(booking_id: int, payload: ReasonIn, user: User = Depends(current_user), db=Depends(get_db)):
    booking = load_booking(db, user, booking_id)
    if user.role not in ("customer", "admin"):
        raise HTTPException(403, "Only the customer or admin can cancel.")
    if booking.status not in ("Pending", "Confirmed", "Provider Assigned"):
        raise HTTPException(400, "This booking can no longer be cancelled.")
    booking.status = "Cancelled"
    booking.cancel_reason = payload.reason.strip()
    booking.slot_key = None
    paid = db.query(Payment).filter_by(booking_id=booking.id, status="Paid").all()
    for payment in paid:
        payment.status = "Refunded"
    if paid:
        booking.payment_status = "Refunded"
        for earning in db.query(ProviderEarning).filter_by(booking_id=booking.id, status="accrued").all():
            earning.status = "refunded"
    provider = db.get(ServiceProvider, booking.provider_id)
    customer = db.get(Customer, booking.customer_id)
    notify(db, customer.user_id, "Booking cancelled", f"{booking.booking_code} was cancelled.", "booking")
    if provider:
        notify(db, provider.user_id, "Booking cancelled", f"{booking.booking_code} was cancelled.", "booking")
    db.commit()
    return booking_json(db, booking)


@app.post("/api/bookings/{booking_id}/reschedule", tags=["Booking"])
def reschedule(booking_id: int, payload: RescheduleIn, user: User = Depends(require("customer")), db=Depends(get_db)):
    booking = load_booking(db, user, booking_id)
    if booking.status not in ("Pending", "Confirmed", "Provider Assigned"):
        raise HTTPException(400, "This booking cannot be rescheduled.")
    try:
        day = datetime.strptime(payload.scheduled_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(400, "Use a date in YYYY-MM-DD format.")
    if day < date.today() or payload.scheduled_time not in hours_for(db, booking.provider_id, day):
        raise HTTPException(400, "That slot is not available.")
    slot_key = f"{booking.provider_id}:{payload.scheduled_date}:{payload.scheduled_time}"
    clash = db.query(Booking).filter(Booking.slot_key == slot_key, Booking.id != booking.id).first()
    if clash:
        raise HTTPException(409, "That slot is already booked.")
    booking.scheduled_date = payload.scheduled_date
    booking.scheduled_time = payload.scheduled_time
    booking.slot_key = slot_key
    provider = db.get(ServiceProvider, booking.provider_id)
    notify(db, user.id, "Booking rescheduled", f"{booking.booking_code} moved to {payload.scheduled_date} {payload.scheduled_time}.", "booking")
    if provider:
        notify(db, provider.user_id, "Booking rescheduled", f"{booking.booking_code} moved to {payload.scheduled_date} {payload.scheduled_time}.", "booking")
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "That slot is already booked.")
    return booking_json(db, booking)


@app.post("/api/bookings/{booking_id}/accept", tags=["Booking"])
def accept_booking(booking_id: int, user: User = Depends(require("provider", "admin")), db=Depends(get_db)):
    booking = load_booking(db, user, booking_id)
    if booking.status != "Pending":
        raise HTTPException(400, "Only a pending request can be accepted.")
    booking.status = "Confirmed"
    customer = db.get(Customer, booking.customer_id)
    notify(db, customer.user_id, "Booking confirmed", f"{booking.booking_code} is confirmed for {booking.scheduled_date} at {booking.scheduled_time}.", "booking")
    db.commit()
    return booking_json(db, booking)


@app.post("/api/bookings/{booking_id}/reject", tags=["Booking"])
def reject_booking(booking_id: int, payload: ReasonIn, user: User = Depends(require("provider", "admin")), db=Depends(get_db)):
    booking = load_booking(db, user, booking_id)
    if booking.status != "Pending":
        raise HTTPException(400, "Only a pending request can be rejected.")
    booking.status = "Rejected"
    booking.cancel_reason = payload.reason.strip()
    booking.slot_key = None
    customer = db.get(Customer, booking.customer_id)
    notify(db, customer.user_id, "Booking declined", f"{booking.booking_code} was declined. {booking.cancel_reason}".strip(), "booking")
    db.commit()
    return booking_json(db, booking)


@app.post("/api/bookings/{booking_id}/assign", tags=["Booking"])
def assign_tech(booking_id: int, payload: AssignIn, user: User = Depends(require("provider", "admin")), db=Depends(get_db)):
    booking = load_booking(db, user, booking_id)
    if booking.status not in ("Confirmed", "Provider Assigned"):
        raise HTTPException(400, "Confirm the booking before assigning a technician.")
    tech = db.get(Technician, payload.technician_id)
    if not tech or tech.provider_id != booking.provider_id or tech.status != "active":
        raise HTTPException(400, "Choose an active technician from this provider.")
    for old in db.query(BookingAssignment).filter_by(booking_id=booking.id).all():
        if old.status != "completed":
            old.status = "reassigned"
    booking.technician_id = tech.id
    booking.status = "Provider Assigned"
    db.add(BookingAssignment(booking_id=booking.id, technician_id=tech.id, status="assigned"))
    customer = db.get(Customer, booking.customer_id)
    tech_user = db.get(User, tech.user_id)
    notify(db, customer.user_id, "Technician assigned", f"{tech_user.full_name} is assigned to {booking.booking_code}.", "booking")
    notify(db, tech.user_id, "New job", f"{booking.booking_code} on {booking.scheduled_date} at {booking.scheduled_time}.", "job")
    db.commit()
    return booking_json(db, booking)


@app.post("/api/bookings/{booking_id}/arrive", tags=["Booking"])
def arrive(booking_id: int, user: User = Depends(require("technician", "provider", "admin")), db=Depends(get_db)):
    booking = load_booking(db, user, booking_id)
    if booking.status != "Provider Assigned":
        raise HTTPException(400, "Arrival can be marked after a technician is assigned.")
    if user.role == "technician" and booking.technician_id != technician_of(db, user).id:
        raise HTTPException(403, "This job is not assigned to you.")
    booking.status = "In Progress"
    booking.arrived_at = datetime.utcnow()
    assignment = db.query(BookingAssignment).filter_by(booking_id=booking.id, technician_id=booking.technician_id).order_by(BookingAssignment.id.desc()).first()
    if assignment:
        assignment.status = "arrived"
        assignment.arrived_at = booking.arrived_at
    customer = db.get(Customer, booking.customer_id)
    notify(db, customer.user_id, "Technician has arrived", f"Work has started on {booking.booking_code}.", "booking")
    db.commit()
    return booking_json(db, booking)


@app.post("/api/bookings/{booking_id}/complete", tags=["Booking"])
def complete(booking_id: int, payload: CompleteIn, user: User = Depends(require("technician", "provider", "admin")), db=Depends(get_db)):
    booking = load_booking(db, user, booking_id)
    if booking.status != "In Progress":
        raise HTTPException(400, "Start the job before marking it complete.")
    if user.role == "technician" and booking.technician_id != technician_of(db, user).id:
        raise HTTPException(403, "This job is not assigned to you.")
    booking.status = "Completed"
    booking.remarks = payload.remarks.strip()
    booking.completed_at = datetime.utcnow()
    assignment = db.query(BookingAssignment).filter_by(booking_id=booking.id, technician_id=booking.technician_id).order_by(BookingAssignment.id.desc()).first()
    if assignment:
        assignment.status = "completed"
        assignment.completed_at = booking.completed_at
        assignment.remarks = booking.remarks
    customer = db.get(Customer, booking.customer_id)
    notify(db, customer.user_id, "Service completed", f"{booking.booking_code} is done. You can pay the balance and leave a review.", "booking")
    db.commit()
    return booking_json(db, booking)


@app.post("/api/bookings/{booking_id}/images", tags=["Booking"])
def add_image(booking_id: int, payload: ImageIn, user: User = Depends(current_user), db=Depends(get_db)):
    booking = load_booking(db, user, booking_id)
    if payload.kind not in ("problem", "before", "after", "document"):
        raise HTTPException(400, "Unknown image type.")
    if not (UPLOAD_RE.match(payload.url or "") or CLOUDINARY_RE.match(payload.url or "")):
        raise HTTPException(400, "Upload the file first.")
    if payload.kind == "problem" and user.role not in ("customer", "admin"):
        raise HTTPException(403, "Only the customer can add a problem photo.")
    if payload.kind in ("before", "after") and user.role not in ("provider", "technician", "admin"):
        raise HTTPException(403, "Only the crew can add job photos.")
    db.add(BookingImage(booking_id=booking.id, url=payload.url, kind=payload.kind))
    db.commit()
    return booking_json(db, booking)


@app.post("/api/payments/checkout", tags=["Payments"])
def checkout(payload: CheckoutIn, user: User = Depends(require("customer", "admin")), db=Depends(get_db)):
    booking = load_booking(db, user, payload.booking_id)
    if booking.status in ("Cancelled", "Rejected"):
        raise HTTPException(400, "This booking cannot be paid.")
    balance = round(booking.total - paid_sum(db, booking.id), 2)
    if balance <= 0:
        raise HTTPException(400, "This booking is already paid.")
    amount = round(balance * 0.3, 2) if payload.mode == "advance" else balance
    if amount <= 0 or amount - balance > 0.01:
        raise HTTPException(400, "Payment amount is not valid.")
    if amount > balance:
        amount = balance
    order_id = f"order_test_{uuid.uuid4().hex[:12]}"
    key_id = os.getenv("RAZORPAY_KEY_ID", "")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET", "")
    mode = "test"
    if key_id and key_secret:
        response = httpx.post(
            "https://api.razorpay.com/v1/orders",
            auth=(key_id, key_secret),
            json={"amount": int(round(amount * 100)), "currency": "INR", "receipt": booking.booking_code},
            timeout=20,
        )
        if response.status_code >= 300:
            raise HTTPException(502, "Razorpay could not create the order.")
        order_id = response.json().get("id", order_id)
        mode = "razorpay"
    ratio = amount / booking.total if booking.total else 1
    payment = Payment(booking_id=booking.id, amount=amount, commission=round(booking.commission * ratio, 2), status="Pending", method="razorpay_test", order_id=order_id)
    db.add(payment)
    db.commit()
    return {"order_id": order_id, "amount": amount, "currency": "INR", "key_id": key_id or "rzp_test_demo", "mode": mode, "booking_code": booking.booking_code, "balance": balance}


@app.post("/api/payments/verify", tags=["Payments"])
def verify_payment(payload: VerifyIn, user: User = Depends(require("customer", "admin")), db=Depends(get_db)):
    booking = load_booking(db, user, payload.booking_id)
    payment = db.query(Payment).filter_by(booking_id=booking.id, order_id=payload.order_id).first()
    if not payment or payment.status != "Pending":
        raise HTTPException(404, "Payment order not found.")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET", "")
    outcome = payload.outcome
    if key_secret:
        signed = f"{payload.order_id}|{payload.payment_id}".encode()
        expected = hmac.new(key_secret.encode(), signed, hashlib.sha256).hexdigest()
        if not payload.signature or not hmac.compare_digest(expected, payload.signature):
            raise HTTPException(400, "Payment signature did not match.")
        outcome = "success"
    else:
        digits = re.sub(r"\D", "", payload.test_card)
        if digits == "4000000000000002":
            outcome = "failed"
        elif outcome == "success" and digits != "4111111111111111":
            raise HTTPException(400, "Use the Razorpay test card 4111 1111 1111 1111.")
    if outcome == "success":
        payment.status = "Paid"
        payment.txn_id = payload.payment_id or f"pay_test_{uuid.uuid4().hex[:10]}"
        db.flush()
        paid = refresh_payment_status(db, booking)
        db.add(Invoice(payment_id=payment.id, booking_id=booking.id, invoice_number=f"INV-2026-{payment.id:04d}", amount=payment.amount, issued_on=date.today().isoformat()))
        customer = db.get(Customer, booking.customer_id)
        provider = db.get(ServiceProvider, booking.provider_id)
        notify(db, customer.user_id, "Payment received", f"{booking.booking_code}: ₹{payment.amount:.0f} received. Balance ₹{max(booking.total - paid, 0):.0f}.", "payment")
        if provider:
            notify(db, provider.user_id, "Payment update", f"{booking.booking_code} received ₹{payment.amount:.0f}.", "payment")
    else:
        payment.status = "Failed"
        booking.payment_status = booking.payment_status if booking.payment_status == "Partial" else "Failed"
        if paid_sum(db, booking.id) > 0:
            booking.payment_status = "Partial"
    db.commit()
    return booking_json(db, booking)


@app.get("/api/payments", tags=["Payments"])
def list_payments(user: User = Depends(current_user), db=Depends(get_db)):
    query = db.query(Payment)
    if user.role == "customer":
        ids = [row.id for row in db.query(Booking).filter_by(customer_id=customer_of(db, user).id).all()]
        query = query.filter(Payment.booking_id.in_(ids or [0]))
    elif user.role == "provider":
        ids = [row.id for row in db.query(Booking).filter_by(provider_id=provider_of(db, user).id).all()]
        query = query.filter(Payment.booking_id.in_(ids or [0]))
    elif user.role == "technician":
        raise HTTPException(403, "Technicians do not have a payment ledger.")
    rows = query.order_by(Payment.id.desc()).all()
    result = []
    for row in rows:
        booking = db.get(Booking, row.booking_id)
        invoice = db.query(Invoice).filter_by(payment_id=row.id).first()
        result.append({
            "id": row.id,
            "booking_id": row.booking_id,
            "booking_code": booking.booking_code if booking else "",
            "amount": row.amount,
            "commission": row.commission,
            "status": row.status,
            "method": row.method,
            "order_id": row.order_id,
            "txn_id": row.txn_id,
            "invoice_number": invoice.invoice_number if invoice else "",
            "created_at": iso(row.created_at),
        })
    return result


@app.get("/api/bookings/{booking_id}/invoice", tags=["Payments"])
def invoice(booking_id: int, user: User = Depends(current_user), db=Depends(get_db)):
    booking = load_booking(db, user, booking_id)
    data = booking_json(db, booking)
    invoices = db.query(Invoice).filter_by(booking_id=booking.id).all()
    lines = []
    for row in invoices:
        payment = db.get(Payment, row.payment_id)
        lines.append({"invoice_number": row.invoice_number, "amount": row.amount, "issued_on": row.issued_on, "txn_id": payment.txn_id if payment else "", "status": payment.status if payment else ""})
    data["invoices"] = lines
    data["business"] = "HomeServe Technologies"
    return data


@app.post("/api/reviews", tags=["Reviews"])
def create_review(payload: ReviewIn, user: User = Depends(require("customer")), db=Depends(get_db)):
    booking = load_booking(db, user, payload.booking_id)
    if booking.status != "Completed":
        raise HTTPException(400, "You can review a booking after the job is completed.")
    if db.query(Review).filter_by(booking_id=booking.id).first():
        raise HTTPException(400, "This booking already has a review.")
    row = Review(booking_id=booking.id, customer_id=booking.customer_id, provider_id=booking.provider_id, rating=payload.rating, comment=payload.comment.strip(), is_visible=True)
    db.add(row)
    db.flush()
    recalc_rating(db, booking.provider_id)
    provider = db.get(ServiceProvider, booking.provider_id)
    notify(db, provider.user_id, "New review", f"{user.full_name} rated {booking.booking_code} {payload.rating}/5.", "review")
    db.commit()
    db.refresh(row)
    return review_json(db, row)


@app.post("/api/reviews/{review_id}/respond", tags=["Reviews"])
def respond_review(review_id: int, payload: RespondIn, user: User = Depends(require("provider")), db=Depends(get_db)):
    provider = provider_of(db, user)
    row = db.get(Review, review_id)
    if not row or row.provider_id != provider.id:
        raise HTTPException(404, "Review not found.")
    row.provider_response = payload.response.strip()
    db.commit()
    return review_json(db, row)


@app.post("/api/complaints", tags=["Complaints"])
def create_complaint(payload: ComplaintIn, user: User = Depends(require("customer")), db=Depends(get_db)):
    if payload.booking_id:
        load_booking(db, user, payload.booking_id)
    row = Complaint(user_id=user.id, booking_id=payload.booking_id, subject=payload.subject.strip(), description=payload.description.strip(), status="Open")
    db.add(row)
    admin = db.query(User).filter_by(role="admin").first()
    if admin:
        notify(db, admin.id, "New complaint", payload.subject.strip(), "complaint")
    db.commit()
    db.refresh(row)
    return {"id": row.id, "status": row.status}


@app.get("/api/complaints", tags=["Complaints"])
def list_complaints(user: User = Depends(current_user), db=Depends(get_db)):
    query = db.query(Complaint)
    if user.role == "customer":
        query = query.filter(Complaint.user_id == user.id)
    elif user.role == "provider":
        provider = provider_of(db, user)
        ids = [row.id for row in db.query(Booking).filter_by(provider_id=provider.id).all()]
        query = query.filter(Complaint.booking_id.in_(ids or [0]))
    elif user.role == "technician":
        raise HTTPException(403, "Complaints are handled by admin.")
    rows = query.order_by(Complaint.id.desc()).all()
    result = []
    for row in rows:
        owner = db.get(User, row.user_id)
        booking = db.get(Booking, row.booking_id) if row.booking_id else None
        result.append({
            "id": row.id,
            "subject": row.subject,
            "description": row.description or "",
            "status": row.status,
            "admin_note": row.admin_note or "",
            "booking_id": row.booking_id,
            "booking_code": booking.booking_code if booking else "",
            "customer_name": owner.full_name if owner else "",
            "created_at": iso(row.created_at),
        })
    return result


@app.patch("/api/complaints/{complaint_id}", tags=["Complaints"])
def update_complaint(complaint_id: int, payload: ComplaintUpdate, _: User = Depends(require("admin")), db=Depends(get_db)):
    if payload.status not in ("Open", "In Review", "Resolved"):
        raise HTTPException(400, "Unknown complaint status.")
    row = db.get(Complaint, complaint_id)
    if not row:
        raise HTTPException(404, "Complaint not found.")
    row.status = payload.status
    row.admin_note = payload.admin_note.strip()
    notify(db, row.user_id, "Complaint update", f"{row.subject} is now {row.status}.", "complaint")
    db.commit()
    return {"ok": True}


@app.get("/api/notifications", tags=["Notifications"])
def list_notifications(user: User = Depends(current_user), db=Depends(get_db)):
    rows = db.query(Notification).filter_by(user_id=user.id).order_by(Notification.id.desc()).limit(40).all()
    return [{"id": row.id, "title": row.title, "body": row.body, "type": row.ntype, "is_read": row.is_read, "created_at": iso(row.created_at)} for row in rows]


@app.post("/api/notifications/read", tags=["Notifications"])
def read_notifications(user: User = Depends(current_user), db=Depends(get_db)):
    for row in db.query(Notification).filter_by(user_id=user.id, is_read=False).all():
        row.is_read = True
    db.commit()
    return {"ok": True}


@app.get("/api/provider/dashboard", tags=["Provider"])
def provider_dashboard(user: User = Depends(require("provider")), db=Depends(get_db)):
    provider = provider_of(db, user)
    rows = db.query(Booking).filter_by(provider_id=provider.id).all()
    today = date.today().isoformat()
    earnings = db.query(ProviderEarning).filter_by(provider_id=provider.id, status="accrued").all()
    months = recent_months()
    monthly = []
    for key in months:
        month_rows = [row for row in earnings if row.created_at and row.created_at.strftime("%Y-%m") == key]
        monthly.append({"month": key[5:], "revenue": round(sum(row.net for row in month_rows), 2)})
    return {
        "total_bookings": len(rows),
        "today": len([row for row in rows if row.scheduled_date == today and row.status not in ("Cancelled", "Rejected")]),
        "pending": len([row for row in rows if row.status == "Pending"]),
        "completed": len([row for row in rows if row.status == "Completed"]),
        "earnings": round(sum(row.net for row in earnings), 2),
        "rating": provider.rating_avg,
        "rating_count": provider.rating_count,
        "monthly": monthly,
        "verification_status": provider.verification_status,
    }


@app.get("/api/provider/services", tags=["Provider"])
def my_services(user: User = Depends(require("provider")), db=Depends(get_db)):
    provider = provider_of(db, user)
    rows = db.query(ProviderService).filter_by(provider_id=provider.id).all()
    result = []
    for row in rows:
        service = db.get(Service, row.service_id)
        result.append({"id": row.id, "service_id": row.service_id, "name": service.name if service else "", "price": row.price, "description": row.description or "", "status": row.status})
    return result


@app.post("/api/provider/services", tags=["Provider"])
def add_offer(payload: OfferIn, user: User = Depends(require("provider")), db=Depends(get_db)):
    provider = provider_of(db, user)
    service = db.get(Service, payload.service_id)
    if not service or service.status != "active":
        raise HTTPException(404, "Service not found.")
    if payload.price <= 0:
        raise HTTPException(400, "Price must be greater than zero.")
    row = ProviderService(provider_id=provider.id, service_id=service.id, price=payload.price, description=payload.description.strip(), status="active")
    db.add(row)
    db.commit()
    return {"id": row.id}


@app.patch("/api/provider/services/{offer_id}", tags=["Provider"])
def patch_offer(offer_id: int, payload: OfferPatch, user: User = Depends(require("provider")), db=Depends(get_db)):
    provider = provider_of(db, user)
    row = db.get(ProviderService, offer_id)
    if not row or row.provider_id != provider.id:
        raise HTTPException(404, "Listing not found.")
    if payload.price is not None:
        row.price = payload.price
    if payload.description is not None:
        row.description = payload.description
    if payload.status in ("active", "inactive"):
        row.status = payload.status
    db.commit()
    return {"ok": True}


@app.get("/api/provider/availability", tags=["Provider"])
def my_hours(user: User = Depends(require("provider")), db=Depends(get_db)):
    provider = provider_of(db, user)
    rows = db.query(AvailabilitySlot).filter_by(provider_id=provider.id).order_by(AvailabilitySlot.day_of_week).all()
    return [{"id": row.id, "day_of_week": row.day_of_week, "start_time": row.start_time, "end_time": row.end_time, "is_active": row.is_active} for row in rows]


@app.post("/api/provider/availability", tags=["Provider"])
def add_hours(payload: SlotIn, user: User = Depends(require("provider")), db=Depends(get_db)):
    if not re.match(r"^\d{2}:\d{2}$", payload.start_time) or not re.match(r"^\d{2}:\d{2}$", payload.end_time):
        raise HTTPException(400, "Use HH:MM for working hours.")
    if not generate_slots(payload.start_time, payload.end_time):
        raise HTTPException(400, "The window must be at least 60 minutes.")
    provider = provider_of(db, user)
    row = AvailabilitySlot(provider_id=provider.id, day_of_week=payload.day_of_week, start_time=payload.start_time, end_time=payload.end_time, is_active=True)
    db.add(row)
    db.commit()
    return {"id": row.id}


@app.delete("/api/provider/availability/{slot_id}", tags=["Provider"])
def delete_hours(slot_id: int, user: User = Depends(require("provider")), db=Depends(get_db)):
    provider = provider_of(db, user)
    row = db.get(AvailabilitySlot, slot_id)
    if not row or row.provider_id != provider.id:
        raise HTTPException(404, "Working hours not found.")
    db.delete(row)
    db.commit()
    return {"ok": True}


@app.get("/api/provider/areas", tags=["Provider"])
def my_areas(user: User = Depends(require("provider")), db=Depends(get_db)):
    provider = provider_of(db, user)
    rows = db.query(ServiceArea).filter_by(provider_id=provider.id).all()
    return [{"id": row.id, "city": row.city, "pincode": row.pincode} for row in rows]


@app.post("/api/provider/areas", tags=["Provider"])
def add_area(payload: AreaIn, user: User = Depends(require("provider")), db=Depends(get_db)):
    if not payload.city.strip():
        raise HTTPException(400, "City is required.")
    provider = provider_of(db, user)
    row = ServiceArea(provider_id=provider.id, city=payload.city.strip(), pincode=payload.pincode.strip())
    db.add(row)
    db.commit()
    return {"id": row.id}


@app.delete("/api/provider/areas/{area_id}", tags=["Provider"])
def delete_area(area_id: int, user: User = Depends(require("provider")), db=Depends(get_db)):
    provider = provider_of(db, user)
    row = db.get(ServiceArea, area_id)
    if not row or row.provider_id != provider.id:
        raise HTTPException(404, "Area not found.")
    db.delete(row)
    db.commit()
    return {"ok": True}


@app.get("/api/provider/technicians", tags=["Provider"])
def my_techs(user: User = Depends(require("provider")), db=Depends(get_db)):
    provider = provider_of(db, user)
    rows = db.query(Technician).filter_by(provider_id=provider.id).all()
    result = []
    for row in rows:
        person = db.get(User, row.user_id)
        done = db.query(BookingAssignment).filter_by(technician_id=row.id, status="completed").count()
        result.append({"id": row.id, "name": person.full_name, "email": person.email, "phone": person.phone, "skills": row.skills, "status": row.status, "completed_jobs": done})
    return result


@app.post("/api/provider/technicians", tags=["Provider"])
def add_tech(payload: TechIn, user: User = Depends(require("provider")), db=Depends(get_db)):
    provider = provider_of(db, user)
    email = clean_email(payload.email)
    check_password(payload.password)
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(400, "That email is already in use.")
    person = User(full_name=payload.full_name.strip(), email=email, phone=clean_phone(payload.phone), role="technician", password_hash=hash_password(payload.password), status="active")
    db.add(person)
    db.flush()
    row = Technician(user_id=person.id, provider_id=provider.id, skills=payload.skills.strip(), status="active")
    db.add(row)
    db.commit()
    return {"id": row.id, "email": person.email}


@app.get("/api/provider/earnings", tags=["Provider"])
def earnings(user: User = Depends(require("provider")), db=Depends(get_db)):
    provider = provider_of(db, user)
    rows = db.query(ProviderEarning).filter_by(provider_id=provider.id).order_by(ProviderEarning.id.desc()).all()
    result = []
    for row in rows:
        booking = db.get(Booking, row.booking_id)
        result.append({"id": row.id, "booking_code": booking.booking_code if booking else "", "gross": row.gross, "commission": row.commission, "net": row.net, "status": row.status, "created_at": iso(row.created_at)})
    return result


@app.get("/api/provider/reviews", tags=["Provider"])
def my_reviews(user: User = Depends(require("provider")), db=Depends(get_db)):
    provider = provider_of(db, user)
    rows = db.query(Review).filter_by(provider_id=provider.id).order_by(Review.id.desc()).all()
    return [review_json(db, row) for row in rows]


@app.patch("/api/provider/profile", tags=["Provider"])
def provider_profile(payload: ProviderProfileIn, user: User = Depends(require("provider")), db=Depends(get_db)):
    provider = provider_of(db, user)
    if payload.business_name is not None and payload.business_name.strip():
        provider.business_name = payload.business_name.strip()
    if payload.bio is not None:
        provider.bio = payload.bio.strip()
    if payload.experience_years is not None:
        provider.experience_years = max(payload.experience_years, 0)
    if payload.document_url is not None:
        if payload.document_url and not (UPLOAD_RE.match(payload.document_url) or CLOUDINARY_RE.match(payload.document_url)):
            raise HTTPException(400, "Upload the document first.")
        provider.document_url = payload.document_url
        if provider.verification_status == "rejected":
            provider.verification_status = "pending"
            provider.rejection_reason = ""
    db.commit()
    return public_user(db, user)


@app.post("/api/provider/plan", tags=["Provider"])
def pick_plan(payload: PlanPick, user: User = Depends(require("provider")), db=Depends(get_db)):
    provider = provider_of(db, user)
    plan = db.get(SubscriptionPlan, payload.plan_id)
    if not plan or not plan.is_active:
        raise HTTPException(404, "Plan not found.")
    provider.plan_id = plan.id
    provider.commission_rate = plan.commission_rate
    db.commit()
    return {"plan": plan.name, "commission_rate": plan.commission_rate}


@app.get("/api/technician/dashboard", tags=["Technician"])
def tech_dashboard(user: User = Depends(require("technician")), db=Depends(get_db)):
    tech = technician_of(db, user)
    assignments = db.query(BookingAssignment).filter_by(technician_id=tech.id).all()
    return {
        "completed": sum(1 for row in assignments if row.status == "completed"),
        "active": sum(1 for row in assignments if row.status in ("assigned", "arrived")),
        "total": len(assignments),
        "skills": tech.skills,
    }


@app.get("/api/technician/jobs", tags=["Technician"])
def tech_jobs(user: User = Depends(require("technician")), db=Depends(get_db)):
    tech = technician_of(db, user)
    rows = db.query(Booking).filter_by(technician_id=tech.id).order_by(Booking.scheduled_date.desc()).all()
    return [booking_json(db, row) for row in rows]


@app.get("/api/admin/stats", tags=["Admin"])
def admin_stats(_: User = Depends(require("admin")), db=Depends(get_db)):
    bookings = db.query(Booking).all()
    payments = db.query(Payment).filter_by(status="Paid").all()
    earnings = db.query(ProviderEarning).filter_by(status="accrued").all()
    months = recent_months()
    monthly = []
    for key in months:
        month_bookings = [row for row in bookings if row.created_at and row.created_at.strftime("%Y-%m") == key]
        month_pay = [row for row in payments if row.created_at and row.created_at.strftime("%Y-%m") == key]
        monthly.append({"month": key[5:], "bookings": len(month_bookings), "revenue": round(sum(row.amount for row in month_pay), 2)})
    customers = db.query(User).filter_by(role="customer").all()
    growth = []
    for key in months:
        growth.append({"month": key[5:], "customers": len([row for row in customers if row.created_at and row.created_at.strftime("%Y-%m") == key])})
    popular = defaultdict(int)
    for row in bookings:
        service = db.get(Service, row.service_id)
        if service:
            category = db.get(ServiceCategory, service.category_id)
            if category:
                popular[category.name] += 1
    top = sorted(({"name": name, "count": count} for name, count in popular.items()), key=lambda item: item["count"], reverse=True)[:6]
    return {
        "customers": db.query(Customer).count(),
        "providers": db.query(ServiceProvider).count(),
        "technicians": db.query(Technician).count(),
        "bookings": len(bookings),
        "pending": len([row for row in bookings if row.status == "Pending"]),
        "completed": len([row for row in bookings if row.status == "Completed"]),
        "cancelled": len([row for row in bookings if row.status == "Cancelled"]),
        "revenue": round(sum(row.amount for row in payments), 2),
        "commission": round(sum(row.commission for row in earnings), 2),
        "provider_earnings": round(sum(row.net for row in earnings), 2),
        "popular": top,
        "monthly": monthly,
        "growth": growth,
    }


@app.get("/api/admin/users", tags=["Admin"])
def admin_users(role: str = "", q: str = "", _: User = Depends(require("admin")), db=Depends(get_db)):
    query = db.query(User)
    if role.strip():
        query = query.filter(User.role == role.strip())
    rows = query.order_by(User.id).all()
    if q.strip():
        needle = q.strip().lower()
        rows = [row for row in rows if needle in row.full_name.lower() or needle in row.email.lower()]
    return [public_user(db, row) for row in rows]


@app.patch("/api/admin/users/{user_id}", tags=["Admin"])
def admin_user_status(user_id: int, payload: StatusIn, actor: User = Depends(require("admin")), db=Depends(get_db)):
    if payload.status not in ("active", "suspended"):
        raise HTTPException(400, "Status must be active or suspended.")
    row = db.get(User, user_id)
    if not row:
        raise HTTPException(404, "User not found.")
    if row.id == actor.id:
        raise HTTPException(400, "You cannot suspend your own admin account.")
    row.status = payload.status
    db.commit()
    return public_user(db, row)


@app.post("/api/admin/providers/{provider_id}/verify", tags=["Admin"])
def verify_provider(provider_id: int, payload: VerifyProviderIn, _: User = Depends(require("admin")), db=Depends(get_db)):
    if payload.status not in ("approved", "rejected"):
        raise HTTPException(400, "Choose approved or rejected.")
    row = db.get(ServiceProvider, provider_id)
    if not row:
        raise HTTPException(404, "Provider not found.")
    if payload.status == "rejected" and not payload.reason.strip():
        raise HTTPException(400, "Add a reason when rejecting a provider.")
    row.verification_status = payload.status
    row.rejection_reason = payload.reason.strip()
    notify(db, row.user_id, "Verification update", f"Your provider account is {payload.status}. {row.rejection_reason}".strip(), "admin")
    db.commit()
    return {"ok": True, "status": row.verification_status}


@app.get("/api/admin/listings", tags=["Admin"])
def admin_listings(_: User = Depends(require("admin")), db=Depends(get_db)):
    rows = db.query(ProviderService).order_by(ProviderService.id).all()
    result = []
    for row in rows:
        service = db.get(Service, row.service_id)
        provider = db.get(ServiceProvider, row.provider_id)
        result.append({"id": row.id, "service": service.name if service else "", "provider": provider.business_name if provider else "", "price": row.price, "status": row.status})
    return result


@app.patch("/api/admin/listings/{offer_id}", tags=["Admin"])
def admin_listing_status(offer_id: int, payload: StatusIn, _: User = Depends(require("admin")), db=Depends(get_db)):
    row = db.get(ProviderService, offer_id)
    if not row:
        raise HTTPException(404, "Listing not found.")
    if payload.status not in ("active", "inactive"):
        raise HTTPException(400, "Status must be active or inactive.")
    row.status = payload.status
    db.commit()
    return {"ok": True}


@app.get("/api/coupons", tags=["Admin"])
def list_coupons(_: User = Depends(require("admin")), db=Depends(get_db)):
    rows = db.query(Coupon).order_by(Coupon.id).all()
    return [{"id": row.id, "code": row.code, "discount_type": row.discount_type, "value": row.value, "min_amount": row.min_amount, "max_discount": row.max_discount, "expires_on": row.expires_on, "is_active": row.is_active} for row in rows]


@app.post("/api/coupons", tags=["Admin"])
def create_coupon(payload: CouponIn, _: User = Depends(require("admin")), db=Depends(get_db)):
    code = payload.code.strip().upper()
    if db.query(Coupon).filter_by(code=code).first():
        raise HTTPException(400, "That coupon code already exists.")
    if payload.discount_type not in ("percent", "flat"):
        raise HTTPException(400, "Discount type must be percent or flat.")
    row = Coupon(code=code, discount_type=payload.discount_type, value=payload.value, min_amount=payload.min_amount, max_discount=payload.max_discount, expires_on=payload.expires_on, is_active=payload.is_active)
    db.add(row)
    db.commit()
    return {"id": row.id}


@app.patch("/api/coupons/{coupon_id}", tags=["Admin"])
def patch_coupon(coupon_id: int, payload: CouponIn, _: User = Depends(require("admin")), db=Depends(get_db)):
    row = db.get(Coupon, coupon_id)
    if not row:
        raise HTTPException(404, "Coupon not found.")
    row.code = payload.code.strip().upper()
    row.discount_type = payload.discount_type
    row.value = payload.value
    row.min_amount = payload.min_amount
    row.max_discount = payload.max_discount
    row.expires_on = payload.expires_on
    row.is_active = payload.is_active
    db.commit()
    return {"ok": True}


@app.get("/api/plans", tags=["Admin"])
def list_plans(db=Depends(get_db)):
    rows = db.query(SubscriptionPlan).filter_by(is_active=True).all()
    return [{"id": row.id, "name": row.name, "price": row.price, "commission_rate": row.commission_rate, "description": row.description, "features": row.features, "is_active": row.is_active} for row in rows]


@app.post("/api/plans", tags=["Admin"])
def create_plan(payload: PlanIn, _: User = Depends(require("admin")), db=Depends(get_db)):
    row = SubscriptionPlan(name=payload.name.strip(), price=payload.price, commission_rate=payload.commission_rate, description=payload.description.strip(), features=payload.features.strip(), is_active=payload.is_active)
    db.add(row)
    db.commit()
    return {"id": row.id}


@app.patch("/api/plans/{plan_id}", tags=["Admin"])
def patch_plan(plan_id: int, payload: PlanIn, _: User = Depends(require("admin")), db=Depends(get_db)):
    row = db.get(SubscriptionPlan, plan_id)
    if not row:
        raise HTTPException(404, "Plan not found.")
    row.name = payload.name.strip()
    row.price = payload.price
    row.commission_rate = payload.commission_rate
    row.description = payload.description.strip()
    row.features = payload.features.strip()
    row.is_active = payload.is_active
    db.commit()
    return {"ok": True}


@app.post("/api/admin/announcements", tags=["Notifications"])
def announce(payload: AnnounceIn, _: User = Depends(require("admin")), db=Depends(get_db)):
    roles = ["customer", "provider", "technician", "admin"] if payload.audience == "all" else [payload.audience]
    users = db.query(User).filter(User.role.in_(roles), User.status == "active").all()
    for person in users:
        notify(db, person.id, payload.title.strip(), payload.body.strip(), "announcement")
    db.commit()
    return {"sent": len(users)}


@app.patch("/api/admin/reviews/{review_id}", tags=["Reviews"])
def hide_review(review_id: int, payload: ReviewHide, _: User = Depends(require("admin")), db=Depends(get_db)):
    row = db.get(Review, review_id)
    if not row:
        raise HTTPException(404, "Review not found.")
    row.is_visible = payload.is_visible
    recalc_rating(db, row.provider_id)
    db.commit()
    return {"ok": True}


def csv_response(header, rows, filename):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header)
    writer.writerows(rows)
    return Response(buffer.getvalue(), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@app.get("/api/reports/bookings.csv", tags=["Admin"])
def report_bookings(_: User = Depends(require("admin")), db=Depends(get_db)):
    rows = []
    for row in db.query(Booking).order_by(Booking.id).all():
        data = booking_json(db, row)
        rows.append([data["booking_code"], data["status"], data["payment_status"], data["customer_name"], data["provider_name"], data["service_name"], data["scheduled_date"], data["scheduled_time"], data["total"]])
    return csv_response(["code", "status", "payment", "customer", "provider", "service", "date", "time", "total"], rows, "bookings.csv")


@app.get("/api/reports/payments.csv", tags=["Admin"])
def report_payments(_: User = Depends(require("admin")), db=Depends(get_db)):
    rows = []
    for row in db.query(Payment).order_by(Payment.id).all():
        booking = db.get(Booking, row.booking_id)
        rows.append([booking.booking_code if booking else "", row.amount, row.status, row.method, row.txn_id, iso(row.created_at)])
    return csv_response(["booking", "amount", "status", "method", "txn", "created"], rows, "payments.csv")


@app.get("/api/reports/customers.csv", tags=["Admin"])
def report_customers(_: User = Depends(require("admin")), db=Depends(get_db)):
    rows = []
    for row in db.query(User).filter_by(role="customer").all():
        rows.append([row.full_name, row.email, row.phone, row.status, iso(row.created_at)])
    return csv_response(["name", "email", "phone", "status", "joined"], rows, "customers.csv")


@app.get("/api/provider/earnings.csv", tags=["Provider"])
def earnings_csv(user: User = Depends(require("provider")), db=Depends(get_db)):
    provider = provider_of(db, user)
    rows = []
    for row in db.query(ProviderEarning).filter_by(provider_id=provider.id).all():
        booking = db.get(Booking, row.booking_id)
        rows.append([booking.booking_code if booking else "", row.gross, row.commission, row.net, row.status])
    return csv_response(["booking", "gross", "commission", "net", "status"], rows, "earnings.csv")


@app.post("/api/uploads", tags=["Files"])
def cloudinary_url(content: bytes, name: str) -> str | None:
    cloud = os.getenv("CLOUDINARY_CLOUD_NAME", "")
    key = os.getenv("CLOUDINARY_API_KEY", "")
    secret = os.getenv("CLOUDINARY_API_SECRET", "")
    if not (cloud and key and secret):
        return None
    timestamp = str(int(datetime.utcnow().timestamp()))
    payload = f"public_id=homeserve/{name}&timestamp={timestamp}{secret}"
    signature = hashlib.sha1(payload.encode()).hexdigest()
    response = httpx.post(
        f"https://api.cloudinary.com/v1_1/{cloud}/auto/upload",
        data={"api_key": key, "timestamp": timestamp, "public_id": f"homeserve/{name}", "signature": signature},
        files={"file": (name, content)},
        timeout=30,
    )
    if response.status_code >= 300:
        raise HTTPException(502, "Cloudinary could not store the file.")
    return response.json().get("secure_url")


async def upload(file: UploadFile = File(...), _: User = Depends(current_user)):
    ext = ALLOWED_EXT.get(Path(file.filename or "").suffix.lower())
    if not ext:
        raise HTTPException(400, "Upload a JPG, PNG, WEBP or PDF up to 5 MB.")
    content = await file.read()
    if len(content) > MAX_BYTES:
        raise HTTPException(400, "File is larger than 5 MB.")
    name = f"{uuid.uuid4().hex}{ext}"
    remote = cloudinary_url(content, name)
    if remote:
        return {"url": remote}
    (UPLOAD_DIR / name).write_bytes(content)
    return {"url": f"/uploads/{name}"}


app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


@app.get("/", include_in_schema=False)
def root():
    dist = frontend_dist()
    if dist:
        return FileResponse(dist / "index.html")
    return {"name": "HomeServe API", "docs": "/docs", "health": "/api/health"}


@app.get("/{full_path:path}", include_in_schema=False)
def spa(full_path: str):
    if full_path.startswith("api") or full_path.startswith("uploads"):
        raise HTTPException(404, "Not found.")
    dist = frontend_dist()
    if not dist:
        raise HTTPException(404, "Not found.")
    target = (dist / full_path).resolve()
    if full_path and target.is_file() and str(target).startswith(str(dist.resolve())):
        return FileResponse(target)
    return FileResponse(dist / "index.html")
