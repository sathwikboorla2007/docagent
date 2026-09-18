import re
import copy
from typing import Dict, List, Any

MASKING_PATTERNS = {
    "passport_number": r"[A-Z]\d{7}",
    "aadhaar": r"\d{12}",
    "pan": r"[A-Z]{5}\d{4}[A-Z]",
    "bank_account": r"\d{9,18}",
    "phone": r"\+?\d{10,13}",
    "email": r"[^@]+@[^@]+\.[^@]+",
    "credit_card": r"\d{13,19}",
    "tax_id": r"\d{9}",
    "gstin": r"\d{2}[A-Z]{5}\d{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}"
}

def mask_value(value: str, field_type: str = None) -> str:
    if not value or not isinstance(value, str):
        return value
        
    if field_type == "email" or (field_type is None and "@" in value):
        parts = value.split("@")
        if len(parts) == 2:
            username, domain = parts
            masked_username = username[0] + "****" + username[-1] if len(username) > 2 else "****"
            return f"{masked_username}@{domain}"
            
    if len(value) <= 4:
        return "****"
        
    return "****" + value[-4:]

def detect_pii_fields(data: dict) -> List[str]:
    detected_fields = []
    for key, value in data.items():
        if isinstance(value, str):
            for pattern_name, pattern in MASKING_PATTERNS.items():
                if re.fullmatch(pattern, value) or (pattern_name in key.lower()):
                    detected_fields.append(key)
                    break
        elif isinstance(value, dict):
            detected_fields.extend(detect_pii_fields(value))
    return list(set(detected_fields))

def mask_dict(data: dict, fields_to_mask: List[str] = None) -> dict:
    if not isinstance(data, dict):
        return data
        
    result = copy.deepcopy(data)
    
    if fields_to_mask is None:
        fields_to_mask = detect_pii_fields(result)
        
    for key, value in result.items():
        if isinstance(value, dict):
            result[key] = mask_dict(value, fields_to_mask)
        elif isinstance(value, list):
            result[key] = [mask_dict(item, fields_to_mask) if isinstance(item, dict) else item for item in value]
        elif key in fields_to_mask and isinstance(value, str):
            field_type = "email" if "email" in key.lower() else None
            result[key] = mask_value(value, field_type)
            
    return result

def unmask_value(masked: str, original: str, permission_granted: bool = False) -> str:
    if permission_granted:
        return original
    return masked
