import os
import json
import asyncio
from pathlib import Path
from jinja2 import Template
import tempfile
import anthropic
from openai import OpenAI
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import shutil
from prompts import script_system_prompt, animation_system_prompt
from video import merge_with_ffmpeg, merge_videos
from animation import generate_html, record_animation
from helper import safe_launch, clear_folder, run_async_safely
from progress import set_progress  # using our shared progress module
import shutil

load_dotenv()

# API keys from env variables
openai_api = os.getenv("OPENAI_API_KEY")
claude_api = os.getenv("CLAUDE_API_KEY")

client = OpenAI(api_key=openai_api)
client_claude = anthropic.Anthropic(api_key=claude_api)

if os.name == "nt":  # Windows
    possible_paths = [
        os.getenv("CHROME_PATH"),
        shutil.which("chrome"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    ]
    # Select the first path that is not None and exists on disk.
    CHROME_PATH = next((p for p in possible_paths if p and os.path.exists(p)), None)
    if not CHROME_PATH:
        # Fallback: assume "chrome" is in the PATH.
        CHROME_PATH = "chrome"
else:
    # Linux / Unix. Try the common binary names or a default location.
    CHROME_PATH = (
        os.getenv("CHROME_PATH") or
        shutil.which("google-chrome-stable") or
        shutil.which("google-chrome") or
        shutil.which("chromium-browser") or
        shutil.which("chromium") or
        shutil.which("chrome") or
        "/usr/bin/google-chrome"
    )

print("Using Chrome path:", CHROME_PATH)

# <----------------------Generation Section---------------------->

def generate_response(msg_history, model = "gpt-4o"):
    response = client.chat.completions.create(
        model=model,
        messages=msg_history
    )
    return response.choices[0].message.content

def generate_voice(save_file_path, script):
    with client.audio.speech.with_streaming_response.create(
        model="gpt-4o-mini-tts",
        voice="alloy",
        input=script
    ) as response:
        response.stream_to_file(save_file_path)

# <----------------------Cleaning Section---------------------->

def extract_code_from_response(content):
    # Assuming content is a string or an iterable of blocks:
    if isinstance(content, str):
        return content
    for block in content:
        if hasattr(block, 'type') and block.type == 'text':
            return block.text
    return None

def safe_parse_json(gpt_output):
    try:
        if gpt_output.startswith("```json"):
            gpt_output = gpt_output.strip()[7:-3].strip()
        elif gpt_output.startswith("```"):
            gpt_output = gpt_output.strip()[3:-3].strip()
        return json.loads(gpt_output)
    except json.JSONDecodeError as e:
        print("❌ JSON parsing failed:", e)
        return None

# <----------------------Animation Section---------------------->

def generate_valid_animation_code(prompt, max_attempts=3):
    past_error = ""
    msg_history = [
            {"role": "system", "content": animation_system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    for attempt in range(1, max_attempts + 1):
        print(f"🎯 Generating animation code (attempt {attempt})...")
        set_progress({"step": f"Generating animation code (attempt {attempt})", "message": prompt})
        clean_code = generate_response(msg_history, model = "o4-mini-2025-04-16")
        print("Generated code:", clean_code)  # Log the generated code
        try:
            is_valid, logs = run_async_safely(validate_code_in_browser(clean_code))
            print("Validation logs:", logs)  # Log any validation messages
            past_error = "\n".join(logs) if logs and isinstance(logs, list) else str(logs)
            print("error: ", past_error)
        except Exception as e:
            print(f"⚠️ Validation failed: {e}")
            is_valid = False

        if is_valid:
            print("✅ Valid animation code generated.")
            return clean_code
        else:
            msg_history.append({"role": "system", "content":clean_code})
            msg_history.append({"role":"user", "content":f"the code isnt working and has error: {past_error}. try again to make animation {prompt}"})
            print("❌ Code invalid or has JS errors. Retrying...")
            # print(clean_code)
    # Instead of stopping all generation, we now raise an error that will be caught outside.
    raise RuntimeError("❌ All attempts to generate valid animation code failed.")


async def validate_code_in_browser(js_code):
    # HTML template that loads p5.js and tries to run the animation code
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
        await asyncio.sleep(3)
        success = await page.evaluate("window.__animationLoaded === true")
    except Exception as e:
        success = False
    finally:
        await browser.close()
    has_js_error = any("JSERROR:" in log for log in logs)
    return (success and not has_js_error, logs)


def generate_placeholder_video(segment_id, duration):
    placeholder_video_path = f"segments/{segment_id}.webm"
    cmd = (
        f"ffmpeg -y -f lavfi -i color=c=black:s=1280x720:d={duration} "
        f"-c:v libvpx -crf 10 -b:v 1M {placeholder_video_path}"
    )
    os.system(cmd)
    print(f"Placeholder video created for segment {segment_id} with duration {duration}s.")

def generate_video(user_prompt, output_filename, username):
    try:
        # Update progress: initialize and clear folders.
        set_progress({"step": "Initializing", "message": "Clearing folders and starting generation"}, user_id="global")
        clear_folder("final_videos")
        clear_folder("segments")
        clear_folder("voice")

        msg_history_voice = [
            {"role": "system", "content": script_system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # Generate video script from the prompt.
        set_progress({"step": "Generating script", "message": "Using prompt to generate the video script"}, user_id="global")
        script = generate_response(msg_history_voice)
        script = safe_parse_json(script)
        if not script:
            raise RuntimeError("Script generation returned invalid JSON")
        with open('scripts.json', 'w') as f:
            json.dump(script, f)

        set_progress({"step": "Script generated", "message": "Proceeding to segment processing"}, user_id="global")

        # Process each segment.
        for segment in script:
            segment_id = segment["id"]
            voiceover = segment["voice_script"]
            animation = segment["animation"]
            duration = segment["duration"]

            set_progress({"step": f"Processing segment {segment_id}", "message": "Generating animation code"}, user_id="global")
            animation_prompt = f"{animation} to last at least {duration} seconds. The voiceover for this is {voiceover}"
            try:
                animation_code = generate_valid_animation_code(animation_prompt)
            except RuntimeError as e:
                print(f"⚠️ Warning: Animation code generation for segment {segment_id} failed: {e}")
                set_progress({"step": f"Error in segment {segment_id}", "message": "Failed to generate animation code, using placeholder video"}, user_id="global")
                animation_code = None

            if animation_code is not None:
                html_path = generate_html(animation_code)
                set_progress({"step": f"Recording animation for segment {segment_id}", "message": "Capturing animation with headless browser"}, user_id="global")
                try:
                    run_async_safely(record_animation(html_path, segment_id, duration))
                except Exception as e:
                    err_str = str(e)
                    if "Timed out waiting for blob base64" in err_str or "Waiting for selector" in err_str:
                        set_progress({"step": f"Timeout for segment {segment_id}", "message": "Using placeholder video"}, user_id="global")
                        print(f"⚠️ Warning: Animation for segment {segment_id} timed out. Generating placeholder video...")
                        generate_placeholder_video(segment_id, duration)
                    else:
                        set_progress({"step": f"Error in recording segment {segment_id}", "message": str(e)}, user_id="global")
                        print(f"⚠️ Warning: Error encountered during recording of segment {segment_id}. Using placeholder video instead.")
                        generate_placeholder_video(segment_id, duration)
            else:
                set_progress({"step": f"Using placeholder for segment {segment_id}", "message": "No valid animation code generated."}, user_id="global")
                generate_placeholder_video(segment_id, duration)

            set_progress({"step": f"Generating voiceover for segment {segment_id}", "message": "Synthesizing voice"}, user_id="global")
            generate_voice(f"voice/{segment_id}.mp3", voiceover)

            set_progress({"step": f"Merging segment {segment_id}", "message": "Merging voiceover and animation"}, user_id="global")
            merge_with_ffmpeg(f"segments/{segment_id}.webm", f"voice/{segment_id}.mp3", f"final_videos/{segment_id}.mp4")
            print("Done with segment:", segment_id)

        set_progress({"step": "Merging final video", "message": "Merging all segments into one video"}, user_id="global")
        # Save the final video to a user-specific folder.
        user_output_folder = os.path.join("output", f"{username}_output")
        os.makedirs(user_output_folder, exist_ok=True)
        final_output_path = os.path.join(user_output_folder, output_filename)
        merge_videos("final_videos", final_output_path)

        set_progress({"step": "Completed", "message": "Video generation completed"}, user_id="global")
        return True

    except Exception as e:
        set_progress({"step": "Error", "message": str(e)}, user_id="global")
        raise


if __name__ == "__main__":
    user_prompt = "explain thermodynamics in short"
    filename_base = "_".join(user_prompt.split()[:10])
    raw_filename = f"{filename_base}.mp4"
    computed_filename = secure_filename(raw_filename)
    generate_video(user_prompt, computed_filename, username="dev")
