import hmac, hashlib
import time
import aiohttp, asyncio
import logging

from typing import Union
from .logger import CustomLogger

logger_manager = CustomLogger()
wfp_logger = logger_manager.get_logger("WayForPay", "logs/wfp.log", logging.ERROR)


class SingletonMeta(type):
    """
    A metaclass for creating singleton classes.
    Ensures that only one instance of the class exists.
    """

    _instances = {}

    def __call__(cls, *args, **kwargs):
        """
        Returns the singleton instance of the class.
        If the instance does not exist, it creates one.
                
        Returns:
            The singleton instance of the class.
        """
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


class WayForPayHandler(metaclass=SingletonMeta):
    """
    A handler class for WayForPay integration.
    Uses SingletonMeta to ensure only one instance exists.
    """

    def __init__(self, merchant_account=None, secret_key=None, domain_name=None):
        """
        Initializes the WayForPayHandler instance.
        
        Args:
            merchant_account (str, optional): The merchant account identifier.
            secret_key (str, optional): The secret key for the merchant account.
            domain_name (str, optional): The domain name associated with the merchant account.
        """
        if not hasattr(self, "initialized"):
            self.MERCHANT_ACCOUNT = merchant_account
            self.SECRET_KEY = secret_key
            self.DOMAIN_NAME = domain_name
            self.payments = {}  # Stores payment data for each user
            asyncio.create_task(self.get_payment_data())
            self.initialized = True
        

    async def generate_signature(self, data: str) -> str:
        """
        Generates an HMAC-MD5 signature for the given data using the secret key.

        Args:
            data (str): The data to be signed. Depends on the specific use case.

        Returns:
            str: The generated HMAC-MD5 signature.
        """
        return hmac.new(self.SECRET_KEY.encode(), data.encode(), hashlib.md5).hexdigest()
    
    async def create_invoice(self, user_id: Union[int, str], amount: int, product_type: str) -> dict:
        """
        Creates an invoice for the specified user and product type.
        
        Args:
            user_id (int | str): The user's unique identifier.
            amount (int): The amount to be paid in UAH.
            product_type (str): The type of product being purchased.
        
        Returns:
            dict: A dictionary containing the invoice URL and QR code, or an error message.
        """
        order_date = int(time.time())
        order_reference = f"{user_id}-{order_date}"
        product_name = product_type

        create_invoice_signature_data = f"{self.MERCHANT_ACCOUNT};{self.DOMAIN_NAME};{order_reference};{order_date};{amount};UAH;{product_name};1;{amount}"
        signature = await self.generate_signature(create_invoice_signature_data)
        
        try:
            user_info = self.payments.get(user_id)
            if not user_info:
                self.payments[user_id] = []
        except Exception as e:
            wfp_logger.error(f"Error in WayForPayHandler.create_invoice: {e}\nself.payments in user_id: {user_id} -> {self.payments[user_id]}")
        try:
            self.payments[user_id].append({
                "order_reference": order_reference,
                "product_type": product_type,
                "order_date": order_date
            })
        except Exception as e:
            wfp_logger.error(f"Error in WayForPayHandler.create_invoice: {e}\nself.payments in user_id: {user_id} -> {self.payments[user_id]}")

        invoice_data = {
            "transactionType": "CREATE_INVOICE",
            "apiVersion": 1,
            "merchantAccount": self.MERCHANT_ACCOUNT,
            "merchantDomainName": self.DOMAIN_NAME,
            "orderReference": order_reference,
            "orderDate": order_date,
            "amount": amount,
            "currency": "UAH",
            "paymentSystems": "card;googlePay;applePay;privat24",
            "productName": [product_name],
            "productPrice": [amount],
            "productCount": [1],
            "merchantSignature": signature
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post("https://api.wayforpay.com/api", json=invoice_data) as responce:
                    result = await responce.json()
                    if result.get("invoiceUrl"):
                        return {"invoice_url": result["invoiceUrl"], "qr_code": result["qrCode"]}
                    else:
                        return {"error": "error"}
        except Exception as e:
            wfp_logger.error(f"Error in WayForPayHandler.create_invoice in post for user_id {user_id}: {e} -> {result}")

                
    async def get_payment_data(self):
        """
        Periodically checks for updates on payment statuses and updates the local cache.
        This function runs in an infinite loop with a sleep interval.
        """
        while True:
            try:
                if not self.payments:
                    await asyncio.sleep(5)
                    continue
            except Exception as e:
                wfp_logger.error(f"Error in WayForPayHandler.get_payment_data start: {e}")

            date_end = int(time.time())

            for user_id in list(self.payments.keys()):
                try:
                    payments = self.payments[user_id]
                    for payment in payments:
                        order_reference = payment["order_reference"]
                        date_begin = payment["order_date"]

                        get_payment_signature_data = f"{self.MERCHANT_ACCOUNT};{date_begin-1000};{date_end}"
                        signature = await self.generate_signature(get_payment_signature_data)

                        request_data = {
                            "apiVersion": 1,
                            "transactionType": "TRANSACTION_LIST",
                            "merchantAccount": self.MERCHANT_ACCOUNT,
                            "merchantSignature": signature,
                            "dateBegin": date_begin - 1000,
                            "dateEnd": date_end,
                        }

                        async with aiohttp.ClientSession() as session:
                            async with session.post(
                                "https://api.wayforpay.com/api", json=request_data
                            ) as response:
                                result = await response.json()

                                transaction_list = result.get("transactionList", [])

                                for transaction in transaction_list:
                                    if transaction.get("orderReference") == order_reference:
                                        transaction_status = transaction.get("transactionStatus")
                                        logging.info(f"transaction_status: {transaction_status}")
                                        if transaction_status in ["Approved", "Declined", "Expired"]:
                                            payment["payment_status"] = transaction_status

                    if not payments:
                        del self.payments[user_id]

                except Exception as e:
                    wfp_logger.error(f"Error in WayForPayHandler.get_payment_data after: {e}\n\norder_reference: {order_reference}\ndate_begin: {date_begin}\nrequest_data: {request_data}\nresult: {result}")

            await asyncio.sleep(15)


    async def check_payment_data(self, user_id: Union[int, str], product_type: str) -> tuple:
        """
        Checks the status of a payment for a specific user and product type.
        
        Args:
            user_id (int | str): The user's unique identifier.
            product_type (str): The type of product being checked.
        
        Returns:
            tuple: A tuple containing the user ID and the payment status.
        
        Raises:
            ValueError: If the specified transaction is not found.
            TimeoutError: If the transaction status update times out.
        """
        user_payments = self.payments.get(user_id, [])

        target_dict = None
        target_index = None

        try:
            user_payments[:] = [
                payment for i, payment in enumerate(user_payments)
                if not (payment.get("product_type") == product_type and target_dict is not None)
            ]
            for i, payment in enumerate(user_payments):
                if payment.get("product_type") == product_type and target_dict is None:
                    target_dict = payment
                    target_index = i
        except Exception as e:
            wfp_logger.error(
                f"Error in check_payment_data: {e}, user_id: {user_id}, "
                f"product_type: {product_type}, target_dict: {target_dict}, user_payments: {user_payments}"
            )
            raise RuntimeError(
                f"Unexpected error in check_payment_data: {e}, user_id: {user_id}, product_type: {product_type}"
            ) from e

        if target_dict is None:
            wfp_logger.warning(f"No transaction found for user {user_id} with product_type {product_type}")
            raise ValueError("Transaction with the specified product_type not found.")

        timeout = 60 * 20
        start_time = time.time()

        while True:
            try:
                if "payment_status" in target_dict:
                    status = target_dict["payment_status"]

                    if target_index is not None:
                        user_payments.pop(target_index)
                    if not user_payments and user_id in self.payments:
                        del self.payments[user_id]

                    wfp_logger.info(
                        f"Transaction completed for user {user_id}, status: {status}, product_type: {product_type}"
                    )
                    return user_id, status

            except KeyError as e:
                wfp_logger.error(f"Error in payment dictionary structure: {e}, target_dict: {target_dict}")
                raise

            except Exception as e:
                wfp_logger.error(
                    f"Unexpected error in check_payment_data: {e}, user_id: {user_id}, "
                    f"product_type: {product_type}, target_dict: {target_dict}"
                )
                raise

            if time.time() - start_time > timeout:
                wfp_logger.warning(
                    f"Timeout while waiting for transaction completion for user {user_id}, product_type: {product_type}"
                )
                raise TimeoutError("Transaction status update timed out.")

            await asyncio.sleep(5)
