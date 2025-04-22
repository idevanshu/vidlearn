import React, { useRef, useEffect } from "react";

function PromptBox({
  prompt,
  handleChange,
  handleFileUpload,
  handleSubmit,
  loading,
  timeValue,
  handleSliderChange,
}) {
  const inputRef = useRef(null);
  const ref = useRef();

  const adjust = () => {
    const el = ref.current;
    el.style.height = "auto";
    el.style.height = el.scrollHeight + "px";
  };

  useEffect(adjust, []);

  const handleDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files.length) {
      handleFileUpload({ target: { files: e.dataTransfer.files } });
    }
  };

  const handleClick = () => {
    inputRef.current.click();
  };

  return (
    <div className="prompt-box tool-row">
      <h3 className="row">What educational concept would you like to learn?</h3>
      <textarea
        value={prompt}
        onChange={handleChange}
        placeholder="Explain Thermodynamics First Law"
        rows="5"
        onInput={adjust}
        ref={ref}
      />

      <div className="row">
        <label htmlFor="time-slider">Video Length: {timeValue} mins</label>
        <input
          type="range"
          id="time-slider"
          min="1"
          max="10"
          step="1"
          value={timeValue}
          onChange={handleSliderChange}
          className="slider"
        />
      </div>

      <div className="row">
        <div
          className="upload-box"
          onClick={handleClick}
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
        >
          Drop a PDF or click to browse
          <input
            type="file"
            accept=".pdf,.doc,.docx"
            ref={inputRef}
            onChange={handleFileUpload}
            style={{ display: "none" }}
          />
        </div>
        <button
          className="submit-btn"
          onClick={handleSubmit}
          disabled={loading}
        >
          {loading ? "Generating..." : "Generate Video"}
        </button>
      </div>
    </div>
  );
}

export default PromptBox;
