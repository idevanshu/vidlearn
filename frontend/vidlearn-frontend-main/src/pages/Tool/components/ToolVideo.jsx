import React from "react";

function ToolVideo({ vid }) {
  return (
    <div>
      <video className="video-tool" src={vid} controls />
    </div>
  );
}

export default ToolVideo;
