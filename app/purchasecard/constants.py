from enum import Enum


class MarqetaResponseCodes(str, Enum):
    SUCCESS = "0000"
    ACCOUNT_LOAD_FAILED = "1842"
    ECOMMERCE_TRANSACTION_NOT_ALLOWED = "1847"
    AUTH_RESTRICTION = "1832"


class TransactionWebhookProcessType(str, Enum):
    SUCCESS = "success"
    TIMEOUT = "timeout"
    LEGIT_JIT_FAILURE = "legit_jit_failure"
    TERMINAL_FAILURE = "terminal_failure"
    OTHER = "other"


# Seconds to wait for time_out confirmation webhook
MARQETA_WEBHOOK_TIMEOUT = 30

# the extra buffer amount funded onto a red card for a delivery
BUFFER_MULTIPLIER_FOR_DELIVERY = 1.35