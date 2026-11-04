from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint

from sqlalchemy.orm import declarative_base

Base = declarative_base()


def utcnow():
    return datetime.utcnow()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    full_name = Column(String(120), nullable=False)
    email = Column(String(180), unique=True, nullable=False, index=True)
    phone = Column(String(20), default="")
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, index=True)
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=utcnow)


class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"
    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    price = Column(Float, default=0)
    commission_rate = Column(Float, default=15)
    description = Column(Text, default="")
    features = Column(Text, default="")
    is_active = Column(Boolean, default=True)


class ServiceProvider(Base):
    __tablename__ = "service_providers"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    business_name = Column(String(160), nullable=False)
    bio = Column(Text, default="")
    experience_years = Column(Integer, default=1)
    verification_status = Column(String(20), default="pending")
    document_url = Column(String(500), default="")
    rejection_reason = Column(String(300), default="")
    commission_rate = Column(Float, default=15)
    rating_avg = Column(Float, default=0)
    rating_count = Column(Integer, default=0)
    plan_id = Column(Integer, ForeignKey("subscription_plans.id"), nullable=True)


class Technician(Base):
    __tablename__ = "technicians"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    provider_id = Column(Integer, ForeignKey("service_providers.id"), nullable=False, index=True)
    skills = Column(String(300), default="")
    status = Column(String(20), default="active")


class Address(Base):
    __tablename__ = "addresses"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    label = Column(String(40), default="Home")
    line1 = Column(String(200), nullable=False)
    city = Column(String(80), nullable=False)
    state = Column(String(80), default="Gujarat")
    pincode = Column(String(10), default="")
    is_default = Column(Boolean, default=False)


class ServiceCategory(Base):
    __tablename__ = "service_categories"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    description = Column(Text, default="")
    icon = Column(String(40), default="bolt")
    parent_id = Column(Integer, ForeignKey("service_categories.id"), nullable=True)
    is_active = Column(Boolean, default=True)


class Service(Base):
    __tablename__ = "services"
    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey("service_categories.id"), nullable=False, index=True)
    name = Column(String(140), nullable=False)
    description = Column(Text, default="")
    base_price = Column(Float, default=0)
    duration_mins = Column(Integer, default=60)
    image_url = Column(String(500), default="")
    status = Column(String(20), default="active")


class ProviderService(Base):
    __tablename__ = "provider_services"
    id = Column(Integer, primary_key=True)
    provider_id = Column(Integer, ForeignKey("service_providers.id"), nullable=False, index=True)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False, index=True)
    price = Column(Float, nullable=False)
    description = Column(Text, default="")
    status = Column(String(20), default="active")


class ServiceArea(Base):
    __tablename__ = "service_areas"
    id = Column(Integer, primary_key=True)
    provider_id = Column(Integer, ForeignKey("service_providers.id"), nullable=False, index=True)
    city = Column(String(80), nullable=False)
    pincode = Column(String(10), default="")


class AvailabilitySlot(Base):
    __tablename__ = "availability_slots"
    id = Column(Integer, primary_key=True)
    provider_id = Column(Integer, ForeignKey("service_providers.id"), nullable=False, index=True)
    day_of_week = Column(Integer, nullable=False)
    start_time = Column(String(5), nullable=False)
    end_time = Column(String(5), nullable=False)
    is_active = Column(Boolean, default=True)


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        UniqueConstraint("slot_key", name="uq_booking_slot"),
        Index("ix_booking_status", "status"),
    )
    id = Column(Integer, primary_key=True)
    booking_code = Column(String(20), unique=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    provider_id = Column(Integer, ForeignKey("service_providers.id"), nullable=False, index=True)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)
    provider_service_id = Column(Integer, ForeignKey("provider_services.id"), nullable=False)
    technician_id = Column(Integer, ForeignKey("technicians.id"), nullable=True)
    address_text = Column(String(300), default="")
    city = Column(String(80), default="")
    scheduled_date = Column(String(10), nullable=False)
    scheduled_time = Column(String(5), nullable=False)
    status = Column(String(30), default="Pending")
    payment_status = Column(String(20), default="Pending")
    problem_note = Column(Text, default="")
    remarks = Column(Text, default="")
    cancel_reason = Column(String(300), default="")
    subtotal = Column(Float, default=0)
    discount = Column(Float, default=0)
    taxable = Column(Float, default=0)
    gst = Column(Float, default=0)
    commission = Column(Float, default=0)
    provider_earning = Column(Float, default=0)
    total = Column(Float, default=0)
    coupon_code = Column(String(40), default="")
    slot_key = Column(String(80), nullable=True)
    arrived_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)


class BookingAssignment(Base):
    __tablename__ = "booking_assignments"
    id = Column(Integer, primary_key=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False, index=True)
    technician_id = Column(Integer, ForeignKey("technicians.id"), nullable=False)
    status = Column(String(20), default="assigned")
    remarks = Column(Text, default="")
    arrived_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)


class BookingImage(Base):
    __tablename__ = "booking_images"
    id = Column(Integer, primary_key=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False, index=True)
    url = Column(String(500), nullable=False)
    kind = Column(String(20), default="problem")
    created_at = Column(DateTime, default=utcnow)


class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    commission = Column(Float, default=0)
    status = Column(String(20), default="Pending")
    method = Column(String(40), default="razorpay_test")
    order_id = Column(String(80), default="")
    txn_id = Column(String(80), default="")
    created_at = Column(DateTime, default=utcnow)


class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=False, unique=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    invoice_number = Column(String(40), unique=True, nullable=False)
    amount = Column(Float, nullable=False)
    issued_on = Column(String(10), nullable=False)


class Coupon(Base):
    __tablename__ = "coupons"
    id = Column(Integer, primary_key=True)
    code = Column(String(40), unique=True, nullable=False)
    discount_type = Column(String(20), default="percent")
    value = Column(Float, nullable=False)
    min_amount = Column(Float, default=0)
    max_discount = Column(Float, nullable=True)
    expires_on = Column(String(10), default="")
    is_active = Column(Boolean, default=True)


class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), unique=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    provider_id = Column(Integer, ForeignKey("service_providers.id"), nullable=False, index=True)
    rating = Column(Integer, nullable=False)
    comment = Column(Text, default="")
    provider_response = Column(Text, default="")
    is_visible = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)


class Complaint(Base):
    __tablename__ = "complaints"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=True)
    subject = Column(String(160), nullable=False)
    description = Column(Text, default="")
    status = Column(String(20), default="Open")
    admin_note = Column(Text, default="")
    created_at = Column(DateTime, default=utcnow)


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(160), nullable=False)
    body = Column(Text, default="")
    ntype = Column(String(40), default="info")
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)


class ProviderEarning(Base):
    __tablename__ = "provider_earnings"
    id = Column(Integer, primary_key=True)
    provider_id = Column(Integer, ForeignKey("service_providers.id"), nullable=False, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True)
    gross = Column(Float, default=0)
    commission = Column(Float, default=0)
    net = Column(Float, default=0)
    status = Column(String(20), default="accrued")
    created_at = Column(DateTime, default=utcnow)


class Favorite(Base):
    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("customer_id", "provider_id", name="uq_favorite"),)
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    provider_id = Column(Integer, ForeignKey("service_providers.id"), nullable=False)


class PasswordReset(Base):
    __tablename__ = "password_resets"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    code = Column(String(10), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
