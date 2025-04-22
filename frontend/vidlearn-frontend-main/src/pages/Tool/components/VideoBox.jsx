import React from "react";

function VideoBox({ videoUrl }) {
  return (
    <div className="video-box tool-row">
      <video src={videoUrl} controls />
      <div className="row">
        <a href={videoUrl} download>
          <button className="submit-btn">Download Video</button>
        </a>
        <a href="#" download>
          <button className="submit-btn">Download PDF</button>
        </a>
      </div>
    </div>
  );
}

export default VideoBox;
