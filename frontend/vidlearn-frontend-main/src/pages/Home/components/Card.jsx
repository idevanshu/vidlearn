import React from "react";

function Card({ text, color, children }) {
  return (
    <div className="card" style={{ background: color }}>
      {children}
      <p>{text}</p>
    </div>
  );
}

export default Card;
