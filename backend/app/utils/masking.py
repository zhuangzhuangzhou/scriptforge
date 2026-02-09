"""数据脱敏工具

用于敏感数据的脱敏显示
"""


def mask_api_key(api_key: str) -> str:
    """脱敏 API Key

    保留前缀和后缀，中间部分用星号替代

    Args:
        api_key: 原始 API Key

    Returns:
        脱敏后的 API Key

    Examples:
        >>> mask_api_key("sk-xxxxxxxxxxxxxxxx")
        'sk-***...***xxx'
        >>> mask_api_key("short")
        '***'
    """
    if not api_key:
        return "***"

    # 如果 API Key 太短，全部脱敏
    if len(api_key) <= 10:
        return "***"

    # 保留前缀（前3个字符）和后缀（最后3个字符）
    prefix = api_key[:3]
    suffix = api_key[-3:]

    return f"{prefix}***...***{suffix}"


def mask_email(email: str) -> str:
    """脱敏邮箱地址

    保留邮箱前缀的首字符和域名，中间部分用星号替代

    Args:
        email: 原始邮箱地址

    Returns:
        脱敏后的邮箱地址

    Examples:
        >>> mask_email("user@example.com")
        'u***@example.com'
    """
    if not email or '@' not in email:
        return "***"

    parts = email.split('@')
    if len(parts) != 2:
        return "***"

    username, domain = parts

    if len(username) <= 1:
        masked_username = "*"
    else:
        masked_username = username[0] + "***"

    return f"{masked_username}@{domain}"


def mask_phone(phone: str) -> str:
    """脱敏手机号

    保留前3位和后4位，中间部分用星号替代

    Args:
        phone: 原始手机号

    Returns:
        脱敏后的手机号

    Examples:
        >>> mask_phone("13812345678")
        '138****5678'
    """
    if not phone:
        return "***"

    # 如果手机号太短，全部脱敏
    if len(phone) <= 7:
        return "***"

    # 保留前3位和后4位
    prefix = phone[:3]
    suffix = phone[-4:]

    return f"{prefix}****{suffix}"
