import React from "react";

import Card from "./Card";
import { LuWandSparkles } from "react-icons/lu";
import { LuClapperboard } from "react-icons/lu";
import { RiVoiceAiFill } from "react-icons/ri";
import { MdOutlineQuiz } from "react-icons/md";

function Gallery() {
  return (
    <div className="gallery">
      <Card color="#a2b29f" text="Utilizes advanced AI for content creation">
        <LuWandSparkles className="icon" />
        <h3>AI Powered</h3>
      </Card>
      <Card color="#91a8d0" text="Automatically generates engaging animations">
        <LuClapperboard className="icon" />
        <h3>Animated Videos</h3>
      </Card>
      <Card color="#bda9c9" text="Provides clear and expressive narration">
        <RiVoiceAiFill className="icon" />
        <h3>Natural Voiceovers</h3>
      </Card>
      <Card color="#e3cba5" text="Enhances learning with instant quizzes">
        <MdOutlineQuiz className="icon" />
        <h3>Interactive Quizzes</h3>
      </Card>
    </div>
  );
}

export default Gallery;
