"""
Phase 5.0 — User-Friendly Error Messages

Maps technical API errors to readable Chinese messages with solutions.

Usage:
    from src.config.error_helper import format_provider_error

    error_msg, solution = format_provider_error("DeepSeek", "401 Unauthorized")
    # → ("API Key 无效", "请检查你的 DeepSeek API Key...")
"""

from __future__ import annotations


# ── Provider API URLs ──────────────────────

PROVIDER_API_URLS = {
    "deepseek": "https://platform.deepseek.com/api_keys",
    "openai": "https://platform.openai.com/api-keys",
    "spark": "https://console.xfyun.cn/app/myapp",
}

PROVIDER_HELP_PAGES = {
    "deepseek": "https://platform.deepseek.com",
    "openai": "https://platform.openai.com/docs",
    "spark": "https://www.xfyun.cn/doc/spark/",
}


# ── Error categorisation ───────────────────

def _categorise_error(error: str) -> str:
    """Categorise a raw error string into a known type."""
    error_lower = error.lower() if error else ""

    if any(k in error_lower for k in ("401", "unauthorized", "invalid api key", "incorrect api key")):
        return "auth_invalid"
    if any(k in error_lower for k in ("403", "forbidden", "access denied")):
        return "auth_forbidden"
    if any(k in error_lower for k in ("429", "rate limit", "too many requests")):
        return "rate_limit"
    if any(k in error_lower for k in ("402", "insufficient", "quota", "balance", "billing")):
        return "quota_exhausted"
    if any(k in error_lower for k in ("timeout", "timed out", "connect", "refused", "unreachable")):
        return "network"
    if any(k in error_lower for k in ("500", "502", "503", "server error", "internal")):
        return "server_error"
    if any(k in error_lower for k in ("not found", "model", "404")):
        return "model_not_found"
    return "unknown"


_ERROR_MESSAGES: dict[str, dict[str, str]] = {
    "auth_invalid": {
        "title": "API Key 无效",
        "reason": "你的 API Key 被服务端拒绝。可能原因：Key 已过期、输错、或在服务商后台被撤销。",
        "solution": (
            "1. 检查 API Key 是否复制完整（无多余空格）\n"
            "2. 登录服务商后台确认 Key 仍在有效期内\n"
            "3. 如已过期，创建新的 API Key 并重新保存"
        ),
    },
    "auth_forbidden": {
        "title": "访问被拒绝",
        "reason": "你的账号没有访问此模型/接口的权限，或 API Key 缺少必要权限。",
        "solution": (
            "1. 检查服务商后台，确认你的账号已开通该模型的访问权限\n"
            "2. 部分模型需要单独申请（如 OpenAI GPT-4）\n"
            "3. 确认 API Key 的作用域包含模型调用权限"
        ),
    },
    "rate_limit": {
        "title": "请求频率过高",
        "reason": "短时间内发送了过多请求，触发了服务商的速率限制。",
        "solution": (
            "1. 稍等片刻后重试\n"
            "2. 如果频繁遇到此问题，考虑升级服务套餐\n"
            "3. 检查是否有其他应用在使用同一个 API Key"
        ),
    },
    "quota_exhausted": {
        "title": "额度已用尽",
        "reason": "你的 API 账户余额不足或免费额度已用完。",
        "solution": (
            "1. 登录服务商后台查看余额\n"
            "2. 充值或等待下个计费周期\n"
            "3. 可以切换到 Mock 模式继续使用 A3"
        ),
    },
    "network": {
        "title": "网络连接失败",
        "reason": "无法连接到服务商服务器。可能由于网络问题、防火墙、或代理配置。",
        "solution": (
            "1. 检查网络连接是否正常\n"
            "2. 如使用代理，确认代理已正确配置\n"
            "3. 检查服务商服务状态页面确认无宕机\n"
            "4. 可以切换到 Mock 模式继续使用 A3"
        ),
    },
    "server_error": {
        "title": "服务商服务器异常",
        "reason": "服务商（DeepSeek/OpenAI/Spark）服务器返回了错误。这是临时性问题。",
        "solution": (
            "1. 稍等 1-2 分钟后重试\n"
            "2. 检查服务商状态页面\n"
            "3. 可以切换到 Mock 模式，稍后再切换回来"
        ),
    },
    "model_not_found": {
        "title": "模型不可用",
        "reason": "你选择的模型名称无效或已下线。",
        "solution": (
            "1. 进入 ⚙️ AI模型设置，选择其他可用模型\n"
            "2. 确认服务商当前支持的模型列表\n"
            "3. 检查模型名称拼写是否正确（区分大小写）"
        ),
    },
    "unknown": {
        "title": "连接失败",
        "reason": "发生了未预期的错误。",
        "solution": (
            "1. 检查 API Key 是否正确\n"
            "2. 检查网络连接\n"
            "3. 尝试重新输入 API Key 并保存\n"
            "4. 如问题持续，切换到 Mock 模式"
        ),
    },
}


def format_provider_error(provider: str, raw_error: str) -> dict:
    """
    Format a raw provider error into a user-friendly message.

    Returns a dict with:
        provider: provider name
        api_url: URL where user can get/manage API keys
        title: short error title in Chinese
        reason: explanation of what went wrong
        solution: actionable steps
        raw: original error message (for debugging)

    Args:
        provider: Provider name (deepseek, openai, spark).
        raw_error: Raw error message from the provider.
    """
    category = _categorise_error(raw_error)
    template = _ERROR_MESSAGES.get(category, _ERROR_MESSAGES["unknown"])

    return {
        "provider": provider,
        "api_url": PROVIDER_API_URLS.get(provider, ""),
        "help_url": PROVIDER_HELP_PAGES.get(provider, ""),
        "title": template["title"],
        "reason": template["reason"],
        "solution": template["solution"],
        "raw": raw_error,
    }
