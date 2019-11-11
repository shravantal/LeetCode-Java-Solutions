from fastapi import APIRouter, Depends, Body, Path
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
)
from app.commons.api.models import PaymentErrorResponseBody
from app.payout.api.transfer.v1 import models as transfer_models
from app.payout.core.transfer.processor import TransferProcessors
from app.payout.core.transfer.processors.create_transfer import CreateTransferRequest
from app.payout.core.transfer.processors.get_transfer_by_id import (
    GetTransferByIdRequest,
)
from app.payout.core.transfer.processors.submit_transfer import SubmitTransferRequest
from app.payout.models import TransferId
from app.payout.service import create_transfer_processors


api_tags = ["TransfersV1"]
router = APIRouter()


@router.post(
    "/",
    operation_id="CreateTransfer",
    status_code=HTTP_201_CREATED,
    responses={HTTP_400_BAD_REQUEST: {"model": PaymentErrorResponseBody}},
    tags=api_tags,
)
async def create_transfer(
    body: transfer_models.CreateTransfer = Body(
        ..., description="Create a new transfer request body"
    ),
    transfer_processors: TransferProcessors = Depends(create_transfer_processors),
):
    create_transfer_request = CreateTransferRequest(
        payout_account_id=body.payout_account_id,
        transfer_type=body.transfer_type,
        start_time=body.start_time,
        end_time=body.end_time,
        target_id=body.target_id,
        target_type=body.target_type,
        target_business_id=body.target_business_id,
        payout_countries=body.payout_countries,
        created_by_id=body.created_by_id,
    )
    create_transfer_response = await transfer_processors.create_transfer(
        create_transfer_request
    )
    return transfer_models.Transfer(**create_transfer_response.transfer.dict())


@router.post(
    "/{transfer_id}/submit",
    operation_id="SubmitTransfer",
    status_code=HTTP_200_OK,
    responses={HTTP_400_BAD_REQUEST: {"model": PaymentErrorResponseBody}},
    tags=api_tags,
)
async def submit_transfer(
    transfer_id: TransferId = Path(..., description="Transfer ID"),
    body: transfer_models.SubmitTransfer = Body(
        ..., description="Request body for submitting transfer"
    ),
    transfer_processors: TransferProcessors = Depends(create_transfer_processors),
):
    submit_transfer_request = SubmitTransferRequest(
        transfer_id=transfer_id,
        retry=body.retry,
        submitted_by=body.submitted_by,
        statement_descriptor=body.statement_descriptor,
        target_type=body.target_type,
        target_id=body.target_id,
        method=body.method,
    )
    submit_transfer_response = await transfer_processors.submit_transfer(
        submit_transfer_request
    )
    return transfer_models.SubmitTransferResponse(**submit_transfer_response.dict())


@router.get(
    "/{transfer_id}",
    operation_id="GetTransferById",
    status_code=HTTP_200_OK,
    responses={HTTP_404_NOT_FOUND: {"model": PaymentErrorResponseBody}},
    tags=api_tags,
)
async def get_transfer_by_id(
    transfer_id: TransferId = Path(..., description="Transfer ID"),
    transfer_processors: TransferProcessors = Depends(create_transfer_processors),
):
    get_transfer_by_id_request = GetTransferByIdRequest(transfer_id=transfer_id)
    get_transfer_by_id_response = await transfer_processors.get_transfer_by_id(
        get_transfer_by_id_request
    )
    return transfer_models.Transfer(**get_transfer_by_id_response.dict())