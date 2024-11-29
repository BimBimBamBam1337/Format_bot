import aiohttp
from loguru import logger
from typing import Optional, Dict, Any


class AmoCRMClient:
    def __init__(
        self,
        base_url: str,
        access_token: str,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        refresh_token: Optional[str] = None,
        permanent_access_token: bool = False,
    ):
        self.base_url = base_url
        self.access_token = access_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.refresh_token = refresh_token
        self.permanent_access_token = permanent_access_token
        self.session: Optional[aiohttp.ClientSession] = None

    def start_session(self) -> aiohttp.ClientSession:
        """Создание aiohttp-сессии"""
        if self.session is None:
            self.session = aiohttp.ClientSession()
            logger.info("HTTP-сессия для AmoCRM создана.")

    async def close_session(self):
        """Явное закрытие aiohttp-сессии"""
        if self.session:
            await self.session.close()
            logger.info("HTTP-сессия для AmoCRM закрыта.")
            self.session = None

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
    ):
        """Приватный метод для выполнения HTTP-запросов к AmoCRM API с обработкой ошибок и логированием"""
        url = f"{self.base_url}{endpoint}"

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        logger.debug(
            f"Отправка {method}-запроса на {url} с параметрами: {params} и данными: {data}"
        )

        try:
            async with self.session.request(
                method, url, headers=headers, params=params, json=data
            ) as response:
                logger.info(
                    f"Ответ от сервера: статус {response.status} для {method}-запроса на {url}"
                )
                if (
                    response.status == 401 and not self.permanent_access_token
                ):  # Неавторизован — обновляем токен, если токен не постоянный
                    logger.warning("Токен истек, попытка обновления.")
                    await self._refresh_access_token()
                    return await self._make_request(method, endpoint, params, data)
                response.raise_for_status()  # Генерируем исключение, если статус-код не 200-299
                return await response.json()  # Возвращаем JSON ответ
        except aiohttp.ClientResponseError as e:
            logger.error(f"Ошибка запроса: {e.status} {e.message}")
            raise
        except aiohttp.ClientError as e:
            logger.error(f"Ошибка сети или соединения: {e}")
            raise

    async def _refresh_access_token(self):
        """Приватный метод для обновления access_token с использованием refresh_token, если токен не постоянный"""
        if self.permanent_access_token:
            logger.info(
                "Постоянный access_token установлен. Обновление токена не требуется."
            )
            return

        url = f"{self.base_url}/oauth2/access_token"
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "redirect_uri": self.redirect_uri,
        }

        logger.info("Попытка обновления access_token...")

        try:
            async with self.session.post(url, json=data) as response:
                if response.status == 200:
                    tokens = await response.json()
                    self.access_token = tokens["access_token"]
                    self.refresh_token = tokens["refresh_token"]
                    logger.info("Токен успешно обновлен.")
                else:
                    logger.critical(
                        f"Не удалось обновить токен: статус {response.status}"
                    )
                    response.raise_for_status()
        except aiohttp.ClientError as e:
            logger.error(f"Ошибка при обновлении токена: {e}")
            raise

    async def get_lead(self, id: int) -> Dict[Any, Any]:
        """Получение информации о сделке по `id`"""
        return await self._make_request("GET", f"/api/v4/leads/{id}?with=contacts")

    async def get_user(self, id: int) -> Dict[Any, Any]:
        """Получение инофрмации о пользователе по `id`"""
        return await self._make_request("GET", f"/api/v4/users/{id}")

    async def get_contact(self, id: int):
        return await self._make_request("GET", f"/api/v4/contacts/{id}")
