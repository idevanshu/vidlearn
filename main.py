from openai import OpenAI
import json
from jinja2 import Template
from pathlib import Path
import asyncio
from pyppeteer import launch
import os

from prompts import script_system_prompt, animation_system_prompt

openai_api = "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"

client = OpenAI(api_key = openai_api)

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

def generate_voice(save_file_path , script):
    with client.audio.speech.with_streaming_response.create(
        model="gpt-4o-mini-tts",
        voice="coral",
        input=script,
        instructions="Speak in a teacher-like tone, in a professional manner, stay positive and human",
    ) as response:
        response.stream_to_file(save_file_path)


def generate_html(js_code, output_html_path="temp_render.html"):
    template_text = Path("base.html").read_text()
    template = Template(template_text)
    rendered_html = template.render(code=js_code)
    print("rendered template \n")
    Path(output_html_path).write_text(rendered_html, encoding="utf-8")
    return output_html_path

import asyncio
import base64
from pathlib import Path
from pyppeteer import launch

async def record_animation(html_path, segment_id, duration=10):
    CHROME_PATH = "C:/Program Files/Google/Chrome/Application/chrome.exe"

    browser = await launch(
        headless=True,
        executablePath=CHROME_PATH,
        args=["--no-sandbox"]
    )

    try:
        page = await browser.newPage()
        page.on('console', lambda msg: print(f'BROWSER LOG: {msg.text}'))

        await page.goto(f"file://{str(Path(html_path).absolute())}")
        print("✅ Page loaded")

        await page.waitForSelector("canvas")
        print("✅ Canvas found")

        # Set up error logging
        await page.evaluate("""
            window.onerror = function(message, source, lineno, colno, error) {
                console.error('JavaScript error:', message, 'at line', lineno, ':', error);
                return true;
            };
        """)

        print("🎥 Setting up CCapture and base64 blob handling...")

        await page.evaluate(f"""
            try {{
                const capturer = new CCapture({{
                    format: 'webm',
                    framerate: 60,
                    name: '{segment_id}'
                }});
                capturer.start();

                let frameCount = 0;
                const maxFrames = {duration * 60};

                window.blobBase64 = null;

                function captureFrame() {{
                    capturer.capture(document.querySelector('canvas'));
                    frameCount++;

                    if (frameCount >= maxFrames) {{
                        capturer.stop();
                        capturer.save(function(blob) {{
                            const reader = new FileReader();
                            reader.onloadend = function() {{
                                const base64Data = reader.result.split(',')[1]; // strip data URI
                                window.blobBase64 = base64Data;
                                console.log("✅ Blob base64 ready.");
                            }};
                            reader.readAsDataURL(blob);
                        }});
                    }} else {{
                        requestAnimationFrame(captureFrame);
                    }}
                }}

                captureFrame();
            }} catch (e) {{
                console.error("Capture setup error:", e);
            }}
        """)

        # Wait for animation + blob to be ready
        print(f"🕒 Waiting {duration + 5} seconds for recording...")
        await asyncio.sleep(duration + 5)

        # Wait until blob is populated
        for i in range(10):
            ready = await page.evaluate("window.blobBase64 !== null")
            if ready:
                break
            await asyncio.sleep(1)

        if not ready:
            raise RuntimeError("❌ Timed out waiting for blob base64.")

        # Retrieve and decode base64
        base64_str = await page.evaluate("window.blobBase64")
        video_data = base64.b64decode(base64_str)

        # Save to segments/ folder
        out_path = Path("segments") / f"{segment_id}.webm"
        out_path.parent.mkdir(exist_ok=True)
        out_path.write_bytes(video_data)
        print(f"✅ Video saved to {out_path}")

    finally:
        await browser.close()
        print("🚪 Browser closed")


import subprocess
from pathlib import Path

def merge_with_ffmpeg(video_path, audio_path, output_path):
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    command = [
        "ffmpeg",
        "-y",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        str(output_path)
    ]

    try:
        subprocess.run(command, check=True)
        print(f"✅ Merged into {output_path}")
    except subprocess.CalledProcessError as e:
        print("❌ FFmpeg failed:", e)

def merge_videos(folder_path, output_path):
    folder = Path(folder_path).resolve()  # Make absolute path
    video_files = sorted(folder.glob("segment_*.mp4"))

    if not video_files:
        print("❌ No .mp4 files found in folder.")
        return

    concat_file = folder / "concat_list.txt"

    # Use absolute paths in list file
    with open(concat_file, "w", encoding="utf-8") as f:
        for file in video_files:
            f.write(f"file '{file.as_posix()}'\n")

    # Build FFmpeg command
    command = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        str(Path(output_path).resolve())
    ]

    try:
        subprocess.run(command, check=True)
        print(f"✅ Merged into {output_path}")
    except subprocess.CalledProcessError as e:
        print("❌ FFmpeg failed to stitch videos:", e)

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

if __name__ == "__main__":
    

    user_prompt = "explain linear algebra"

    # script = generate_response(script_system_prompt , user_prompt)

    # script = safe_parse_json(script)

    # for segments in script:
    #     segment_id = segments["id"]
    #     voiceover = segments["voice_script"]
    #     animation = segments["animation"]
    #     duration = segments["duration"]

    #     animation_prompt = f"{animation} to last atleast {duration} seconds"

    #     animation_code = generate_response(animation_system_prompt , animation_prompt)

    #     animation_code = extract_js_code(animation_code)

    #     html_path = generate_html(animation_code)

    #     asyncio.run(
    #         record_animation(html_path, segment_id, duration)
    #     )

    #     generate_voice(f"voice/{segment_id}.mp3" , voiceover)

    #     merge_with_ffmpeg( f"segments/{segment_id}.webm", f"voice/{segment_id}.mp3" , f"final_videos/{segment_id}.mp4")

    #     print("Done with: ", segment_id)
    
    merge_videos("final_videos", "output.mp4" )
