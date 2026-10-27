import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { GoogleLogin } from '@react-oauth/google';
import { Sparkles, User, Mail, Lock, Eye, EyeOff, ArrowRight, Loader2, AlertCircle, Info } from 'lucide-react';
import './Auth.css';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || '';

function Register() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const parseError = (err, defaultMsg) => {
    const detail = err.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) return detail.map(d => d.msg || JSON.stringify(d)).join(', ');
    if (detail && typeof detail === 'object') return JSON.stringify(detail);
    return err.message || defaultMsg;
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await axios.post(`${API_BASE}/auth/register`, {
        name,
        email,
        password
      });
      navigate('/login');
    } catch (err) {
      setError(parseError(err, 'Registration failed. Please try again.'));
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleSuccess = async (credentialResponse) => {
    setError('');
    setLoading(true);
    try {
      const response = await axios.post(`${API_BASE}/auth/google`, {
        token: credentialResponse.credential,
      });
      localStorage.setItem('token', response.data.access_token);
      if (response.data.user) {
        localStorage.setItem('user', JSON.stringify(response.data.user));
      }
      navigate('/dashboard');
    } catch (err) {
      setError(parseError(err, 'Google sign-up failed. Please try again.'));
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleError = () => {
    setError('Google Sign-In prompt was closed or failed.');
  };


  return (
    <div className="auth-page-wrapper">
      {/* Background ambient orbs */}
      <div className="ambient-bg">
        <div className="ambient-orb-1"></div>
        <div className="ambient-orb-3"></div>
      </div>

      <div className="auth-floating-card">
        <div className="auth-header-brand">
          <div className="brand-icon-badge">
            <Sparkles size={28} />
          </div>
          <h1 className="auth-title">Create Account</h1>
          <p className="auth-subtitle">Join the AI-Powered Database Query System</p>
        </div>

        {error && (
          <div className="auth-alert-error mb-4">
            <AlertCircle size={18} className="shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleRegister} className="auth-form">
          <div className="auth-input-group">
            <label className="auth-input-label">Full Name</label>
            <div className="auth-input-container">
              <span className="auth-input-icon">
                <User size={18} />
              </span>
              <input 
                type="text" 
                className="auth-input-field"
                placeholder="Alex Morgan"
                value={name} 
                onChange={(e) => setName(e.target.value)} 
                required 
              />
            </div>
          </div>

          <div className="auth-input-group">
            <label className="auth-input-label">Email Address</label>
            <div className="auth-input-container">
              <span className="auth-input-icon">
                <Mail size={18} />
              </span>
              <input 
                type="email" 
                className="auth-input-field"
                placeholder="name@company.com"
                value={email} 
                onChange={(e) => setEmail(e.target.value)} 
                required 
              />
            </div>
          </div>

          <div className="auth-input-group">
            <label className="auth-input-label">Password</label>
            <div className="auth-input-container">
              <span className="auth-input-icon">
                <Lock size={18} />
              </span>
              <input 
                type={showPassword ? "text" : "password"} 
                className="auth-input-field"
                placeholder="Create a strong password"
                value={password} 
                onChange={(e) => setPassword(e.target.value)} 
                required 
              />
              <button 
                type="button" 
                className="password-toggle-btn"
                onClick={() => setShowPassword(!showPassword)}
                tabIndex="-1"
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>

          <button 
            type="submit" 
            className="auth-submit-btn" 
            disabled={loading}
          >
            {loading ? (
              <>
                <Loader2 size={18} className="animate-spin-custom" />
                <span>Creating Account...</span>
              </>
            ) : (
              <>
                <span>Get Started Now</span>
                <ArrowRight size={18} />
              </>
            )}
          </button>
        </form>

        <div className="auth-divider">
          <span>or sign up with</span>
        </div>

        {/* Google Authentication Section */}
        <div className="google-auth-wrapper">
          {GOOGLE_CLIENT_ID ? (
            <div className="google-btn-container">
              <GoogleLogin
                onSuccess={handleGoogleSuccess}
                onError={handleGoogleError}
                shape="rectangular"
                theme="outline"
                size="large"
                text="signup_with"
                width="368"
              />
            </div>
          ) : (
            <div className="auth-alert-info">
              <Info size={16} className="shrink-0" />
              <span>Add <code>VITE_GOOGLE_CLIENT_ID</code> in <code>frontend/.env</code> to enable 1-Click Google Sign-Up.</span>
            </div>
          )}
        </div>

        <div className="auth-footer-nav">
          Already have an account? <Link to="/login" className="auth-footer-link">Sign In</Link>
        </div>
      </div>
    </div>
  );
}

export default Register;

