import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import "./Login.css";

import Footer from "../../components/Footer";
import Logo from "../../components/Logo";

const API = import.meta.env.VITE_API_URL;

function Login() {
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    try {
      const res = await fetch(`${API}/login`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: identifier, password }),
      });

      const data = await res.json();
      if (res.ok) {
        navigate("/tool");
      } else {
        setError(data.error || "Login failed");
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
            <h2 className="login-title">Welcome back</h2>
            {error && <p className="error">{error}</p>}
            <div className="form-row">
              <label htmlFor="username">Username</label>
              <input
                type="text"
                placeholder="Username or Email"
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                id="username"
                required
              />
            </div>
            <div className="form-row">
              <label htmlFor="password">Password</label>
              <input
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                id="password"
                required
              />
            </div>
            <button type="submit" className=" form-row login-btn">
              Login
            </button>
            <div className="form-row">
              <p>
                Don't have an account yet? <a href="/signup">Sign Up</a>
              </p>
            </div>
          </form>
        </div>
      </div>
      <Footer />
    </div>
  );
}

export default Login;
