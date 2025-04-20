import React from "react";

import Header from "./components/Header";
import About from "./components/About";
import Footer from "../../components/Footer";
import "./Home.css";

function Home() {
  return (
    <div className="container-wrapper">
      <Header>
        <h1>Effortless creation of educational videos with AI</h1>
        <br />
        <p>
          Simply provide a topic and let GyanAI create an animated video with
          stunning visuals.
        </p>
      </Header>
      <About />
      <Footer />
    </div>
  );
}

export default Home;
