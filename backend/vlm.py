import os
import time
from google import genai

# Using Gemini API for video analysis. This version uses gemini-2.5-flash,
# which is smaller and but offers more free usage than the larger gemini-2.5-pro.
# Usually it takes a few attempts to generate since it is often busy.

# 1. Input API key and choose video path
API_KEY = "AIzaSyDkFUqfvdTzWjDFMMogJnWmtlXAMF4fxME" 
client = genai.Client(api_key=API_KEY)


def analyze_video(video_path: str):
    # 2 Upload video to Gemini for processing
    print(f"Uploading: {video_path}")
    video_file = client.files.upload(file=video_path)
    
    # it takes a while for the video to be processed and become ACTIVE,
    # so we poll for status

    print(f"Processing (ID: {video_file.name})", end="")
    while video_file.state.name == "PROCESSING":
        print(".", end="", flush=True)
        time.sleep(2)
        video_file = client.files.get(name=video_file.name)

    if video_file.state.name != "ACTIVE":
        raise ValueError(f"Video failed to reach ACTIVE state: {video_file.state.name}")

    # 3. Once active, we can now ask the model to analyze the video content.
    # We wrap this in a retry loop since the model is often busy and may return
    # 503 errors.

    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"\nAnalysis Attempt {attempt + 1}...")
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    video_file, 
                    "Describe the sequence of events in this video in detail."
                ]
            )
            
            # Clean up cloud storage immediately after success
            client.files.delete(name=video_file.name)
            return response.text
        
        except Exception as e:
            if "503" in str(e) and attempt < max_retries - 1:
                wait = (attempt + 1) * 10
                print(f"Server busy. Waiting {wait}s...")
                time.sleep(wait)
                continue
            
            # Clean up even on failure
            client.files.delete(name=video_file.name)
            raise e


if __name__ == "__main__":
    test_path = r"C:\Users\ldahl\Videos\WIN_20260429_16_56_29_Pro.mp4"
    
    try:
        description = analyze_video(test_path)
        print("\n" + "="*50)
        print("ACE-VISION BACKEND OUTPUT:")
        print("="*50)
        print(description)
        print("="*50)
            
    except Exception as e:
        print(f"\n Final Error: {e}")