import React, { useState } from "react";
import { useAuth } from "../hooks/useAuth.js";
import { Mail, Lock, Eye, EyeOff, AlertCircle, CheckCircle } from "lucide-react";

export function AuthPage() {
  const { login, register, error: authError } = useAuth();
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [localError, setLocalError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const validate = () => {
    if (!email || !password) {
      setLocalError("Email and password are required");
      return false;
    }
    if (!email.includes("@")) {
      setLocalError("Please enter a valid email address");
      return false;
    }
    if (password.length < 12) {
      setLocalError("Password must be at least 12 characters");
      return false;
    }
    if (password.length > 128) {
      setLocalError("Password must not exceed 128 characters");
      return false;
    }
    if (!isLogin && password !== confirmPassword) {
      setLocalError("Passwords do not match");
      return false;
    }
    setLocalError("");
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLocalError("");
    if (!validate()) return;

    setIsSubmitting(true);
    try {
      if (isLogin) {
        const result = await login(email, password);
        if (!result.success) {
          setLocalError(result.error);
        }
      } else {
        const result = await register(email, password);
        if (!result.success) {
          setLocalError(result.error);
        }
      }
    } catch (err) {
      setLocalError(err.message || "An unexpected error occurred");
    } finally {
      setIsSubmitting(false);
    }
  };

  const toggleMode = () => {
    setIsLogin((prev) => !prev);
    setLocalError("");
    setEmail("");
    setPassword("");
    setConfirmPassword("");
  };

  const displayError = authError || localError;

  return (
    <div className="min-h-screen flex items-center justify-center bg-ink px-4">
      <div className="w-full max-w-md">
        {/* Logo/Brand */}
        <div className="text-center mb-8">
          <h1 className="text-2xl font-semibold text-slate-200">QuantNiti</h1>
          <p className="text-slate-400 text-sm mt-1">PAPER / SIMULATED</p>
        </div>

        {/* Card */}
        <div className="card p-6">
          {/* Tabs */}
          <div className="flex mb-6 border-b border-line">
            <button
              type="button"
              onClick={toggleMode}
              className={`flex-1 py-2 text-sm font-medium transition-colors ${
                isLogin
                  ? "text-ai border-b-2 border-ai"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Login
            </button>
            <button
              type="button"
              onClick={toggleMode}
              className={`flex-1 py-2 text-sm font-medium transition-colors ${
                !isLogin
                  ? "text-ai border-b-2 border-ai"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Register
            </button>
          </div>

          {/* Error Display */}
          {displayError && (
            <div
              className="flex items-center gap-2 mb-4 p-3 bg-down/10 border border-down/50 text-down text-sm rounded"
              role="alert"
            >
              <AlertCircle size={16} className="flex-shrink-0" />
              <span>{displayError}</span>
            </div>
          )}

          {/* Form */}
          <form data-testid="login-form" onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm text-slate-300 mb-1">
                Email
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                <input
                  id="email"
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  className="w-full pl-10 pr-4 py-2 bg-ink border border-line rounded focus:outline-none focus:ring-2 focus:ring-ai/50 focus:border-ai text-sm"
                  disabled={isSubmitting}
                  required
                />
              </div>
            </div>

            <div>
              <label htmlFor="password" className="block text-sm text-slate-300 mb-1">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete={isLogin ? "current-password" : "new-password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder={isLogin ? "••••••••" : "Min 12 characters"}
                  className="w-full pl-10 pr-12 py-2 bg-ink border border-line rounded focus:outline-none focus:ring-2 focus:ring-ai/50 focus:border-ai text-sm"
                  disabled={isSubmitting}
                  required
                  minLength={12}
                  maxLength={128}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
              {!isLogin && (
                <p className="mt-1 text-xs text-slate-400">
                  Minimum 12 characters, maximum 128 characters
                </p>
              )}
            </div>

            {!isLogin && (
              <div>
                <label htmlFor="confirmPassword" className="block text-sm text-slate-300 mb-1">
                  Confirm Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                  <input
                    id="confirmPassword"
                    type={showPassword ? "text" : "password"}
                    autoComplete="new-password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Confirm password"
                    className="w-full pl-10 pr-4 py-2 bg-ink border border-line rounded focus:outline-none focus:ring-2 focus:ring-ai/50 focus:border-ai text-sm"
                    disabled={isSubmitting}
                    required
                  />
                </div>
              </div>
            )}

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full btn-ai py-2.5 mt-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                      fill="none"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                  </svg>
                  Processing...
                </span>
              ) : isLogin ? (
                "Log In"
              ) : (
                "Create Account"
              )}
            </button>
          </form>

          {/* Switch mode link */}
          <p className="mt-6 text-center text-sm text-slate-400">
            {isLogin ? "Don't have an account? " : "Already have an account? "}
            <button
              type="button"
              onClick={toggleMode}
              className="text-ai hover:underline font-medium"
            >
              {isLogin ? "Sign up" : "Log in"}
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}