from openai import OpenAI
import json
import asyncio
import os
from pathlib import Path

from prompts import script_system_prompt, animation_system_prompt
from video import merge_with_ffmpeg, merge_videos
from animation import generate_html, record_animation

openai_api = "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"

client = OpenAI(api_key = openai_api)

"""
Pipeline:

user_prompt -> generate script -> generate animation + generate animations -> merge into one video

"""
def clear_folder(folder_path):
    folder = Path(folder_path)
    if not folder.exists():
        print(f"⚠️ Folder '{folder}' does not exist.")
        return

    for item in folder.iterdir():
        try:
            if item.is_file() or item.is_symlink():
                item.unlink()
            elif item.is_dir():
                # Recursively delete all contents
                for root, dirs, files in os.walk(item, topdown=False):
                    for file in files:
                        Path(root, file).unlink()
                    for subdir in dirs:
                        Path(root, subdir).rmdir()
                item.rmdir()
        except Exception as e:
            print(f"❌ Failed to delete {item}: {e}")

    print(f"✅ Cleared contents of folder: {folder}")


def generate_response(system_prompt, user_prompt):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role":"system" , "content":system_prompt},
            {"role":"user", "content":user_prompt}
        ]
    )

    return response.choices[0].message.content

async def validate_code_in_browser(js_code):

    CHROME_PATH = "C:/Program Files/Google/Chrome/Application/chrome.exe"
    from pyppeteer import launch
    from pathlib import Path
    from jinja2 import Template
    import tempfile

    # Inject code into HTML template
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
    html_path.write_text(rendered)

    # Launch headless browser
    browser = await launch(headless=True, args=["--no-sandbox"], executablePath = CHROME_PATH)
    page = await browser.newPage()
    logs = []

    # Capture console logs
    page.on("console", lambda msg: logs.append(msg.text))

    try:
        await page.goto(f"file://{html_path}")
        await asyncio.sleep(3)  # give animation a second to start
        success = await page.evaluate("window.__animationLoaded === true")
    except Exception as e:
        success = False
    finally:
        await browser.close()

    # Check logs for any JS errors
    has_js_error = any("JSERROR:" in log for log in logs)
    return success and not has_js_error

def generate_valid_animation_code(prompt, max_attempts=3):
    for attempt in range(1, max_attempts + 1):
        print(f"🎯 Generating animation code (attempt {attempt})...")
        raw_code = generate_response(animation_system_prompt, prompt)
        clean_code = extract_js_code(raw_code)

        try:
            is_valid = asyncio.run(validate_code_in_browser(clean_code))
        except Exception as e:
            print(f"⚠️ Validation failed: {e}")
            is_valid = False

        if is_valid:
            print("✅ Valid animation code generated.")
            return clean_code
        else:
            print("❌ Code invalid or has JS errors. Retrying...")

    raise RuntimeError("❌ All attempts to generate valid animation code failed.")

def generate_voice(save_file_path , script):
    with client.audio.speech.with_streaming_response.create(
        model="gpt-4o-mini-tts",
        voice="alloy",
        input=script,
        instructions="Speak in a teacher-like tone, in a professional manner, stay positive and human, never shout",
    ) as response:
        response.stream_to_file(save_file_path)


def safe_parse_json(gpt_output):
    try:
        # Strip code fences if present
        if gpt_output.startswith("```json"):
            gpt_output = gpt_output.strip()[7:-3].strip()  # remove ```json and ending ```
        elif gpt_output.startswith("```"):
            gpt_output = gpt_output.strip()[3:-3].strip()

        return json.loads(gpt_output)
    except json.JSONDecodeError as e:
        print("❌ JSON parsing failed:", e)
        return None
    
def extract_js_code(gpt_output: str) -> str:
    """
    Extracts raw JavaScript code from a Markdown code block like ```javascript ... ```
    """
    if gpt_output.startswith("```javascript"):
        # Remove the first line and last line
        lines = gpt_output.strip().splitlines()
        return "\n".join(lines[1:-1]).strip()
    elif gpt_output.startswith("```"):
        # In case it just uses ``` without specifying language
        lines = gpt_output.strip().splitlines()
        return "\n".join(lines[1:-1]).strip()
    return gpt_output.strip()

if __name__ == "__main__":
    clear_folder("final_videos")
    clear_folder("segments")
    clear_folder("voice")

    user_prompt = "explain democracy"

    script = generate_response(script_system_prompt , user_prompt)

    script = safe_parse_json(script)

    for segments in script:
        segment_id = segments["id"]
        voiceover = segments["voice_script"]
        animation = segments["animation"]
        duration = segments["duration"]

        animation_prompt = f"{animation} to last atleast {duration} seconds. The voiceover for this is {voiceover}"

        animation_code = generate_valid_animation_code(animation_prompt)

        html_path = generate_html(animation_code)

        asyncio.run(
            record_animation(html_path, segment_id, duration)
        )

        generate_voice(f"voice/{segment_id}.mp3" , voiceover)

        merge_with_ffmpeg( f"segments/{segment_id}.webm", f"voice/{segment_id}.mp3" , f"final_videos/{segment_id}.mp4")

        print("Done with: ", segment_id)
    
    merge_videos("final_videos", "output.mp4" )
