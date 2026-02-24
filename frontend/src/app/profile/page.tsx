"use client";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { profileAPI, gameAPI } from "@/lib/api";
import { useUserStore } from "@/lib/store";
import { BottomNav } from "@/app/page";

export default function ProfilePage() {
    const { userId, firstName } = useUserStore();
    const [profile, setProfile] = useState<any>(null);
    const [game, setGame] = useState<any>(null);

    useEffect(() => {
        if (!userId) return;
        Promise.all([profileAPI.get(userId), gameAPI.getState(userId)]).then(([p, g]) => {
            setProfile(p.data);
            setGame(g.data);
        });
    }, [userId]);

    const SPHERE_ICONS: Record<string, string> = {
        IDENTITY: "✦", MONEY: "◈", RELATIONS: "❤", FAMILY: "⚘",
        MISSION: "◉", HEALTH: "⬡", SOCIETY: "◐", SPIRIT: "∞"
    };

    return (
        <div className="min-h-screen pb-24">
            <div className="px-4 pt-6 pb-4">
                <h1 className="text-xl font-bold gradient-text">Профиль</h1>
            </div>

            <div className="px-4 space-y-4">
                {/* User card */}
                <div className="glass-strong p-5 text-center">
                    <div className="w-16 h-16 rounded-full mx-auto mb-3 flex items-center justify-center text-3xl"
                        style={{ background: "linear-gradient(135deg, var(--violet), var(--gold))" }}>
                        ✦
                    </div>
                    <h2 className="text-xl font-bold" style={{ color: "var(--text-primary)" }}>{firstName}</h2>
                    <p className="text-sm mb-2" style={{ color: "var(--violet-l)" }}>{game?.title || "Искатель"}</p>
                    <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                        Уровень эволюции {game?.evolution_level}
                    </p>
                </div>

                {/* Stats */}
                {game && (
                    <div className="grid grid-cols-3 gap-3">
                        {[
                            { label: "Энергия ✦", value: game.energy },
                            { label: "Серия 🔥", value: game.streak },
                            { label: "XP", value: game.xp },
                        ].map((stat) => (
                            <div key={stat.label} className="glass p-3 text-center">
                                <p className="text-lg font-bold" style={{ color: "var(--text-primary)" }}>{stat.value}</p>
                                <p className="text-xs" style={{ color: "var(--text-muted)" }}>{stat.label}</p>
                            </div>
                        ))}
                    </div>
                )}

                {/* XP bar */}
                {game && (
                    <div className="glass p-4">
                        <div className="flex justify-between text-xs mb-2" style={{ color: "var(--text-muted)" }}>
                            <span>Опыт</span>
                            <span>{game.xp_progress}/{game.xp_needed} XP</span>
                        </div>
                        <div className="phase-bar">
                            <div className="phase-bar-fill"
                                style={{ width: `${Math.min(100, (game.xp_progress / Math.max(1, game.xp_needed)) * 100)}%` }} />
                        </div>
                    </div>
                )}

                {/* Sphere awareness */}
                {game?.sphere_data && (
                    <div className="glass p-4">
                        <h3 className="text-sm font-semibold mb-3" style={{ color: "var(--text-secondary)" }}>
                            Осознанность сфер
                        </h3>
                        <div className="space-y-2">
                            {Object.entries(game.sphere_data as Record<string, any>).map(([sphere, data]) => (
                                <div key={sphere} className="flex items-center gap-3">
                                    <span className="text-sm w-6 text-center" style={{ color: "var(--text-muted)" }}>
                                        {SPHERE_ICONS[sphere] || "•"}
                                    </span>
                                    <div className="flex-1">
                                        <div className="flex justify-between text-xs mb-1">
                                            <span style={{ color: "var(--text-secondary)" }}>{sphere}</span>
                                            <span style={{ color: "var(--text-muted)" }}>{data.awareness}</span>
                                        </div>
                                        <div className="phase-bar">
                                            <div className="phase-bar-fill"
                                                style={{ width: `${Math.min(100, (data.min_hawkins / 1000) * 100)}%` }} />
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Fingerprint */}
                {profile?.fingerprint && (
                    <div className="glass p-4">
                        <h3 className="text-sm font-semibold mb-2" style={{ color: "var(--text-secondary)" }}>Отпечаток</h3>
                        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                            {profile.fingerprint.matching_available
                                ? "🟢 Матчинг доступен"
                                : "🔒 Пройдите все 22 карты в любой сфере до ≥500 для разблокировки матчинга"}
                        </p>
                    </div>
                )}
            </div>

            <BottomNav active="profile" />
        </div>
    );
}
