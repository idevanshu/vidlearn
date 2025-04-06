from openai import OpenAI
import json
import asyncio
from pathlib import Path
from jinja2 import Template
import tempfile
import anthropic

from prompts import script_system_prompt, animation_system_prompt
from video import merge_with_ffmpeg, merge_videos
from animation import generate_html, record_animation
from helper import safe_launch, clear_folder, run_async_safely

openai_api = "openai-api"

claude_api = "claude-api"

client = OpenAI(api_key = openai_api)

client_claude = anthropic.Anthropic(api_key = claude_api)


def generate_claude(system_prompt, user_prompt):
    response = client_claude.messages.create(
        model="claude-3-7-sonnet-20250219",
        max_tokens = 8000,
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

user_prompt -> generate script -> generate animation + generate animations -> merge into one video

"""



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
    html_path.write_text(rendered , encoding = "utf-8")

    # Launch headless browser
    browser = await safe_launch(headless=True, args=["--no-sandbox"], executablePath = CHROME_PATH)
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

    has_js_error = any("JSERROR:" in log for log in logs)
    return (success and not has_js_error , logs)

def generate_valid_animation_code(prompt, max_attempts=3):
    past_error = ""
    for attempt in range(1, max_attempts + 1):
        print(f"🎯 Generating animation code (attempt {attempt})...")
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
    
    
def generate_video(user_prompt , output_path):
    script = generate_response(script_system_prompt , user_prompt)

    script = safe_parse_json(script)

    with open('scripts.json', 'w') as f:
        json.dump(script ,f)

    for segments in script:
        segment_id = segments["id"]
        voiceover = segments["voice_script"]
        animation = segments["animation"]
        duration = segments["duration"]

        animation_prompt = f"{animation} to last atleast {duration} seconds. The voiceover for this is {voiceover}"

        animation_code = generate_valid_animation_code(animation_prompt)

        html_path = generate_html(animation_code)

        run_async_safely(
            record_animation(html_path, segment_id, duration)
        )

        generate_voice(f"voice/{segment_id}.mp3" , voiceover)

        merge_with_ffmpeg( f"segments/{segment_id}.webm", f"voice/{segment_id}.mp3" , f"final_videos/{segment_id}.mp4")

        print("Done with: ", segment_id)
    
    merge_videos("final_videos", output_path)

    return True

if __name__ == "__main__":
    clear_folder("final_videos")
    clear_folder("segments")
    clear_folder("voice")

    user_prompt = "explain binary search algo"

    generate_video(user_prompt , "output.mp4")
