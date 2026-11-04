def generate_slots(start: str, end: str) -> list[str]:
    sh, sm = [int(part) for part in start.split(":")]
    eh, em = [int(part) for part in end.split(":")]
    cursor = sh * 60 + sm
    stop = eh * 60 + em
    slots = []
    while cursor + 60 <= stop:
        slots.append(f"{cursor // 60:02d}:{cursor % 60:02d}")
        cursor += 60
    return slots


def quote(price: float, coupon: dict | None = None, commission_rate: float = 15.0, gst_rate: float = 18.0) -> dict:
    price = round(float(price), 2)
    discount = 0.0
    if coupon:
        if coupon.get("discount_type") == "percent":
            discount = price * float(coupon.get("value") or 0) / 100
        else:
            discount = float(coupon.get("value") or 0)
        if coupon.get("max_discount"):
            discount = min(discount, float(coupon["max_discount"]))
        min_amount = float(coupon.get("min_amount") or 0)
        if price < min_amount:
            discount = 0.0
    discount = round(min(max(discount, 0.0), price), 2)
    taxable = round(price - discount, 2)
    gst = round(taxable * float(gst_rate) / 100, 2)
    commission = round(taxable * float(commission_rate) / 100, 2)
    total = round(taxable + gst, 2)
    earning = round(taxable - commission, 2)
    return {
        "subtotal": price,
        "discount": discount,
        "taxable": taxable,
        "gst": gst,
        "commission": commission,
        "total": total,
        "earning": earning,
    }
