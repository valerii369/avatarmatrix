"use client";
import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { motion } from "framer-motion";
import { cardsAPI } from "@/lib/api";
import { useUserStore } from "@/lib/store";
import { BottomNav } from "@/app/page";

// ─── Status config ────────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<string, { label: string; statusLabel: string; color: string }> = {
    locked: { label: "ЗАКРЫТА", statusLabel: "ЗАКРЫТА", color: "rgba(255,255,255,0.3)" },
    recommended: { label: "РЕКОМЕНДОВАНА", statusLabel: "ДОСТУПНА", color: "#F59E0B" },
    in_sync: { label: "В ПРОЦЕССЕ", statusLabel: "В ПРОЦЕССЕ", color: "#06B6D4" },
    synced: { label: "АКТИВНА", statusLabel: "АКТИВНА", color: "#10B981" },
    aligning: { label: "АКТИВНА", statusLabel: "АКТИВНА", color: "#10B981" },
    aligned: { label: "АКТИВНА", statusLabel: "АКТИВНА", color: "#10B981" },
};

const getHawkinsColor = (score: number) => {
    if (score <= 200) {
        const ratio = score / 200;
        const r = Math.round(239 + (245 - 239) * ratio);
        const g = Math.round(68 + (158 - 68) * ratio);
        const b = Math.round(68 + (11 - 68) * ratio);
        return `rgb(${r}, ${g}, ${b})`;
    } else {
        const ratio = Math.min(1, (score - 200) / 300);
        const r = Math.round(245 + (16 - 245) * ratio);
        const g = Math.round(158 + (185 - 158) * ratio);
        const b = Math.round(11 + (129 - 11) * ratio);
        return `rgb(${r}, ${g}, ${b})`;
    }
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
            .then((r) => {
                setCard(r.data);
                setLoading(false);
                // Removed auto-sync if recommended to let user see card details first
                // if (r.data.status === "recommended") {
                //     router.push(`/sync/${r.data.id}`);
                // }
            })
            .catch(() => setLoading(false));
    }, [userId, params.id, router]);

    if (loading) return (
        <div className="flex items-center justify-center min-h-screen" style={{ background: "var(--bg-deep)" }}>
            <motion.div animate={{ rotate: 360 }} transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                className="w-10 h-10 border-2 border-violet-500 border-t-transparent rounded-full" />
        </div>
    );

    if (!card) return null;

    const statusCfg = STATUS_CONFIG[card.status] ?? STATUS_CONFIG.locked;
    const canSync = ["recommended", "in_sync"].includes(card.status);
    const canAlign = ["synced", "aligning", "aligned"].includes(card.status);
    const isResuming = card.status === "in_sync";
    const sphereColor = card.sphere_color ?? "#10B981";

    return (
        <div className="min-h-screen pb-28" style={{ background: "var(--bg-deep)" }}>

            {/* ── Back button ──────────────────────────────────────────────── */}
            <div style={{ padding: "16px 20px 8px" }}>
                <button
                    onClick={() => router.back()}
                    style={{
                        fontSize: 15,
                        color: "rgba(255,255,255,0.5)",
                        background: "none",
                        border: "none",
                        cursor: "pointer",
                        padding: 0,
                        display: "flex",
                        alignItems: "center",
                        gap: 4,
                    }}
                >
                    {"< Назад"}
                </button>
            </div>

            {/* ── Sphere + Name + Score ────────────────────────────────────── */}
            <div style={{ padding: "4px 20px 16px", display: "flex", alignItems: "flex-end", justifyContent: "space-between" }}>
                {/* Left: sphere label + archetype name */}
                <div>
                    <p style={{
                        fontSize: 11,
                        fontWeight: 600,
                        letterSpacing: "0.12em",
                        color: "rgba(255,255,255,0.45)",
                        marginBottom: 4,
                        textTransform: "uppercase",
                    }}>
                        Сфера: {card.sphere_name_ru}
                    </p>
                    <h1 style={{
                        fontSize: 30,
                        fontWeight: 800,
                        color: "var(--text-primary)",
                        margin: 0,
                        lineHeight: 1,
                        fontFamily: "'Outfit', sans-serif",
                    }}>
                        {card.archetype_name}
                    </h1>
                </div>

                {/* Right: lvl + hawkins score */}
                <div style={{ textAlign: "right" }}>
                    <p style={{
                        fontSize: 11,
                        fontWeight: 600,
                        color: "rgba(255,255,255,0.45)",
                        marginBottom: 4,
                        letterSpacing: "0.08em",
                        textTransform: "uppercase",
                    }}>
                        LVL {card.rank}
                    </p>
                    <p style={{
                        fontSize: 30,
                        fontWeight: 800,
                        color: card.hawkins_peak > 0 ? getHawkinsColor(card.hawkins_peak) : "rgba(255,255,255,0.2)",
                        margin: 0,
                        lineHeight: 1,
                        fontFamily: "'Outfit', sans-serif",
                    }}>
                        {card.hawkins_peak > 0 ? card.hawkins_peak : "—"}
                    </p>
                </div>
            </div>

            {/* ── Archetype Image ──────────────────────────────────────────── */}
            <div style={{ padding: "0 16px" }}>
                <div style={{
                    width: "100%",
                    aspectRatio: "4/5",
                    borderRadius: 20,
                    overflow: "hidden",
                    position: "relative",
                    background: `linear-gradient(135deg, ${sphereColor}18 0%, rgba(0,0,0,0.7) 100%)`,
                    border: "1px solid rgba(255,255,255,0.08)",
                }}>
                    <img
                        src={`/archetypes/${card.archetype_id}.webp`}
                        alt={card.archetype_name}
                        style={{
                            width: "100%",
                            height: "100%",
                            objectFit: "cover",
                            objectPosition: "center top",
                            display: "block",
                        }}
                    />
                    {/* Bottom gradient overlay for readability */}
                    <div style={{
                        position: "absolute", bottom: 0, left: 0, right: 0, height: "30%",
                        background: "linear-gradient(to top, rgba(6,8,24,0.8) 0%, transparent 100%)",
                        pointerEvents: "none",
                    }} />
                </div>
            </div>

            {/* ── Info block ───────────────────────────────────────────────── */}
            <div style={{ padding: "16px 20px 0" }}>

                {/* Status row */}
                <div style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: 16,
                    paddingBottom: 16,
                    borderBottom: "1px solid rgba(255,255,255,0.07)",
                }}>
                    <p style={{
                        fontSize: 11,
                        fontWeight: 600,
                        letterSpacing: "0.12em",
                        color: "rgba(255,255,255,0.35)",
                        margin: 0,
                        textTransform: "uppercase",
                    }}>
                        Статус: {statusCfg.label}
                    </p>
                    <p style={{
                        fontSize: 12,
                        fontWeight: 700,
                        color: statusCfg.color,
                        margin: 0,
                        letterSpacing: "0.08em",
                        textTransform: "uppercase",
                    }}>
                        {statusCfg.statusLabel}
                    </p>
                </div>

                {/* Shadow */}
                <div style={{ marginBottom: 16 }}>
                    <p style={{
                        fontSize: 12,
                        fontWeight: 700,
                        color: "var(--text-primary)",
                        margin: "0 0 6px",
                        letterSpacing: "0.06em",
                    }}>
                        ТЕНЬ:
                    </p>
                    <p style={{
                        fontSize: 13,
                        color: "rgba(255,255,255,0.55)",
                        lineHeight: 1.55,
                        margin: 0,
                    }}>
                        {card.archetype_shadow || "—"}
                    </p>
                </div>

                {/* Light */}
                <div style={{ marginBottom: 24 }}>
                    <p style={{
                        fontSize: 12,
                        fontWeight: 700,
                        color: "var(--text-primary)",
                        margin: "0 0 6px",
                        letterSpacing: "0.06em",
                    }}>
                        СВЕТ:
                    </p>
                    <p style={{
                        fontSize: 13,
                        color: "rgba(255,255,255,0.55)",
                        lineHeight: 1.55,
                        margin: 0,
                    }}>
                        {card.archetype_light || "—"}
                    </p>
                </div>

                {/* Sphere main question */}
                {card.sphere_main_question && (
                    <div style={{
                        marginBottom: 20,
                        padding: "12px 14px",
                        background: `${sphereColor}0d`,
                        borderRadius: 14,
                        border: `1px solid ${sphereColor}25`,
                    }}>
                        <p style={{ fontSize: 13, color: "rgba(255,255,255,0.5)", margin: 0, lineHeight: 1.5, fontStyle: "italic" }}>
                            {card.sphere_main_question}
                        </p>
                    </div>
                )}

                {/* ── Action buttons ── */}
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>

                    {card.status === "locked" && (
                        <div style={{
                            padding: "14px 16px", borderRadius: 16,
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
                                padding: "18px",
                                borderRadius: 18,
                                border: "none",
                                cursor: "pointer",
                                background: "linear-gradient(135deg, #10B981, #059669)",
                                color: "#000",
                                fontWeight: 800,
                                fontSize: 15,
                                letterSpacing: "0.08em",
                                boxShadow: "0 8px 28px rgba(16,185,129,0.4)",
                                fontFamily: "'Outfit', sans-serif",
                                textTransform: "uppercase",
                            }}
                        >
                            {isResuming ? "▶ Продолжить синхронизацию" : `Синхронизация · 25 ✦`}
                        </motion.button>
                    )}

                    {canAlign && (
                        <motion.button
                            whileTap={{ scale: 0.97 }}
                            onClick={() => router.push(`/session/${card.id}`)}
                            style={{
                                width: "100%",
                                padding: "18px",
                                borderRadius: 18,
                                border: "none",
                                cursor: "pointer",
                                background: "linear-gradient(135deg, #F59E0B, #D97706)",
                                color: "#000",
                                fontWeight: 800,
                                fontSize: 15,
                                letterSpacing: "0.08em",
                                boxShadow: "0 8px 28px rgba(245,158,11,0.35)",
                                fontFamily: "'Outfit', sans-serif",
                                textTransform: "uppercase",
                            }}
                        >
                            Сессия выравнивания · 40 ✦
                        </motion.button>
                    )}
                </div>
            </div>

            <BottomNav active="cards" />
        </div>
    );
}
