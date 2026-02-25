"""LLM/API error types with user-facing messages. Used to abort runs and return clear messages."""


class LLMError(Exception):
    """Base for LLM-related errors. .message is the user-facing text."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NoModelProvidedError(LLMError):
    """No model configured (missing env / no provider available)."""

    USER_MESSAGE = "No model specified. Please provide a valid model."

    def __init__(self):
        super().__init__(self.USER_MESSAGE)


class InvalidModelError(LLMError):
    """The requested model does not exist or is not available."""

    USER_MESSAGE = "The requested model does not exist. Please check the model name."

    def __init__(self):
        super().__init__(self.USER_MESSAGE)


class APIQuotaOrFailureError(LLMError):
    """Quota limit or other API failure."""

    USER_MESSAGE = "API request failed due to quota limits or temporary issues. Please try again later."

    def __init__(self):
        super().__init__(self.USER_MESSAGE)


def user_message_for_exception(e: BaseException) -> str | None:
    """Return user-facing message if e is a known LLM error; else None."""
    if isinstance(e, LLMError):
        return e.message
    return None


def is_quota_or_api_failure(e: BaseException) -> bool:
    """True if exception indicates quota limit or generic API failure."""
    msg = (str(e) or "").lower()
    if "429" in str(e) or "rate limit" in msg or "quota" in msg:
        return True
    if "503" in str(e) or "500" in str(e) or "timeout" in msg:
        return True
    if "api" in msg and ("fail" in msg or "error" in msg):
        return True
    return False


def is_invalid_model_error(e: BaseException) -> bool:
    """True if exception indicates model not found / invalid model."""
    msg = (str(e) or "").lower()
    if "404" in str(e) or "not found" in msg:
        return True
    if "model" in msg and ("does not exist" in msg or "invalid" in msg or "unknown" in msg):
        return True
    if "no such model" in msg or "model not found" in msg:
        return True
    return False


def normalize_llm_exception(e: BaseException) -> LLMError:
    """Convert a generic exception from LLM invoke into a typed LLMError with user message."""
    if isinstance(e, LLMError):
        return e
    if is_invalid_model_error(e):
        return InvalidModelError()
    if is_quota_or_api_failure(e):
        return APIQuotaOrFailureError()
    return APIQuotaOrFailureError()
