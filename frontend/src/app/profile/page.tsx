"use client";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { profileAPI, gameAPI } from "@/lib/api";
import { useUserStore } from "@/lib/store";
import { BottomNav } from "@/app/page";

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

const SPHERE_ICONS: Record<string, string> = {
    IDENTITY: "✦", MONEY: "◈", RELATIONS: "❤", FAMILY: "⚘",
    MISSION: "◉", HEALTH: "⬡", SOCIETY: "◐", SPIRIT: "∞"
};

// ─── Profile Page ─────────────────────────────────────────────────────────────

export default function ProfilePage() {
    const router = useRouter();
    const { userId, firstName } = useUserStore();
    const [profile, setProfile] = useState<any>(null);
    const [game, setGame] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!userId) return;
        setLoading(true);
        Promise.all([profileAPI.get(userId), gameAPI.getState(userId)])
            .then(([p, g]) => {
                setProfile(p.data);
                setGame(g.data);
            })
            .catch(err => console.error("Failed to load profile", err))
            .finally(() => setLoading(false));
    }, [userId]);

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center min-h-screen" style={{ background: "var(--bg-deep)" }}>
                <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
                    className="w-12 h-12 border-2 border-violet-500 border-t-transparent rounded-full mb-4"
                />
                <p className="text-xs text-muted-foreground animate-pulse">Загрузка профиля...</p>
            </div>
        );
    }

    const xpProgress = game ? Math.min(100, (game.xp_progress / Math.max(1, game.xp_needed)) * 100) : 0;

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
                    }}>
                        👤
                    </div>
                    <div className="flex flex-col">
                        <span className="font-semibold text-base" style={{ color: "var(--text-primary)" }}>
                            {firstName || "Пользователь"}
                        </span>
                        <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
                            {game?.title || "Искатель"}
                        </span>
                    </div>
                </div>
            </div>

            {/* ── Stats grid ── */}
            <div className="px-4 mb-5">
                <div className="grid grid-cols-3 gap-2">
                    <StatTile label="Энергия" value={String(game?.energy || 0)} color="#F59E0B" />
                    <StatTile label="Серия" value={`${game?.streak || 0} дн`} color="#10B981" />
                    <StatTile label="Опыт" value={String(game?.xp || 0)} color="#60A5FA" />
                </div>
            </div>

            {/* ── Level & XP Progress ── */}
            <div className="px-4 mb-6">
                <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="glass p-4"
                >
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
                </motion.div>
            </div>

            {/* ── Sphere awareness list ── */}
            <div className="px-4 mb-6">
                <h3 className="text-sm font-bold mb-3 px-1" style={{ color: "var(--text-secondary)" }}>
                    Осознанность по сферам
                </h3>
                <div className="space-y-3">
                    {SPHERES.map((sphere, idx) => {
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
                                        <span style={{ fontSize: 14, color: sphere.color }}>{SPHERE_ICONS[sphere.key]}</span>
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
                    })}
                </div>
            </div>

            {/* ── Fingerprint ── */}
            {profile?.fingerprint && (
                <div className="px-4 mb-6">
                    <motion.div
                        initial={{ opacity: 0 }}
                        whileInView={{ opacity: 1 }}
                        className="glass p-4 border-dashed"
                        style={{ borderColor: "rgba(255,255,255,0.1)" }}
                    >
                        <h3 className="text-sm font-bold mb-2" style={{ color: "var(--text-secondary)" }}>Отпечаток</h3>
                        <p className="text-xs leading-relaxed" style={{ color: "var(--text-muted)" }}>
                            {profile.fingerprint.matching_available
                                ? "🟢 Матчинг доступен. Ваша энергоинформационная подпись полностью сформирована."
                                : "🔒 Пройдите все 22 карты в любой сфере до уровня ≥500 для разблокировки глобального матчинга."}
                        </p>
                    </motion.div>
                </div>
            )}

            <BottomNav active="profile" />
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
            <p style={{ fontSize: 18, fontWeight: 700, color: "var(--text-primary)", lineHeight: 1 }}>
                {value}
            </p>
        </div>
    );
}
