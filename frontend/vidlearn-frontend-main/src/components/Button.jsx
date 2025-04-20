import React from "react";

function Button({ clas, link, text }) {
  return (
    <a href={`${link}`}>
      <button className={`${clas} btn`}>{text}</button>
    </a>
  );
}

export default Button;
