import inspect
from datetime import datetime
from typing import Optional, List

from app.payout.core.transfer.tasks.base_task import BaseTask, normalize_task_arguments
from app.payout.models import PayoutTask, TransferType, PayoutCountry


class CreateTransferTask(BaseTask):
    def __init__(
        self,
        payout_account_id: int,
        end_time: datetime,
        start_time: Optional[datetime],
        payout_countries: Optional[List[PayoutCountry]],
        created_by_id: Optional[int],
        transfer_type: TransferType = TransferType.SCHEDULED,
    ):
        self.topic_name = "payment_payout"
        self.task_type = PayoutTask.CREATE_TRANSFER
        auto_retry_for: List[Exception] = []
        max_retries: int = 0
        fn_args: list = []
        super().__init__(
            self.topic_name,
            self.task_type,
            auto_retry_for,
            max_retries,
            fn_args,
            normalize_task_arguments(inspect.currentframe()),
        )