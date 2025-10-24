import secrets
import string


def generate_referral_code() -> str:
    """
    Unique referal kod yaratish (masalan: REF8X4KP9)
    """
    chars = string.ascii_uppercase + string.digits
    code = ''.join(secrets.choice(chars) for _ in range(6))
    return f"OXUDOCX_{code}"


def get_referral_link(bot_username: str, referral_code: str) -> str:
    """
    Referal havola yaratish
    """
    return f"https://t.me/{bot_username}?start={referral_code}"


def extract_referral_code(text: str) -> str | None:
    """
    /start REF123456 dan REF123456 ni ajratib olish
    """
    if not text:
        return None
    
    parts = text.split()
    if len(parts) == 2 and parts[1].startswith("OXUDOCX"):
        return parts[1]
    
    return None
