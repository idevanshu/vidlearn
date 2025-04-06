import streamlit as st
import json
import os

from main import generate_video , clear_folder

def main():
    clear_folder("final_videos")
    clear_folder("segments")
    clear_folder("voice")

    st.set_page_config(page_title="Educational Animation Generator", page_icon="🎬", layout="wide")
    
    st.title("🎬 Educational Animation Generator")
    st.write("Generate educational animations with synchronized voiceovers")
    
    with st.form("animation_form"):
        user_prompt = st.text_area(
            "What educational concept would you like to animate?", 
            height=100,
            placeholder="Example: Explain binary search algorithm"
        )
        
        output_filename = st.text_input(
            "Output filename", 
            value="output.mp4",
            help="The filename for your generated video (include .mp4 extension)"
        )
        
        submitted = st.form_submit_button("Generate Animation")
    
    if submitted:
        if not user_prompt:
            st.error("Please enter a prompt describing the educational concept.")
            return
        
        with st.spinner("Generating your educational animation..."):
            try:
                success = generate_video(user_prompt, output_filename)
                
                if success and os.path.exists(output_filename):
                    with open(output_filename, "rb") as video_file:
                        video_bytes = video_file.read()
                        
                    st.success(f"Animation successfully generated! Download below.")
                    st.video(video_bytes)
                    
                    st.download_button(
                        label="Download Video",
                        data=video_bytes,
                        file_name=output_filename,
                        mime="video/mp4"
                    )
                    
                    with open('scripts.json', 'r') as f:
                        script_data = json.load(f)
                    
                    with st.expander("View Generated Script"):
                        st.json(script_data)
                        
                else:
                    st.error("Failed to generate the animation. Please try again.")
            
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                st.exception(e)

if __name__ == "__main__":
    main()