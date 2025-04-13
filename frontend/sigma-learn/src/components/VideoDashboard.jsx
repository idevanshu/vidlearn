import React, { useState, useRef, useEffect, useCallback } from 'react';

function VideoDashboard() {
  const [prompt, setPrompt] = useState('');
  const [attachment, setAttachment] = useState(null);
  const [videoUrl, setVideoUrl] = useState('');
  const [progressMessage, setProgressMessage] = useState('');
  const [scriptData, setScriptData] = useState(null);
  const [quizData, setQuizData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [timerCount, setTimerCount] = useState('00:00');
  const [history, setHistory] = useState([]);

  // Modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedVideo, setSelectedVideo] = useState(null);
  const [selectedQuiz, setSelectedQuiz] = useState(null);

  const progressIntervalRef = useRef(null);
  const timerIntervalRef = useRef(null);
  const timerStartRef = useRef(null);

  const baseUrl = process.env.REACT_APP_API_URL || '';

  const fetchHistory = useCallback(async () => {
    try {
      const res = await fetch(`${baseUrl}/history`, { credentials: 'include' });
      if (res.ok) {
        const data = await res.json();
        setHistory(data);
      } else {
        console.error("Failed to load history");
      }
    } catch (err) {
      console.error("Error fetching history:", err);
    }
  }, [baseUrl]);

  useEffect(() => {
    // Fetch history on mount.
    fetchHistory();
  }, [fetchHistory]);

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
        const res = await fetch(`${baseUrl}/progress`, { credentials: 'include' });
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
      const res = await fetch(`${baseUrl}/generate-video`, {
        method: 'POST',
        credentials: 'include',
        body: formData,
      });
      stopTimer();
      if (res.ok) {
        const data = await res.json();
        if (data.success) {
          setScriptData(data.script);
          setVideoUrl(`${baseUrl}/download-video?filename=${data.filename}`);
          setProgressMessage('');
          fetchHistory(); // Refresh history after generating a video.
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
      const res = await fetch(`${baseUrl}/generate-quiz`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ script: scriptData }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.success) {
          setQuizData(data.quiz);
          setSelectedQuiz(data.quiz);
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
    selectedQuiz.forEach((q, i) => {
      const selected = document.querySelector(`input[name="question-${i}"]:checked`);
      if (selected && selected.value === q[5]) score++;
    });
    alert(`You scored ${score} out of ${selectedQuiz.length}`);
  };

  // Handler for opening the modal with a selected video from history.
  const openModal = (video) => {
    setSelectedVideo(video);
    setVideoUrl(`${baseUrl}/download-video?filename=${video.filename}`);
    setModalOpen(true);
  };

  const closeModal = () => {
    setModalOpen(false);
    setSelectedVideo(null);
    setSelectedQuiz(null);
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow-md mb-8">
      <h2 className="text-3xl font-bold text-center mb-6">Gyanai Video Dashboard</h2>
      
      {/* Video Generation Form */}
      <div className="mb-6">
        <label className="block text-xl font-semibold text-gray-800 mb-2">
          What concept do you want to learn?
        </label>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          rows="4"
          placeholder="Example: Explain Newton's Laws"
          className="w-full p-4 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-400"
        ></textarea>
      </div>
      <div className="mb-6">
        <label className="block text-xl font-semibold text-gray-800 mb-2">
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
          className="bg-blue-600 hover:bg-blue-700 text-white py-3 px-8 rounded transition duration-150"
        >
          Generate Video
        </button>
      </div>
      
      {isLoading && (
        <div className="flex items-center justify-center mt-6">
          <svg
            className="animate-spin h-6 w-6 text-blue-600 mr-3"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8v8H4z"
            ></path>
          </svg>
          <span className="text-blue-600 font-medium">{progressMessage}</span>
        </div>
      )}
      {timerIntervalRef.current && (
        <div className="text-center text-blue-600 font-medium mt-4">
          Timer: {timerCount}
        </div>
      )}
      
      {videoUrl && (
        <div className="bg-gray-50 p-6 rounded-lg shadow-md mt-8">
          <h2 className="text-2xl font-bold mb-4">Generated Video</h2>
          <video className="w-full rounded" controls>
            <source src={videoUrl} type="video/mp4" />
            Your browser does not support the video tag.
          </video>
          <div className="flex justify-around mt-4">
            <a
              href={videoUrl}
              download
              className="bg-green-600 hover:bg-green-700 text-white font-semibold py-2 px-4 rounded transition duration-150"
            >
              Download Video
            </a>
            <button
              onClick={handleGenerateQuiz}
              className="bg-purple-600 hover:bg-purple-700 text-white font-semibold py-2 px-4 rounded transition duration-150"
            >
              Generate Quiz
            </button>
          </div>
        </div>
      )}
      
      {quizData && (
        <div className="bg-gray-50 p-6 rounded-lg shadow-md mt-8">
          <h2 className="text-2xl font-bold mb-4">Quiz Based on the Video</h2>
          <form onSubmit={handleQuizSubmit}>
            {quizData.map((q, i) => (
              <div key={i} className="mb-4 p-4 border rounded border-gray-300">
                <p className="font-bold text-lg">Q{i + 1}. {q[0].trim()}</p>
                {['A', 'B', 'C', 'D'].map((opt, j) => (
                  <div key={j} className="mt-2">
                    <label className="inline-flex items-center">
                      <input
                        type="radio"
                        name={`question-${i}`}
                        value={opt}
                        className="form-radio text-indigo-600"
                      />
                      <span className="ml-2">{q[j + 1].trim()}</span>
                    </label>
                  </div>
                ))}
              </div>
            ))}
            <div className="text-right">
              <button
                type="submit"
                className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded transition duration-150"
              >
                Submit Quiz
              </button>
            </div>
          </form>
        </div>
      )}
      
      {/* History Section */}
      <div className="mt-10">
        <h2 className="text-2xl font-bold mb-4">History of Generated Videos</h2>
        {history.length > 0 ? (
          <ul className="list-disc pl-6 space-y-3">
            {history.map((video, idx) => (
              <li key={idx} className="border-b pb-2">
                <span className="font-bold text-gray-800">{video.filename}</span>
                <br />
                <span className="text-gray-600">{video.prompt_text}</span>
                <br />
                <button
                  onClick={() => openModal(video)}
                  className="mt-1 bg-blue-600 hover:bg-blue-700 text-white font-semibold py-1 px-3 rounded transition duration-150"
                >
                  View
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-gray-700">No videos generated yet.</p>
        )}
        <div className="text-center mt-4">
          <button
            onClick={fetchHistory}
            className="bg-gray-600 hover:bg-gray-700 text-white font-semibold py-2 px-4 rounded transition duration-150"
          >
            Refresh History
          </button>
        </div>
      </div>
      
      {/* Modal for viewing video and quiz */}
      {modalOpen && selectedVideo && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="bg-white rounded-lg shadow-lg p-6 w-11/12 md:w-2/3 lg:w-1/2">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-bold">Video Details: {selectedVideo.filename}</h3>
              <button onClick={closeModal} className="text-gray-600 hover:text-gray-800 text-3xl leading-none">&times;</button>
            </div>
            <video className="w-full rounded mb-4" controls>
              <source src={videoUrl} type="video/mp4" />
              Your browser does not support the video tag.
            </video>
            <div className="flex justify-end mb-4">
              <a
                href={videoUrl}
                download
                className="bg-green-600 hover:bg-green-700 text-white font-semibold py-2 px-4 rounded transition duration-150"
              >
                Download Video
              </a>
            </div>
            <div>
              <h4 className="text-lg font-bold mb-2">Quiz</h4>
              {selectedQuiz ? (
                <form onSubmit={handleQuizSubmit}>
                  {selectedQuiz.map((q, i) => (
                    <div key={i} className="mb-4">
                      <p className="font-bold">Q{i + 1}. {q[0].trim()}</p>
                      {['A', 'B', 'C', 'D'].map((opt, j) => (
                        <label key={j} className="inline-flex items-center mt-1">
                          <input type="radio" name={`modal-question-${i}`} value={opt} className="form-radio text-indigo-600"/>
                          <span className="ml-2">{q[j+1].trim()}</span>
                        </label>
                      ))}
                    </div>
                  ))}
                  <div className="text-right">
                    <button type="submit" className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded transition duration-150">
                      Submit Quiz
                    </button>
                  </div>
                </form>
              ) : (
                <p className="text-gray-700">No quiz available.</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default VideoDashboard;
