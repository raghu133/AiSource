def make_barcode(item: dict, qty_or_weight: float, settings: dict) -> str:
    qr = settings["qr"]
    prefix = str(qr["prefix_value"])
    code_len = int(qr["code_len"])
    price_len = int(qr["price_len"])
    qty_len = int(qr["qty_len"])

    item_code = str(item.get("Code", "0")).zfill(code_len)[-code_len:]
    retail_price = float(item.get("Price", 0.0))
    uom = str(item.get("UOM", "KG")).upper()

    if uom == "PCS":
        qty = max(1.0, float(qty_or_weight))
        total_amount = retail_price * qty
        amt_int = int(round(total_amount * (10 ** (price_len - 2))))
        amt_str = str(amt_int).zfill(price_len)[-price_len:]

        qty_int = int(round(qty * (10 ** (qty_len - 1))))
        qty_str = str(qty_int).zfill(qty_len)[-qty_len:]
        return f"{prefix}{item_code}{amt_str}{qty_str}0"

    weight_val = max(0.0, float(qty_or_weight))
    total_amount = retail_price * weight_val
    amt_int = int(round(total_amount * (10 ** (price_len - 2))))
    amt_str = str(amt_int).zfill(price_len)[-price_len:]

    # wt_int = int(round(weight_val * (10 ** (qty_len - 1))))
    # wt_str = str(wt_int).zfill(qty_len)[-qty_len:]
    wt_int = int(round(weight_val * 1000))
    wt_str = str(wt_int).zfill(qty_len)[-qty_len:]
    return f"{prefix}{item_code}{amt_str}{wt_str}0"
