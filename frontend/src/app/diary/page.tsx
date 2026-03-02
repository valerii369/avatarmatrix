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
        diaryAPI.getAll(userId, activeFilter === "all" ? undefined : activeFilter, undefined, "reflection")
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
                        className="glass-strong p-5 rounded-[1.5rem] border border-white/5 relative overflow-hidden">

                        {/* Background glow for reflections */}
                        {entry.entry_type === "reflection" && (
                            <div className="absolute top-0 right-0 w-32 h-32 bg-violet-600/10 blur-[50px] -z-1" />
                        )}

                        <div className="flex items-start justify-between mb-3">
                            <div className="flex flex-wrap gap-2">
                                <span className="text-[10px] px-2 py-0.5 rounded-full uppercase tracking-widest font-bold"
                                    style={{
                                        background: entry.entry_type === "reflection" ? "var(--gold)" : "rgba(139,92,246,0.15)",
                                        color: entry.entry_type === "reflection" ? "#20124d" : "var(--violet-l)"
                                    }}>
                                    {entry.entry_type === "reflection" ? "Рефлексия" : (SPHERE_NAMES[entry.sphere] || entry.sphere || "Общее")}
                                </span>
                                {entry.entry_type === "reflection" && (
                                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-violet-500/10 text-violet-300 border border-violet-500/20 uppercase tracking-widest font-bold">
                                        {entry.archetype_name || "Общее"}
                                    </span>
                                )}
                                {entry.entry_type === "session_result" && (
                                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-white/5 text-white/40 uppercase tracking-widest border border-white/5">
                                        Сессия
                                    </span>
                                )}
                            </div>
                            <span className="text-[10px] text-white/30 font-medium">
                                {new Date(entry.created_at).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })}
                            </span>
                        </div>

                        {entry.hawkins_score && (
                            <div className="flex items-center gap-2 mb-3">
                                <div className="text-xl font-black text-violet-400">{entry.hawkins_score}</div>
                                <div className="h-1 w-1 rounded-full bg-white/20" />
                                <div className="text-[10px] uppercase tracking-tighter text-white/40 font-bold">
                                    Хокинс
                                </div>
                            </div>
                        )}

                        {entry.content && (
                            <p className="text-sm mb-4 leading-relaxed text-white/80 italic">
                                «{entry.content}»
                            </p>
                        )}

                        {entry.ai_analysis && (
                            <div className="bg-violet-500/5 rounded-xl p-4 mb-4 border border-violet-500/10">
                                <p className="text-[10px] uppercase tracking-widest text-violet-300/50 mb-2 font-bold">Инсайт от ИИ</p>
                                <p className="text-sm font-medium text-white/70 leading-relaxed">
                                    {entry.ai_analysis}
                                </p>
                            </div>
                        )}

                        {entry.integration_plan && (
                            <div className="rounded-xl p-4 mb-4" style={{ background: "rgba(16,185,129,0.06)", border: "1px solid rgba(16,185,129,0.1)" }}>
                                <p className="text-[10px] uppercase tracking-widest text-emerald-400/50 mb-2 font-bold">📋 План интеграции</p>
                                <p className="text-sm text-emerald-100/80">{entry.integration_plan}</p>
                            </div>
                        )}

                        {entry.integration_plan && !entry.integration_done && (
                            <div className="flex gap-2 pt-2">
                                <button onClick={() => handleIntegration(entry.id, true)}
                                    className="flex-1 py-3 rounded-xl text-xs font-bold transition-all hover:scale-[1.02] active:scale-95"
                                    style={{ background: "rgba(16,185,129,0.15)", color: "#68d391", border: "1px solid rgba(16,185,129,0.3)" }}>
                                    ✅ Выполнено · +20✦
                                </button>
                            </div>
                        )}

                        {entry.integration_done && (
                            <div className="flex items-center gap-2 text-xs text-emerald-400 font-bold pt-1">
                                <span>✅</span>
                                <span className="uppercase tracking-widest text-[10px]">Интеграция завершена</span>
                            </div>
                        )}
                    </motion.div>
                ))}
            </div>

            <BottomNav active="diary" />
        </div>
    );
}
