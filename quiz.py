import google.generativeai as genai
from prompts import quiz_system_prompt
import re
import json

genai.configure(api_key="google-key")

def generate_quiz(script):
    model = genai.GenerativeModel("gemini-1.5-pro")

    full_text = "\n".join([s['voice_script'] for s in script])

    chat = model.start_chat()
    response = chat.send_message(quiz_system_prompt + "\n\nScript:\n" + full_text)
    text = response.text

    # Parse questions using regex
    questions = re.findall(
        r"Q:\s*(.*?)\nA\.\s*(.*?)\nB\.\s*(.*?)\nC\.\s*(.*?)\nD\.\s*(.*?)\nAnswer:\s*([A-D])",
        text,
        re.DOTALL
    )

    return questions[:10] if len(questions) >= 10 else []


if __name__ == "__main__":
    with open("scripts.json", "r", encoding="utf-8") as f:
        script = json.load(f)

    # Now pass it to the quiz generator
    questions = generate_quiz(script)

    print(questions)