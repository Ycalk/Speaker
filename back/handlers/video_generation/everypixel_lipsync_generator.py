import os
import queue
import requests
import logging
class EverypixelLipsyncGenerator:
    
    def __init__(self, accounts_info):
        self.__accounts: list[EverypixelAccount] = [EverypixelAccount(acc_info[0], acc_info[1]) for acc_info in accounts_info]
        self.__current_adding = 0
        self.__request_account: dict[str, EverypixelAccount] = {}
        self.__created = {}
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
    def create_request(self, request_id, audio_url, video_url):
        acc = self.__accounts[self.__current_adding % len(self.__accounts)]
        self.__request_account[request_id] = acc
        acc.add_to_queue(request_id, audio_url, video_url)
        self.logger.info(f"Getting new request: id:{request_id} audio_url: {audio_url} video_url: {video_url}")
    
    def get_video (self, request_id):
        self.logger.info(f"Checking for video in request: {request_id}")
        if request_id not in self.__request_account:
            return None
        res = self.__request_account[request_id].check_status()
        self.logger.info(f"Check result: {res}")
        if res:
            self.__created[res[0]] = res[1]
        
        if request_id in self.__created:
            return self.__created[request_id]
        


class EverypixelAccount:
    
    class Request:
        def __init__(self, request_id: str, audio_url: str, video_url: str):
            self.request_id = request_id
            self.audio_url = audio_url
            self.video_url = video_url
            self.task_id = None
    
    
    def __init__(self, client_id: str, secret: str):
        self.__client_id = client_id
        self.__secret = secret
        self.__queue = queue.Queue()
        self.__current_request: EverypixelAccount.Request = None
        self.__api_url = os.getenv('EVERYPIXEL_API_URL')
        self.__check_status_url = os.getenv('EVERYPIXEL_API_CHECK_STATUS_URL')
    
    def add_to_queue(self, request_id, audio_url: str, video_url: str):
        self.__queue.put(EverypixelAccount.Request(request_id, audio_url, video_url), False)
    
    def check_status(self):
        if not self.__current_request:
            try:
                self.__current_request = self.__queue.get_nowait()
            except queue.Empty:
                return None
        
        if not self.__current_request.task_id:
            try:
                response = requests.get(
                    url=self.__api_url,
                    params={
                        "audio_url": self.__current_request.audio_url,
                        "video_url": self.__current_request.video_url,
                    },
                    auth=(self.__client_id, self.__secret)
                )
                self.__current_request.task_id = response.json().get("task_id")
            except Exception as _:
                return None
        
        else:
            try:
                response = requests.get(self.__check_status_url.format(task_id=self.__current_request.task_id), 
                                        auth=(self.__client_id, self.__secret)).json()
                if response['status'] == 'SUCCESS':
                    out = (self.__current_request.request_id, response['result'])
                    self.__current_request = None
                    return out
            except Exception as _:
                return None
        
        
    
    