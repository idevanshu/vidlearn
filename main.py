from openai import OpenAI
from prompts import script_system_prompt, animation_system_prompt

openai_api = "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"

client = OpenAI(api_key = openai_api)


def generate_response(system_prompt, user_prompt):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role":"system" , "content":system_prompt},
            {"role":"user", "content":user_prompt}
        ]
    )

    return response.choices[0].message.content

def generate_voice(save_file_path):
    with client.audio.speech.with_streaming_response.create(
        model="gpt-4o-mini-tts",
        voice="coral",
        input="Today is a wonderful day to build something people love!",
        instructions="Speak in a cheerful and positive tone.",
    ) as response:
        response.stream_to_file(save_file_path)

if __name__ == "__main__":
    pass