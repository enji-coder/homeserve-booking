from app.billing import generate_slots, quote


def test_percent_coupon_and_commission():
    priced = quote(1000, {"discount_type": "percent", "value": 10, "min_amount": 0, "max_discount": None})
    assert priced["discount"] == 100
    assert priced["taxable"] == 900
    assert priced["gst"] == 162
    assert priced["commission"] == 135
    assert priced["total"] == 1062
    assert priced["earning"] == 765


def test_flat_coupon_respects_minimum():
    priced = quote(400, {"discount_type": "flat", "value": 150, "min_amount": 500, "max_discount": None})
    assert priced["discount"] == 0
    assert priced["total"] == 472


def test_percent_coupon_respects_cap():
    priced = quote(2000, {"discount_type": "percent", "value": 20, "min_amount": 800, "max_discount": 300}, commission_rate=10)
    assert priced["discount"] == 300
    assert priced["taxable"] == 1700
    assert priced["commission"] == 170


def test_slots_are_hourly():
    assert generate_slots("09:00", "12:00") == ["09:00", "10:00", "11:00"]
    assert generate_slots("17:30", "18:00") == []
