"use client";
import { useEffect, useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { useUserStore, useCardsStore } from "@/lib/store";
import { authAPI, cardsAPI, profileAPI } from "@/lib/api";

// ─── Constants ────────────────────────────────────────────────────────────────

const TOTAL_CARDS = 176;
const MAX_LEVEL = 100;

// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Format number with space separator: 131323 → "131 323" */
function formatScore(n: number): string {
  return n.toLocaleString("ru-RU").replace(/,/g, " ");
}

// ─── Home Page ────────────────────────────────────────────────────────────────

export default function HomePage() {
  const router = useRouter();
  const {
    userId, tgId, setUser, energy, evolutionLevel, title, firstName, onboardingDone,
  } = useUserStore();
  const { cards, setCards, setLoading } = useCardsStore();
  const [status, setStatus] = useState<"loading" | "redirecting" | "ready" | "error">("loading");
  const [errorInfo, setErrorInfo] = useState<string>("");

  const init = useCallback(async () => {
    try {
      const tg = (window as any).Telegram?.WebApp;
      if (tg) { tg.ready(); tg.expand(); }

      const initData = tg?.initData || "";
      const isDev = process.env.NODE_ENV === "development";

      console.log("DEBUG: Init started", { isDev, hasInitData: !!initData });

      if (!initData && !isDev) {
        throw new Error("Telegram initData missing. Please open the app from the bot.");
      }

      // 1. Auth & Get User Flag
      const authRes = await authAPI.login(initData, isDev);
      const d = authRes.data;

      console.log("DEBUG: Auth success", {
        userId: d.user_id,
        onboardingDone: d.onboarding_done
      });

      setUser({
        userId: d.user_id, tgId: d.tg_id, firstName: d.first_name,
        token: d.token, energy: d.energy, streak: d.streak,
        evolutionLevel: d.evolution_level, title: d.title,
        onboardingDone: d.onboarding_done,
      });

      if (typeof window !== "undefined")
        localStorage.setItem("avatar_token", d.token);

      // 2. Simple Logic: If NOT done -> redirect
      if (!d.onboarding_done) {
        console.log("DEBUG: Onboarding required, redirecting...");
        setStatus("redirecting");
        router.push("/onboarding");
        return;
      }

      // 3. Robust Safety Net: If birth_date is missing, ALWAYS redirect
      try {
        const profileRes = await profileAPI.get(d.user_id);
        if (!profileRes.data.birth_date) {
          console.warn("DEBUG: Birth date missing, forcing onboarding redirect.");
          setStatus("redirecting");
          router.push("/onboarding");
          return;
        }
      } catch (err) {
        console.error("DEBUG: Profile check failed", err);
      }

      // 4. Load App Data
      setStatus("loading");
      setLoading(true);
      try {
        const cardsRes = await cardsAPI.getAll(d.user_id);
        setCards(cardsRes.data);
      } catch (err) {
        console.error("DEBUG: Failed to load cards", err);
        throw new Error("Failed to load cards session data.");
      } finally {
        setLoading(false);
      }

      setStatus("ready");
    } catch (e: any) {
      console.error("DEBUG: Init error", e);
      const msg = e.response?.data?.detail || e.message || "Unknown error";
      setErrorInfo(msg);
      setStatus("error");

      const { reset } = useUserStore.getState();
      reset();
    }
  }, [router, setUser, setCards, setLoading]);

  useEffect(() => { init(); }, [init]);

  // ── Derived stats ──────────────────────────────────────────────────────────
  const openedSpheres = new Set(
    cards.filter((c) => c.status !== "locked" && c.hawkins_peak > 0).map((c) => c.sphere)
  ).size;
  const openedCards = cards.filter((c) => c.status !== "locked").length;
  const recommended = cards.filter((c) => c.is_recommended_astro).length;

  // Total score: sum of all hawkins peaks
  const totalScore = cards.reduce((sum, c) => sum + (c.hawkins_peak || 0), 0);

  // Level progress 0..1
  const levelProgress = Math.min(evolutionLevel / MAX_LEVEL, 1);

  // ── Loading/Error States ───────────────────────────────────────────────────
  if (status === "loading" || status === "redirecting") {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen" style={{ background: "var(--bg-deep)" }}>
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
          className="w-12 h-12 border-2 border-violet-500 border-t-transparent rounded-full mb-4"
        />
        <p className="text-xs text-muted-foreground animate-pulse">
          {status === "redirecting" ? "Подготовка онбординга..." : "Инициализация..."}
        </p>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen p-6 text-center" style={{ background: "var(--bg-deep)" }}>
        <div style={{ fontSize: 48, marginBottom: 16 }}>⚠️</div>
        <h2 className="text-xl font-bold text-white mb-2">Ошибка инициализации</h2>
        <p className="text-sm text-gray-400 mb-6">{errorInfo}</p>
        <button
          onClick={() => window.location.reload()}
          className="px-6 py-2 bg-violet-600 text-white rounded-lg font-semibold"
        >
          Попробовать снова
        </button>
        {/* Debug Info & Reset (Testing only) */}
        <div style={{ marginTop: 20, padding: 10, border: '1px dashed rgba(255,255,255,0.1)', borderRadius: 10, fontSize: 10, color: 'var(--text-muted)' }}>
          <p>Debug ID: {userId}</p>
          <button
            onClick={async () => {
              if (!tgId) {
                alert("No TG ID found in store.");
                return;
              }
              if (confirm("Reset all data?")) {
                try {
                  await profileAPI.reset(tgId);
                  window.location.reload();
                } catch (err) {
                  console.error("Reset failed", err);
                  alert("Reset failed. Check logs.");
                }
              }
            }}
            style={{ marginTop: 5, padding: '4px 8px', background: 'rgba(255,0,0,0.1)', color: 'red', border: '1px solid red', borderRadius: 4 }}
          >
            Force Reset Data (Testing)
          </button>
        </div>
      </div>
    );
  }

  return (
    <div
      className="min-h-screen flex flex-col"
      style={{ background: "var(--bg-deep)", paddingBottom: 96 }}
    >

      {/* ── Header ── */}
      <div className="px-4 pt-5 pb-3">
        <div
          className="flex items-center gap-3 p-3"
          style={{
            background: "rgba(255,255,255,0.05)",
            border: "1px solid var(--border)",
            borderRadius: 18,
          }}
        >
          <div style={{
            width: 44, height: 44, borderRadius: "50%",
            background: "rgba(255,255,255,0.1)",
            border: "1px solid var(--border)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 20, color: "var(--text-muted)", flexShrink: 0,
          }}>
            👤
          </div>
          <span className="font-semibold text-base" style={{ color: "var(--text-primary)" }}>
            {firstName || "Пользователь"}
          </span>
        </div>
      </div>

      {/* ── Stats tiles ── */}
      <div className="px-4 mb-4">
        <div className="grid grid-cols-3 gap-2">
          <StatTile label="Сферы" value={`${openedSpheres}/8`} color="#F59E0B" />
          <StatTile label="Карточки" value={`${openedCards}/${TOTAL_CARDS}`} color="#10B981" />
          <StatTile label="Рекомендовано" value={String(recommended)} color="#60A5FA" />
        </div>
      </div>

      {/* ── Score ── */}
      <div className="px-4 text-center mb-1">
        <motion.p
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          style={{
            fontSize: 48,
            fontWeight: 800,
            color: "var(--text-primary)",
            letterSpacing: "-1px",
            lineHeight: 1,
            fontFamily: "'Outfit', sans-serif",
          }}
        >
          {formatScore(totalScore || energy || 0)}
        </motion.p>
      </div>

      {/* ── Rank + Level row ── */}
      <div className="px-4 mb-3">
        <div className="flex items-center justify-between mb-1">
          <span style={{ fontSize: 13, color: "var(--text-secondary)", fontWeight: 500 }}>
            {title || "Новичек"}
          </span>
          <span style={{ fontSize: 13, color: "var(--text-muted)", fontWeight: 500 }}>
            Level <span style={{ color: "var(--text-primary)", fontWeight: 700 }}>{evolutionLevel}</span>/100
          </span>
        </div>
        {/* Progress bar */}
        <div style={{
          height: 3, background: "rgba(255,255,255,0.08)", borderRadius: 2, overflow: "hidden",
        }}>
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${levelProgress * 100}%` }}
            transition={{ duration: 1, ease: "easeOut", delay: 0.3 }}
            style={{
              height: "100%",
              background: "linear-gradient(90deg, #10B981, #06B6D4)",
              borderRadius: 2,
            }}
          />
        </div>
      </div>

      {/* ── Glowing Orb ── */}
      <div className="flex-1 flex items-center justify-center px-4">
        <div style={{ position: "relative", width: "85vw", maxWidth: 340, aspectRatio: "1/1" }}>

          {/* Outer ambient glow */}
          <div style={{
            position: "absolute",
            inset: -20,
            borderRadius: "50%",
            background: "radial-gradient(circle at 50% 50%, rgba(16,185,129,0.15) 0%, transparent 70%)",
            filter: "blur(16px)",
            pointerEvents: "none",
          }} />

          {/* Animated ring */}
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
            style={{
              position: "absolute", inset: 0,
              borderRadius: "50%",
              border: "3px solid transparent",
              backgroundImage: "conic-gradient(from 0deg, #10B981 0%, #06B6D4 40%, transparent 60%)",
              WebkitMask: "radial-gradient(circle, transparent calc(100% - 3px), white calc(100% - 3px))",
              mask: "radial-gradient(circle, transparent calc(100% - 3px), white calc(100% - 3px))",
            }}
          />

          {/* Static outer ring */}
          <div style={{
            position: "absolute", inset: 0, borderRadius: "50%",
            border: "3px solid rgba(255,255,255,0.05)",
          }} />

          {/* Main orb */}
          <div style={{
            position: "absolute", inset: 4, borderRadius: "50%",
            background: "radial-gradient(circle at 35% 35%, rgba(16,185,129,0.15) 0%, rgba(6,182,212,0.08) 40%, rgba(13,18,38,0.95) 70%, #060818 100%)",
            backdropFilter: "blur(4px)",
            border: "1px solid rgba(16,185,129,0.2)",
            boxShadow: "inset 0 0 60px rgba(6,182,212,0.08), 0 0 40px rgba(16,185,129,0.1)",
          }} />

          {/* Inner glow dot */}
          <div style={{
            position: "absolute", inset: "30%",
            borderRadius: "50%",
            background: "radial-gradient(circle at 40% 40%, rgba(6,182,212,0.2) 0%, transparent 70%)",
            filter: "blur(20px)",
          }} />

          {/* Pulsing ring animation */}
          <motion.div
            animate={{ scale: [1, 1.03, 1], opacity: [0.4, 0.7, 0.4] }}
            transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
            style={{
              position: "absolute", inset: -3, borderRadius: "50%",
              border: "1.5px solid rgba(16,185,129,0.3)",
            }}
          />
        </div>
      </div>

      {/* ── Island Bottom Nav ── */}
      <BottomNav active="home" />
    </div>
  );
}

// ─── StatTile ─────────────────────────────────────────────────────────────────

function StatTile({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div style={{
      background: "rgba(255,255,255,0.04)",
      border: "1px solid var(--border)",
      borderRadius: 16,
      padding: "12px 10px",
      textAlign: "center",
    }}>
      <p style={{ fontSize: 11, color, fontWeight: 600, marginBottom: 4, lineHeight: 1 }}>
        {label}
      </p>
      <p style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)", lineHeight: 1 }}>
        {value}
      </p>
    </div>
  );
}

// ─── Island Bottom Nav ────────────────────────────────────────────────────────

export function BottomNav({ active }: { active: string }) {
  const router = useRouter();

  const navItems = [
    { key: "home", icon: "◈", label: "AVATAR", path: "/" },
    { key: "cards", icon: "🃏", label: "Карточки", path: "/cards" },
    { key: "diary", icon: "📖", label: "Дневник", path: "/diary" },
    { key: "reflect", icon: "🌅", label: "Рефлексия", path: "/reflect" },
    { key: "profile", icon: "◉", label: "Профиль", path: "/profile" },
  ];

  return (
    <nav style={{
      position: "fixed",
      bottom: 16,
      left: 16,
      right: 16,
      background: "rgba(13,18,38,0.92)",
      backdropFilter: "blur(24px)",
      WebkitBackdropFilter: "blur(24px)",
      border: "1px solid rgba(255,255,255,0.09)",
      borderRadius: 28,
      display: "flex",
      justifyContent: "space-around",
      alignItems: "center",
      padding: "10px 4px",
      zIndex: 100,
      boxShadow: "0 8px 32px rgba(0,0,0,0.5), 0 1px 0 rgba(255,255,255,0.05) inset",
    }}>
      {navItems.map((item) => {
        const isActive = active === item.key;
        return (
          <button
            key={item.key}
            onClick={() => router.push(item.path)}
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 4,
              padding: "6px 12px",
              borderRadius: 18,
              border: "none",
              cursor: "pointer",
              background: isActive ? "rgba(255,255,255,0.1)" : "transparent",
              transition: "all 0.2s",
              minWidth: 52,
            }}
          >
            <span style={{
              fontSize: 18,
              color: isActive ? "var(--text-primary)" : "var(--text-muted)",
              lineHeight: 1,
              transition: "color 0.2s",
            }}>
              {item.icon}
            </span>
            <span style={{
              fontSize: 10,
              fontWeight: 500,
              color: isActive ? "var(--text-primary)" : "var(--text-muted)",
              letterSpacing: "0.01em",
              transition: "color 0.2s",
            }}>
              {item.label}
            </span>
          </button>
        );
      })}
    </nav>
  );
}
