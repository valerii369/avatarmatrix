"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import useSWR from "swr";
import { useUserStore, useCardsStore } from "@/lib/store";
import { authAPI, cardsAPI, profileAPI } from "@/lib/api";
import { EnergyIcon } from "@/components/EnergyIcon";
import { Skeleton } from "@/components/Skeleton";

// ─── Constants ────────────────────────────────────────────────────────────────

const TOTAL_CARDS = 176;

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatScore(n: number): string {
  return n.toLocaleString("ru-RU").replace(/,/g, " ");
}

// ─── Home Page ────────────────────────────────────────────────────────────────

export default function HomePage() {
  const router = useRouter();
  const {
    userId, tgId, setUser, energy, evolutionLevel, title, firstName,
    xp, xpCurrent, xpNext, photoUrl,
  } = useUserStore();
  const { cards, setCards } = useCardsStore();
  const [status, setStatus] = useState<"loading" | "redirecting" | "ready" | "error">("loading");
  const [errorInfo, setErrorInfo] = useState<string>("");

  // 1. Auth & Init
  useEffect(() => {
    const initAuth = async () => {
      try {
        const tg = (window as any).Telegram?.WebApp;
        if (tg) { tg.ready(); tg.expand(); }

        const initData = tg?.initData || "";
        const isDev = process.env.NODE_ENV === "development";
        const isDebug = new URLSearchParams(window.location.search).get("debug") === "true";

        if (!initData && !isDev && !isDebug) {
          throw new Error("Telegram context missing. Please open via the bot or use ?debug=true for testing.");
        }

        const authRes = await authAPI.login(initData, isDev);
        const d = authRes.data;

        setUser({
          userId: d.user_id, tgId: d.tg_id, firstName: d.first_name,
          token: d.token, energy: d.energy, streak: d.streak,
          evolutionLevel: d.evolution_level, title: d.title,
          onboardingDone: d.onboarding_done,
          xp: d.xp, xpCurrent: d.xp_current, xpNext: d.xp_next,
          referralCode: d.referral_code,
          photoUrl: d.photo_url || "",
        });

        if (typeof window !== "undefined")
          localStorage.setItem("avatar_token", d.token);

        if (!d.onboarding_done) {
          setStatus("redirecting");
          router.push("/onboarding");
          return;
        }

        setStatus("ready");
      } catch (e: any) {
        console.error("Init error", e);
        setErrorInfo(e.message || "Unknown error");
        setStatus("error");
      }
    };
    initAuth();
  }, [router, setUser]);

  // 2. Data Fetching via SWR
  const { data: profile } = useSWR(
    userId && status === "ready" ? ["profile", userId] : null,
    () => profileAPI.get(userId!).then(res => res.data),
    {
      onSuccess: (data) => {
        // AI-path users have no birth_date but have onboarding_done=true — don't redirect them
        if (!data.birth_date && !data.onboarding_done) router.push("/onboarding");
        setUser({
          xp: data.xp,
          xpCurrent: data.xp_current,
          xpNext: data.xp_next,
          evolutionLevel: data.evolution_level,
          title: data.title,
          energy: data.energy,
        });
      }
    }
  );

  const { data: cardsData, isValidating: cardsLoading } = useSWR(
    userId && status === "ready" ? ["cards", userId] : null,
    () => cardsAPI.getAll(userId!).then(res => res.data),
    {
      onSuccess: (data) => setCards(data),
      revalidateOnFocus: false,
    }
  );

  const displayCards = cardsData || cards;

  // ── Derived stats ──────────────────────────────────────────────────────────
  const openedSpheres = new Set(
    displayCards?.filter((c: any) => c.status !== "locked" && c.hawkins_peak > 0).map((c: any) => c.sphere)
  ).size || 0;
  const openedCards = displayCards?.filter((c: any) => c.status !== "locked").length || 0;
  const recommended = displayCards?.filter((c: any) => c.is_recommended_astro || c.is_recommended_ai).length || 0;
  const totalScore = displayCards?.reduce((sum: number, c: any) => sum + (c.hawkins_peak || 0), 0) || 0;

  const levelRange = Math.max(xpNext - xpCurrent, 1);
  const xpCollectedInLevel = Math.max(xp - xpCurrent, 0);
  const levelProgress = Math.min(xpCollectedInLevel / levelRange, 1);

  const activeCards = displayCards?.filter((c: any) => ["synced", "aligned", "aligning"].includes(c.status)).length || 0;

  // ── Loading/Error States ───────────────────────────────────────────────────
  if (status === "loading" || status === "redirecting" || !userId) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen" style={{ background: "var(--bg-deep)" }}>
        <div className="w-12 h-12 border-2 border-violet-500 border-t-transparent rounded-full mb-4 animate-spin" />
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
            overflow: "hidden",
          }}>
            {photoUrl ? (
              <img
                src={photoUrl}
                alt={firstName}
                style={{ width: "100%", height: "100%", objectFit: "cover" }}
              />
            ) : (
              "👤"
            )}
          </div>
          <div className="flex-1 flex justify-between items-center">
            <div className="flex flex-col">
              <span className="font-semibold text-base" style={{ color: "var(--text-primary)" }}>
                {firstName || "Пользователь"}
              </span>
              <span style={{ fontSize: 12, color: "var(--text-muted)", fontWeight: 500, marginTop: -2 }}>
                Level <span style={{ color: "var(--text-primary)", fontWeight: 700 }}>{evolutionLevel}</span>/100
              </span>
            </div>
            <span className="font-semibold text-base flex items-center gap-0.5" style={{ color: "#F59E0B" }}>
              <EnergyIcon size={20} color="#F59E0B" />
              {energy}
            </span>
          </div>
        </div>
      </div>

      {/* ── Stats tiles ── */}
      <div className="px-4 mb-4">
        <div className="grid grid-cols-3 gap-2">
          {cardsLoading && !cardsData ? (
            <>
              <Skeleton className="h-16 rounded-2xl" />
              <Skeleton className="h-16 rounded-2xl" />
              <Skeleton className="h-16 rounded-2xl" />
            </>
          ) : (
            <>
              <StatTile label="Сферы" value={`${openedSpheres}/8`} color="#F59E0B" />
              <StatTile label="Карточки" value={`${activeCards}/${TOTAL_CARDS}`} color="#10B981" />
              <StatTile label="Рекомендовано" value={String(recommended)} color="#60A5FA" />
            </>
          )}
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
          {formatScore(totalScore)}
        </motion.p>
        <p style={{
          fontSize: 12,
          fontWeight: 600,
          color: "rgba(255,255,255,0.3)",
          textTransform: "uppercase",
          letterSpacing: "0.1em",
          marginTop: 4
        }}>
          Общий Индекс
        </p>
      </div>

      {/* ── Rank + Level row ── */}
      <div className="px-4 mb-3">
        <div className="flex items-center justify-between mb-1">
          <span style={{ fontSize: 13, color: "var(--text-secondary)", fontWeight: 500 }}>
            {title || "Новичок"}
          </span>
          <span style={{ fontSize: 12, fontWeight: 400 }}>
            <span style={{ color: "var(--text-muted)" }}>
              ({formatScore(xpCollectedInLevel)} / {formatScore(levelRange)} XP)
            </span>
            {" "}
            <span style={{ color: "var(--text-secondary)", fontWeight: 500 }}>
              {Math.round(levelProgress * 100)}%
            </span>
          </span>
        </div>
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
          <div style={{
            position: "absolute",
            inset: -20,
            borderRadius: "50%",
            background: "radial-gradient(circle at 50% 50%, rgba(16,185,129,0.15) 0%, transparent 70%)",
            filter: "blur(16px)",
            pointerEvents: "none",
          }} />

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

          <div style={{
            position: "absolute", inset: 0, borderRadius: "50%",
            border: "3px solid rgba(255,255,255,0.05)",
          }} />

          <div style={{
            position: "absolute", inset: 4, borderRadius: "50%",
            background: "radial-gradient(circle at 35% 35%, rgba(16,185,129,0.15) 0%, rgba(6,182,212,0.08) 40%, rgba(13,18,38,0.95) 70%, #060818 100%)",
            backdropFilter: "blur(4px)",
            border: "1px solid rgba(16,185,129,0.2)",
            boxShadow: "inset 0 0 60px rgba(6,182,212,0.08), 0 0 40px rgba(16,185,129,0.1)",
          }} />

          <div style={{
            position: "absolute", inset: "30%",
            borderRadius: "50%",
            background: "radial-gradient(circle at 40% 40%, rgba(6,182,212,0.2) 0%, transparent 70%)",
            filter: "blur(20px)",
          }} />

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

      <BottomNav active="home" />
    </div>
  );
}

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

export function BottomNav({ active }: { active: string }) {
  const router = useRouter();
  const navItems = [
    { key: "home", icon: "/icons/home.svg", label: "AVATAR", path: "/" },
    { key: "cards", icon: "/icons/cards.svg", label: "Карточки", path: "/cards" },
    { key: "diary", icon: "/icons/diary.svg", label: "Дневник", path: "/diary" },
    { key: "reflect", icon: "/icons/reflect.svg", label: "Рефлексия", path: "/reflect" },
    { key: "profile", icon: "/icons/profile.svg", label: "Профиль", path: "/profile" },
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
            <img
              src={item.icon}
              alt={item.label}
              style={{
                width: 24,
                height: 24,
                opacity: isActive ? 1 : 0.5,
                filter: isActive ? "none" : "grayscale(100%) brightness(0.8)",
                transition: "all 0.2s"
              }}
            />
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
