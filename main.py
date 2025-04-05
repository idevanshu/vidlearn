from openai import OpenAI
import json
from jinja2 import Template
from pathlib import Path
import asyncio
from pyppeteer import launch

from prompts import script_system_prompt, animation_system_prompt

openai_api = "your-api-key-here"

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

async def record_animation(html_path, segment_id, duration=10):
    CHROME_PATH = "C:/Program Files/Google/Chrome/Application/chrome.exe"
    browser = await launch(
        headless=True,
        executablePath=CHROME_PATH,
        args=["--no-sandbox"]
    )
    
    try:
        page = await browser.newPage()
        
        # Enable console logging from the browser
        page.on('console', lambda msg: print(f'BROWSER LOG: {msg.text}'))
        
        await page.goto(f"file://{str(Path(html_path).absolute())}")
        print("Page loaded")
        
        await page.waitForSelector("canvas")
        print("Canvas found")
        
        # Test if basic evaluation works
        result = await page.evaluate("console.log('Hello from pyppeteer'); true;")
        print(f"Simple JS result: {result}")
        
        # Set up window.onerror to catch JavaScript errors
        await page.evaluate("""
        window.onerror = function(message, source, lineno, colno, error) {
            console.error('JavaScript error:', message, 'at line', lineno, ':', error);
            return true;
        };
        """)
        
        print("Setting up CCapture...")
        # Create capture object
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

                function captureFrame() {{
                    capturer.capture(document.querySelector('canvas'));
                    frameCount++;
                    if (frameCount >= maxFrames) {{
                        capturer.stop();
                        capturer.save(function(blob) {{
                            const file = new File([blob], "{segment_id}.webm", {{ type: "video/webm" }});
                            saveAs(file);
                            console.log("✅ Saved as {segment_id}.webm");
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
        
        print(f"Waiting {duration + 5} seconds for recording to complete...")
        await asyncio.sleep(duration + 5)
        print("Wait completed")
        
    finally:
        await browser.close()
        print("Browser closed")

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


if __name__ == "__main__":
    

    user_prompt = "explain linear algebra"

    script = generate_response(script_system_prompt , user_prompt)

    with open("scripts.json") as f:
        script = json.load(f)

    for segments in script:
        segment_id = segments["id"]
        voiceover = segments["voice_script"]
        animation = segments["animation"]
        duration = segments["duration"]

        animation_prompt = f"{animation} to last atleast {duration} seconds"

        animation_code = generate_response(animation_system_prompt , animation_prompt)

        animation_code = extract_js_code(animation_code)

        html_path = generate_html(animation_code)

        asyncio.run(
            record_animation(html_path, segment_id, duration)
        )

        generate_voice(f"voice/{segment_id}.mp3" , voiceover)

        merge_with_ffmpeg( f"segments/{segment_id}.webm", f"voice/{segment_id}.mp3" , f"final_videos/{segment_id}.mp4")

        break
