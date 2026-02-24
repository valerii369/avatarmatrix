"use client";
import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { motion } from "framer-motion";
import { cardsAPI } from "@/lib/api";
import { useUserStore } from "@/lib/store";
import { BottomNav } from "@/app/page";

const STATUS_LABELS: Record<string, string> = {
    locked: "🔒 Закрыта",
    recommended: "✨ Рекомендована",
    in_sync: "🔄 Синхронизация",
    synced: "✅ Синхронизирована",
    aligning: "⚡ Выравнивание",
    aligned: "🌟 Выровнена",
};
const RANK_STARS = ["☆ Спящий", "⭐ Пробуждающийся", "⭐⭐ Осознающий", "⭐⭐⭐ Мастер", "⭐⭐⭐⭐ Мудрец", "⭐⭐⭐⭐⭐ Просветлённый"];

export default function CardPage() {
    const router = useRouter();
    const params = useParams();
    const { userId } = useUserStore();
    const [card, setCard] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!userId || !params.id) return;
        cardsAPI.getOne(userId, Number(params.id))
            .then(r => { setCard(r.data); setLoading(false); })
            .catch(() => setLoading(false));
    }, [userId, params.id]);

    if (loading) return (
        <div className="flex items-center justify-center min-h-screen">
            <div className="w-10 h-10 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
        </div>
    );

    if (!card) return null;

    const canSync = ["recommended", "synced", "aligned"].includes(card.status);
    const canAlign = card.status === "synced" || card.status === "aligned";

    return (
        <div className="min-h-screen pb-24">
            {/* Back button */}
            <div className="px-4 pt-4 pb-2">
                <button onClick={() => router.back()} className="text-sm" style={{ color: "var(--text-muted)" }}>
                    ← Назад
                </button>
            </div>

            <div className="px-4 space-y-4">
                {/* Card header */}
                <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
                    className="glass-strong p-6 text-center"
                    style={{ borderColor: card.sphere_color, boxShadow: `0 0 32px ${card.sphere_color}30` }}>
                    <div className="text-5xl mb-3" style={{ color: card.sphere_color }}>
                        {card.rank === 5 ? "🌟" : card.rank >= 3 ? "✦" : "◈"}
                    </div>
                    <h1 className="text-2xl font-bold mb-1" style={{ color: "var(--text-primary)" }}>
                        {card.archetype_name}
                    </h1>
                    <p className="text-sm mb-3" style={{ color: card.sphere_color }}>
                        {card.sphere_name_ru}
                    </p>
                    <div className="flex items-center justify-center gap-4">
                        <span className="text-sm" style={{ color: "var(--text-muted)" }}>
                            {RANK_STARS[card.rank]}
                        </span>
                        {card.hawkins_peak > 0 && (
                            <span className="text-sm font-semibold" style={{ color: card.sphere_color }}>
                                {card.hawkins_peak} Хокинс (пик)
                            </span>
                        )}
                    </div>
                </motion.div>

                {/* Status & sessions */}
                <div className="glass p-4">
                    <div className="flex items-center justify-between mb-3">
                        <span className="text-sm" style={{ color: "var(--text-muted)" }}>Статус</span>
                        <span className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                            {STATUS_LABELS[card.status] || card.status}
                        </span>
                    </div>
                    <div className="flex items-center justify-between mb-3">
                        <span className="text-sm" style={{ color: "var(--text-muted)" }}>Синхронизаций</span>
                        <span className="text-sm" style={{ color: "var(--text-primary)" }}>{card.sync_sessions_count}</span>
                    </div>
                    <div className="flex items-center justify-between">
                        <span className="text-sm" style={{ color: "var(--text-muted)" }}>Сессий</span>
                        <span className="text-sm" style={{ color: "var(--text-primary)" }}>{card.align_sessions_count}</span>
                    </div>
                    {card.astro_priority && (
                        <div className="mt-3 pt-3" style={{ borderTop: "1px solid var(--border)" }}>
                            <p className="text-xs" style={{ color: "var(--text-muted)" }}>{card.astro_reason}</p>
                        </div>
                    )}
                </div>

                {/* Archetype info */}
                <div className="glass p-4 space-y-3">
                    <div>
                        <p className="text-xs mb-1" style={{ color: "var(--text-muted)" }}>🌑 Тень</p>
                        <p className="text-sm" style={{ color: "#fc8181" }}>{card.archetype_shadow}</p>
                    </div>
                    <div style={{ borderTop: "1px solid var(--border)", paddingTop: "12px" }}>
                        <p className="text-xs mb-1" style={{ color: "var(--text-muted)" }}>☀️ Свет</p>
                        <p className="text-sm" style={{ color: "#68d391" }}>{card.archetype_light}</p>
                    </div>
                    <div style={{ borderTop: "1px solid var(--border)", paddingTop: "12px" }}>
                        <p className="text-xs mb-2" style={{ color: "var(--text-muted)" }}>Главный вопрос сферы</p>
                        <p className="text-sm italic" style={{ color: card.sphere_color }}>
                            {card.sphere_main_question}
                        </p>
                    </div>
                </div>

                {/* Hawkins bar */}
                {card.hawkins_current > 0 && (
                    <div className="glass p-4">
                        <div className="flex items-center justify-between mb-2">
                            <p className="text-xs" style={{ color: "var(--text-muted)" }}>Уровень сознания</p>
                            <p className="text-xs font-semibold" style={{ color: "var(--text-primary)" }}>
                                {card.hawkins_current} / {card.hawkins_peak}
                            </p>
                        </div>
                        <div className="hawkins-bar rounded-full overflow-hidden">
                            <div style={{ width: `${(card.hawkins_peak / 1000) * 100}%`, height: "100%" }} />
                        </div>
                    </div>
                )}

                {/* Action buttons */}
                <div className="space-y-3 pb-4">
                    {canSync && (
                        <motion.button whileTap={{ scale: 0.97 }}
                            onClick={() => router.push(`/sync/${card.id}`)}
                            className="w-full py-4 rounded-2xl font-semibold text-base"
                            style={{
                                background: "linear-gradient(135deg, var(--violet), #6366f1)",
                                color: "#fff",
                                boxShadow: "0 8px 24px rgba(139,92,246,0.4)",
                            }}>
                            Синхронизация (10 фаз) · 25 ✦
                        </motion.button>
                    )}
                    {canAlign && (
                        <motion.button whileTap={{ scale: 0.97 }}
                            onClick={() => router.push(`/session/${card.id}`)}
                            className="w-full py-4 rounded-2xl font-semibold text-base"
                            style={{
                                background: "linear-gradient(135deg, var(--gold), #f97316)",
                                color: "#000",
                                boxShadow: "0 8px 24px rgba(245,158,11,0.4)",
                            }}>
                            Сессия выравнивания · 40 ✦
                        </motion.button>
                    )}
                    {card.status === "locked" && (
                        <div className="glass p-4 text-center">
                            <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                                🔒 Сначала пройдите рекомендованные карты
                            </p>
                        </div>
                    )}
                </div>
            </div>

            <BottomNav active="" />
        </div>
    );
}
