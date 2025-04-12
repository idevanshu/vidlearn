// src/components/VideoDashboard.jsx
import React, { useState, useRef, useEffect } from 'react';

function VideoDashboard() {
  const [prompt, setPrompt] = useState('');
  const [attachment, setAttachment] = useState(null);
  const [videoUrl, setVideoUrl] = useState('');
  const [progressMessage, setProgressMessage] = useState('');
  const [scriptData, setScriptData] = useState(null);
  const [quizData, setQuizData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [timerCount, setTimerCount] = useState('00:00');

  const progressIntervalRef = useRef(null);
  const timerIntervalRef = useRef(null);
  const timerStartRef = useRef(null);

  useEffect(() => {
    // Cleanup on unmount
    return () => {
      if (progressIntervalRef.current) clearInterval(progressIntervalRef.current);
      if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
    };
  }, []);

  const startTimer = () => {
    timerStartRef.current = Date.now();
    timerIntervalRef.current = setInterval(() => {
      const diff = Math.floor((Date.now() - timerStartRef.current) / 1000);
      const m = String(Math.floor(diff / 60)).padStart(2, '0');
      const s = String(diff % 60).padStart(2, '0');
      setTimerCount(`${m}:${s}`);
    }, 1000);
  };

  const stopTimer = () => {
    if (timerIntervalRef.current) {
      clearInterval(timerIntervalRef.current);
      timerIntervalRef.current = null;
    }
  };

  const startProgressPolling = () => {
    progressIntervalRef.current = setInterval(async () => {
      try {
        const res = await fetch('http://localhost:5000/progress', {
          credentials: 'include',
        });
        if (res.ok) {
          const progress = await res.json();
          const msg = `${progress.step}${progress.segment ? ' - ' + progress.segment : ''}: ${progress.message}`;
          setProgressMessage(msg);
        }
      } catch (err) {
        console.error('Error fetching progress:', err);
      }
    }, 1000);
  };

  const stopProgressPolling = () => {
    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current);
      progressIntervalRef.current = null;
    }
  };

  const handleGenerateVideo = async () => {
    if (!prompt) {
      alert('Please enter a topic');
      return;
    }
    setIsLoading(true);
    setProgressMessage('Starting video generation...');
    startProgressPolling();
    startTimer();

    const formData = new FormData();
    formData.append('prompt', prompt);
    if (attachment) formData.append('attachment', attachment);

    try {
      const res = await fetch('http://localhost:5000/generate-video', {
        method: 'POST',
        credentials: 'include',
        body: formData,
      });
      stopTimer();
      if (res.ok) {
        const data = await res.json();
        if (data.success) {
          setScriptData(data.script);
          setVideoUrl(`http://localhost:5000/download-video?filename=${data.filename}`);
          setProgressMessage('');
        } else {
          setProgressMessage(`Error: ${data.error}`);
        }
      } else {
        const errText = await res.text();
        setProgressMessage(`Error: ${errText}`);
      }
    } catch (err) {
      setProgressMessage(`Error: ${err.message}`);
    }
    stopProgressPolling();
    setIsLoading(false);
  };

  const handleGenerateQuiz = async () => {
    if (!scriptData) {
      alert('No script available');
      return;
    }
    setIsLoading(true);
    setProgressMessage('Generating quiz...');
    try {
      const res = await fetch('http://localhost:5000/generate-quiz', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ script: scriptData }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.success) {
          setQuizData(data.quiz);
          setProgressMessage('');
        } else {
          setProgressMessage(`Error: ${data.error}`);
        }
      } else {
        const errText = await res.text();
        setProgressMessage(`Error: ${errText}`);
      }
    } catch (err) {
      setProgressMessage(`Error: ${err.message}`);
    }
    setIsLoading(false);
  };

  const handleQuizSubmit = (e) => {
    e.preventDefault();
    let score = 0;
    quizData.forEach((q, i) => {
      const selected = document.querySelector(`input[name="question-${i}"]:checked`);
      if (selected && selected.value === q[5]) score++;
    });
    alert(`You scored ${score} out of ${quizData.length}`);
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow-md mb-8">
      <h2 className="text-2xl font-bold text-center mb-4">Gyanai Video Dashboard</h2>
      <div className="mb-4">
        <label className="block text-gray-700 font-semibold mb-2">
          What concept do you want to learn?
        </label>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          rows="4"
          placeholder="Example: Explain Newton's Laws"
          className="w-full p-3 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-400"
        ></textarea>
      </div>
      <div className="mb-4">
        <label className="block text-gray-700 font-semibold mb-2">
          Attach a PDF or image (optional):
        </label>
        <input
          type="file"
          onChange={(e) => setAttachment(e.target.files[0])}
          className="w-full p-3 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
      </div>
      <div className="text-center">
        <button
          onClick={handleGenerateVideo}
          className="bg-blue-500 hover:bg-blue-600 text-white font-semibold py-2 px-6 rounded"
        >
          Generate Video
        </button>
      </div>
      {isLoading && (
        <div className="flex items-center justify-center mt-4">
          <svg
            className="animate-spin h-6 w-6 text-blue-500 mr-2"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            ></circle>
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8v8H4z"
            ></path>
          </svg>
          <span className="text-blue-500 font-semibold">{progressMessage}</span>
        </div>
      )}
      {timerIntervalRef.current && (
        <div className="text-center text-blue-500 font-semibold mt-4">
          Timer: {timerCount}
        </div>
      )}
      {videoUrl && (
        <div className="bg-white p-6 rounded-lg shadow-md mt-8">
          <h2 className="text-2xl font-bold mb-4">Generated Video</h2>
          <video className="w-full" controls>
            <source src={videoUrl} type="video/mp4" />
            Your browser does not support the video tag.
          </video>
          <div className="text-center mt-4">
            <a
              href={videoUrl}
              download
              className="bg-green-500 hover:bg-green-600 text-white font-semibold py-2 px-4 rounded inline-block"
            >
              Download Video
            </a>
          </div>
          <div className="text-center mt-4">
            <button
              onClick={handleGenerateQuiz}
              className="bg-purple-500 hover:bg-purple-600 text-white font-semibold py-2 px-4 rounded"
            >
              Generate Quiz
            </button>
          </div>
        </div>
      )}
      {quizData && (
        <div className="bg-white p-6 rounded-lg shadow-md mt-8">
          <h2 className="text-2xl font-bold mb-4">Quiz Based on the Video</h2>
          <form onSubmit={handleQuizSubmit}>
            {quizData.map((q, i) => (
              <div key={i} className="mb-4 p-4 border rounded">
                <p className="font-semibold text-lg">
                  Q{i + 1}. {q[0].trim()}
                </p>
                {['A', 'B', 'C', 'D'].map((opt, j) => (
                  <div key={j} className="mt-2">
                    <label className="inline-flex items-center">
                      <input
                        type="radio"
                        name={`question-${i}`}
                        value={opt}
                        className="form-radio text-indigo-600"
                      />
                      {` ${q[j + 1].trim()}`}
                    </label>
                  </div>
                ))}
              </div>
            ))}
            <div className="text-center mt-4">
              <button
                type="submit"
                className="bg-blue-500 hover:bg-blue-600 text-white font-semibold py-2 px-4 rounded"
              >
                Submit Quiz
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}

export default VideoDashboard;
