import React from "react";

function VideoBox({ videoUrl }) {
  return (
    <div className="video-box tool-row">
      <video src={videoUrl} controls />
      <a href={videoUrl} download>
        <button className="submit-btn">Download Video</button>
      </a>
    </div>
  );
}

export default VideoBox;
