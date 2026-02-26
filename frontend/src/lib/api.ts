import axios from "axios";

// API endpoint via environment variable or fallback to production
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://avatar.aiguro.pro";

export const api = axios.create({
    baseURL: API_BASE,
    timeout: 30000,
});

export const voiceAxios = axios.create({
    baseURL: API_BASE,
    timeout: 60000,   // 60s for Whisper transcription
});

voiceAxios.interceptors.request.use((config) => {
    if (typeof window !== "undefined") {
        const token = localStorage.getItem("avatar_token");
        if (token) config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

// Inject user token from localStorage
api.interceptors.request.use((config) => {
    if (typeof window !== "undefined") {
        const token = localStorage.getItem("avatar_token");
        if (token) config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

export const authAPI = {
    login: (initData: string, testMode = false) =>
        api.post("/api/auth", { initData, test_mode: testMode }),
};

export const calcAPI = {
    calculate: (data: { birth_date: string; birth_time: string; birth_place: string; user_id: number }) =>
        api.post("/api/calc", data),
};

export const cardsAPI = {
    getAll: (userId: number) => api.get(`/api/cards/${userId}`),
    getOne: (userId: number, cardId: number) => api.get(`/api/cards/${userId}/card/${cardId}`),
};

export const syncAPI = {
    start: (userId: number, cardProgressId: number) =>
        api.post("/api/sync/start", { user_id: userId, card_progress_id: cardProgressId }),
    phase: (userId: number, syncSessionId: number, phase: number, userResponse?: string) =>
        api.post("/api/sync/phase", { user_id: userId, sync_session_id: syncSessionId, phase, user_response: userResponse }),
};

export const diaryAPI = {
    create: (data: Record<string, unknown>) => api.post("/api/diary", data),
    getAll: (userId: number, sphere?: string) =>
        api.get(`/api/diary/${userId}`, { params: { sphere } }),
    updateIntegration: (userId: number, entryId: number, done: boolean, partial = false) =>
        api.post("/api/diary/integration", { user_id: userId, entry_id: entryId, done, partial }),
};

export const gameAPI = {
    getState: (userId: number) => api.get(`/api/game/${userId}`),
};

export const profileAPI = {
    get: (userId: number) => api.get(`/api/profile/${userId}`),
    reset: (tgId: number) => api.post(`/api/profile/tg/${tgId}/reset`),
};

export const reflectAPI = {
    submit: (userId: number, currentEmotion: string, integrationDone: string, focusSphere: string) =>
        api.post("/api/reflect", { user_id: userId, current_emotion: currentEmotion, integration_done: integrationDone, focus_sphere: focusSphere }),
};

export const retro = {
    week: (userId: number) => api.get(`/api/retro/${userId}/week`),
    month: (userId: number) => api.get(`/api/retro/${userId}/month`),
};

export const voiceAPI = {
    transcribe: (userId: number, audioBlob: Blob, sessionType = "general") => {
        const form = new FormData();
        form.append("user_id", String(userId));
        form.append("session_type", sessionType);
        // Use the correct file extension based on actual mime type
        const ext = audioBlob.type.includes("mp4") ? "m4a" : "webm";
        form.append("audio", audioBlob, `voice.${ext}`);
        return voiceAxios.post("/api/voice", form);
    },
};

// WebSocket helper
export function createSessionWS(userId: number, cardProgressId: number): WebSocket {
    const wsBase = API_BASE.replace("http", "ws");
    return new WebSocket(`${wsBase}/api/session/${userId}/${cardProgressId}`);
}
