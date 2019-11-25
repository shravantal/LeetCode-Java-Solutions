import os

from apscheduler.triggers.cron import CronTrigger

from app.commons.config.app_config import (
    AppConfig,
    ApiStatsDConfig,
    DBConfig,
    SentryConfig,
)
from app.commons.config.secrets import Secret


def create_app_config() -> AppConfig:
    """
    Create AppConfig for local environment
    """
    # allow db endpoint (host:port) be overridden in docker compose
    dsj_db_endpoint: str = os.getenv("DSJ_DB_ENDPOINT", "localhost:5435")

    sentry_config = None
    if os.getenv("SENTRY_DSN", None):
        sentry_config = SentryConfig(
            dsn=Secret.from_env(name="sentry_dsn", env="SENTRY_DSN"),
            environment="local",
            release=f"payment-service@release-{os.getenv('RELEASE_TAG', 'unknown')}",
        )

    return AppConfig(
        ENVIRONMENT="local",
        DEBUG=False,  # Set this to True for debugging
        REMOTE_SECRET_ENABLED=False,
        API_STATSD_CONFIG=ApiStatsDConfig(
            TAGS={"service_name": "payment-service", "cluster": "local"}
        ),
        IDENTITY_SERVICE_HTTP_ENDPOINT="https://identity-service.doorcrawl.com",
        IDENTITY_SERVICE_GRPC_ENDPOINT="identity.doorcrawl-int.com:50051",
        PAYIN_SERVICE_ID=1631011374003906560,
        PAYOUT_SERVICE_ID=1631011374003906560,
        LEDGER_SERVICE_ID=1631011374003906560,
        PURCHASECARD_SERVICE_ID=1631011374003906560,
        TEST_SECRET=Secret(name="test_secret", value="hello_world_secret"),
        PAYIN_MAINDB_MASTER_URL=Secret(
            name="payin_maindb_url",
            value=f"postgresql://payin_user@{dsj_db_endpoint}/maindb_dev",
        ),
        PAYIN_MAINDB_REPLICA_URL=Secret(
            name="payin_maindb_url",
            value=f"postgresql://payin_user@{dsj_db_endpoint}/maindb_dev",
        ),
        PAYIN_PAYMENTDB_MASTER_URL=Secret(
            name="payin_paymentdb_url",
            value=f"postgresql://payin_user@{dsj_db_endpoint}/paymentdb_dev",
        ),
        PAYIN_PAYMENTDB_REPLICA_URL=Secret(
            name="payin_paymentdb_url",
            value=f"postgresql://payin_user@{dsj_db_endpoint}/paymentdb_dev",
        ),
        PAYOUT_MAINDB_MASTER_URL=Secret(
            name="payout_maindb_url",
            value=f"postgresql://payout_user@{dsj_db_endpoint}/maindb_dev",
        ),
        PAYOUT_MAINDB_REPLICA_URL=Secret(
            name="payout_maindb_url",
            value=f"postgresql://payout_user@{dsj_db_endpoint}/maindb_dev",
        ),
        PAYOUT_BANKDB_MASTER_URL=Secret(
            name="payout_bankdb_url",
            value=f"postgresql://payout_user@{dsj_db_endpoint}/bankdb_dev",
        ),
        PAYOUT_BANKDB_REPLICA_URL=Secret(
            name="payout_bankdb_url",
            value=f"postgresql://payout_user@{dsj_db_endpoint}/bankdb_dev",
        ),
        LEDGER_MAINDB_MASTER_URL=Secret(
            name="ledger_maindb_url",
            value=f"postgresql://ledger_user@{dsj_db_endpoint}/maindb_dev",
        ),
        LEDGER_MAINDB_REPLICA_URL=Secret(
            name="ledger_maindb_url",
            value=f"postgresql://ledger_user@{dsj_db_endpoint}/maindb_dev",
        ),
        LEDGER_PAYMENTDB_MASTER_URL=Secret(
            name="ledger_paymentdb_url",
            value=f"postgresql://ledger_user@{dsj_db_endpoint}/paymentdb_dev",
        ),
        LEDGER_PAYMENTDB_REPLICA_URL=Secret(
            name="ledger_paymentdb_url",
            value=f"postgresql://ledger_user@{dsj_db_endpoint}/paymentdb_dev",
        ),
        PURCHASECARD_MAINDB_MASTER_URL=Secret(
            name="purchasecard_maindb_url",
            value=f"postgresql://payout_user@{dsj_db_endpoint}/maindb_dev",
        ),
        PURCHASECARD_MAINDB_REPLICA_URL=Secret(
            name="purchasecard_maindb_url",
            value=f"postgresql://payout_user@{dsj_db_endpoint}/maindb_dev",
        ),
        DEFAULT_DB_CONFIG=DBConfig(
            replica_pool_max_size=1, master_pool_max_size=5, debug=True
        ),
        AVAILABLE_MAINDB_REPLICAS=["maindb_dev"],
        STRIPE_US_SECRET_KEY=Secret(
            name="stripe_us_secret_key", value="sk_test_NH2ez5KKOx5qPWcNcFhjdr1R"
        ),
        STRIPE_US_PUBLIC_KEY=Secret(
            name="stripe_us_public_key", value="pk_test_NH2ez5KKOx5qPWcNcFhjdr1R"
        ),
        STRIPE_CA_SECRET_KEY=Secret(
            name="stripe_ca_secret_key", value="sk_test_DjN82k53PAi4mKVlkeOXUsGh"
        ),
        STRIPE_CA_PUBLIC_KEY=Secret(
            name="stripe_ca_public_key", value="pk_test_6BIBosD7fUMQKx5ehGg5L6pz"
        ),
        STRIPE_AU_SECRET_KEY=Secret(
            name="stripe_au_secret_key",
            value="sk_test_kwb7Pky1rEyIYbWhIBnHbEG500GIVp7eeO",
        ),
        STRIPE_AU_PUBLIC_KEY=Secret(
            name="stripe_au_public_key",
            value="pk_test_dJ998ZEOQNHLDCAQG37EKbId00c9TVHvH7",
        ),
        DSJ_API_BASE_URL="https://api.doorcrawl.com",
        DSJ_API_USER_EMAIL=Secret(name="dsj_api_user_email", value=""),
        DSJ_API_USER_PASSWORD=Secret(name="dsj_api_user_password", value=""),
        DSJ_API_JWT_TOKEN_TTL=1800,
        SENTRY_CONFIG=sentry_config,
        # don't need frequent monitoring for dev
        MONITOR_INTERVAL_EVENT_LOOP_LATENCY=10,
        MONITOR_INTERVAL_RESOURCE_JOB_POOL=10,
        # Payin
        CAPTURE_CRON_TRIGGER=CronTrigger(minute="*/2"),
        MARQETA_BASE_URL="https://doordash-dev.marqeta.com/v3/",
        MARQETA_USERNAME=Secret(
            name="marqeta_username", value="doordash_sandbox_api_consumer"
        ),
        MARQETA_PASSWORD=Secret(name="marqeta_password", value="sTZqUU5SAvvNErqY"),
        MARQETA_JIT_USERNAME=Secret(name="marqeta_jit_username", value=""),
        MARQETA_JIT_PASSWORD=Secret(name="marqeta_jit_password", value=""),
        MARQETA_PROGRAM_FUND_TOKEN=Secret(
            name="marqeta_program_fund_token",
            value="a6e2bbe7-4f28-43b4-980d-6416f35fe33e",
        ),
        MARQETA_CARD_TOKEN_PREFIX_CUTOVER_ID=Secret(
            name="marqeta_card_token_prefix_cutover_id", value="73617"
        ),
        REDIS_INSTANCES=[("localhost", 6380)],
    )
