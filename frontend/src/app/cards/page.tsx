"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { useUserStore, useCardsStore, type CardProgress } from "@/lib/store";
import { authAPI, cardsAPI } from "@/lib/api";
import { BottomNav } from "@/app/page";

// ─── Constants ────────────────────────────────────────────────────────────────

const SPHERES = [
    { key: "ALL", name: "Все", color: "#ffffff" },
    { key: "IDENTITY", name: "Личность", color: "#F59E0B" },
    { key: "MONEY", name: "Деньги", color: "#10B981" },
    { key: "RELATIONS", name: "Отношения", color: "#EC4899" },
    { key: "FAMILY", name: "Род", color: "#F97316" },
    { key: "MISSION", name: "Миссия", color: "#3B82F6" },
    { key: "HEALTH", name: "Здоровье", color: "#22C55E" },
    { key: "SOCIETY", name: "Влияние", color: "#8B5CF6" },
    { key: "SPIRIT", name: "Духовность", color: "#A78BFA" },
];

const SPHERE_EMOJI: Record<string, string> = {
    IDENTITY: "✦", MONEY: "◈", RELATIONS: "❤", FAMILY: "⚘",
    MISSION: "◉", HEALTH: "⬡", SOCIETY: "◐", SPIRIT: "∞",
};

// Status labels & colors as shown on the screenshot
const STATUS_CONFIG: Record<string, { label: string; color: string }> = {
    locked: { label: "Не открыта", color: "rgba(255,255,255,0.35)" },
    recommended: { label: "Рекомендована", color: "#F59E0B" },
    in_sync: { label: "Синхронизация", color: "#06B6D4" },
    synced: { label: "Активна", color: "#10B981" },
    aligning: { label: "Выравнивание", color: "#A78BFA" },
    aligned: { label: "Активна", color: "#10B981" },
};

const TOTAL_CARDS = 176;

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function CardsPage() {
    const router = useRouter();
    const { userId, firstName, setUser } = useUserStore();
    const { cards, setCards, setLoading } = useCardsStore();

    const [tab, setTab] = useState<"all" | "recommended" | "active">("all");
    const [sphereFilter, setSphereFilter] = useState("ALL");
    const [initialized, setInitialized] = useState(false);

    // Init: authenticate + load cards if not already in store
    useEffect(() => {
        const init = async () => {
            try {
                if (!userId) {
                    const tg = (window as any).Telegram?.WebApp;
                    if (tg) { tg.ready(); tg.expand(); }
                    const initData = tg?.initData || "";
                    const isDev = process.env.NODE_ENV === "development";
                    const authRes = await authAPI.login(initData, isDev);
                    const d = authRes.data;
                    setUser({
                        userId: d.user_id, tgId: d.tg_id, firstName: d.first_name,
                        token: d.token, energy: d.energy, streak: d.streak,
                        evolutionLevel: d.evolution_level, title: d.title,
                        onboardingDone: d.onboarding_done,
                    });
                    if (typeof window !== "undefined")
                        localStorage.setItem("avatar_token", d.token);
                    if (cards.length === 0) {
                        setLoading(true);
                        const r = await cardsAPI.getAll(d.user_id);
                        setCards(r.data);
                        setLoading(false);
                    }
                } else if (cards.length === 0) {
                    setLoading(true);
                    const r = await cardsAPI.getAll(userId);
                    setCards(r.data);
                    setLoading(false);
                }
            } catch (e) {
                console.error(e);
            } finally {
                setInitialized(true);
            }
        };
        init();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // ── Derived stats ────────────────────────────────────────────────────────
    const openedSpheres = new Set(
        cards.filter((c) => c.status !== "locked" && c.hawkins_peak > 0).map((c) => c.sphere)
    ).size;
    const openedCards = cards.filter((c) => c.status !== "locked").length;
    const recommended = cards.filter((c) => c.is_recommended_astro).length;
    const activeCards = cards.filter((c) => c.status === "synced" || c.status === "aligned").length;

    // ── Tabs filter ──────────────────────────────────────────────────────────
    const byTab = (c: CardProgress) => {
        if (tab === "recommended") return c.is_recommended_astro;
        if (tab === "active") return c.status === "synced" || c.status === "aligned";
        return true;
    };

    // ── Sphere filter ────────────────────────────────────────────────────────
    const bySphere = (c: CardProgress) =>
        sphereFilter === "ALL" || c.sphere === sphereFilter;

    const visible = cards.filter((c) => byTab(c) && bySphere(c));

    // ── Spinner while loading ────────────────────────────────────────────────
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
        <div className="min-h-screen pb-28" style={{ background: "var(--bg-deep)" }}>

            {/* ── Header ─────────────────────────────────────────────────────── */}
            <div className="px-4 pt-5 pb-3">
                <div
                    className="flex items-center gap-3 p-3"
                    style={{
                        background: "rgba(255,255,255,0.05)",
                        border: "1px solid var(--border)",
                        borderRadius: 18,
                    }}
                >
                    {/* Avatar circle */}
                    <div
                        style={{
                            width: 44, height: 44, borderRadius: "50%",
                            background: "rgba(255,255,255,0.1)",
                            border: "1px solid var(--border)",
                            display: "flex", alignItems: "center", justifyContent: "center",
                            fontSize: 20, color: "var(--text-muted)",
                            flexShrink: 0,
                        }}
                    >
                        👤
                    </div>
                    <span className="font-semibold text-base" style={{ color: "var(--text-primary)" }}>
                        {firstName || "Пользователь"}
                    </span>
                </div>
            </div>

            {/* ── Stats row ──────────────────────────────────────────────────── */}
            <div className="px-4 mb-4">
                <div className="grid grid-cols-3 gap-2">
                    <StatTile label="Сферы" value={`${openedSpheres}/8`} color="#F59E0B" />
                    <StatTile label="Карточки" value={`${activeCards}/${TOTAL_CARDS}`} color="#10B981" />
                    <StatTile label="Рекомендовано" value={String(recommended)} color="#60A5FA" />
                </div>
            </div>

            {/* ── Category tabs ──────────────────────────────────────────────── */}
            <div className="px-4 mb-3">
                <div
                    className="grid grid-cols-3 gap-1 p-1"
                    style={{
                        background: "rgba(255,255,255,0.04)",
                        border: "1px solid var(--border)",
                        borderRadius: 14,
                    }}
                >
                    {[
                        { key: "all", label: "Все карточки" },
                        { key: "recommended", label: "Рекоменд карточки" },
                        { key: "active", label: "Активные карточки" },
                    ].map((t) => (
                        <button
                            key={t.key}
                            onClick={() => setTab(t.key as typeof tab)}
                            style={{
                                padding: "8px 4px",
                                borderRadius: 10,
                                fontSize: 11,
                                fontWeight: 500,
                                transition: "all 0.2s",
                                background: tab === t.key ? "rgba(255,255,255,0.1)" : "transparent",
                                color: tab === t.key ? "var(--text-primary)" : "var(--text-muted)",
                                border: "none",
                                cursor: "pointer",
                            }}
                        >
                            {t.label}
                        </button>
                    ))}
                </div>
            </div>

            {/* ── Sphere filter (horizontal scroll) ──────────────────────────── */}
            <div
                className="px-4 mb-4 flex gap-2 overflow-x-auto pb-1"
                style={{ scrollbarWidth: "none" }}
            >
                {SPHERES.map((s) => {
                    const active = sphereFilter === s.key;
                    return (
                        <button
                            key={s.key}
                            onClick={() => setSphereFilter(s.key)}
                            style={{
                                flexShrink: 0,
                                padding: "6px 14px",
                                borderRadius: 20,
                                fontSize: 12,
                                fontWeight: 500,
                                border: `1px solid ${active ? s.color : "var(--border)"}`,
                                background: active ? `${s.color}22` : "transparent",
                                color: active ? s.color : "var(--text-muted)",
                                cursor: "pointer",
                                transition: "all 0.2s",
                                whiteSpace: "nowrap",
                            }}
                        >
                            {s.name}
                        </button>
                    );
                })}
            </div>

            {/* ── 2-column card grid ─────────────────────────────────────────── */}
            <div className="px-4 grid grid-cols-2 gap-3">
                {visible.length === 0 ? (
                    <div
                        className="col-span-2 text-center py-12"
                        style={{ color: "var(--text-muted)", fontSize: 14 }}
                    >
                        Нет карточек по выбранному фильтру
                    </div>
                ) : (
                    visible.map((card, i) => (
                        <motion.div
                            key={card.id}
                            initial={{ opacity: 0, y: 8 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: i * 0.025 }}
                        >
                            <MiniCard card={card} onClick={() => router.push(`/card/${card.id}`)} />
                        </motion.div>
                    ))
                )}
            </div>

            <BottomNav active="cards" />
        </div>
    );
}

// ─── StatTile ─────────────────────────────────────────────────────────────────

function StatTile({ label, value, color }: { label: string; value: string; color: string }) {
    return (
        <div
            style={{
                background: "rgba(255,255,255,0.04)",
                border: "1px solid var(--border)",
                borderRadius: 16,
                padding: "12px 10px",
                textAlign: "center",
            }}
        >
            <p style={{ fontSize: 11, color: color, fontWeight: 600, marginBottom: 4, lineHeight: 1 }}>
                {label}
            </p>
            <p style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)", lineHeight: 1 }}>
                {value}
            </p>
        </div>
    );
}

// ─── MiniCard ─────────────────────────────────────────────────────────────────
// Horizontal layout: square image left, text right, lvl|action bottom

function MiniCard({ card, onClick }: { card: CardProgress; onClick: () => void }) {
    const cfg = STATUS_CONFIG[card.status] ?? STATUS_CONFIG.locked;
    const isActive = card.status === "synced" || card.status === "aligned";
    const sphereColor = SPHERES.find((s) => s.key === card.sphere)?.color ?? "#ffffff";
    const actionText = isActive ? `Energy ${card.hawkins_peak}` : "Открыть";
    const actionColor = isActive ? "#10B981" : "#F59E0B";

    return (
        <button
            onClick={onClick}
            style={{
                width: "100%",
                background: "rgba(255,255,255,0.04)",
                border: "1px solid var(--border)",
                borderRadius: 16,
                overflow: "hidden",
                textAlign: "left",
                cursor: "pointer",
                display: "flex",
                flexDirection: "column",
                padding: 0,
                transition: "border-color 0.2s, box-shadow 0.2s",
            }}
            onMouseEnter={(e) => {
                (e.currentTarget as HTMLElement).style.borderColor = `${sphereColor}55`;
                (e.currentTarget as HTMLElement).style.boxShadow = `0 0 14px ${sphereColor}20`;
            }}
            onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.borderColor = "var(--border)";
                (e.currentTarget as HTMLElement).style.boxShadow = "none";
            }}
        >
            {/* ── Top row: image + text ── */}
            <div style={{ display: "flex", alignItems: "stretch", gap: 0 }}>

                {/* Square image */}
                <div
                    style={{
                        width: 68,
                        minHeight: 68,
                        flexShrink: 0,
                        background: `linear-gradient(135deg, ${sphereColor}18 0%, rgba(0,0,0,0.3) 100%)`,
                        position: "relative",
                        borderRight: "1px solid var(--border)",
                        overflow: "hidden",
                    }}
                >
                    <img
                        src={`/archetypes/${card.archetype_id}.webp`}
                        alt={card.archetype_name}
                        style={{
                            width: "100%",
                            height: "100%",
                            objectFit: "cover",
                            opacity: isActive ? 1 : 0.6,
                            filter: isActive ? "none" : "grayscale(80%)",
                        }}
                    />
                    {isActive && (
                        <div style={{
                            position: "absolute", inset: 0,
                            background: `radial-gradient(circle at 50% 50%, ${sphereColor}40 0%, transparent 70%)`,
                            pointerEvents: "none",
                            mixBlendMode: "overlay"
                        }} />
                    )}
                </div>

                {/* Text block */}
                <div style={{ flex: 1, padding: "10px 10px 8px", minWidth: 0 }}>
                    <p style={{
                        fontSize: 10,
                        color: "var(--text-muted)",
                        marginBottom: 3,
                        lineHeight: 1,
                    }}>
                        Сфера: {card.sphere_name_ru}
                    </p>
                    <p style={{
                        fontSize: 13,
                        fontWeight: 700,
                        color: "var(--text-primary)",
                        lineHeight: 1.25,
                        marginBottom: 5,
                        overflow: "hidden",
                        display: "-webkit-box",
                        WebkitLineClamp: 2,
                        WebkitBoxOrient: "vertical",
                    }}>
                        {card.archetype_name}
                    </p>
                    <p style={{
                        fontSize: 10,
                        fontWeight: 600,
                        color: cfg.color,
                        lineHeight: 1,
                    }}>
                        {cfg.label}
                    </p>
                </div>
            </div>

            {/* ── Bottom row: lvl | action ── */}
            <div style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "7px 10px",
                borderTop: "1px solid var(--border)",
            }}>
                <span style={{ fontSize: 11, color: "var(--text-muted)", fontWeight: 600 }}>
                    lvl {card.rank}
                </span>
                <span style={{ fontSize: 11, fontWeight: 700, color: actionColor }}>
                    {actionText}
                </span>
            </div>
        </button>
    );
}
