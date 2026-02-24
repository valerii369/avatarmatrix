"use client";
import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { useUserStore, useCardsStore, type CardProgress } from "@/lib/store";
import { authAPI, cardsAPI } from "@/lib/api";

const SPHERES = [
  { key: "IDENTITY", name: "Личность", emoji: "✦", color: "#F59E0B" },
  { key: "MONEY", name: "Деньги", emoji: "◈", color: "#10B981" },
  { key: "RELATIONS", name: "Отношения", emoji: "❤", color: "#EC4899" },
  { key: "FAMILY", name: "Род", emoji: "⚘", color: "#F97316" },
  { key: "MISSION", name: "Миссия", emoji: "◉", color: "#3B82F6" },
  { key: "HEALTH", name: "Здоровье", emoji: "⬡", color: "#22C55E" },
  { key: "SOCIETY", name: "Влияние", emoji: "◐", color: "#8B5CF6" },
  { key: "SPIRIT", name: "Духовность", emoji: "∞", color: "#A78BFA" },
];

const STATUS_ICONS: Record<string, string> = {
  locked: "🔒", recommended: "✨", in_sync: "🔄", synced: "✅", aligning: "⚡", aligned: "🌟"
};
const RANK_STARS = ["☆", "⭐", "⭐⭐", "⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐⭐⭐"];

export default function HomePage() {
  const router = useRouter();
  const { userId, setUser, energy, streak, evolutionLevel, title, onboardingDone } = useUserStore();
  const { cards, setCards, setLoading } = useCardsStore();
  const [activeSphere, setActiveSphere] = useState<string | null>(null);
  const [initialized, setInitialized] = useState(false);

  const init = useCallback(async () => {
    try {
      // Telegram WebApp init
      const tg = (window as any).Telegram?.WebApp;
      if (tg) {
        tg.ready();
        tg.expand();
      }

      // Authenticate
      const initData = tg?.initData || "";
      const isDev = process.env.NODE_ENV === "development";
      const authRes = await authAPI.login(initData, isDev);
      const userData = authRes.data;

      setUser({
        userId: userData.user_id,
        tgId: userData.tg_id,
        firstName: userData.first_name,
        token: userData.token,
        energy: userData.energy,
        streak: userData.streak,
        evolutionLevel: userData.evolution_level,
        title: userData.title,
        onboardingDone: userData.onboarding_done,
      });

      if (typeof window !== "undefined") {
        localStorage.setItem("avatar_token", userData.token);
      }

      if (!userData.onboarding_done) {
        router.push("/onboarding");
        return;
      }

      // Load cards
      setLoading(true);
      const cardsRes = await cardsAPI.getAll(userData.user_id);
      setCards(cardsRes.data);
      setLoading(false);
    } catch (e) {
      console.error("Init error", e);
    } finally {
      setInitialized(true);
    }
  }, [router, setUser, setCards, setLoading]);

  useEffect(() => { init(); }, [init]);

  const getSphereCards = (sphereKey: string) =>
    cards.filter((c) => c.sphere === sphereKey);

  const getSphereStats = (sphereKey: string) => {
    const sc = getSphereCards(sphereKey);
    const played = sc.filter((c) => c.hawkins_peak > 0);
    const recommended = sc.filter((c) => c.is_recommended_astro && c.status !== "locked");
    const avgHawkins = played.length > 0
      ? Math.round(played.reduce((a, c) => a + c.hawkins_peak, 0) / played.length)
      : 0;
    return { played: played.length, total: sc.length, recommended: recommended.length, avgHawkins };
  };

  if (!initialized) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
          className="w-12 h-12 border-2 border-violet-500 border-t-transparent rounded-full"
        />
      </div>
    );
  }

  return (
    <div className="min-h-screen pb-24">
      {/* Header */}
      <div className="sticky top-0 z-50 px-4 pt-4 pb-3"
        style={{ background: "linear-gradient(180deg, rgba(6,8,24,1) 70%, transparent)" }}>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold gradient-text">AVATAR</h1>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              {title} • Ур. {evolutionLevel}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="energy-display text-sm">
              <span>✦</span>
              <span>{energy}</span>
            </div>
            <div className="flex items-center gap-1 text-sm" style={{ color: "var(--text-secondary)" }}>
              <span>🔥</span>
              <span>{streak}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="px-4 pt-2">
        {/* Sphere Grid */}
        <div className="grid grid-cols-2 gap-3 mb-4">
          {SPHERES.map((sphere) => {
            const stats = getSphereStats(sphere.key);
            const isActive = activeSphere === sphere.key;
            return (
              <motion.button
                key={sphere.key}
                whileTap={{ scale: 0.96 }}
                onClick={() => setActiveSphere(isActive ? null : sphere.key)}
                className={`sphere-${sphere.key} glass text-left p-4 relative overflow-hidden transition-all`}
                style={{
                  borderColor: isActive ? sphere.color : undefined,
                  boxShadow: isActive ? `0 0 20px ${sphere.color}40` : undefined,
                }}>
                <div className="flex items-center justify-between mb-2">
                  <span style={{ color: sphere.color, fontSize: "1.4rem" }}>{sphere.emoji}</span>
                  {stats.recommended > 0 && (
                    <span className="text-xs px-2 py-0.5 rounded-full text-yellow-400"
                      style={{ background: "rgba(245,158,11,0.15)" }}>
                      {stats.recommended} ✨
                    </span>
                  )}
                </div>
                <p className="font-semibold text-sm mb-1" style={{ color: "var(--text-primary)" }}>
                  {sphere.name}
                </p>
                <div className="flex items-center gap-2 text-xs" style={{ color: "var(--text-secondary)" }}>
                  <span>{stats.played}/{stats.total}</span>
                  {stats.avgHawkins > 0 && <span>• {stats.avgHawkins} Хокинс</span>}
                </div>
                {/* Progress fill */}
                <div className="absolute bottom-0 left-0 right-0 h-0.5"
                  style={{ background: `${sphere.color}60` }} />
              </motion.button>
            );
          })}
        </div>

        {/* Card list for selected sphere */}
        <AnimatePresence>
          {activeSphere && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="overflow-hidden mb-4">
              <h2 className="text-sm font-semibold mb-3" style={{ color: "var(--text-secondary)" }}>
                {SPHERES.find(s => s.key === activeSphere)?.name} — 22 архетипа
              </h2>
              <div className="space-y-2">
                {getSphereCards(activeSphere).map((card) => (
                  <CardRow key={card.id} card={card} onTap={() => router.push(`/card/${card.id}`)} />
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Bottom Nav */}
      <BottomNav active="home" />
    </div>
  );
}

function CardRow({ card, onTap }: { card: CardProgress; onTap: () => void }) {
  const isRecommended = card.is_recommended_astro && card.status !== "locked";
  return (
    <motion.button
      whileTap={{ scale: 0.97 }}
      onClick={onTap}
      className={`w-full glass flex items-center gap-3 p-3 text-left ${isRecommended ? "pulse-recommended" : ""}`}>
      <div className="text-lg w-8 text-center">
        {STATUS_ICONS[card.status] || "🔒"}
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-medium text-sm truncate" style={{ color: "var(--text-primary)" }}>
          {card.archetype_name}
        </p>
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
          {RANK_STARS[card.rank] || "☆"}
          {card.hawkins_peak > 0 && ` • ${card.hawkins_peak}`}
        </p>
      </div>
      {card.astro_priority === "critical" && (
        <span className="text-xs text-red-400">🔴</span>
      )}
      {card.astro_priority === "high" && (
        <span className="text-xs text-orange-400">🟠</span>
      )}
      <span style={{ color: "var(--text-muted)" }}>›</span>
    </motion.button>
  );
}

export function BottomNav({ active }: { active: string }) {
  const router = useRouter();
  const navItems = [
    { key: "home", icon: "◈", label: "Карта", path: "/" },
    { key: "diary", icon: "📖", label: "Дневник", path: "/diary" },
    { key: "reflect", icon: "🌅", label: "Рефлексия", path: "/reflect" },
    { key: "profile", icon: "◉", label: "Профиль", path: "/profile" },
  ];
  return (
    <nav className="bottom-nav">
      {navItems.map((item) => (
        <button key={item.key} onClick={() => router.push(item.path)}
          className="flex flex-col items-center gap-1 px-4 py-1 transition-all"
          style={{ color: active === item.key ? "var(--violet-l)" : "var(--text-muted)" }}>
          <span className="text-lg">{item.icon}</span>
          <span className="text-xs">{item.label}</span>
        </button>
      ))}
    </nav>
  );
}
