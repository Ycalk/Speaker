from moviepy import VideoFileClip, concatenate_videoclips, ImageClip
import numpy as np
from moviepy.video.fx import Crop, Resize
from PIL import Image, ImageDraw

class VideoProcessor:
    def create_circle_mask(self, size):
        """Creates a circular mask of the given size."""
        mask = Image.new("L", (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size, size), fill=255)
        return ImageClip(np.array(mask) / 255.0, is_mask=True)

    def apply_circle_mask(self, video: VideoFileClip):
        """Applies a circular mask to the video."""
        size = min(video.size)
        mask_array = self.create_circle_mask(size)
        video = video.with_mask(mask_array).with_effects([Crop(width=size, height=size, x_center=video.w / 2, y_center=video.h / 2)])
        return video

    def concatenate_videos(self, video1_path: str, video2_path: str, output_path: str):
        """Concatenates two video clips, applies a circular mask, and saves the final output."""
        video1 = VideoFileClip(video1_path)
        video2 = VideoFileClip(video2_path)

        video1 = self.apply_circle_mask(video1)
        video2 = self.apply_circle_mask(video2)

        final_video = concatenate_videoclips([video1, video2], method="compose")
        
        final_video = final_video.with_effects([Resize(height=480, width=480)])

        final_video.write_videofile(output_path, codec="libx264", audio_codec="aac")