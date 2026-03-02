# XP and Leveling System Guide (AVATAR)

This document serves as a reference for agents and developers working with the XP and leveling mechanics of the AVATAR platform.

## 1. Core Principles
The system is designed to reward user consistency, depth of practice, and milestones. All calculations are handled on the backend to ensure integrity.

## 2. XP Distribution (Economy Constants)
XP values are defined in `backend/app/core/economy.py` under the `XP_VALUES` dictionary.

| Action | XP Awarded | Description |
| :--- | :--- | :--- |
| `card_opened` | 100 | First completion of card sync |
| `diary_entry` | 25 | Creating a new diary entry |
| `integration_success` | 50 | Completing a practice integration |
| `daily_login` | 15 | Daily app access reward |
| `streak_7` | 200 | Completion of 7-day streak |
| `streak_30` | 1000 | Completion of 30-day streak |
| `card_rank_bonus_10`| 1000 | Reaching Rank 10 on a card |
| `card_rank_bonus_20`| 2000 | Reaching Rank 20 (Mastery) on a card |

## 3. Leveling Formula
The system uses a piecewise exponential formula to balance early progress and long-term retention. 
Path: `calculate_xp_for_level(level: int)` in `economy.py`.

- **Levels 1-25**: `5 * (level ^ 2.3)`
- **Levels 26-100**: `5 * (level ^ 2.6)`

## 4. Title System (Evolution Levels)
Titles change every 5 levels. There are 20 unique titles stored in `TITLES_BY_LEVEL` in `economy.py`.
- **Level 1**: Пробуждённый (Default)
- **Level 6**: Искатель
- ...
- **Level 96**: Квантовый Архитектор

> [!IMPORTANT]
> When a user levels up, the `award_xp` function automatically updates the `user.title`. The `get_profile` API also forces a title sync for consistency.

## 5. Main Screen Display Logic
- **Progress Bar**: Shows progress **within the current level**.
- **Percentage Calculation**: `(CurrentXP - XP_for_current_level) / (XP_for_next_level - XP_for_current_level)`
- **Header**: Shows `⚡️{Energy}` and the numeric XP breakdown `(Current/Goal XP)` next to the Title.

## 6. Key Files
- `backend/app/core/economy.py`: Core logic, formulas, and award functions.
- `backend/app/routers/profile.py`: Proactive title/XP data synchronization.
- `frontend/src/app/page.tsx`: Home screen display logic.
- `frontend/src/lib/store.ts`: State management for User statistics.
