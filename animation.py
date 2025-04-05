import asyncio
import base64
from pathlib import Path
from pyppeteer import launch
from jinja2 import Template

def generate_html(js_code, output_html_path="temp_render.html"):
    template_text = Path("base.html").read_text()
    template = Template(template_text)
    rendered_html = template.render(code=js_code)
    print("rendered template \n")
    Path(output_html_path).write_text(rendered_html, encoding="utf-8")
    return output_html_path


async def record_animation(html_path, segment_id, duration):
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