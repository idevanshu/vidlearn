import React from "react";
import Logo from "../../../components/Logo";

import { RiMenu3Fill } from "react-icons/ri";

function ToolHeader({ open, handleNav }) {
  return (
    <div className="tool-header">
      <div className="header-row">
        <button
          className={`menu-icon secondary-icon ${open ? "hide" : ""}`}
          onClick={handleNav}
        >
          <RiMenu3Fill />
        </button>
      </div>
      <Logo />
    </div>
  );
}

export default ToolHeader;
