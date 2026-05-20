import pyotp
from ..api.client import get_client
from ..utils.token_manager import token_manager
from ..utils.logger import get_logger
from ..exceptions import AuthException

logger = get_logger(__name__)

class AuthService:
    def __init__(self):
        self.client_wrapper = get_client()

    async def login(self, client_code: str = None, password: str = None, totp: str = None) -> dict:
        """
        Automates the login process using TOTP or explicit credentials.
        """
        import traceback
        logger.info("Initiating Angel One login process...")
        try:
            logger.info(f"AuthService.login called - client_code: {client_code}, has password: {bool(password)}, has totp: {bool(totp)}")

            login_client_code = client_code or self.client_wrapper.client_id
            login_password = password or self.client_wrapper.password

            logger.info(f"Using client_code: {login_client_code}, has password: {bool(login_password)}")

            if not login_client_code or not login_password:
                raise AuthException("Client code and password are required")

            if not totp and self.client_wrapper.totp_secret:
                login_totp = pyotp.TOTP(self.client_wrapper.totp_secret).now()
            else:
                login_totp = totp

            if not login_totp:
                raise AuthException("TOTP is required")

            logger.info(f"Angel login payload keys: dict_keys(['clientcode', 'password', 'totp'])")
            logger.info(f"Outgoing login payload: {{'clientcode': '{login_client_code}', 'totp': '{login_totp}'}} (password hidden)")

            payload = {
                "clientcode": login_client_code,
                "password": login_password,
                "totp": login_totp
            }

            logger.info(f"About to call generateSession for client: {login_client_code}")
            data = await self.client_wrapper.execute_async(
                self.client_wrapper.smart_api.generateSession,
                payload["clientcode"],
                payload["password"],
                payload["totp"]
            )
            logger.info(f"generateSession returned: status={data.get('status')}, keys={list(data.keys())}")

            if data.get('status') is False:
                raise AuthException(f"Login failed: {data.get('message')}")

            response_data = data['data']

            token_manager.save_tokens(
                jwt_token=response_data['jwtToken'],
                refresh_token=response_data['refreshToken'],
                feed_token=response_data['feedToken'],
                mac_address=response_data.get('macAddress')
            )

            logger.info("Angel One login successful.")
            return response_data

        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            logger.error(f"Auth service traceback:\n{traceback.format_exc()}")
            raise AuthException(f"Failed to authenticate: {str(e)}")

    async def logout(self) -> dict:
        try:
            data = await self.client_wrapper.execute_async(
                self.client_wrapper.smart_api.terminateSession,
                self.client_wrapper.client_id
            )
            token_manager.clear_tokens()
            logger.info("Logged out successfully.")
            return data
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            raise AuthException(str(e))

    async def get_profile(self) -> dict:
        try:
            data = await self.client_wrapper.execute_async(
                self.client_wrapper.smart_api.getProfile,
                self.client_wrapper.smart_api.refresh_token
            )
            if data.get('status') is False:
                raise AuthException(data.get('message'))
            return data['data']
        except Exception as e:
            logger.error(f"Profile fetch error: {str(e)}")
            raise AuthException(str(e))
