import React from "react";

import AboutText from "./AboutText";
import Gallery from "./Gallery";

function About() {
  return (
    <div className="container">
      <div className="about">
        <AboutText />
        <Gallery />
      </div>
    </div>
  );
}

export default About;
