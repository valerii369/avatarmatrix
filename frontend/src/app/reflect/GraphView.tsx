"use client";
import { motion } from "framer-motion";

interface GraphViewProps {
    history: any[];
    loadingHistory: boolean;
    activeFilter: string;
    timeRange: "week" | "month" | "year" | "all";
    sphereNames: Record<string, string>;
}

export const GraphView = ({ history, loadingHistory, activeFilter, timeRange, sphereNames }: GraphViewProps) => {
    const processGraphData = () => {
        if (!history || history.length === 0) return [];

        let filtered = history;
        if (activeFilter !== "all") {
            filtered = history.filter(h => h.sphere === activeFilter);
        }

        const now = new Date();
        const lookback = new Date();
        if (timeRange === 'week') lookback.setDate(now.getDate() - 7);
        else if (timeRange === 'month') lookback.setMonth(now.getMonth() - 1);
        else if (timeRange === 'year') lookback.setFullYear(now.getFullYear() - 1);
        else lookback.setFullYear(2000); // All time

        filtered = filtered.filter(h => new Date(h.created_at) >= lookback);

        const grouped: Record<string, { total: number; count: number }> = {};
        filtered.forEach(h => {
            const date = h.created_at.split('T')[0];
            if (!grouped[date]) grouped[date] = { total: 0, count: 0 };
            grouped[date].total += (h.hawkins_score || 0);
            grouped[date].count += 1;
        });

        return Object.entries(grouped)
            .map(([date, val]) => ({
                date,
                score: Math.round(val.total / val.count)
            }))
            .sort((a, b) => a.date.localeCompare(b.date));
    };

    const data = processGraphData();
    const height = 220;
    const paddingX = 30;
    const paddingY = 40;

    if (loadingHistory) return (
        <div className="flex justify-center py-20">
            <div className="w-8 h-8 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
        </div>
    );

    if (data.length < 2) return (
        <div className="px-4">
            <div className="glass-strong p-12 text-center rounded-[2.5rem]">
                <p className="text-3xl mb-4 opacity-20">📊</p>
                <p className="text-sm text-white/40 leading-relaxed">
                    Недостаточно данных для графика.<br />Нужно хотя бы 2 дня рефлексии.
                </p>
            </div>
        </div>
    );

    const getY = (score: number) => height - paddingY - ((score / 1000) * (height - 2 * paddingY));
    const getX = (index: number) => paddingX + (index * (350 - 2 * paddingX) / (data.length - 1));

    return (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="px-4">
            <div className="glass-strong p-6 rounded-[2.5rem] border border-white/5 relative overflow-hidden">
                <div className="absolute top-0 right-0 w-48 h-48 bg-violet-600/5 blur-[60px] -z-1" />

                <div className="flex justify-between items-end mb-6">
                    <div>
                        <p className="text-[10px] text-white/30 uppercase tracking-[0.2em] font-bold mb-1">Динамика состояний</p>
                        <h3 className="text-lg font-black text-white/90">Шкала Хокинса</h3>
                    </div>
                    <div className="text-right">
                        <span className="text-[10px] text-violet-400 font-bold uppercase tracking-widest bg-violet-500/10 px-2 py-0.5 rounded-full border border-violet-500/20">
                            {activeFilter === "all" ? "Все сферы" : sphereNames[activeFilter]}
                        </span>
                    </div>
                </div>

                <div className="relative h-[220px] w-full mt-4">
                    <svg width="100%" height={height} viewBox={`0 0 350 ${height}`} className="overflow-visible">
                        <defs>
                            <linearGradient id="lineGrad" x1="0" y1="0" x2="1" y2="0">
                                <stop offset="0%" stopColor="#8b5cf6" stopOpacity="1" />
                                <stop offset="100%" stopColor="#ec4899" stopOpacity="1" />
                            </linearGradient>
                            <linearGradient id="fillGrad" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stopColor="#8b5cf6" stopOpacity="0.2" />
                                <stop offset="100%" stopColor="#8b5cf6" stopOpacity="0" />
                            </linearGradient>
                        </defs>

                        {[0, 200, 400, 600, 800, 1000].map(s => (
                            <g key={s}>
                                <line x1={paddingX} y1={getY(s)} x2={350 - paddingX} y2={getY(s)}
                                    stroke="rgba(255,255,255,0.03)" strokeWidth="1" />
                                <text x={paddingX - 10} y={getY(s) + 4} fill="rgba(255,255,255,0.15)" fontSize="8" textAnchor="end">{s}</text>
                            </g>
                        ))}

                        <motion.path
                            d={`M ${paddingX},${height - paddingY} ` + data.map((d, i) => `L ${getX(i)},${getY(d.score)}`).join(' ') + ` L ${getX(data.length - 1)},${height - paddingY} Z`}
                            fill="url(#fillGrad)"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{ duration: 1 }}
                        />

                        <motion.path
                            d={`M ` + data.map((d, i) => `${getX(i)},${getY(d.score)}`).join(' L ')}
                            fill="none"
                            stroke="url(#lineGrad)"
                            strokeWidth="3"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            initial={{ pathLength: 0 }}
                            animate={{ pathLength: 1 }}
                            transition={{ duration: 1.5, ease: "easeInOut" }}
                        />

                        {data.map((d, i) => (
                            <motion.circle
                                key={i}
                                cx={getX(i)}
                                cy={getY(d.score)}
                                r="4"
                                fill="#fff"
                                initial={{ scale: 0 }}
                                animate={{ scale: 1 }}
                                transition={{ delay: 1 + i * 0.1 }}
                            />
                        ))}
                    </svg>
                </div>
            </div>
        </motion.div>
    );
};

export default GraphView;
