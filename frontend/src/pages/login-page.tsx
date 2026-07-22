import { AlertCircle, ArrowRight, Eye, EyeOff, LockKeyhole, Mail, Scale, UserRound } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState, type FormEvent } from "react";
import { Navigate } from "react-router-dom";

import { useAuth } from "@/auth/auth-context";
import { BrandLogo } from "@/components/brand-logo";
import { getAuthError } from "@/services/api";

export function LoginPage() {
  const { user, login, register } = useAuth();
  const [registerMode, setRegisterMode] = useState(false);
  const [desktop, setDesktop] = useState(() => window.matchMedia("(min-width: 768px)").matches);
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  useEffect(() => {
    const media = window.matchMedia("(min-width: 768px)");
    const update = () => setDesktop(media.matches);
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);

  if (user) return <Navigate to="/" replace />;

  const switchMode = () => {
    setRegisterMode((current) => !current);
    setError(null);
    setShowPassword(false);
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (registerMode) await register(name.trim(), email.trim(), password);
      else await login(email.trim(), password);
    } catch (requestError) {
      setError(getAuthError(requestError));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="relative grid min-h-dvh place-items-center overflow-hidden bg-[radial-gradient(circle_at_12%_10%,rgba(45,212,191,0.18),transparent_30%),linear-gradient(135deg,#dfeae7,#f6f7f4_55%,#d8e6e3)] px-4 py-8">
      <div className="pointer-events-none absolute -right-24 -top-24 size-80 rounded-full bg-teal-300/15 blur-3xl" />
      <section className="relative min-h-[650px] w-full max-w-5xl overflow-hidden rounded-[34px] border border-white/80 bg-white shadow-[0_35px_100px_-38px_rgba(15,55,50,0.42)] md:min-h-[620px]" aria-label="JuriGPT authentication">
        <motion.div
          className="absolute inset-y-0 z-10 hidden w-1/2 overflow-hidden bg-gradient-to-br from-[#123b37] via-[#0e695e] to-[#13a391] p-12 text-white md:flex md:flex-col md:items-center md:justify-center md:text-center"
          animate={{ x: registerMode ? "0%" : "100%" }}
          transition={{ type: "spring", stiffness: 180, damping: 24 }}
        >
          <div className="absolute -right-16 -top-16 size-56 rounded-full bg-white/10" />
          <div className="absolute -bottom-24 -left-16 size-64 rounded-full bg-teal-200/10" />
          <BrandLogo className="relative size-16 rounded-[22px] bg-white/15 text-white shadow-none ring-1 ring-white/20" />
          <AnimatePresence mode="wait">
            <motion.div key={registerMode ? "register-panel" : "login-panel"} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} className="relative mt-7">
              <h2 className="text-3xl font-semibold tracking-[-0.04em]">
                {registerMode ? "Welcome back" : "Hello, legal explorer"}
              </h2>
              <p className="mx-auto mt-3 max-w-xs text-sm leading-6 text-teal-50/70">
                {registerMode
                  ? "Sign in to continue your journey toward clearer legal understanding."
                  : "Create your secure account and get grounded answers from trusted legal documents."}
              </p>
              <button type="button" onClick={switchMode} className="mt-8 rounded-full border border-white/50 px-8 py-3 text-xs font-semibold uppercase tracking-[0.14em] transition hover:bg-white hover:text-teal-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white">
                {registerMode ? "Sign in" : "Sign up"}
              </button>
            </motion.div>
          </AnimatePresence>
        </motion.div>

        <motion.div
          className="absolute inset-y-0 flex w-full items-center justify-center px-6 py-10 md:w-1/2 md:px-12"
          animate={{ x: desktop && registerMode ? "100%" : "0%" }}
          transition={{ type: "spring", stiffness: 180, damping: 24 }}
        >
          <div className="w-full max-w-sm">
            <div className="mb-8 flex items-center gap-3 md:hidden">
              <BrandLogo className="size-11 rounded-2xl bg-teal-700 shadow-none" />
              <div><p className="font-semibold text-slate-900">JuriGPT</p><p className="text-[10px] uppercase tracking-[0.16em] text-teal-700">Legal intelligence</p></div>
            </div>
            <AnimatePresence mode="wait">
              <motion.div key={registerMode ? "register-form" : "login-form"} initial={{ opacity: 0, x: registerMode ? 12 : -12 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }}>
                <div className="mb-7">
                  <span className="grid size-11 place-items-center rounded-2xl bg-teal-50 text-teal-700"><Scale className="size-5" /></span>
                  <h1 className="mt-5 text-3xl font-semibold tracking-[-0.04em] text-slate-950">{registerMode ? "Create account" : "Welcome back"}</h1>
                  <p className="mt-2 text-sm text-slate-500">{registerMode ? "Register with your email to get started." : "Sign in with your email and password."}</p>
                </div>

                {error ? <div className="mb-5 flex items-start gap-2 rounded-2xl border border-rose-100 bg-rose-50 px-4 py-3 text-xs leading-5 text-rose-700" role="alert"><AlertCircle className="mt-0.5 size-4 shrink-0" />{error}</div> : null}

                <form onSubmit={submit} className="space-y-4">
                  {registerMode ? <AuthInput icon={UserRound} label="Full name" type="text" value={name} onChange={setName} autoComplete="name" minLength={2} /> : null}
                  <AuthInput icon={Mail} label="Email address" type="email" value={email} onChange={setEmail} autoComplete="email" />
                  <div className="relative">
                    <AuthInput icon={LockKeyhole} label="Password" type={showPassword ? "text" : "password"} value={password} onChange={setPassword} autoComplete={registerMode ? "new-password" : "current-password"} minLength={registerMode ? 8 : 1} />
                    <button type="button" onClick={() => setShowPassword((value) => !value)} className="absolute right-4 top-1/2 -translate-y-1/2 rounded-md p-1 text-slate-400 hover:text-teal-700" aria-label={showPassword ? "Hide password" : "Show password"}>{showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}</button>
                  </div>
                  <button type="submit" disabled={submitting} className="flex h-12 w-full items-center justify-center gap-2 rounded-2xl bg-teal-700 px-5 text-sm font-semibold text-white shadow-[0_14px_30px_-16px_rgba(15,118,110,0.7)] transition hover:-translate-y-0.5 hover:bg-teal-600 disabled:pointer-events-none disabled:opacity-60">
                    {submitting ? <span className="size-4 animate-spin rounded-full border-2 border-white/40 border-t-white" /> : <>{registerMode ? "Create account" : "Sign in"}<ArrowRight className="size-4" /></>}
                  </button>
                </form>
                <p className="mt-6 text-center text-xs text-slate-500 md:hidden">{registerMode ? "Already have an account?" : "New to JuriGPT?"} <button type="button" onClick={switchMode} className="font-semibold text-teal-700 hover:text-teal-600">{registerMode ? "Sign in" : "Create account"}</button></p>
              </motion.div>
            </AnimatePresence>
          </div>
        </motion.div>
      </section>
    </main>
  );
}

interface AuthInputProps {
  icon: typeof Mail;
  label: string;
  type: string;
  value: string;
  onChange: (value: string) => void;
  autoComplete: string;
  minLength?: number;
}

function AuthInput({ icon: Icon, label, type, value, onChange, autoComplete, minLength }: AuthInputProps) {
  return (
    <label className="relative block">
      <span className="sr-only">{label}</span>
      <Icon className="pointer-events-none absolute left-4 top-1/2 size-4 -translate-y-1/2 text-slate-400" />
      <input required type={type} value={value} onChange={(event) => onChange(event.target.value)} autoComplete={autoComplete} minLength={minLength} placeholder={label} className="h-12 w-full rounded-2xl border border-slate-200 bg-slate-50/70 pl-11 pr-11 text-sm text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-teal-400 focus:bg-white focus:ring-2 focus:ring-teal-100" />
    </label>
  );
}
