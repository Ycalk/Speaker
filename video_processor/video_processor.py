import os
from moviepy import ImageSequenceClip, VideoFileClip, concatenate_videoclips, ImageClip
import numpy as np
from moviepy.video.fx import Crop, Resize, MultiplySpeed
from PIL import Image, ImageDraw
from multiprocessing import Queue
import requests
import redis
import json
import cv2
from boto3 import Session
import logging


class Video:
    def __init__ (self, video_path:str):
        self.video_path = video_path
    
    @staticmethod
    def from_url (video_url:str, save_path:str):
        res = Video(save_path)
        with open(save_path, "wb") as f:
            video_response = requests.get(video_url)
            f.write(video_response.content)
        return res
        
    def get_clip(self) -> VideoFileClip:
        return VideoFileClip(self.video_path)


class Worker:
    def __init__ (self, output_channel: str, 
                    redis_storage_url: str):
        session = Session(
            aws_access_key_id=os.getenv('YC_STATIC_KEY_ID'),
            aws_secret_access_key=os.getenv('YC_STATIC_KEY'),
            region_name='ru-central1'  
        )
        self.storage_url = os.getenv('STORAGE_URL')
        self.s3 = session.client(service_name='s3', endpoint_url=self.storage_url)
        self.output_channel = output_channel
        self.redis = redis.Redis.from_url(redis_storage_url)
        self.bucket_name = os.getenv('BUCKET_NAME')
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    @staticmethod
    def start_listening(queue: Queue, 
                        output_channel: str,
                        redis_storage_url: str):
        def get_video_path(celebrity_code: str):
            return f"data/{celebrity_code.replace('_', '/')}/part2.mp4"
        processor = VideoProcessor()
        listener = Worker(output_channel, redis_storage_url)
        listener.logger.info("Worker started")
        while True:
            try:
                data = queue.get()
                data = json.loads(data)
                if data == "STOP":
                    break
                listener.logger.info(f"Processing request: {data}")
                request_id = data['id']
                user_name = data['user_name']
                celebrity_code = data['celebrity_code']
                lip_sync_url = data['lip_sync_url']
                
                video1 = Video.from_url(lip_sync_url, f"temp/{request_id}_lip_sync.mp4")
                video2 = Video(get_video_path(celebrity_code))
                packshot = Video("data/packshot.mp4")
                output_path = f"temp/{request_id}_out.mp4"
                
                processor._concatenate_videos(video1, video2, packshot, output_path)
                listener.logger.info(f"Video concatenated and saved to {output_path}")
                path_in_bucket = listener.get_path_in_bucket(celebrity_code, user_name)
                listener.upload(output_path, path_in_bucket)
                listener.logger.info(f"Video uploaded to {listener.storage_url}/{listener.bucket_name}/{path_in_bucket}")
                listener.notify(request_id, path_in_bucket)
                os.remove(output_path)
                os.remove(video1.video_path)
            except Exception as e:
                listener.logger.error(f"Error processing request: {e}")
            
    def get_path_in_bucket(self, celebrity_code: str, user_name: str):
        return f'video/{celebrity_code.replace("_", "/")}/{user_name}.mp4'
    
    def upload(self, file_path: str, path_in_bucket: str):
        self.s3.upload_file(file_path, self.bucket_name, path_in_bucket)
    
    def notify(self, request_id: str, path_in_bucket: str):
        response = {
            "id": request_id,
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

    def _match_colors(self, source_frame, reference_frame):
        """Matches the color of the source frame to the reference frame."""
        source_lab = cv2.cvtColor(source_frame, cv2.COLOR_RGB2Lab)
        reference_lab = cv2.cvtColor(reference_frame, cv2.COLOR_RGB2Lab)
        matched_lab = source_lab.copy()
        
        for i in range(3):
            source_hist, _ = np.histogram(source_lab[:, :, i].flatten(), bins=256, range=[0, 256])
            reference_hist, _ = np.histogram(reference_lab[:, :, i].flatten(), bins=256, range=[0, 256])

            source_cdf = np.cumsum(source_hist).astype(float) / source_hist.sum()
            reference_cdf = np.cumsum(reference_hist).astype(float) / reference_hist.sum()

            mapping = np.interp(source_cdf, reference_cdf, np.arange(256))
            matched_lab[:, :, i] = cv2.LUT(source_lab[:, :, i], mapping.astype(np.uint8))

        return cv2.cvtColor(matched_lab, cv2.COLOR_Lab2RGB)

    def _generate_intermediate_frames(self, frame1, frame2, num_frames=30):
        """Generates intermediate frames between two frames."""
        intermediate_frames = []
        for i in range(1, num_frames + 1):
            alpha = i / (num_frames + 1)
            blended_frame = (1 - alpha) * frame1 + alpha * frame2
            intermediate_frames.append(np.uint8(blended_frame))
        return intermediate_frames
    
    def _get_intermediate_clip(self, video1: VideoFileClip, video2: VideoFileClip) -> ImageSequenceClip:
        frame1 = list(video1.iter_frames())[-1]
        frame2 = video2.get_frame(0)
        
        frame2 = cv2.resize(frame2, (frame1.shape[1], frame1.shape[0]))
        
        intermediate_frames = self._generate_intermediate_frames(frame1, frame2)
        return ImageSequenceClip(intermediate_frames, fps=video1.fps).resized(width=video1.w, height=video1.h)
    
    def color_correct_clip(self, clip: VideoFileClip, ref_frame) -> ImageSequenceClip:
        processed_frames = [self._match_colors(frame, ref_frame) for frame in clip.iter_frames(dtype="uint8")]
        
        return ImageSequenceClip(processed_frames, fps=clip.fps).resized(width=clip.w, height=clip.h).with_audio(clip.audio)
    
    def _concatenate_videos(self, video1: Video, video2: Video, packshot: Video, output_path: str):
        """Concatenates two video clips, applies a circular mask, and saves the final output."""
        
        video2_clip = video2.get_clip()
        video1_clip = video1.get_clip().resized(new_size=video2_clip.size)
        video3_clip = packshot.get_clip().resized(new_size=video2_clip.size)
        
        video1_color_correct = self.color_correct_clip(video1_clip, video2_clip.get_frame(0))
        
        video1_masked = self._apply_circle_mask(video1_color_correct)
        video2_masked = self._apply_circle_mask(video2_clip)
        video3_masked = self._apply_circle_mask(video3_clip)
        
        intermediate_clip = self._get_intermediate_clip(video1_masked, video2_masked)
        intermediate_clip_masked = self._apply_circle_mask(intermediate_clip)
        intermediate_clip_speed_up = MultiplySpeed(factor=6).apply(intermediate_clip_masked)
        
        final_video = concatenate_videoclips([video1_masked, intermediate_clip_speed_up, video2_masked, video3_masked], method="compose")
        
        final_video = final_video.with_effects([Resize(height=480, width=480)])

        final_video.write_videofile(output_path, codec="libx264", audio_codec="aac")