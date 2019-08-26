from copy import deepcopy
import pytest
from unittest.mock import MagicMock
from app.commons.providers.stripe.stripe_models import CreatePaymentIntent
from app.payin.core.cart_payment.types import IntentStatus, ChargeStatus
from app.payin.tests.utils import (
    generate_payment_intent,
    generate_pgp_payment_intent,
    generate_cart_payment,
    generate_payment_charge,
    generate_pgp_payment_charge,
    FunctionMock,
)
from app.payin.core.exceptions import (
    PaymentIntentRefundError,
    CartPaymentCreateError,
    PaymentChargeRefundError,
    PaymentIntentCancelError,
    PaymentIntentCaptureError,
    PayinErrorCode,
)
import uuid


class TestCartPaymentInterface:
    """
    Test CartPaymentInterface class functions.
    """

    @pytest.mark.asyncio
    async def test_find_existing_no_matches(self, cart_payment_interface):
        mock_intent_search = FunctionMock(return_value=None)
        cart_payment_interface.payment_repo.get_payment_intent_for_idempotency_key = (
            mock_intent_search
        )
        result = await cart_payment_interface._find_existing(
            payer_id="payer_id", idempotency_key="idempotency_key"
        )
        assert result == (None, None)

    @pytest.mark.asyncio
    async def test_find_existing_with_matches(self, cart_payment_interface):
        # Mock function to find intent
        intent = generate_payment_intent()
        cart_payment_interface.payment_repo.get_payment_intent_for_idempotency_key = FunctionMock(
            return_value=intent
        )

        # Mock function to find cart payment
        cart_payment = MagicMock()
        cart_payment_interface.payment_repo.get_cart_payment_by_id = FunctionMock(
            return_value=cart_payment
        )

        result = await cart_payment_interface._find_existing(
            payer_id="payer_id", idempotency_key="idempotency_key"
        )
        assert result == (cart_payment, intent)

    @pytest.mark.asyncio
    async def test_get_cart_payment(self, cart_payment_interface):
        cart_payment = generate_cart_payment()
        cart_payment_interface.payment_repo.get_cart_payment_by_id = FunctionMock(
            return_value=cart_payment
        )

        result = await cart_payment_interface._get_cart_payment(cart_payment.id)
        assert result == cart_payment

    @pytest.mark.asyncio
    async def test_get_cart_payment_no_match(self, cart_payment_interface):
        cart_payment_interface.payment_repo.get_cart_payment_by_id = FunctionMock(
            return_value=None
        )

        result = await cart_payment_interface._get_cart_payment(uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_get_most_recent_pgp_payment_intent(self, cart_payment_interface):
        first_pgp_intent = generate_pgp_payment_intent()
        second_pgp_intent = generate_pgp_payment_intent()

        cart_payment_interface.payment_repo.find_pgp_payment_intents = FunctionMock(
            return_value=[first_pgp_intent, second_pgp_intent]
        )

        result = await cart_payment_interface._get_most_recent_pgp_payment_intent(
            MagicMock()
        )
        assert result == second_pgp_intent

    @pytest.mark.asyncio
    async def test_get_most_recent_intent(self, cart_payment_interface):
        first_intent = generate_payment_intent()
        second_intent = generate_payment_intent()

        result = cart_payment_interface._get_most_recent_intent(
            [first_intent, second_intent]
        )
        assert result == second_intent

    def test_transform_method_for_stripe(self, cart_payment_interface):
        assert (
            cart_payment_interface._transform_method_for_stripe("auto") == "automatic"
        )
        assert cart_payment_interface._transform_method_for_stripe("manual") == "manual"

    def test_get_provider_capture_method(self, cart_payment_interface):
        intent = generate_payment_intent(capture_method="manual")
        result = cart_payment_interface._get_provider_capture_method(intent)
        assert result == CreatePaymentIntent.CaptureMethod.MANUAL

        intent = generate_payment_intent(capture_method="auto")
        result = cart_payment_interface._get_provider_capture_method(intent)
        assert result == CreatePaymentIntent.CaptureMethod.AUTOMATIC

    def test_get_provider_confirmation_method(self, cart_payment_interface):
        intent = generate_payment_intent(confirmation_method="manual")
        result = cart_payment_interface._get_provider_confirmation_method(intent)
        assert result == CreatePaymentIntent.ConfirmationMethod.MANUAL

        intent = generate_payment_intent(confirmation_method="auto")
        result = cart_payment_interface._get_provider_confirmation_method(intent)
        assert result == CreatePaymentIntent.ConfirmationMethod.AUTOMATIC

    def test_get_provider_future_usage(self, cart_payment_interface):
        intent = generate_payment_intent(capture_method="manual")
        result = cart_payment_interface._get_provider_future_usage(intent)
        assert result == CreatePaymentIntent.SetupFutureUsage.OFF_SESSION

        intent = generate_payment_intent(capture_method="auto")
        result = cart_payment_interface._get_provider_future_usage(intent)
        assert result == CreatePaymentIntent.SetupFutureUsage.ON_SESSION

    def test_intent_submit_status_evaluation(self, cart_payment_interface):
        intent = generate_payment_intent(status="init")
        assert cart_payment_interface._is_payment_intent_submitted(intent) is False

        intent = generate_payment_intent(status="processing")
        assert cart_payment_interface._is_payment_intent_submitted(intent) is True

    def test_intent_can_be_cancelled(self, cart_payment_interface):
        intent = generate_payment_intent(status=IntentStatus.FAILED)
        assert cart_payment_interface._can_payment_intent_be_cancelled(intent) is False

        intent = generate_payment_intent(status=IntentStatus.SUCCEEDED)
        assert cart_payment_interface._can_payment_intent_be_cancelled(intent) is False

        intent = generate_payment_intent(status=IntentStatus.REQUIRES_CAPTURE)
        assert cart_payment_interface._can_payment_intent_be_cancelled(intent) is True

    def test_can_payment_intent_be_refunded(self, cart_payment_interface):
        intent = generate_payment_intent(status=IntentStatus.FAILED)
        assert cart_payment_interface._can_payment_intent_be_refunded(intent) is False

        intent = generate_payment_intent(status=IntentStatus.SUCCEEDED)
        assert cart_payment_interface._can_payment_intent_be_refunded(intent) is True

        intent = generate_payment_intent(status=IntentStatus.REQUIRES_CAPTURE)
        assert cart_payment_interface._can_payment_intent_be_refunded(intent) is False

    def test_can_pgp_payment_intent_be_refunded(self, cart_payment_interface):
        pgp_intent = generate_pgp_payment_intent(status=IntentStatus.FAILED)
        assert (
            cart_payment_interface._can_pgp_payment_intent_be_refunded(pgp_intent)
            is False
        )

        pgp_intent = generate_pgp_payment_intent(status=IntentStatus.SUCCEEDED)
        assert (
            cart_payment_interface._can_pgp_payment_intent_be_refunded(pgp_intent)
            is True
        )

        pgp_intent = generate_pgp_payment_intent(status=IntentStatus.REQUIRES_CAPTURE)
        assert (
            cart_payment_interface._can_pgp_payment_intent_be_refunded(pgp_intent)
            is False
        )

    def test_has_capture_been_attempted(self, cart_payment_interface):
        intent = generate_payment_intent(status="init")
        assert cart_payment_interface._has_capture_been_attempted(intent) is False

        intent = generate_payment_intent(status="requires_capture")
        assert cart_payment_interface._has_capture_been_attempted(intent) is False

        intent = generate_payment_intent(status="succeeded")
        assert cart_payment_interface._has_capture_been_attempted(intent) is True

        intent = generate_payment_intent(status="failed")
        assert cart_payment_interface._has_capture_been_attempted(intent) is True

    def test_get_intent_status_from_provider_status(self, cart_payment_interface):
        intent_status = cart_payment_interface._get_intent_status_from_provider_status(
            "requires_capture"
        )
        assert intent_status == IntentStatus.REQUIRES_CAPTURE

        with pytest.raises(ValueError):
            cart_payment_interface._get_intent_status_from_provider_status(
                "coffee_beans"
            )

    def test_pgp_intent_status_evaluation(self, cart_payment_interface):
        intent = generate_pgp_payment_intent(status="init")
        assert cart_payment_interface._is_pgp_payment_intent_submitted(intent) is False

        intent = generate_pgp_payment_intent(status="processing")
        assert cart_payment_interface._is_pgp_payment_intent_submitted(intent) is True

    def test_get_cart_payment_submission_pgp_intent(self, cart_payment_interface):
        first_intent = generate_pgp_payment_intent(status="init")
        second_intent = generate_pgp_payment_intent(status="init")
        pgp_intents = [first_intent, second_intent]
        selected_intent = cart_payment_interface._get_cart_payment_submission_pgp_intent(
            pgp_intents
        )
        assert selected_intent == first_intent

    def test_filter_for_payment_intent_by_status(self, cart_payment_interface):
        succeeded_intent = generate_payment_intent(status="succeeded")
        intents = [
            generate_payment_intent(status="init"),
            succeeded_intent,
            generate_payment_intent(status="init"),
        ]
        result = cart_payment_interface._filter_payment_intents_by_state(
            intents, IntentStatus.SUCCEEDED
        )
        assert result == [succeeded_intent]

        result = cart_payment_interface._filter_payment_intents_by_state(
            intents, IntentStatus.INIT
        )
        assert result == [intents[0], intents[2]]

        result = cart_payment_interface._filter_payment_intents_by_state(
            intents, IntentStatus.FAILED
        )
        assert result == []

    def test_filter_for_payment_intent_by_idempotency_key(self, cart_payment_interface):
        target_intent = generate_payment_intent()
        intents = [generate_payment_intent(), target_intent, generate_payment_intent()]
        result = cart_payment_interface._filter_payment_intents_by_idempotency_key(
            intents, target_intent.idempotency_key
        )
        assert result == target_intent

        result = cart_payment_interface._filter_payment_intents_by_idempotency_key(
            intents, f"{target_intent.idempotency_key}-fake"
        )
        assert result is None

    def test_filter_payment_intents_by_function(self, cart_payment_interface):
        target_payment_intent = generate_payment_intent()
        second_intent = generate_payment_intent()

        def filter_function(payment_intent):
            return payment_intent.id == target_payment_intent.id

        result = cart_payment_interface._filter_payment_intents_by_function(
            [target_payment_intent, second_intent], filter_function
        )
        assert result == [target_payment_intent]

    def test_get_charge_status_from_intent_status(self, cart_payment_interface):
        charge_status = cart_payment_interface._get_charge_status_from_intent_status(
            IntentStatus.SUCCEEDED
        )
        assert charge_status == ChargeStatus.SUCCEEDED

        charge_status = cart_payment_interface._get_charge_status_from_intent_status(
            IntentStatus.FAILED
        )
        assert charge_status == ChargeStatus.FAILED

        charge_status = cart_payment_interface._get_charge_status_from_intent_status(
            IntentStatus.REQUIRES_CAPTURE
        )
        assert charge_status == ChargeStatus.REQUIRES_CAPTURE

        charge_status = cart_payment_interface._get_charge_status_from_intent_status(
            IntentStatus.CANCELLED
        )
        assert charge_status == ChargeStatus.CANCELLED

        with pytest.raises(ValueError):
            cart_payment_interface._get_charge_status_from_intent_status(
                IntentStatus.INIT
            )

    def test_is_amount_adjusted_higher(self, cart_payment_interface):
        cart_payment = generate_cart_payment()
        cart_payment.amount = 500

        assert (
            cart_payment_interface._is_amount_adjusted_higher(cart_payment, 400)
            is False
        )
        assert (
            cart_payment_interface._is_amount_adjusted_higher(cart_payment, 500)
            is False
        )
        assert (
            cart_payment_interface._is_amount_adjusted_higher(cart_payment, 600) is True
        )

    def test_is_amount_adjusted_lower(self, cart_payment_interface):
        cart_payment = generate_cart_payment()
        cart_payment.amount = 500

        assert (
            cart_payment_interface._is_amount_adjusted_lower(cart_payment, 400) is True
        )
        assert (
            cart_payment_interface._is_amount_adjusted_lower(cart_payment, 500) is False
        )
        assert (
            cart_payment_interface._is_amount_adjusted_lower(cart_payment, 600) is False
        )

    @pytest.mark.asyncio
    async def test_submit_payment_to_provider(self, cart_payment_interface):
        intent = generate_payment_intent()
        pgp_intent = generate_pgp_payment_intent()
        result = await cart_payment_interface._submit_payment_to_provider(
            payment_intent=intent,
            pgp_payment_intent=pgp_intent,
            provider_payment_resource_id="payment_resource_id",
            provider_customer_resource_id="customer_resource_id",
        )

        # TODO once repo layer is refactored, assert returned (updated) objects instead
        assert result is None

    @pytest.mark.asyncio
    async def test_create_provider_payment(self, cart_payment_interface):
        intent = generate_payment_intent(status="requires_capture")
        pgp_intent = generate_pgp_payment_intent(status="requires_capture")
        response = await cart_payment_interface._create_provider_payment(
            intent, pgp_intent, "payment_resource_id", "customer_resource_id"
        )
        assert response

    @pytest.mark.asyncio
    async def test_create_provider_payment_error(self, cart_payment_interface):
        mocked_stripe_function = FunctionMock()
        mocked_stripe_function.side_effect = Exception()
        cart_payment_interface.app_context.stripe.create_payment_intent = (
            mocked_stripe_function
        )

        intent = generate_payment_intent(status="requires_capture")
        pgp_intent = generate_pgp_payment_intent(status="requires_capture")

        with pytest.raises(CartPaymentCreateError) as payment_error:
            await cart_payment_interface._create_provider_payment(
                intent, pgp_intent, "payment_resource_id", "customer_resource_id"
            )

        assert (
            payment_error.value.error_code
            == PayinErrorCode.PAYMENT_INTENT_CREATE_STRIPE_ERROR
        )

    @pytest.mark.asyncio
    async def test_cancel_provider_payment_charge(self, cart_payment_interface):
        intent = generate_payment_intent(status="requires_capture")
        pgp_intent = generate_pgp_payment_intent(status="requires_capture")
        response = await cart_payment_interface._cancel_provider_payment_charge(
            intent, pgp_intent, "abandoned"
        )
        assert response

    @pytest.mark.asyncio
    async def test_cancel_provider_payment_charge_error(self, cart_payment_interface):
        mocked_stripe_function = FunctionMock()
        mocked_stripe_function.side_effect = Exception()
        cart_payment_interface.app_context.stripe.cancel_payment_intent = (
            mocked_stripe_function
        )

        intent = generate_payment_intent(status="requires_capture")
        pgp_intent = generate_pgp_payment_intent(status="requires_capture")

        with pytest.raises(PaymentChargeRefundError) as payment_error:
            await cart_payment_interface._cancel_provider_payment_charge(
                intent, pgp_intent, "abandoned"
            )

        assert (
            payment_error.value.error_code
            == PayinErrorCode.PAYMENT_INTENT_ADJUST_REFUND_ERROR
        )

    @pytest.mark.asyncio
    async def test_refund_provider_payment(self, cart_payment_interface):
        intent = generate_payment_intent(status="succeeded")
        pgp_intent = generate_pgp_payment_intent(status="succeeded")
        response = await cart_payment_interface._refund_provider_payment(
            payment_intent=intent,
            pgp_payment_intent=pgp_intent,
            reason="abandoned",
            refund_amount=500,
        )
        assert response

    @pytest.mark.asyncio
    async def test_refund_provider_payment_error(self, cart_payment_interface):
        mocked_stripe_function = FunctionMock()
        mocked_stripe_function.side_effect = Exception()
        cart_payment_interface.app_context.stripe.refund_charge = mocked_stripe_function

        intent = generate_payment_intent(status="succeeded")
        pgp_intent = generate_pgp_payment_intent(status="succeeded")

        with pytest.raises(PaymentIntentCancelError) as payment_error:
            await cart_payment_interface._refund_provider_payment(
                payment_intent=intent,
                pgp_payment_intent=pgp_intent,
                reason="abandoned",
                refund_amount=500,
            )

        assert (
            payment_error.value.error_code
            == PayinErrorCode.PAYMENT_INTENT_ADJUST_REFUND_ERROR
        )

    @pytest.mark.asyncio
    async def test_capture_payment_with_provider(self, cart_payment_interface):
        intent = generate_payment_intent(status="requires_capture")
        pgp_intent = generate_pgp_payment_intent(status="requires_capture")
        response = await cart_payment_interface._capture_payment_with_provider(
            intent, pgp_intent
        )
        assert response

    @pytest.mark.asyncio
    async def test_capture_payment_with_provider_error(self, cart_payment_interface):
        mocked_stripe_function = FunctionMock()
        mocked_stripe_function.side_effect = Exception()
        cart_payment_interface.app_context.stripe.capture_payment_intent = (
            mocked_stripe_function
        )

        intent = generate_payment_intent(status="requires_capture")
        pgp_intent = generate_pgp_payment_intent(status="requires_capture")

        with pytest.raises(PaymentIntentCaptureError) as payment_error:
            await cart_payment_interface._capture_payment_with_provider(
                intent, pgp_intent
            )

        assert (
            payment_error.value.error_code
            == PayinErrorCode.PAYMENT_INTENT_CAPTURE_STRIPE_ERROR
        )

    def test_is_accessible(self, cart_payment_interface):
        # Stub function: return value is fixed
        assert (
            cart_payment_interface.is_accessible(
                cart_payment=MagicMock(),
                request_payer_id="payer_id",
                credential_owner="credential_ower",
            )
            is True
        )

    def test_is_capture_immediate(self, cart_payment_interface):
        # Stub function: return value is fixed
        intent = generate_payment_intent()
        assert cart_payment_interface._is_capture_immediate(intent) is False

    def test_populate_cart_payment_for_response(self, cart_payment_interface):
        cart_payment = generate_cart_payment()
        cart_payment.capture_method = "manual"
        cart_payment.payer_statement_description = "Fill in here"
        intent = generate_payment_intent(
            status="requires_capture", capture_method="auto"
        )
        pgp_intent = generate_pgp_payment_intent(
            status="requires_capture", capture_method="auto"
        )

        original_cart_payment = deepcopy(cart_payment)
        cart_payment_interface._populate_cart_payment_for_response(
            cart_payment, intent, pgp_intent
        )

        # Fields populated based on related objects
        assert cart_payment.payment_method_id == pgp_intent.payment_method_resource_id
        assert cart_payment.payer_statement_description == intent.statement_descriptor
        assert cart_payment.capture_method == intent.capture_method

        # Unchanged attributes
        assert cart_payment.id == original_cart_payment.id
        assert cart_payment.amount == original_cart_payment.amount
        assert cart_payment.payer_id == original_cart_payment.payer_id
        assert cart_payment.cart_metadata == original_cart_payment.cart_metadata
        assert cart_payment.created_at == original_cart_payment.created_at
        assert cart_payment.updated_at == original_cart_payment.updated_at
        assert cart_payment.deleted_at == original_cart_payment.deleted_at
        assert (
            cart_payment.client_description == original_cart_payment.client_description
        )
        assert cart_payment.legacy_payment == original_cart_payment.legacy_payment
        assert cart_payment.split_payment == original_cart_payment.split_payment

    @pytest.mark.asyncio
    async def test_create_new_intent_pair(self, cart_payment_interface):
        cart_payment = generate_cart_payment()
        intent = generate_payment_intent(cart_payment_id=cart_payment.id)
        pgp_intent = generate_pgp_payment_intent(payment_intent_id=intent.id)

        cart_payment_interface.payment_repo.insert_payment_intent = FunctionMock(
            return_value=intent
        )
        cart_payment_interface.payment_repo.insert_pgp_payment_intent = FunctionMock(
            return_value=pgp_intent
        )

        result_intent, result_pgp_intent = await cart_payment_interface._create_new_intent_pair(
            cart_payment=cart_payment,
            idempotency_key="idempotency_key",
            payment_method_id=cart_payment.payment_method_id,
            amount=cart_payment.amount,
            country="US",
            currency="USD",
            capture_method=cart_payment.capture_method,
            payer_statement_description=None,
        )

        assert result_intent
        assert result_intent.id
        assert result_intent.cart_payment_id == intent.cart_payment_id

        assert result_pgp_intent
        assert result_pgp_intent.id
        assert result_pgp_intent.payment_intent_id == intent.id

    @pytest.mark.asyncio
    async def test_create_new_charge_pair(self, cart_payment_interface):
        payment_charge = generate_payment_charge()
        cart_payment_interface.payment_repo.insert_payment_charge = FunctionMock(
            return_value=payment_charge
        )

        pgp_charge = generate_pgp_payment_charge()
        cart_payment_interface.payment_repo.insert_pgp_payment_charge = FunctionMock(
            return_value=pgp_charge
        )

        provider_intent = (
            await cart_payment_interface.app_context.stripe.capture_payment_intent()
        )

        result_payment_charge, result_pgp_charge = await cart_payment_interface._create_new_charge_pair(
            payment_intent=MagicMock(),
            pgp_payment_intent=MagicMock(),
            provider_intent=provider_intent,
        )

        assert result_payment_charge == payment_charge
        assert result_pgp_charge == pgp_charge

    @pytest.mark.asyncio
    async def test_update_charge_pair_after_capture(self, cart_payment_interface):
        updated_payment_charge = generate_payment_charge(status=ChargeStatus.SUCCEEDED)
        cart_payment_interface.payment_repo.update_payment_charge_status = FunctionMock(
            return_value=updated_payment_charge
        )

        updated_pgp_charge = generate_pgp_payment_charge(status=ChargeStatus.SUCCEEDED)
        cart_payment_interface.payment_repo.update_pgp_payment_charge = FunctionMock(
            return_value=updated_pgp_charge
        )

        provider_intent = (
            await cart_payment_interface.app_context.stripe.capture_payment_intent()
        )

        result_payment_charge, result_pgp_charge = await cart_payment_interface._update_charge_pair_after_capture(
            payment_intent=MagicMock(),
            status=ChargeStatus.SUCCEEDED,
            provider_intent=provider_intent,
        )

        assert result_payment_charge == updated_payment_charge
        assert result_pgp_charge == updated_pgp_charge

    @pytest.mark.asyncio
    async def test_update_charge_pair_after_cancel(self, cart_payment_interface):
        updated_payment_charge = generate_payment_charge(status=ChargeStatus.CANCELLED)
        cart_payment_interface.payment_repo.update_payment_charge_status = FunctionMock(
            return_value=updated_payment_charge
        )

        updated_pgp_charge = generate_pgp_payment_charge(status=ChargeStatus.CANCELLED)
        cart_payment_interface.payment_repo.update_pgp_payment_charge_status = FunctionMock(
            return_value=updated_pgp_charge
        )

        result_payment_charge, result_pgp_charge = await cart_payment_interface._update_charge_pair_after_cancel(
            payment_intent=MagicMock(), status=ChargeStatus.CANCELLED
        )

        assert result_payment_charge == updated_payment_charge
        assert result_pgp_charge == updated_pgp_charge

    @pytest.mark.asyncio
    async def test_update_charge_pair_after_refund(self, cart_payment_interface):
        updated_payment_charge = generate_payment_charge(status=ChargeStatus.CANCELLED)
        cart_payment_interface.payment_repo.update_payment_charge = FunctionMock(
            return_value=updated_payment_charge
        )

        updated_pgp_charge = generate_pgp_payment_charge(status=ChargeStatus.CANCELLED)
        cart_payment_interface.payment_repo.update_pgp_payment_charge = FunctionMock(
            return_value=updated_pgp_charge
        )

        provider_refund = (
            await cart_payment_interface.app_context.stripe.refund_charge()
        )
        result_payment_charge, result_pgp_charge = await cart_payment_interface._update_charge_pair_after_refund(
            payment_intent=MagicMock(), provider_refund=provider_refund
        )

        assert result_payment_charge == updated_payment_charge
        assert result_pgp_charge == updated_pgp_charge

    @pytest.mark.asyncio
    async def test_update_charge_pair_after_amount_reduction(
        self, cart_payment_interface
    ):
        updated_payment_charge = generate_payment_charge(status=ChargeStatus.CANCELLED)
        cart_payment_interface.payment_repo.update_payment_charge_amount = FunctionMock(
            return_value=updated_payment_charge
        )

        updated_pgp_charge = generate_pgp_payment_charge(status=ChargeStatus.CANCELLED)
        cart_payment_interface.payment_repo.update_pgp_payment_charge_amount = FunctionMock(
            return_value=updated_pgp_charge
        )

        result_payment_charge, result_pgp_charge = await cart_payment_interface._update_charge_pair_after_amount_reduction(
            payment_intent=MagicMock(), amount=600
        )

        assert result_payment_charge == updated_payment_charge
        assert result_pgp_charge == updated_pgp_charge

    @pytest.mark.asyncio
    async def test_update_pgp_charge_from_provider(self, cart_payment_interface):
        provider_intent = (
            await cart_payment_interface.app_context.stripe.capture_payment_intent()
        )

        pgp_charge = generate_pgp_payment_charge(status=ChargeStatus.SUCCEEDED)
        cart_payment_interface.payment_repo.update_pgp_payment_charge = FunctionMock(
            return_value=pgp_charge
        )

        result = await cart_payment_interface._update_pgp_charge_from_provider(
            payment_charge_id=uuid.uuid4(),
            status=ChargeStatus.SUCCEEDED,
            provider_intent=provider_intent,
        )

        assert result == pgp_charge

    @pytest.mark.asyncio
    async def test_update_cart_payment_attributes(self, cart_payment_interface):
        cart_payment = generate_cart_payment()
        updated_cart_payment = generate_cart_payment(amount=100)

        cart_payment_interface.payment_repo.update_cart_payment_details = FunctionMock(
            return_value=updated_cart_payment
        )

        result = await cart_payment_interface._update_cart_payment_attributes(
            cart_payment=cart_payment,
            idempotency_key=str(uuid.uuid4()),
            payment_intent=generate_payment_intent(),
            pgp_payment_intent=generate_pgp_payment_intent(),
            amount=100,
            client_description=None,
        )

        # Since updated_cart_payment object returned from mocked db function, it is modified aftewards via the
        # _populate_cart_payment_for_response function.
        assert result == updated_cart_payment

    @pytest.mark.asyncio
    async def test_submit_new_payment(self, cart_payment_interface):
        # Parameters for function
        request_cart_payment = generate_cart_payment()
        payment_resource_id = "payment_resource_id"
        customer_resource_id = "customer_resource_id"
        idempotency_key = uuid.uuid4()
        country = "US"
        currency = "USD"
        client_description = "test"

        # Mock DB and external reaching functions
        intent = generate_payment_intent()
        pgp_intent = generate_pgp_payment_intent()
        cart_payment_interface.payment_repo.insert_cart_payment = FunctionMock(
            return_value=request_cart_payment
        )
        cart_payment_interface.payment_repo.insert_payment_intent = FunctionMock(
            return_value=intent
        )
        cart_payment_interface.payment_repo.insert_pgp_payment_intent = FunctionMock(
            return_value=pgp_intent
        )

        cart_payment, payment_intent = await cart_payment_interface.submit_new_payment(
            request_cart_payment,
            payment_resource_id,
            customer_resource_id,
            idempotency_key,
            country,
            currency,
            client_description,
        )
        assert cart_payment
        assert cart_payment.capture_method == intent.capture_method
        assert cart_payment.payer_statement_description == intent.statement_descriptor
        assert cart_payment.payment_method_id == pgp_intent.payment_method_resource_id

        assert payment_intent
        assert payment_intent.id == intent.id

    @pytest.mark.asyncio
    async def test_resubmit_existing_payment(self, cart_payment_interface):
        # Parameters for function
        request_cart_payment = generate_cart_payment()
        intent = generate_payment_intent(cart_payment_id=request_cart_payment.id)
        pgp_intent = generate_pgp_payment_intent()
        payment_resource_id = "payment_resource_id"
        customer_resource_id = "customer_resource_id"

        # Mock DB and external reaching functions
        cart_payment_interface.payment_repo.find_pgp_payment_intents = FunctionMock(
            return_value=[pgp_intent]
        )

        # Already submitted before
        response = await cart_payment_interface.resubmit_existing_payment(
            request_cart_payment,
            generate_payment_intent(status=IntentStatus.SUCCEEDED),
            payment_resource_id,
            customer_resource_id,
        )
        assert response == request_cart_payment

        # Success case
        response = await cart_payment_interface.resubmit_existing_payment(
            request_cart_payment, intent, payment_resource_id, customer_resource_id
        )
        assert response == request_cart_payment

    @pytest.mark.asyncio
    async def test_cancel_intent(self, cart_payment_interface):
        intent = generate_payment_intent()
        pgp_intent = generate_pgp_payment_intent()
        result = await cart_payment_interface._cancel_intent(
            payment_intent=intent, pgp_payment_intents=[pgp_intent]
        )
        # TODO once repo layer is refactored, assert returned (updated) objects instead
        assert result is None

    @pytest.mark.asyncio
    async def test_refund_intent_invalid_state(self, cart_payment_interface):
        payment_intent = generate_payment_intent()
        pgp_intent = generate_pgp_payment_intent(status=IntentStatus.REQUIRES_CAPTURE)

        with pytest.raises(PaymentIntentRefundError):
            await cart_payment_interface._refund_intent(
                payment_intent=payment_intent,
                pgp_payment_intents=[pgp_intent],
                refund_amount=300,
            )

    @pytest.mark.asyncio
    async def test_refund_intent(self, cart_payment_interface):
        payment_intent = generate_payment_intent(status=IntentStatus.SUCCEEDED)
        pgp_intent = generate_pgp_payment_intent(status=IntentStatus.SUCCEEDED)

        updated_payment_charge = generate_payment_charge(status=ChargeStatus.CANCELLED)
        cart_payment_interface.payment_repo.update_payment_charge = FunctionMock(
            return_value=updated_payment_charge
        )

        updated_pgp_charge = generate_pgp_payment_charge(status=ChargeStatus.CANCELLED)
        cart_payment_interface.payment_repo.update_pgp_payment_charge = FunctionMock(
            return_value=updated_pgp_charge
        )

        updated_intent = generate_payment_intent()
        cart_payment_interface.payment_repo.update_payment_intent_amount = FunctionMock(
            return_value=updated_intent
        )

        updated_pgp_intent = generate_pgp_payment_intent()
        cart_payment_interface.payment_repo.update_pgp_payment_intent_amount = FunctionMock(
            return_value=updated_pgp_intent
        )

        result_intent, result_pgp_intent = await cart_payment_interface._refund_intent(
            payment_intent=payment_intent,
            pgp_payment_intents=[pgp_intent],
            refund_amount=300,
        )

        assert result_intent == updated_intent
        assert result_pgp_intent == updated_pgp_intent

    @pytest.mark.asyncio
    async def test_resubmit_add_amount_to_cart_payment(self, cart_payment_interface):
        # Already processed
        cart_payment = generate_cart_payment()
        intent = generate_payment_intent(status="requires_capture")
        pgp_intent = generate_pgp_payment_intent(status="requires_capture")
        cart_payment_interface.payment_repo.find_pgp_payment_intents = FunctionMock(
            return_value=[pgp_intent]
        )
        result_intent, result_pgp_intent = await cart_payment_interface._resubmit_add_amount_to_cart_payment(
            cart_payment, intent
        )
        assert result_intent == intent
        assert result_pgp_intent == pgp_intent

        # Resubmit, with need to call out to provider
        intent = generate_payment_intent(status="init")
        pgp_intent = generate_pgp_payment_intent(status="init")
        cart_payment_interface.payment_repo.find_pgp_payment_intents = FunctionMock(
            return_value=[pgp_intent]
        )
        result_intent, result_pgp_intent = await cart_payment_interface._resubmit_add_amount_to_cart_payment(
            cart_payment, intent
        )
        assert result_intent == intent
        assert result_pgp_intent == pgp_intent

    @pytest.mark.asyncio
    async def test_submit_amount_increase_to_cart_payment(self, cart_payment_interface):
        cart_payment_interface._get_required_payment_resource_ids = FunctionMock(
            return_value=("payment_method_id", "customer_id")
        )

        cart_payment = generate_cart_payment()
        most_recent_intent = generate_payment_intent(
            cart_payment_id=cart_payment.id, status="requires_capture"
        )
        intent = generate_payment_intent(
            cart_payment_id=cart_payment.id, status="requires_capture"
        )
        pgp_intent = generate_pgp_payment_intent(
            payment_intent_id=intent.id, status="requires_capture"
        )

        cart_payment_interface.payment_repo.insert_payment_intent = FunctionMock(
            return_value=intent
        )
        cart_payment_interface.payment_repo.insert_pgp_payment_intent = FunctionMock(
            return_value=pgp_intent
        )
        cart_payment_interface.payment_repo.find_pgp_payment_intents = FunctionMock(
            return_value=[generate_pgp_payment_intent()]
        )

        result_intent, result_pgp_intent = await cart_payment_interface._submit_amount_increase_to_cart_payment(
            cart_payment=cart_payment,
            most_recent_intent=most_recent_intent,
            amount=850,
            idempotency_key="id_key_850",
        )

        assert result_intent == intent
        assert result_pgp_intent == pgp_intent

    @pytest.mark.asyncio
    async def test_add_amount_to_cart_payment(self, cart_payment_interface):
        cart_payment = generate_cart_payment()

        # No such existing intent with idempotency key
        cart_payment_interface.payment_repo.get_payment_intents_for_cart_payment = FunctionMock(
            return_value=[generate_payment_intent()]
        )
        intent = generate_payment_intent(
            cart_payment_id=cart_payment.id, status="requires_capture"
        )
        pgp_intent = generate_pgp_payment_intent(
            payment_intent_id=intent.id, status="requires_capture"
        )

        cart_payment_interface.payment_repo.insert_payment_intent = FunctionMock(
            return_value=intent
        )
        cart_payment_interface.payment_repo.insert_pgp_payment_intent = FunctionMock(
            return_value=pgp_intent
        )
        cart_payment_interface._submit_payment_to_provider = FunctionMock()
        cart_payment_interface.payment_repo.find_pgp_payment_intents = FunctionMock(
            return_value=[generate_pgp_payment_intent()]
        )
        updated_cart_payment = deepcopy(cart_payment)
        updated_cart_payment.amount = 850
        updated_cart_payment.client_description = (
            f"{cart_payment.client_description}-updated"
        )
        cart_payment_interface.payment_repo.update_cart_payment_details = FunctionMock(
            return_value=updated_cart_payment
        )

        result_cart_payment = await cart_payment_interface._add_amount_to_cart_payment(
            cart_payment=cart_payment,
            idempotency_key=uuid.uuid4(),
            payment_intents=[intent],
            amount=875,
            legacy_payment=None,
            client_description=None,
            payer_statement_description=None,
            metadata=None,
        )
        assert result_cart_payment == updated_cart_payment

    @pytest.mark.asyncio
    async def test_add_amount_to_cart_payment_resubmit(self, cart_payment_interface):
        # TODO
        pass

    @pytest.mark.asyncio
    async def test_submit_amount_decrease_to_cart_payment(self, cart_payment_interface):
        cart_payment = generate_cart_payment()
        payment_intent = generate_payment_intent()

        updated_intent = generate_payment_intent()
        cart_payment_interface.payment_repo.update_payment_intent_amount = FunctionMock(
            return_value=updated_intent
        )
        updated_pgp_intent = generate_pgp_payment_intent()
        cart_payment_interface.payment_repo.update_pgp_payment_intent_amount = FunctionMock(
            return_value=updated_pgp_intent
        )

        cart_payment_interface.payment_repo.find_pgp_payment_intents = FunctionMock(
            return_value=[generate_pgp_payment_intent()]
        )
        cart_payment_interface.payment_repo.insert_payment_intent_adjustment_history = FunctionMock(
            return_value=MagicMock()
        )
        cart_payment_interface.payment_repo.update_payment_charge_amount = FunctionMock(
            return_value=MagicMock()
        )
        cart_payment_interface.payment_repo.update_pgp_payment_charge_amount = FunctionMock(
            return_value=MagicMock()
        )

        result_intent, result_pgp_intent = await cart_payment_interface._submit_amount_decrease_to_cart_payment(
            cart_payment=cart_payment, payment_intent=payment_intent, amount=500
        )

        assert result_intent == updated_intent
        assert result_pgp_intent == updated_pgp_intent

    @pytest.mark.asyncio
    async def test_deduct_amount_from_cart_payment_pending_capture(
        self, cart_payment_interface
    ):
        cart_payment = generate_cart_payment(amount=500)
        payment_intents = [generate_payment_intent(status="requires_capture")]
        amount = 300

        updated_intent = generate_payment_intent()
        cart_payment_interface.payment_repo.update_payment_intent_amount = FunctionMock(
            return_value=updated_intent
        )
        updated_pgp_intent = generate_pgp_payment_intent()
        cart_payment_interface.payment_repo.update_pgp_payment_intent_amount = FunctionMock(
            return_value=updated_pgp_intent
        )

        cart_payment_interface.payment_repo.find_pgp_payment_intents = FunctionMock(
            return_value=[generate_pgp_payment_intent()]
        )
        cart_payment_interface.payment_repo.insert_payment_intent_adjustment_history = FunctionMock(
            return_value=MagicMock()
        )
        cart_payment_interface.payment_repo.update_payment_charge_amount = FunctionMock(
            return_value=MagicMock()
        )
        cart_payment_interface.payment_repo.update_pgp_payment_charge_amount = FunctionMock(
            return_value=MagicMock()
        )

        updated_cart_payment = generate_cart_payment()
        cart_payment_interface.payment_repo.update_cart_payment_details = FunctionMock(
            return_value=deepcopy(updated_cart_payment)
        )

        result = await cart_payment_interface._deduct_amount_from_cart_payment(
            cart_payment=cart_payment,
            idempotency_key=str(uuid.uuid4()),
            payment_intents=payment_intents,
            amount=amount,
            legacy_payment=None,
            client_description=None,
            payer_statement_description=None,
            metadata=None,
        )

        updated_cart_payment.payment_method_id = (
            updated_pgp_intent.payment_method_resource_id
        )
        updated_cart_payment.payer_statement_description = (
            updated_intent.statement_descriptor
        )
        assert result == updated_cart_payment

    @pytest.mark.asyncio
    async def test_deduct_amount_from_cart_payment_post_capture(
        self, cart_payment_interface
    ):
        cart_payment = generate_cart_payment(amount=500)
        payment_intents = [generate_payment_intent(status="succeeded")]
        amount = 300

        cart_payment_interface.payment_repo.find_pgp_payment_intents = FunctionMock(
            return_value=[generate_pgp_payment_intent(status="succeeded")]
        )

        updated_cart_payment = generate_cart_payment()
        cart_payment_interface.payment_repo.update_cart_payment_details = FunctionMock(
            return_value=deepcopy(updated_cart_payment)
        )
        cart_payment_interface.payment_repo.update_payment_charge = FunctionMock(
            return_value=MagicMock()
        )
        cart_payment_interface.payment_repo.update_pgp_payment_charge = FunctionMock(
            return_value=MagicMock()
        )
        updated_intent = generate_payment_intent()
        cart_payment_interface.payment_repo.update_payment_intent_amount = FunctionMock(
            return_value=updated_intent
        )
        updated_pgp_intent = generate_pgp_payment_intent()
        cart_payment_interface.payment_repo.update_pgp_payment_intent_amount = FunctionMock(
            return_value=updated_pgp_intent
        )
        cart_payment_interface.payment_repo.update_payment_charge_amount = FunctionMock(
            return_value=MagicMock()
        )
        cart_payment_interface.payment_repo.update_pgp_payment_charge_amount = FunctionMock(
            return_value=MagicMock()
        )

        result = await cart_payment_interface._deduct_amount_from_cart_payment(
            cart_payment=cart_payment,
            idempotency_key=str(uuid.uuid4()),
            payment_intents=payment_intents,
            amount=amount,
            legacy_payment=None,
            client_description=None,
            payer_statement_description=None,
            metadata=None,
        )

        updated_cart_payment.payment_method_id = (
            updated_pgp_intent.payment_method_resource_id
        )
        updated_cart_payment.payer_statement_description = (
            updated_intent.statement_descriptor
        )
        assert result == updated_cart_payment

    @pytest.mark.asyncio
    async def test_deduct_amount_from_cart_payment_post_capture_not_refundable(
        self, cart_payment_interface
    ):
        cart_payment = generate_cart_payment(amount=500)
        payment_intents = [generate_payment_intent(status="failed")]
        amount = 900

        cart_payment_interface.payment_repo.find_pgp_payment_intents = FunctionMock(
            return_value=[generate_pgp_payment_intent("failed")]
        )

        updated_cart_payment = generate_cart_payment()
        cart_payment_interface.payment_repo.update_cart_payment_details = FunctionMock(
            return_value=deepcopy(updated_cart_payment)
        )

        with pytest.raises(PaymentIntentRefundError) as refund_error:
            await cart_payment_interface._deduct_amount_from_cart_payment(
                cart_payment=cart_payment,
                idempotency_key=str(uuid.uuid4()),
                payment_intents=payment_intents,
                amount=amount,
                legacy_payment=None,
                client_description=None,
                payer_statement_description=None,
                metadata=None,
            )
        assert (
            refund_error.value.error_code
            == PayinErrorCode.PAYMENT_INTENT_ADJUST_REFUND_ERROR
        )

    @pytest.mark.asyncio
    @pytest.mark.skip("Not yet implemented")
    async def test_update_payment(self, cart_payment_interface):
        # TODO
        pass