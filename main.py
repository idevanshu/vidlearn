from openai import OpenAI
import json
import asyncio
from pathlib import Path
from jinja2 import Template
import tempfile
import anthropic
import os

from prompts import script_system_prompt, animation_system_prompt
from video import merge_with_ffmpeg, merge_videos
from animation import generate_html, record_animation
from helper import safe_launch, clear_folder, run_async_safely

from dotenv import load_dotenv
from progress import progress_data
from werkzeug.utils import secure_filename  # Optional, for consistency in filename sanitization

load_dotenv()

openai_api = os.getenv("OPENAI_API_KEY")
claude_api = os.getenv("CLAUDE_API_KEY")

client = OpenAI(api_key=openai_api)
client_claude = anthropic.Anthropic(api_key=claude_api)


def generate_claude(system_prompt, user_prompt):
    response = client_claude.messages.create(
        model="claude-3-7-sonnet-20250219",
        max_tokens=8000,
        system=system_prompt,
        messages=[
            {"role": "user", "content": user_prompt}
        ]
    )
    code = extract_code_from_response(response.content)
    return code


def extract_code_from_response(content):
    for block in content:
        if hasattr(block, 'type') and block.type == 'text':
            return block.text
    return None


"""
Pipeline:

user_prompt -> generate script -> generate animation + generate voiceover -> merge into one video
"""


def generate_response(system_prompt, user_prompt):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    return response.choices[0].message.content


async def validate_code_in_browser(js_code):
    # Path to Chrome; adjust if necessary.
    CHROME_PATH = "C:/Program Files/Google/Chrome/Application/chrome.exe"
    
    html_template = """
    <html>
      <head>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/p5.js/1.9.0/p5.min.js"></script>
        <script>
        window.onerror = function(msg, src, line, col, err) {
          console.error("JSERROR:" + msg);
        };
        </script>
      </head>
      <body>
        <script>
        try {
            {{ code }}
            window.__animationLoaded = true;
        } catch(e) {
            console.error("JSERROR: " + e.message);
        }
        </script>
      </body>
    </html>
    """
    rendered = Template(html_template).render(code=js_code)
    html_path = Path(tempfile.gettempdir()) / "validate_animation.html"
    html_path.write_text(rendered, encoding="utf-8")

    browser = await safe_launch(headless=True, args=["--no-sandbox"], executablePath=CHROME_PATH)
    page = await browser.newPage()
    logs = []
    page.on("console", lambda msg: logs.append(msg.text))
    try:
        await page.goto(f"file://{html_path}")
        await asyncio.sleep(3)  # Allow time for animation initialization.
        success = await page.evaluate("window.__animationLoaded === true")
    except Exception as e:
        success = False
    finally:
        await browser.close()
    has_js_error = any("JSERROR:" in log for log in logs)
    return (success and not has_js_error, logs)


def generate_valid_animation_code(prompt, max_attempts=3):
    past_error = ""
    for attempt in range(1, max_attempts + 1):
        print(f"🎯 Generating animation code (attempt {attempt})...")
        progress_data["step"] = f"Generating animation code (attempt {attempt})"
        progress_data["message"] = prompt
        clean_code = generate_claude(animation_system_prompt, f"{prompt}. Dont repeat this error again: {past_error}")
        try:
            is_valid, logs = run_async_safely(validate_code_in_browser(clean_code))
            past_error = logs
        except Exception as e:
            print(f"⚠️ Validation failed: {e}")
            is_valid = False

        if is_valid:
            print("✅ Valid animation code generated.")
            return clean_code
        else:
            print("❌ Code invalid or has JS errors. Retrying...")
            print(clean_code)
    raise RuntimeError("❌ All attempts to generate valid animation code failed.")


def generate_voice(save_file_path, script):
    with client.audio.speech.with_streaming_response.create(
        model="gpt-4o-mini-tts",
        voice="alloy",
        input=script
    ) as response:
        response.stream_to_file(save_file_path)


def safe_parse_json(gpt_output):
    try:
        if gpt_output.startswith("```json"):
            gpt_output = gpt_output.strip()[7:-3].strip()  # Remove markdown fences.
        elif gpt_output.startswith("```"):
            gpt_output = gpt_output.strip()[3:-3].strip()
        return json.loads(gpt_output)
    except json.JSONDecodeError as e:
        print("❌ JSON parsing failed:", e)
        return None


def generate_placeholder_video(segment_id, duration):
    """
    Generate a placeholder (black) video of the specified duration.
    Requires ffmpeg to be installed.
    """
    placeholder_video_path = f"segments/{segment_id}.webm"
    cmd = (
        f"ffmpeg -y -f lavfi -i color=c=black:s=1280x720:d={duration} "
        f"-c:v libvpx -crf 10 -b:v 1M {placeholder_video_path}"
    )
    os.system(cmd)
    print(f"Placeholder video created for segment {segment_id} with duration {duration}s.")


def generate_video(user_prompt, output_filename):
    # Update progress status.
    progress_data["step"] = "Initializing"
    progress_data["message"] = "Clearing folders and starting generation."

    # Clear folders for a fresh generation.
    clear_folder("final_videos")
    clear_folder("segments")
    clear_folder("voice")

    # Generate the script from the prompt.
    progress_data["step"] = "Generating script"
    progress_data["message"] = "Using prompt to generate the video script."
    script = generate_response(script_system_prompt, user_prompt)
    script = safe_parse_json(script)
    with open('scripts.json', 'w') as f:
        json.dump(script, f)

    progress_data["step"] = "Script generated"
    progress_data["message"] = "Proceeding to segment processing."

    # Process each segment.
    for segments in script:
        segment_id = segments["id"]
        voiceover = segments["voice_script"]
        animation = segments["animation"]
        duration = segments["duration"]
        progress_data["segment"] = f"Segment {segment_id}"
        progress_data["step"] = f"Processing segment {segment_id}"
        progress_data["message"] = "Generating animation code."
        
        animation_prompt = f"{animation} to last at least {duration} seconds. The voiceover for this is {voiceover}"
        animation_code = generate_valid_animation_code(animation_prompt)
        html_path = generate_html(animation_code)
        
        progress_data["step"] = f"Recording animation for segment {segment_id}"
        progress_data["message"] = "Capturing animation with headless browser."
        try:
            run_async_safely(record_animation(html_path, segment_id, duration))
        except Exception as e:
            err_str = str(e)
            # Catch error if canvas selector is not found or blob base64 times out.
            if "Timed out waiting for blob base64" in err_str or "Waiting for selector" in err_str:
                progress_data["message"] = f"Timeout in recording animation for segment {segment_id}; using placeholder video."
                print(f"⚠️ Warning: Animation for segment {segment_id} timed out (error: {err_str}). Generating placeholder video...")
                generate_placeholder_video(segment_id, duration)
            else:
                raise

        progress_data["step"] = f"Generating voiceover for segment {segment_id}"
        progress_data["message"] = "Synthesizing voice."
        generate_voice(f"voice/{segment_id}.mp3", voiceover)
        
        progress_data["step"] = f"Merging segment {segment_id}"
        progress_data["message"] = "Merging voiceover and animation."
        merge_with_ffmpeg(f"segments/{segment_id}.webm", f"voice/{segment_id}.mp3", f"final_videos/{segment_id}.mp4")
        print("Done with segment:", segment_id)
    
    progress_data["step"] = "Merging final video"
    progress_data["message"] = "Merging all segments into one video."

    # Ensure the output folder exists.
    output_folder = "output"
    os.makedirs(output_folder, exist_ok=True)
    final_output_path = os.path.join(output_folder, output_filename)
    
    merge_videos("final_videos", final_output_path)
    
    progress_data["step"] = "Completed"
    progress_data["message"] = "Video generation completed."
    return True


if __name__ == "__main__":
    # For testing: compute a sanitized filename from the prompt (using the first 10 words).
    user_prompt = "explain binary search algorithm in detail using visuals and examples"
    filename_base = "_".join(user_prompt.split()[:10])
    raw_filename = f"{filename_base}.mp4"
    computed_filename = secure_filename(raw_filename)
    generate_video(user_prompt, computed_filename)
