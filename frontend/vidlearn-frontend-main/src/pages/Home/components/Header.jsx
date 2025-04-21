import React from "react";

import Button from "../../../components/Button";
import Video from "../components/Video";
import Nav from "../components/Nav";

function Header({ children }) {
  return (
    <div className="container">
      <div className="nav">
        <Nav></Nav>
      </div>
      <div className="header-home">
        <div className="col col-left">
          <div>{children}</div>
          <Button text="Try It" link={"signup"} />
        </div>
        <div className="col">
          <Video></Video>
        </div>
      </div>
    </div>
  );
}

export default Header;
