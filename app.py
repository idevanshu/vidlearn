import streamlit as st
import json
import os
from main import generate_video
from quiz import generate_quiz

st.set_page_config(page_title="SigmaLearn", page_icon="🎬", layout="wide")

# --- Init session state ---
for key in ["script", "video_ready", "quiz_ready", "quiz", "video_bytes"]:
    if key not in st.session_state:
        st.session_state[key] = None

st.title("🎬 SigmaLearn - Educational Animation + Quiz")

with st.form("animation_form"):
    user_prompt = st.text_area(
        "What concept do you want to learn?",
        height=100,
        placeholder="Example: Explain Newton's Laws"
    )
    output_filename = st.text_input("Output filename", value="output.mp4")
    submitted = st.form_submit_button("Generate Video")

if submitted:
    if not user_prompt:
        st.error("Please enter a topic.")
    else:
        with st.spinner("Generating video..."):
            success = generate_video(user_prompt, output_filename)
            if success and os.path.exists(output_filename):
                with open(output_filename, "rb") as f:
                    video_bytes = f.read()

                with open("scripts.json", "r" , encoding="utf-8") as f:
                    script = json.load(f)
                    
                st.session_state.video_ready = True
                st.session_state.script = script
                st.session_state.video_bytes = video_bytes
                st.success("✅ Video generated successfully!")
            else:
                st.error("❌ Video generation failed.")

# --- Show video if generated ---
if st.session_state.video_ready:
    st.video(st.session_state.video_bytes)
    st.download_button("Download Video", st.session_state.video_bytes, file_name=output_filename)

    if not st.session_state.quiz_ready:
        if st.button("🧠 Generate Quiz"):
            with st.spinner("Generating quiz..."):
                quiz = generate_quiz(st.session_state.script)
                if quiz:
                    st.session_state.quiz = quiz
                    st.session_state.quiz_ready = True
                    st.success("✅ Quiz is ready!")
                else:
                    st.error("❌ Failed to generate quiz.")

# --- Display Quiz ---
if st.session_state.quiz_ready and st.session_state.quiz:
    st.markdown("### 📝 Quiz Based on the Video")
    quiz = st.session_state.quiz
    all_answered = True
    user_answers = {}

    for i, (q, a, b, c, d, correct) in enumerate(quiz, start=1):
        st.markdown(f"**Q{i}. {q.strip()}**")
        options = [a.strip(), b.strip(), c.strip(), d.strip()]
        selected = st.radio(f"Your answer:", options, key=f"radio_q{i}")
        if selected:
            selected_letter = ["A", "B", "C", "D"][options.index(selected)]
            user_answers[f"Q{i}"] = {
                "selected": selected_letter,
                "correct": correct,
                "text": selected
            }
        else:
            all_answered = False

    if st.button("✅ Submit Quiz", disabled=not all_answered):
        score = sum(1 for ans in user_answers.values() if ans["selected"] == ans["correct"])
        st.success(f"🎯 You scored {score} out of 10")

        with st.expander("🔍 See correct answers"):
            for i in range(1, 11):
                ans = user_answers.get(f"Q{i}")
                if ans:
                    st.markdown(
                        f"**Q{i}**: Your answer: {ans['selected']} | Correct: {ans['correct']} "
                        f"{'✅' if ans['selected'] == ans['correct'] else '❌'}"
                    )
