"""
Handler: create payment transaction
SPDX - License - Identifier: LGPL - 3.0 - or -later
Auteurs : Gabriel C. Ullmann, Fabio Petrillo, 2025
"""
import requests
from handlers.handler import Handler
from order_saga_state import OrderSagaState
import config

class CreatePaymentHandler(Handler):
    """ Handle the creation of a payment transaction for a given order. Trigger rollback of previous steps in case of failure. """

    def __init__(self, order_id, order_data):
        """ Constructor method """
        self.order_id = order_id
        self.order_data = order_data
        self.total_amount = 0
        super().__init__()

    def run(self):
        """Call payment microservice to generate payment transaction"""
        try:
            order_response = requests.get(
                f"{config.API_GATEWAY_URL}/store-manager-api/orders/{self.order_id}",
                headers={'Content-Type': 'application/json'}
            )

            if not order_response.ok:
                self.logger.error(
                    "Erreur lecture commande:",
                    order_response.status_code,
                    order_response.text
                )
                return self.rollback()

            order_data = order_response.json()
            self.total_amount = float(order_data["total_amount"])

            payment_response = requests.post(
                f"{config.API_GATEWAY_URL}/payments-api/payments",
                json={
                    "user_id": self.order_data["user_id"],
                    "order_id": self.order_id,
                    "total_amount": self.total_amount
                },
                headers={'Content-Type': 'application/json'}
            )

# payment_response.ok
            if payment_response.ok: 
                self.logger.debug("Transition d'état: CreatePayment -> PAYMENT_CREATED")
                return OrderSagaState.PAYMENT_CREATED
            else:
                self.logger.error(
                    f"Erreur création paiement: {payment_response.status_code} {payment_response.text}"
                )

                return self.rollback()

        except Exception as e:
            self.logger.error(f"Exception création paiement: {e}")
            return self.rollback()

        
    def rollback(self):
        """ Call StoreManager to restore stock quantities if payment transaction creation fails """
        # TODO: remettre en stock tous les articles qui avaient été retirés du stock (dans self.order_data)
        self.logger.debug("Transition d'état: CreatePaymentFailure -> STOCK_INCREASED")
        return OrderSagaState.STOCK_INCREASED