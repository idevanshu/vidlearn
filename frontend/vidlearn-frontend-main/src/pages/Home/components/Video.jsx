import React from "react";

function Video() {
  return (
    <div className="video">
      <div className="blob1 blob"></div>
      <div className="blob2 blob"></div>
      <div className="blob3 blob"></div>
      <div className="blob4 blob"></div>
      <video className="video-home" src="/videoFrontend.mp4" controls={true} />
    </div>
  );
}

export default Video;
