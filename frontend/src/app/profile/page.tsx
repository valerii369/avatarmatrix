"use client";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { authAPI, profileAPI, gameAPI } from "@/lib/api";
import { useUserStore } from "@/lib/store";
import { BottomNav } from "@/app/page";
import useSWR from "swr";
import { Skeleton } from "@/components/Skeleton";
import { EnergyIcon } from "@/components/EnergyIcon";

// ─── Constants ────────────────────────────────────────────────────────────────

const SPHERES = [
    { key: "IDENTITY", name: "Личность", color: "#F59E0B" },
    { key: "MONEY", name: "Деньги", color: "#10B981" },
    { key: "RELATIONS", name: "Отношения", color: "#EC4899" },
    { key: "FAMILY", name: "Род", color: "#F97316" },
    { key: "MISSION", name: "Миссия", color: "#3B82F6" },
    { key: "HEALTH", name: "Здоровье", color: "#22C55E" },
    { key: "SOCIETY", name: "Влияние", color: "#8B5CF6" },
    { key: "SPIRIT", name: "Духовность", color: "#A78BFA" },
];


// ─── Profile Page ─────────────────────────────────────────────────────────────

export default function ProfilePage() {
    const router = useRouter();
    const { userId, firstName, setUser, referralCode, energy, evolutionLevel, photoUrl } = useUserStore();
    const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
    const [activeTab, setActiveTab] = useState<"main" | "settings" | "referrals">("main");

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
                    referralCode: d.referral_code,
                });

                if (typeof window !== "undefined")
                    localStorage.setItem("avatar_token", d.token);

                setStatus("ready");
            } catch (e: any) {
                console.error("Init error", e);
                setStatus("error");
            }
        };
        if (!userId) {
            initAuth();
        } else {
            setStatus("ready");
        }
    }, [userId, setUser]);

    // 2. Data Fetching via SWR
    const { data: profile, isValidating: loadingProfile } = useSWR(
        userId && status === "ready" ? ["profile", userId] : null,
        () => profileAPI.get(userId!).then(res => res.data)
    );

    const { data: game, isValidating: loadingGame } = useSWR(
        userId && status === "ready" ? ["game_state", userId] : null,
        () => gameAPI.getState(userId!).then(res => res.data)
    );

    // ── Loading/Error States ──────────────────────────────────────────────────
    if (status === "loading" || !userId) {
        return (
            <div className="flex flex-col items-center justify-center min-h-screen" style={{ background: "var(--bg-deep)" }}>
                <div className="w-12 h-12 border-2 border-violet-500 border-t-transparent rounded-full mb-4 animate-spin" />
                <p className="text-xs text-muted-foreground animate-pulse">Загрузка профиля...</p>
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
                        fontSize: 24, color: "var(--text-muted)", flexShrink: 0,
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

            {/* ── Menu (Tabs) ── */}
            <div className="px-4 mb-5 flex gap-2 overflow-x-auto pb-1" style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}>
                <button
                    onClick={() => setActiveTab("main")}
                    className="flex-1 py-2.5 px-4 rounded-[16px] flex flex-col items-center justify-center gap-1 min-w-[30%] transition-all"
                    style={{
                        background: activeTab === "main" ? "rgba(255,255,255,0.12)" : "rgba(255,255,255,0.05)",
                        border: activeTab === "main" ? "1px solid rgba(255,255,255,0.2)" : "1px solid var(--border)"
                    }}
                >
                    <span className="text-xl">🌟</span>
                    <span className={`text-[11px] font-medium ${activeTab === "main" ? "text-white" : "text-white/70"}`}>Основное</span>
                </button>
                <button
                    onClick={() => setActiveTab("settings")}
                    className="flex-1 py-2.5 px-4 rounded-[16px] flex flex-col items-center justify-center gap-1 min-w-[30%] transition-all"
                    style={{
                        background: activeTab === "settings" ? "rgba(255,255,255,0.12)" : "rgba(255,255,255,0.05)",
                        border: activeTab === "settings" ? "1px solid rgba(255,255,255,0.2)" : "1px solid var(--border)"
                    }}
                >
                    <span className="text-xl">⚙️</span>
                    <span className={`text-[11px] font-medium ${activeTab === "settings" ? "text-white" : "text-white/70"}`}>Настройки</span>
                </button>
                <button
                    onClick={() => setActiveTab("referrals")}
                    className="flex-1 py-2.5 px-4 rounded-[16px] flex flex-col items-center justify-center gap-1 min-w-[30%] relative overflow-hidden transition-all"
                    style={{
                        background: activeTab === "referrals" ? "linear-gradient(135deg, rgba(139, 92, 246, 0.25), rgba(236, 72, 153, 0.25))" : "linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(236, 72, 153, 0.1))",
                        border: activeTab === "referrals" ? "1px solid rgba(139, 92, 246, 0.5)" : "1px solid rgba(139, 92, 246, 0.2)"
                    }}
                >
                    {activeTab === "referrals" && <div className="absolute inset-0 bg-gradient-to-tr from-violet-500/20 to-transparent" />}
                    <span className="text-xl">🤝</span>
                    <span className={`text-[11px] font-medium ${activeTab === "referrals" ? "text-violet-100" : "text-violet-200/70"}`}>Рефералы</span>
                </button>
            </div>

            {/* ── Tab Content ── */}
            <div className="flex-1">
                {activeTab === "main" && (
                    <MainProfileView game={game} loadingGame={loadingGame} profile={profile} />
                )}
                {activeTab === "settings" && (
                    <SettingsView />
                )}
                {activeTab === "referrals" && (
                    <ReferralView referralCode={referralCode} />
                )}
            </div>

            <BottomNav active="profile" />
        </div>
    );
}

// ─── Sub-Views ───────────────────────────────────────────────────────────────

function MainProfileView({ game, loadingGame, profile }: any) {
    const xpProgress = game ? Math.min(100, (game.xp_progress / Math.max(1, game.xp_needed)) * 100) : 0;

    return (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
            {/* Stats grid */}
            <div className="px-4 mb-5">
                <div className="grid grid-cols-3 gap-2">
                    {loadingGame && !game ? (
                        <>
                            <Skeleton className="h-16 rounded-2xl" />
                            <Skeleton className="h-16 rounded-2xl" />
                            <Skeleton className="h-16 rounded-2xl" />
                        </>
                    ) : (
                        <>
                            <StatTile label="Энергия" value={String(game?.energy || 0)} color="#F59E0B" />
                            <StatTile label="Серия" value={`${game?.streak || 0} дн`} color="#10B981" />
                            <StatTile label="Опыт" value={String(game?.xp || 0)} color="#60A5FA" />
                        </>
                    )}
                </div>
            </div>

            {/* Level & XP Progress */}
            <div className="px-4 mb-6">
                <div className="glass p-4">
                    <div className="flex items-center justify-between mb-3">
                        <span style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)" }}>
                            Уровень {game?.evolution_level}
                        </span>
                        <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
                            {game?.xp_progress} / {game?.xp_needed} XP
                        </span>
                    </div>
                    <div style={{ height: 4, background: "rgba(255,255,255,0.08)", borderRadius: 2, overflow: "hidden" }}>
                        <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${xpProgress}%` }}
                            transition={{ duration: 1, ease: "easeOut" }}
                            style={{
                                height: "100%",
                                background: "linear-gradient(90deg, #8B5CF6, #F59E0B)",
                            }}
                        />
                    </div>
                </div>
            </div>

            {/* Sphere awareness list */}
            <div className="px-4 mb-6">
                <h3 className="text-sm font-bold mb-3 px-1" style={{ color: "var(--text-secondary)" }}>
                    Осознанность по сферам
                </h3>
                <div className="space-y-3">
                    {loadingGame && !game ? (
                        Array.from({ length: 4 }).map((_, i: number) => (
                            <Skeleton key={i} className="h-16 w-full rounded-2xl" />
                        ))
                    ) : (
                        SPHERES.map((sphere, idx) => {
                            const data = game?.sphere_data?.[sphere.key] || { awareness: 0, min_hawkins: 0 };
                            const progress = Math.min(100, (data.min_hawkins / 1000) * 100);

                            return (
                                <motion.div
                                    key={sphere.key}
                                    initial={{ opacity: 0, x: -10 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    transition={{ delay: idx * 0.05 }}
                                    className="glass p-3 flex flex-col gap-2"
                                >
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-2">
                                            <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>{sphere.name}</span>
                                        </div>
                                        <span style={{ fontSize: 13, fontWeight: 700, color: sphere.color }}>
                                            {data.awareness}
                                        </span>
                                    </div>
                                    <div style={{ height: 3, background: "rgba(255,255,255,0.05)", borderRadius: 1.5, overflow: "hidden" }}>
                                        <motion.div
                                            initial={{ width: 0 }}
                                            animate={{ width: `${progress}%` }}
                                            transition={{ duration: 1, ease: "easeOut", delay: 0.2 + idx * 0.05 }}
                                            style={{
                                                height: "100%",
                                                background: sphere.color,
                                                boxShadow: `0 0 8px ${sphere.color}55`,
                                            }}
                                        />
                                    </div>
                                </motion.div>
                            );
                        })
                    )}
                </div>
            </div>

            {/* Fingerprint */}
            {profile?.fingerprint && (
                <div className="px-4 mb-6">
                    <div className="glass p-4 border-dashed" style={{ borderColor: "rgba(255,255,255,0.1)" }}>
                        <h3 className="text-sm font-bold mb-2" style={{ color: "var(--text-secondary)" }}>Отпечаток</h3>
                        <p className="text-xs leading-relaxed" style={{ color: "var(--text-muted)" }}>
                            {profile.fingerprint.matching_available
                                ? "🟢 Матчинг доступен. Ваша энергоинформационная подпись полностью сформирована."
                                : "🔒 Пройдите все 22 карты в любой сфере до уровня ≥500 для разблокировки глобального матчинга."}
                        </p>
                    </div>
                </div>
            )}
        </motion.div>
    );
}

function SettingsView() {
    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
            className="px-4"
        >
            <div className="glass p-6 text-center">
                <p className="text-sm text-white/50">Настройки будут доступны в ближайшем обновлении</p>
            </div>
        </motion.div>
    );
}

function ReferralView({ referralCode }: { referralCode: string }) {
    const botUsername = "avatarMatrixBot"; // Fallback if not specified
    const refLink = `https://t.me/${botUsername}?startapp=${referralCode}`;

    const handleCopy = () => {
        navigator.clipboard.writeText(refLink);
        // Show some feedback? (toast/alert)
        alert("Ссылка скопирована!");
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
            className="px-4 space-y-4"
        >
            <div className="glass p-5 space-y-4">
                <div className="text-center">
                    <h3 className="text-lg font-bold text-white mb-1">Реферальная программа</h3>
                    <p className="text-xs text-white/60 mb-4">
                        Приглашайте друзей и получайте ✦ Энергию за их первый Sync или покупку пакета
                    </p>
                </div>

                <div className="grid grid-cols-2 gap-3 mb-2">
                    <div className="bg-white/5 rounded-2xl p-3 border border-white/10 text-center">
                        <p className="text-[10px] text-white/40 uppercase font-bold tracking-wider mb-1">Ваш бонус</p>
                        <p className="text-lg font-bold text-amber-400">+500 ✦</p>
                    </div>
                    <div className="bg-white/5 rounded-2xl p-3 border border-white/10 text-center">
                        <p className="text-[10px] text-white/40 uppercase font-bold tracking-wider mb-1">Их бонус</p>
                        <p className="text-lg font-bold text-emerald-400">+200 ✦</p>
                    </div>
                </div>

                <div className="space-y-2">
                    <p className="text-xs font-medium text-white/70 ml-1">Ваша ссылка:</p>
                    <div className="flex gap-2">
                        <div className="flex-1 bg-black/40 border border-white/10 rounded-xl p-3 overflow-hidden text-ellipsis whitespace-nowrap text-xs text-white/60">
                            {refLink}
                        </div>
                        <button
                            onClick={handleCopy}
                            className="bg-violet-600 hover:bg-violet-500 text-white px-4 rounded-xl font-bold text-sm transition-colors"
                        >
                            Копия
                        </button>
                    </div>
                </div>
            </div>

            <div className="glass p-4">
                <h4 className="text-xs font-bold text-white/40 uppercase tracking-widest mb-3">Ваши рефералы</h4>
                <div className="text-center py-6">
                    <p className="text-sm text-white/30 italic">Список пока пуст...</p>
                </div>
            </div>
        </motion.div>
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
            <p style={{ fontSize: 18, fontWeight: 700, color: "var(--text-primary)", lineHeight: 1 }}>
                {value}
            </p>
        </div>
    );
}
