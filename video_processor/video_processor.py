from moviepy import VideoFileClip, concatenate_videoclips, ImageClip
import numpy as np
from moviepy.video.fx import Crop, Resize
from PIL import Image, ImageDraw
from multiprocessing import Queue
import requests
import redis
import json

class Video:
    def __init__ (self, video_path:str):
        self.video_path = video_path
    
    @staticmethod
    def from_url (self, video_url:str, save_path:str):
        self.video_url = video_url
        self.video_path = save_path
        with open(save_path, "wb") as f:
            video_response = requests.get(video_url)
            f.write(video_response.content)
        
    def get_clip(self) -> VideoFileClip:
        return VideoFileClip(self.video_path)


class Listener:
    def __init__ (self, output_channel: str, 
                    redis_storage_url: str, 
                    s3, bucket_name: str, storage_url: str):
        self.output_channel = output_channel
        self.redis = redis.Redis.from_url(redis_storage_url)
        self.s3 = s3
        self.bucket_name = bucket_name
        self.storage_url = storage_url
    
    @staticmethod
    def start_listening(queue: Queue, 
                        output_channel: str,
                        redis_storage_url: str,
                        s3, bucket_name: str, storage_url: str):
        def get_video_path(celebrity_code: str):
            return f"data/{celebrity_code.replace('_', '/')}/part2.mp4"

        processor = VideoProcessor()
        listener = Listener(output_channel, redis_storage_url, s3, bucket_name, storage_url)
        while True:
            data = queue.get()
            if data == "STOP":
                break
            
            request_id = data['id']
            user_name = data['user_name']
            celebrity_code = data['celebrity_code']
            lip_sync_url = data['lip_sync_url']
            
            video1 = Video.from_url(lip_sync_url)
            video2 = Video(get_video_path(celebrity_code))
            output_path = f"temp/{request_id}_out.mp4"
            
            processor._concatenate_videos(video1, video2, output_path)

            path_in_bucket = listener.get_path_in_bucket(celebrity_code, user_name)
            listener.upload(output_path, path_in_bucket)
            listener.notify(request_id, path_in_bucket)
            
    def get_path_in_bucket(self, celebrity_code: str, user_name: str):
        return f'video/{celebrity_code.replace("_", "/")}/{user_name}.mp4'
    
    def upload(self, file_path: str, path_in_bucket: str):
        self.s3.upload_file(file_path, self.bucket_name, path_in_bucket)
    
    def notify(self, request_id: str, path_in_bucket: str):
        response = {
            "request_id": request_id,
            "video_url": f"{self.storage_url}/{self.bucket_name}/{path_in_bucket}"
        }
        self.redis.publish(self.output_channel, json.dumps(response))

class VideoProcessor:
    
    def _create_circle_mask(self, size):
        """Creates a circular mask of the given size."""
        mask = Image.new("L", (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size, size), fill=255)
        return ImageClip(np.array(mask) / 255.0, is_mask=True)

    def _apply_circle_mask(self, video: VideoFileClip):
        """Applies a circular mask to the video."""
        size = min(video.size)
        mask_array = self._create_circle_mask(size)
        video = video.with_mask(mask_array).with_effects([Crop(width=size, height=size, x_center=video.w / 2, y_center=video.h / 2)])
        return video

    def _concatenate_videos(self, video1: Video, video2: Video, output_path: str):
        """Concatenates two video clips, applies a circular mask, and saves the final output."""
        video1 = video1.get_clip()
        video2 = video2.get_clip()

        video1 = self._apply_circle_mask(video1)
        video2 = self._apply_circle_mask(video2)

        final_video = concatenate_videoclips([video1, video2], method="compose")
        
        final_video = final_video.with_effects([Resize(height=480, width=480)])

        final_video.write_videofile(output_path, codec="libx264", audio_codec="aac")