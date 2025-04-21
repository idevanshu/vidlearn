import React from "react";
import { useNavigate } from "react-router-dom";
import ToolVideo from "./ToolVideo";
import { MdOutlineClose } from "react-icons/md";

const API = import.meta.env.VITE_API_URL;

function ToolNav({ open, handleNav, history }) {
  const navigate = useNavigate();

  const handleLogout = async () => {
    await fetch(`${API}/logout`, {
      method: "POST",
      credentials: "include",
    });
    navigate("/login");
  };

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
      <button className="logout-btn btn" onClick={handleLogout}>
        Log Out
      </button>
    </div>
  );
}

export default ToolNav;
