"use client";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { diaryAPI } from "@/lib/api";
import { useUserStore } from "@/lib/store";
import { BottomNav } from "@/app/page";

const SPHERE_NAMES: Record<string, string> = {
    IDENTITY: "Личность", MONEY: "Деньги", RELATIONS: "Отношения",
    FAMILY: "Род", MISSION: "Миссия", HEALTH: "Здоровье", SOCIETY: "Влияние", SPIRIT: "Духовность"
};

export default function DiaryPage() {
    const { userId } = useUserStore();
    const [entries, setEntries] = useState<any[]>([]);
    const [activeFilter, setActiveFilter] = useState<string>("all");
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!userId) return;
        diaryAPI.getAll(userId, activeFilter === "all" ? undefined : activeFilter)
            .then(r => { setEntries(r.data); setLoading(false); })
            .catch(() => setLoading(false));
    }, [userId, activeFilter]);

    const handleIntegration = async (entryId: number, done: boolean) => {
        if (!userId) return;
        await diaryAPI.updateIntegration(userId, entryId, done);
        setEntries(prev => prev.map(e => e.id === entryId ? { ...e, integration_done: done } : e));
    };

    const SPHERES = ["all", "IDENTITY", "MONEY", "RELATIONS", "FAMILY", "MISSION", "HEALTH", "SOCIETY", "SPIRIT"];

    return (
        <div className="min-h-screen pb-24">
            <div className="px-4 pt-6 pb-3">
                <h1 className="text-xl font-bold gradient-text">Дневник</h1>
            </div>

            {/* Sphere filter */}
            <div className="flex gap-2 px-4 overflow-x-auto pb-3" style={{ scrollbarWidth: "none" }}>
                {SPHERES.map(s => (
                    <button key={s} onClick={() => setActiveFilter(s)}
                        className="flex-none px-3 py-1.5 rounded-full text-xs transition-all whitespace-nowrap"
                        style={{
                            background: activeFilter === s ? "var(--violet)" : "rgba(255,255,255,0.06)",
                            color: activeFilter === s ? "#fff" : "var(--text-muted)",
                            border: `1px solid ${activeFilter === s ? "var(--violet)" : "var(--border)"}`,
                        }}>
                        {s === "all" ? "Все" : SPHERE_NAMES[s]}
                    </button>
                ))}
            </div>

            <div className="px-4 space-y-3">
                {loading && (
                    <div className="flex justify-center py-8">
                        <div className="w-8 h-8 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
                    </div>
                )}
                {!loading && entries.length === 0 && (
                    <div className="glass p-8 text-center">
                        <p className="text-3xl mb-2">📖</p>
                        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                            Записи появятся после завершения сессии выравнивания
                        </p>
                    </div>
                )}
                {entries.map(entry => (
                    <motion.div key={entry.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                        className="glass p-4">
                        <div className="flex items-start justify-between mb-2">
                            <div>
                                <span className="text-xs px-2 py-0.5 rounded-full mr-2"
                                    style={{ background: "rgba(139,92,246,0.15)", color: "var(--violet-l)" }}>
                                    {SPHERE_NAMES[entry.sphere] || entry.sphere}
                                </span>
                                <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                                    {entry.created_at?.split("T")[0]}
                                </span>
                            </div>
                        </div>

                        {entry.content && (
                            <p className="text-sm mb-3 line-clamp-3" style={{ color: "var(--text-secondary)" }}>
                                {entry.content}
                            </p>
                        )}

                        {entry.integration_plan && (
                            <div className="rounded-lg p-3 mb-3" style={{ background: "rgba(16,185,129,0.08)", border: "1px solid rgba(16,185,129,0.2)" }}>
                                <p className="text-xs mb-1" style={{ color: "#68d391" }}>📋 Интеграция</p>
                                <p className="text-sm" style={{ color: "var(--text-secondary)" }}>{entry.integration_plan}</p>
                            </div>
                        )}

                        {entry.integration_plan && !entry.integration_done && (
                            <div className="flex gap-2">
                                <button onClick={() => handleIntegration(entry.id, true)}
                                    className="flex-1 py-2 rounded-lg text-xs transition-all"
                                    style={{ background: "rgba(16,185,129,0.15)", color: "#68d391", border: "1px solid rgba(16,185,129,0.3)" }}>
                                    ✅ Выполнено · +20✦
                                </button>
                                <button onClick={() => handleIntegration(entry.id, false)}
                                    className="flex-1 py-2 rounded-lg text-xs"
                                    style={{ background: "rgba(255,255,255,0.04)", color: "var(--text-muted)", border: "1px solid var(--border)" }}>
                                    🌗 Частично
                                </button>
                            </div>
                        )}

                        {entry.integration_done && (
                            <p className="text-xs" style={{ color: "#68d391" }}>✅ Интеграция выполнена</p>
                        )}
                    </motion.div>
                ))}
            </div>

            <BottomNav active="diary" />
        </div>
    );
}
