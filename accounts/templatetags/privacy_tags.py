from django import template


register = template.Library()


@register.filter
def mask_phone(value):
    text = "".join(ch for ch in str(value or "") if ch.isdigit())
    if len(text) < 4:
        return "-"
    return f"{text[:2]}** *** {text[-4:]}"


@register.filter
def mask_email(value):
    text = str(value or "")
    if "@" not in text:
        return "-"
    name, domain = text.split("@", 1)
    visible = name[:2] if len(name) > 1 else name[:1]
    return f"{visible}***@{domain}"


@register.filter
def mask_address(value):
    text = str(value or "").strip()
    if not text:
        return "-"
    parts = [part.strip() for part in text.split(",") if part.strip()]
    if parts:
        return parts[-1]
    words = text.split()
    return " ".join(words[-3:]) if len(words) > 3 else text
