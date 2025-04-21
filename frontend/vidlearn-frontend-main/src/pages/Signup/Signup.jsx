// src/pages/Signup/Signup.jsx
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import "./Signup.css";
import Footer from "../../components/Footer";
import Logo from "../../components/Logo";
const API = import.meta.env.VITE_API_URL;

function Signup() {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    try {
      const res = await fetch(`${API}/signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, email, password }),
      });
      const data = await res.json();

      if (res.ok) {
        navigate("/login");
      } else {
        setError(data.error || "Signup failed");
      }
    } catch (err) {
      console.error(err);
      setError("Network error, please try again");
    }
  };

  return (
    <div className="container-wrapper">
      <div className="gyanai-logo">
        <a href="/">
          <Logo />
        </a>
      </div>
      <div className="container login">
        <div className="illustration">
          <img src="/loginVector.png" alt="" />
        </div>
        <div className="login-form">
          <form onSubmit={handleSubmit}>
            <h2 className="login-title">Sign Up</h2>
            {error && <p className="error">{error}</p>}

            <div className="form-row">
              <label htmlFor="username">Username</label>
              <input
                type="text"
                placeholder="Username"
                id="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </div>

            <div className="form-row">
              <label htmlFor="email">Email</label>
              <input
                type="email"
                id="email"
                placeholder="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            <div className="form-row">
              <label htmlFor="password">Password</label>
              <input
                type="password"
                id="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>

            <button className="form-row login-btn" type="submit">
              Sign Up
            </button>
            <div className="form-row">
              <p>
                Already have an account? <a href="/login">Login</a>
              </p>
            </div>
          </form>
        </div>
      </div>
      <Footer />
    </div>
  );
}

export default Signup;
