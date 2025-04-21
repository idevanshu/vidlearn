import React, { useState, useEffect } from "react";
import ToolNav from "./components/ToolNav";
import PromptBox from "./components/PromptBox";
import ToolHeader from "./components/ToolHeader";
import VideoBox from "./components/VideoBox";
import "./Tool.css";

import { PacmanLoader } from "react-spinners";

const API = import.meta.env.VITE_API_URL;

function Tool() {
  const [open, setOpen] = useState(false);
  const [prompt, setPrompt] = useState("");
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [videoUrl, setVideoUrl] = useState("");
  const [history, setHistory] = useState([]);

  // fetch past generations on mount
  useEffect(() => {
    fetch(`${API}/history`, {
      credentials: "include",
    })
      .then((res) => res.json())
      .then((data) =>
        setHistory(
          data.map((v) => ({
            ...v,
            url: `${API}/download-video?filename=${v.filename}`,
          }))
        )
      )
      .catch(console.error);
  }, []);

  const handleNav = (e) => {
    e.preventDefault();
    setOpen(!open);
  };

  const handleChange = (e) => {
    setPrompt(e.target.value);
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const form = new FormData();
    form.append("attachment", file);

    const res = await fetch(`${API}/upload-pdf`, {
      method: "POST",
      credentials: "include",
      body: form,
    });
    const data = await res.json();
    if (res.ok) {
      console.log("Uploaded PDF as:", data.filename);
      setFile(file); // still keep the file around if you want to send it again
    } else {
      alert(data.error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!prompt) return alert("Please enter a prompt.");

    setLoading(true);
    const form = new FormData();
    form.append("prompt", prompt);
    if (file) form.append("attachment", file);

    try {
      const res = await fetch(`${API}/generate-video`, {
        method: "POST",
        credentials: "include",
        body: form,
      });
      const data = await res.json();
      if (res.ok) {
        const url = `${API}/download-video?filename=${data.filename}`;
        setVideoUrl(url);
        // prepend to history
        setHistory((prev) => [
          { filename: data.filename, url, prompt_text: prompt },
          ...prev,
        ]);
      } else {
        alert(data.error || "Generation failed");
      }
    } catch (err) {
      console.error(err);
      alert("Network error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <ToolNav open={open} handleNav={handleNav} history={history} />
      <div className="container-wrapper">
        <div className="container tool">
          <ToolHeader open={open} handleNav={handleNav} />
          <div className="tool-row" style={{ justifyContent: "center" }}>
            <h1 className="fancy-font">Generate an educational video</h1>
          </div>
          <PromptBox
            prompt={prompt}
            handleChange={handleChange}
            handleFileUpload={handleFileUpload}
            handleSubmit={handleSubmit}
            loading={loading}
          />
          {videoUrl && (
            <div className="tool-row">
              <h2>Generated Video:</h2>
            </div>
          )}
          {loading ? (
            <>
              <div className="tool-row">
                <h2>Generating Video:</h2>
              </div>

              <PacmanLoader color="#ff7f3e" />
              <h2
                style={{
                  color: "#604cc3",
                  textAlign: "center",
                  fontSize: "25px",
                }}
              >
                Pac-Man is chomping frames… your video will be ready shortly!
              </h2>
            </>
          ) : (
            ""
          )}

          {videoUrl && <VideoBox videoUrl={videoUrl} loading={loading} />}
        </div>
      </div>
    </>
  );
}

export default Tool;
