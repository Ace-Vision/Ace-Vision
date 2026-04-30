import os
import time
from google import genai


""""
Using Gemini API for video analysis. This version uses gemini-2.5-flash,
which is smaller and but offers more free usage than the larger gemini-2.5-pro.
Usually it takes a few attempts to generate since it is often busy.
"""

# 1. Input API key and choose video path
API_KEY = "API_KEY_HERE" 
video_path = "video.mp4"  # Replace with your video file path
class gemini_model:
    """
    VLM module to get coaching advice from a video using a Gemini Video Model.

    The get_coaching function uploads the video to Gemini, waits for it to be processed,
    and then sends a prompt asking for coaching advice based on the video's content.
    The response is returned as plain text.

    Note: This implementation assumes the video contains the necessary visual information
    for the model to analyze and provide feedback. Does not process with respect to any
    numerical deviation scores.

    Also, this implementation does not currently integrate with the VectorDatabase for contextual search,
    but that could be added in future iterations by including relevant text from the database in the prompt.
    """
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)

    def analyze_video(self,video_path: str, prompt: str) -> str:
        # 2 Upload video to Gemini for processing
        print(f"Uploading: {video_path}")
        video_file = self.client.files.upload(file=video_path)
        
        """
        it takes a while for the video to be processed and become ACTIVE,
        so we poll for status
        """

        print(f"Processing (ID: {video_file.name})", end="")
        while video_file.state.name == "PROCESSING":
            print(".", end="", flush=True)
            time.sleep(2)
            video_file = self.client.files.get(name=video_file.name)

        if video_file.state.name != "ACTIVE":
            raise ValueError(f"Video failed to reach ACTIVE state: {video_file.state.name}")

        """"
        3. Once active, we can now ask the model to analyze the video content.
        We wrap this in a retry loop since the model is often busy and may return
        503 errors.
        """

        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"\nAnalysis Attempt {attempt + 1}...")
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[
                        video_file, 
                        prompt
                    ]
                )
                
                # Clean up cloud storage immediately after success
                self.client.files.delete(name=video_file.name)
                return response.text
            
            except Exception as e:
                if "503" in str(e) and attempt < max_retries - 1:
                    wait = (attempt + 1) * 10
                    print(f"Server busy. Waiting {wait}s...")
                    time.sleep(wait)
                    continue
                
                # Clean up even on failure
                self.client.files.delete(name=video_file.name)
                raise e
            

    def get_coaching(self, video_path: str, skill_level: str = "intermediate") -> dict | None:
        """
        Ask the local VLM for coaching advice.

        Returns {"advice": "<text>"} or None if VLM is unreachable.

        """

        prompt =  f"""You are an expert sports biomechanics coach.
            The player's skill level is: {skill_level}.Give 2-3 specific 
            coaching corrections targeting the joints with the highest severity scores.
            For each correction: state which checkpoint it affects, 
            what the problem is biomechanically, and a concrete drill to fix it.
            Be concise and practical. Focus on actionable 
            advice.
            
            Maximum 100 words.
            
            If the video is not clear enough or is not a video of tennis or badminton,
            say you cannot analyze the video.
            """
        
        print(f"Analyzing video for coaching advice with skill level '{skill_level}'...")
        print(self.analyze_video(video_path, prompt))

"""
Example usage:
my_vlm = gemini_model(API_KEY)
my_vlm.get_coaching(video_path, skill_level="beginner")
"""
