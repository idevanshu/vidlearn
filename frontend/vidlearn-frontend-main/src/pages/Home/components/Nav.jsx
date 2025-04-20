import React from "react";
import Logo from "../../../components/Logo";
import Button from "../../../components/Button";

function Nav() {
  return (
    <>
      <div className="nav-home">
        <Logo></Logo>
        <div className="ul-home">
          <Button clas={"primary"} text="Log In" link={"login"} />
          <Button text="Sign Up" link={"signup"} />
        </div>
      </div>
    </>
  );
}

export default Nav;
