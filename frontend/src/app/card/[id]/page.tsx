"use client";
import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { motion } from "framer-motion";
import { cardsAPI } from "@/lib/api";
import { useUserStore } from "@/lib/store";
import { BottomNav } from "@/app/page";

// ─── Status config ────────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<string, { label: string; dot: string; color: string }> = {
    locked: { label: "ЗАКРЫТА", dot: "#6b7280", color: "rgba(255,255,255,0.3)" },
    recommended: { label: "ДОСТУПНА", dot: "#F59E0B", color: "#F59E0B" },
    in_sync: { label: "В ПРОЦЕССЕ", dot: "#06B6D4", color: "#06B6D4" },
    synced: { label: "АКТИВНА", dot: "#10B981", color: "#10B981" },
    aligning: { label: "ВЫРАВНИВАНИЕ", dot: "#A78BFA", color: "#A78BFA" },
    aligned: { label: "ЗАВЕРШЕНА", dot: "#10B981", color: "#10B981" },
};

const RANK_STARS = [
    "☆ Спящий", "⭐ Пробуждающийся", "⭐⭐ Осознающий",
    "⭐⭐⭐ Мастер", "⭐⭐⭐⭐ Мудрец", "⭐⭐⭐⭐⭐ Просветлённый",
];

const SPHERE_EMOJI: Record<string, string> = {
    IDENTITY: "✦", MONEY: "◈", RELATIONS: "❤", FAMILY: "⚘",
    MISSION: "◉", HEALTH: "⬡", SOCIETY: "◐", SPIRIT: "∞",
};

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function CardPage() {
    const router = useRouter();
    const params = useParams();
    const { userId } = useUserStore();
    const [card, setCard] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!userId || !params.id) return;
        cardsAPI.getOne(userId, Number(params.id))
            .then((r) => { setCard(r.data); setLoading(false); })
            .catch(() => setLoading(false));
    }, [userId, params.id]);

    if (loading) return (
        <div className="flex items-center justify-center min-h-screen" style={{ background: "var(--bg-deep)" }}>
            <motion.div animate={{ rotate: 360 }} transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                className="w-10 h-10 border-2 border-violet-500 border-t-transparent rounded-full" />
        </div>
    );

    if (!card) return null;

    const statusCfg = STATUS_CONFIG[card.status] ?? STATUS_CONFIG.locked;
    const canSync = ["recommended", "synced", "aligned", "in_sync"].includes(card.status);
    const canAlign = card.status === "synced" || card.status === "aligned";
    const isResuming = card.status === "in_sync";
    const sphereColor = card.sphere_color ?? "#10B981";
    const cardTypeLabel = `КАРТА ${(card.sphere_name_ru || "").toUpperCase()}`;
    const emoji = SPHERE_EMOJI[card.sphere] ?? "◈";

    return (
        <div className="min-h-screen pb-28" style={{ background: "var(--bg-deep)" }}>


            {/* ── Back ── */}

            <div className="px-4 mb-3">
                <button onClick={() => router.back()}
                    style={{ fontSize: 13, color: "var(--text-muted)", background: "none", border: "none", cursor: "pointer", padding: 0 }}>
                    ‹ Назад
                </button>
            </div>

            {/* ── Trading Card ── */}
            <div className="px-4">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.4 }}
                    style={{
                        background: "rgba(17,25,50,0.95)",
                        border: `1px solid rgba(255,255,255,0.1)`,
                        borderRadius: 24,
                        overflow: "hidden",
                        boxShadow: `0 0 40px ${sphereColor}18`,
                    }}
                >
                    {/* Card inner top bar */}
                    <div style={{ padding: "14px 16px 10px" }}>

                        {/* Type + lvl row */}
                        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
                            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                                <span style={{ fontSize: 10, color: sphereColor }}>◆</span>
                                <span style={{ fontSize: 10, fontWeight: 700, color: "rgba(255,255,255,0.35)", letterSpacing: "0.12em" }}>
                                    {cardTypeLabel}
                                </span>
                            </div>
                            <span style={{ fontSize: 12, fontWeight: 700, color: "rgba(255,255,255,0.45)" }}>
                                lvl {card.rank}
                            </span>
                        </div>

                        {/* Name + status badge */}
                        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
                            <h1 style={{ fontSize: 26, fontWeight: 800, color: "var(--text-primary)", lineHeight: 1, margin: 0, fontFamily: "'Outfit', sans-serif" }}>
                                {card.archetype_name}
                            </h1>
                            <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
                                <div style={{
                                    width: 7, height: 7, borderRadius: "50%",
                                    background: statusCfg.dot,
                                    boxShadow: `0 0 6px ${statusCfg.dot}`,
                                    flexShrink: 0,
                                }} />
                                <span style={{ fontSize: 10, fontWeight: 700, color: statusCfg.color, letterSpacing: "0.1em" }}>
                                    {statusCfg.label}
                                </span>
                            </div>
                        </div>

                        {/* ── Large archetype image ── */}
                        <div style={{
                            width: "100%",
                            aspectRatio: "4/3",
                            borderRadius: 16,
                            overflow: "hidden",
                            position: "relative",
                            marginBottom: 16,
                            background: `linear-gradient(135deg, ${sphereColor}22 0%, rgba(0,0,0,0.8) 100%)`,
                            border: "1px solid rgba(255,255,255,0.07)",
                        }}>
                            {/* Decorative diagonal lines overlay */}
                            <div style={{
                                position: "absolute", inset: 0,
                                backgroundImage: `repeating-linear-gradient(
                  -45deg,
                  transparent,
                  transparent 20px,
                  rgba(255,255,255,0.015) 20px,
                  rgba(255,255,255,0.015) 21px
                )`,
                            }} />
                            {/* Full background image */}
                            <img
                                src={`/archetypes/${card.archetype_id}.webp`}
                                alt={card.archetype_name}
                                style={{
                                    position: "absolute", inset: 0,
                                    width: "100%", height: "100%",
                                    objectFit: "cover",
                                    opacity: 0.9,
                                    zIndex: 0,
                                    mixBlendMode: "screen",
                                }}
                            />
                            {/* Sphere name badge at the bottom center */}
                            <div style={{
                                position: "absolute", bottom: 16, left: 0, right: 0,
                                display: "flex", justifyContent: "center", zIndex: 2
                            }}>
                                <div style={{
                                    background: "rgba(0,0,0,0.55)",
                                    backdropFilter: "blur(8px)",
                                    padding: "6px 14px",
                                    borderRadius: 20,
                                    border: `1px solid ${sphereColor}50`,
                                }}>
                                    <p style={{ fontSize: 11, color: "rgba(255,255,255,0.9)", letterSpacing: "0.15em", textTransform: "uppercase", margin: 0, fontWeight: 600 }}>
                                        {card.sphere_name_ru}
                                    </p>
                                </div>
                            </div>
                            {/* Top-right corner glow */}
                            <div style={{
                                position: "absolute", top: 0, right: 0,
                                width: 120, height: 120,
                                background: `radial-gradient(circle at top right, ${sphereColor}25 0%, transparent 70%)`,
                                pointerEvents: "none",
                            }} />
                        </div>

                        {/* ── Shadow + Light + Right panel ── */}
                        <div style={{ display: "flex", gap: 12 }}>

                            {/* Left: Тень + Свет */}
                            <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 12 }}>

                                {/* Тень */}
                                <div>
                                    <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
                                        <span style={{ fontSize: 12, color: "#06B6D4", letterSpacing: "0.15em" }}>⠿</span>
                                        <span style={{ fontSize: 11, fontWeight: 700, color: "#06B6D4", letterSpacing: "0.12em" }}>ТЕНЬ</span>
                                    </div>
                                    <p style={{ fontSize: 12, color: "rgba(255,255,255,0.55)", lineHeight: 1.5, margin: 0 }}>
                                        {card.archetype_shadow || "—"}
                                    </p>
                                </div>

                                {/* Свет */}
                                <div>
                                    <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
                                        <span style={{ fontSize: 12, color: "#10B981", letterSpacing: "0.15em" }}>⠿</span>
                                        <span style={{ fontSize: 11, fontWeight: 700, color: "#10B981", letterSpacing: "0.12em" }}>Свет</span>
                                    </div>
                                    <p style={{ fontSize: 12, color: "rgba(255,255,255,0.55)", lineHeight: 1.5, margin: 0 }}>
                                        {card.archetype_light || "—"}
                                    </p>
                                </div>
                            </div>

                            {/* Right: Hawkins score panel */}
                            <div style={{
                                width: 56,
                                flexShrink: 0,
                                background: "rgba(255,255,255,0.03)",
                                borderRadius: 12,
                                border: "1px solid rgba(255,255,255,0.06)",
                                display: "flex",
                                flexDirection: "column",
                                alignItems: "center",
                                justifyContent: "flex-end",
                                padding: "10px 0 12px",
                                gap: 2,
                                position: "relative",
                                overflow: "hidden",
                            }}>
                                {/* Decorative dashes */}
                                <div style={{
                                    position: "absolute", top: 0, left: 0, right: 0, bottom: 40,
                                    display: "flex", flexDirection: "column",
                                    alignItems: "center",
                                    justifyContent: "flex-start",
                                    paddingTop: 10,
                                    gap: 4,
                                    overflow: "hidden",
                                }}>
                                    {Array.from({ length: 16 }).map((_, i) => (
                                        <div key={i} style={{
                                            width: 18, height: 2, borderRadius: 1,
                                            background: i < Math.round((card.hawkins_peak / 1000) * 16)
                                                ? `${sphereColor}80`
                                                : "rgba(255,255,255,0.08)",
                                        }} />
                                    ))}
                                </div>
                                {/* Score number */}
                                <span style={{
                                    fontSize: 18, fontWeight: 800,
                                    color: card.hawkins_peak > 0 ? sphereColor : "rgba(255,255,255,0.2)",
                                    fontFamily: "'Outfit', sans-serif",
                                    lineHeight: 1,
                                    position: "relative", zIndex: 1,
                                }}>
                                    {card.hawkins_peak > 0 ? card.hawkins_peak : "—"}
                                </span>
                            </div>
                        </div>

                        {/* Sphere main question */}
                        {card.sphere_main_question && (
                            <div style={{
                                marginTop: 16,
                                padding: "12px 14px",
                                background: `${sphereColor}0d`,
                                borderRadius: 12,
                                border: `1px solid ${sphereColor}25`,
                            }}>
                                <p style={{ fontSize: 12, color: "rgba(255,255,255,0.5)", margin: 0, lineHeight: 1.5, fontStyle: "italic" }}>
                                    {card.sphere_main_question}
                                </p>
                            </div>
                        )}
                    </div>

                    {/* ── Action buttons inside card ── */}
                    <div style={{ padding: "0 16px 16px", display: "flex", flexDirection: "column", gap: 10 }}>
                        {card.status === "locked" && (
                            <div style={{
                                padding: "12px 16px", borderRadius: 14,
                                background: "rgba(255,255,255,0.04)",
                                border: "1px solid rgba(255,255,255,0.07)",
                                textAlign: "center",
                            }}>
                                <p style={{ fontSize: 13, color: "var(--text-muted)", margin: 0 }}>
                                    🔒 Сначала пройдите рекомендованные карты
                                </p>
                            </div>
                        )}

                        {canSync && (
                            <motion.button
                                whileTap={{ scale: 0.97 }}
                                onClick={() => router.push(`/sync/${card.id}`)}
                                style={{
                                    width: "100%",
                                    padding: "16px",
                                    borderRadius: 16,
                                    border: "none",
                                    cursor: "pointer",
                                    background: "linear-gradient(135deg, #10B981, #059669)",
                                    color: "#000",
                                    fontWeight: 800,
                                    fontSize: 14,
                                    letterSpacing: "0.08em",
                                    boxShadow: "0 8px 24px rgba(16,185,129,0.35)",
                                    fontFamily: "'Outfit', sans-serif",
                                }}
                            >
                                {isResuming ? "▶ ПРОДОЛЖИТЬ СИНХРОНИЗАЦИЮ" : `СИНХРОНИЗАЦИЯ · 25 ✦`}
                            </motion.button>
                        )}

                        {canAlign && (
                            <motion.button
                                whileTap={{ scale: 0.97 }}
                                onClick={() => router.push(`/session/${card.id}`)}
                                style={{
                                    width: "100%",
                                    padding: "16px",
                                    borderRadius: 16,
                                    border: "none",
                                    cursor: "pointer",
                                    background: "linear-gradient(135deg, #F59E0B, #D97706)",
                                    color: "#000",
                                    fontWeight: 800,
                                    fontSize: 14,
                                    letterSpacing: "0.08em",
                                    boxShadow: "0 8px 24px rgba(245,158,11,0.35)",
                                    fontFamily: "'Outfit', sans-serif",
                                }}
                            >
                                СЕССИЯ ВЫРАВНИВАНИЯ · 40 ✦
                            </motion.button>
                        )}
                    </div>
                </motion.div>
            </div>

            <BottomNav active="cards" />
        </div>
    );
}
