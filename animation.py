import asyncio
import base64
from pathlib import Path
from jinja2 import Template

from helper import safe_launch

def generate_html(js_code, output_html_path="temp_render.html"):
    template_text = Path("base.html").read_text()
    template = Template(template_text)
    rendered_html = template.render(code=js_code)
    print("rendered template \n")
    Path(output_html_path).write_text(rendered_html, encoding="utf-8")
    return output_html_path


async def record_animation(html_path, segment_id, duration):
    CHROME_PATH = "C:/Program Files/Google/Chrome/Application/chrome.exe"

    browser = await safe_launch(
        headless=True,
        executablePath=CHROME_PATH,
        args=["--no-sandbox"]
    )

    try:
        page = await browser.newPage()
        page.on('console', lambda msg: print(f'[JS] {msg.text}'))

        await page.goto(f"file://{str(Path(html_path).absolute())}")
        print("✅ Page loaded")

        await page.waitForSelector("canvas")
        print("✅ Canvas found")

        await page.evaluate("""
            window.onerror = function(msg, src, line, col, err) {
                console.error("JSERROR: " + msg + " at " + line + ":" + col);
                return true;
            };
        """)

        print("🎥 Injecting CCapture setup and base64 save logic...")

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
                    try {{
                        capturer.capture(document.querySelector('canvas'));
                        frameCount++;

                        if (frameCount >= maxFrames) {{
                            console.log("⏱ Max frames reached: " + frameCount);
                            capturer.stop();
                            capturer.save(function(blob) {{
                                console.log("💾 capturer.save() called");
                                const reader = new FileReader();
                                reader.onloadend = function() {{
                                    console.log("📦 base64 generated");
                                    const base64Data = reader.result.split(',')[1];
                                    window.blobBase64 = base64Data;
                                }};
                                reader.onerror = function(e) {{
                                    console.error("❌ FileReader error", e);
                                }};
                                try {{
                                    reader.readAsDataURL(blob);
                                }} catch (err) {{
                                    console.error("❌ Failed to read blob:", err.message);
                                }}
                            }});
                        }} else {{
                            requestAnimationFrame(captureFrame);
                        }}
                    }} catch(e) {{
                        console.error("❌ Error during captureFrame:", e.message);
                    }}
                }}

                captureFrame();
            }} catch(e) {{
                console.error("❌ Top-level capture setup error:", e.message);
            }}
        """)

        print(f"🕒 Waiting {duration + 5} seconds for animation to complete...")
        await asyncio.sleep(duration + 5)

        # Wait for blobBase64 to be ready
        print("⏳ Waiting for blobBase64 to be set...")
        for i in range(30):  # wait up to ~30 seconds
            ready = await page.evaluate("typeof window.blobBase64 === 'string' && window.blobBase64.length > 1000")
            if ready:
                print("✅ Blob is ready!")
                break
            await asyncio.sleep(1)
        else:
            raise RuntimeError("❌ Timed out waiting for blob base64.")

        # Decode and save
        base64_str = await page.evaluate("window.blobBase64")
        video_data = base64.b64decode(base64_str)

        out_path = Path("segments") / f"{segment_id}.webm"
        out_path.parent.mkdir(exist_ok=True)
        out_path.write_bytes(video_data)
        print(f"✅ Video saved to {out_path}")

    finally:
        await browser.close()
        print("🚪 Browser closed")