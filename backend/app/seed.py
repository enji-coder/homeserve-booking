from datetime import datetime, timedelta

from app.models import (
    Address,
    AvailabilitySlot,
    Booking,
    BookingAssignment,
    Complaint,
    Coupon,
    Customer,
    Favorite,
    Invoice,
    Notification,
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
from app.security import hash_password

DEMO_PASSWORD = "Demo@1234"


def seed(db):
    if db.query(User).filter(User.email == "admin@homeserve.test").first():
        return

    def add_user(name, email, role, phone):
        user = User(
            full_name=name,
            email=email,
            phone=phone,
            role=role,
            password_hash=hash_password(DEMO_PASSWORD),
            status="active",
        )
        db.add(user)
        db.flush()
        return user

    plans = [
        SubscriptionPlan(name="Starter", price=0, commission_rate=20, description="For new crews getting their first jobs.", features="Listing, bookings, standard support"),
        SubscriptionPlan(name="Growth", price=999, commission_rate=15, description="For teams that want a lower commission.", features="Lower commission, priority listing"),
        SubscriptionPlan(name="Scale", price=2499, commission_rate=10, description="For multi-technician businesses.", features="Lowest commission, featured badge"),
    ]
    db.add_all(plans)
    db.flush()
    plan_by = {plan.name: plan for plan in plans}

    categories = [
        ("Electrical Services", "electrical", "Wiring, fans, boards and power faults.", "bolt"),
        ("Plumbing Services", "plumbing", "Leaks, taps, blocks and bathroom fittings.", "drop"),
        ("AC Repair & Maintenance", "ac", "Service, gas and breakdown visits.", "snow"),
        ("Home Cleaning", "cleaning", "Deep cleaning for homes and move-ins.", "spark"),
        ("Painting Services", "painting", "Rooms, touch-ups and fresh coats.", "brush"),
        ("Carpentry Services", "carpentry", "Doors, furniture and fittings.", "hammer"),
        ("Appliance Repair", "appliance", "Washers, geysers and kitchen machines.", "washer"),
        ("Pest Control", "pest", "Cockroach, termite and general treatment.", "bug"),
    ]
    cat_rows = {}
    for name, slug, desc, icon in categories:
        row = ServiceCategory(name=name, slug=slug, description=desc, icon=icon)
        db.add(row)
        db.flush()
        cat_rows[slug] = row
    db.add(ServiceCategory(name="Emergency electrical", slug="emergency-electrical", description="Same-day power faults.", icon="bolt", parent_id=cat_rows["electrical"].id))
    db.add(ServiceCategory(name="Bathroom plumbing", slug="bathroom-plumbing", description="Taps, showers and traps.", icon="drop", parent_id=cat_rows["plumbing"].id))

    catalog = [
        ("electrical", "Switchboard repair", "Trip, spark or a dead section of the house.", 499, 60),
        ("electrical", "Fan installation", "Ceiling or wall fan, fitted and tested.", 349, 60),
        ("electrical", "Wiring inspection", "A safety check of old wiring and the main board.", 799, 90),
        ("plumbing", "Tap repair", "Dripping taps, mixers and loose fittings.", 299, 45),
        ("plumbing", "Pipe leak", "Visible leaks in kitchen or bathroom lines.", 599, 90),
        ("plumbing", "Drain blockage", "Slow or blocked floor and sink drains.", 449, 60),
        ("ac", "AC service", "Filter, coil and a full service visit.", 699, 90),
        ("ac", "AC gas refill", "Cooling loss checked, then gas topped up.", 1499, 90),
        ("ac", "AC installation", "Split AC mounting and commissioning.", 1999, 180),
        ("cleaning", "Deep home cleaning", "Kitchen, baths and floors for a full home.", 1499, 240),
        ("cleaning", "Bathroom cleaning", "Descaling and a proper bathroom reset.", 499, 90),
        ("painting", "Room painting", "One room, including basic prep and two coats.", 2499, 480),
        ("carpentry", "Furniture repair", "Hinges, shutters and wobbly furniture.", 599, 90),
        ("appliance", "Washing machine repair", "Not spinning, not draining, or not starting.", 699, 90),
        ("pest", "General pest control", "A standard home treatment with a follow-up window.", 899, 90),
    ]
    svc = {}
    for slug, name, desc, price, mins in catalog:
        row = Service(category_id=cat_rows[slug].id, name=name, description=desc, base_price=price, duration_mins=mins, status="active")
        db.add(row)
        db.flush()
        svc[name] = row

    def provider(name, email, phone, business, bio, years, status, plan, cities):
        user = add_user(name, email, "provider", phone)
        row = ServiceProvider(
            user_id=user.id,
            business_name=business,
            bio=bio,
            experience_years=years,
            verification_status=status,
            commission_rate=plan.commission_rate,
            plan_id=plan.id,
            document_url="",
        )
        db.add(row)
        db.flush()
        for day in range(7):
            db.add(AvailabilitySlot(provider_id=row.id, day_of_week=day, start_time="09:00", end_time="18:00", is_active=True))
        for city, pin in cities:
            db.add(ServiceArea(provider_id=row.id, city=city, pincode=pin))
        return user, row

    _, bright = provider(
        "Kiran Patel", "kiran@homeserve.test", "9898011101", "BrightSpark Electric",
        "Rewiring old flats in Navrangpura and Satellite without making a mess of the walls.",
        11, "approved", plan_by["Growth"], [("Ahmedabad", "380015"), ("Ahmedabad", "380009")],
    )
    _, aqua = provider(
        "Meena Joshi", "meena@homeserve.test", "9898011102", "AquaFix Plumbing",
        "Leak repairs the same day, with the floor left dry.",
        9, "approved", plan_by["Starter"], [("Ahmedabad", "380015"), ("Ahmedabad", "380006")],
    )
    _, cool = provider(
        "Arjun Desai", "arjun@homeserve.test", "9898011103", "CoolBreeze AC",
        "Monsoon breakdowns are my busy season. I carry gas and the usual spares.",
        8, "approved", plan_by["Growth"], [("Ahmedabad", "380054"), ("Ahmedabad", "380015")],
    )
    _, wood = provider(
        "Ramesh Chauhan", "ramesh@homeserve.test", "9898011104", "Wood & Co",
        "Doors, hinges, and the cupboard that never quite shut.",
        14, "approved", plan_by["Starter"], [("Ahmedabad", "380008")],
    )
    _, sparkle = provider(
        "Neha Rao", "neha@homeserve.test", "9898011105", "SparkleClean",
        "Deep cleaning crews for move-in homes. Waiting on document verification.",
        6, "pending", plan_by["Starter"], [("Ahmedabad", "380015")],
    )

    def offer(prow, service_name, price):
        row = ProviderService(provider_id=prow.id, service_id=svc[service_name].id, price=price, description="", status="active")
        db.add(row)
        db.flush()
        return row

    o_switch = offer(bright, "Switchboard repair", 499)
    o_fan = offer(bright, "Fan installation", 349)
    o_wire = offer(bright, "Wiring inspection", 899)
    o_washer = offer(bright, "Washing machine repair", 749)
    o_tap = offer(aqua, "Tap repair", 299)
    o_leak = offer(aqua, "Pipe leak", 649)
    o_drain = offer(aqua, "Drain blockage", 449)
    o_ac = offer(cool, "AC service", 699)
    o_gas = offer(cool, "AC gas refill", 1599)
    offer(cool, "AC installation", 2199)
    offer(wood, "Furniture repair", 599)
    offer(wood, "Room painting", 2699)
    offer(sparkle, "Deep home cleaning", 1599)
    offer(sparkle, "Bathroom cleaning", 499)

    def technician(name, email, phone, prow, skills):
        user = add_user(name, email, "technician", phone)
        row = Technician(user_id=user.id, provider_id=prow.id, skills=skills, status="active")
        db.add(row)
        db.flush()
        return user, row

    _, amit = technician("Amit Shah", "amit@homeserve.test", "9898022201", bright, "Boards, fans, washing machines")
    _, suresh = technician("Suresh Rana", "suresh@homeserve.test", "9898022202", aqua, "Leaks and drain blocks")
    _, imran = technician("Imran Qureshi", "imran@homeserve.test", "9898022203", cool, "Split AC service and gas")
    _, farid = technician("Farid Pathan", "farid@homeserve.test", "9898022204", wood, "Furniture and minor paint")

    priya_user = add_user("Priya Shah", "priya@homeserve.test", "customer", "9898033301")
    rahul_user = add_user("Rahul Mehta", "rahul@homeserve.test", "customer", "9898033302")
    admin = add_user("Ananya Iyer", "admin@homeserve.test", "admin", "9898000001")
    priya_user.created_at = datetime(2026, 8, 12, 10, 0)
    rahul_user.created_at = datetime(2026, 10, 3, 10, 0)
    priya = Customer(user_id=priya_user.id)
    rahul = Customer(user_id=rahul_user.id)
    db.add_all([priya, rahul])
    db.flush()
    db.add(Address(customer_id=priya.id, label="Home", line1="12, Shreeji Apartments, Satellite", city="Ahmedabad", pincode="380015", is_default=True))
    db.add(Address(customer_id=priya.id, label="Parents", line1="44, Premkunj Society, Navrangpura", city="Ahmedabad", pincode="380009", is_default=False))
    db.add(Address(customer_id=rahul.id, label="Home", line1="8, Lakeview, Bopal", city="Ahmedabad", pincode="380058", is_default=True))
    db.add(Favorite(customer_id=priya.id, provider_id=bright.id))
    db.add(Favorite(customer_id=priya.id, provider_id=cool.id))

    def booking(customer, offer_row, prow, service_name, date, time, status, note, tech=None, paid=False, reason=""):
        service = svc[service_name]
        price = offer_row.price
        discount = 0
        taxable = price
        gst = round(taxable * 0.18, 2)
        commission = round(taxable * prow.commission_rate / 100, 2)
        total = round(taxable + gst, 2)
        row = Booking(
            booking_code=f"HS{1000 + offer_row.id + customer.id * 17}{date[-2:]}",
            customer_id=customer.id,
            provider_id=prow.id,
            service_id=service.id,
            provider_service_id=offer_row.id,
            technician_id=tech.id if tech else None,
            address_text="12, Shreeji Apartments, Satellite" if customer.id == priya.id else "8, Lakeview, Bopal",
            city="Ahmedabad",
            scheduled_date=date,
            scheduled_time=time,
            status=status,
            payment_status="Paid" if paid else "Pending",
            problem_note=note,
            subtotal=price,
            discount=discount,
            taxable=taxable,
            gst=gst,
            commission=commission,
            provider_earning=round(taxable - commission, 2),
            total=total,
            slot_key=None if status in ("Cancelled", "Rejected") else f"{prow.id}:{date}:{time}",
            cancel_reason=reason,
            created_at=datetime.strptime(date + " " + time, "%Y-%m-%d %H:%M") - timedelta(days=1),
        )
        if status == "Completed":
            row.completed_at = datetime.strptime(date + " " + time, "%Y-%m-%d %H:%M") + timedelta(hours=2)
            row.arrived_at = datetime.strptime(date + " " + time, "%Y-%m-%d %H:%M") + timedelta(minutes=10)
            row.remarks = "Work finished and the area cleaned up."
        if status == "In Progress":
            row.arrived_at = datetime.strptime(date + " " + time, "%Y-%m-%d %H:%M") + timedelta(minutes=8)
        db.add(row)
        db.flush()
        if tech:
            db.add(BookingAssignment(
                booking_id=row.id,
                technician_id=tech.id,
                status="completed" if status == "Completed" else "arrived" if status == "In Progress" else "assigned",
                remarks=row.remarks or "",
                arrived_at=row.arrived_at,
                completed_at=row.completed_at,
            ))
        if paid:
            pay = Payment(booking_id=row.id, amount=total, commission=commission, status="Paid", method="razorpay_test", order_id=f"order_demo_{row.id}", txn_id=f"pay_demo_{row.id}", created_at=row.created_at)
            db.add(pay)
            db.flush()
            db.add(Invoice(payment_id=pay.id, booking_id=row.id, invoice_number=f"INV-2026-{row.id:04d}", amount=total, issued_on=date))
            db.add(ProviderEarning(provider_id=prow.id, booking_id=row.id, payment_id=pay.id, gross=taxable, commission=commission, net=round(taxable - commission, 2), status="accrued", created_at=row.created_at))
        return row

    done = booking(priya, o_switch, bright, "Switchboard repair", "2026-10-18", "10:00", "Completed", "Kitchen board trips when the microwave starts.", amit, True)
    booking(priya, o_tap, aqua, "Tap repair", "2026-11-08", "11:00", "Confirmed", "Basin tap in the common bathroom keeps dripping.")
    booking(priya, o_ac, cool, "AC service", "2026-11-04", "09:00", "In Progress", "Bedroom AC is running but the air is not cold.", imran)
    booking(rahul, o_fan, bright, "Fan installation", "2026-11-12", "15:00", "Pending", "New ceiling fan, hook is already in the slab.")
    booking(rahul, o_leak, aqua, "Pipe leak", "2026-10-02", "12:00", "Cancelled", "Leak under the kitchen sink.", reason="Found a plumber in the building.")
    booking(rahul, o_gas, cool, "AC gas refill", "2026-10-22", "16:00", "Completed", "Hall AC stopped cooling after the monsoon.", imran, True)
    booking(priya, o_wire, bright, "Wiring inspection", "2026-11-06", "14:00", "Provider Assigned", "Buying the flat next month and want the wiring checked.", amit)

    db.add(Review(booking_id=done.id, customer_id=priya.id, provider_id=bright.id, rating=5, comment="Kiran's team fixed the board and labelled the MCBs. No mess.", provider_response="Thank you Priya. Call us if any switch still feels warm.", is_visible=True))
    gas_booking = db.query(Booking).filter(Booking.service_id == svc["AC gas refill"].id).first()
    db.add(Review(booking_id=gas_booking.id, customer_id=rahul.id, provider_id=cool.id, rating=4, comment="Cooling is back. They were twenty minutes late, but the job was clean.", is_visible=True))

    def refresh(prow):
        rows = db.query(Review).filter(Review.provider_id == prow.id, Review.is_visible.is_(True)).all()
        prow.rating_count = len(rows)
        prow.rating_avg = round(sum(r.rating for r in rows) / len(rows), 1) if rows else 0

    refresh(bright)
    refresh(cool)

    cancelled = db.query(Booking).filter(Booking.status == "Cancelled").first()
    db.add(Complaint(user_id=rahul_user.id, booking_id=cancelled.id, subject="Cancellation fee was unclear", description="I cancelled a day before the visit and want to confirm nothing was charged.", status="Open"))

    db.add_all([
        Coupon(code="WELCOME10", discount_type="percent", value=10, min_amount=0, expires_on="2027-12-31", is_active=True),
        Coupon(code="FLAT150", discount_type="flat", value=150, min_amount=500, expires_on="2027-06-30", is_active=True),
        Coupon(code="MONSOON20", discount_type="percent", value=20, min_amount=800, max_discount=300, expires_on="2027-09-30", is_active=True),
    ])

    def note(user, title, body, ntype="info"):
        db.add(Notification(user_id=user.id, title=title, body=body, ntype=ntype, is_read=False))

    note(priya_user, "Booking confirmed", "AquaFix Plumbing confirmed your tap repair on 8 Nov, 11:00.", "booking")
    note(priya_user, "Technician is on the way", "Imran from CoolBreeze AC has reached your AC service visit.", "booking")
    note(rahul_user, "Request received", "BrightSpark Electric has your fan installation request.", "booking")
    note(admin, "Provider waiting", "SparkleClean submitted documents and needs a verification decision.", "admin")
    note(kiran_user(db), "New request", "Rahul Mehta requested a fan installation on 12 Nov.", "booking")
    db.commit()


def kiran_user(db):
    return db.query(User).filter(User.email == "kiran@homeserve.test").one()
