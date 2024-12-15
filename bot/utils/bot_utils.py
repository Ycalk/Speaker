import aiohttp
import os
from dotenv import load_dotenv
load_dotenv()

class BotUtils:
    @property
    def channel_url(self):
        return self.__channel_url
    
    def __init__(self):
        self.__bot_token = os.getenv('TOKEN')
        self.__channel_id = os.getenv('CHANNEL_ID')
        self.__channel_url = os.getenv('CHANNEL_URL')
    
    async def check_user_subscription(self, user_id: int):
        """
        Check if user is a member of the channel

        Args:
            user_id (int): User id (eg telegram id)

        Returns:
            bool: True if user is a member of the channel, False otherwise
        """
        url = f"https://api.telegram.org/bot{self.__bot_token}/getChatMember"
        j = {
            "chat_id": str(self.__channel_id),
            "user_id": str(user_id)
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=j) as response:
                return response.status == 200 and (await response.json())["result"]["status"] in ("member", "administrator", "creator")