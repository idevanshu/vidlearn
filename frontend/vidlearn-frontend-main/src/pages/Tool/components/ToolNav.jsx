import React from "react";
import ToolVideo from "./ToolVideo";
import { MdOutlineClose } from "react-icons/md";

function ToolNav({ open, handleNav, history }) {
  return (
    <div className={`tool-nav ${open ? "active" : ""}`}>
      <div className="top-box">
        <h3>Past Generations</h3>
        <button className="menu-icon" onClick={handleNav}>
          <MdOutlineClose aria-expanded={open} />
        </button>
      </div>
      <div className="vid-gallery">
        {history.map((item) => (
          <ToolVideo key={item.filename} vid={item.url} />
        ))}
      </div>
      <button className="logout-btn btn">Log Out</button>
    </div>
  );
}

export default ToolNav;
