"""数独 (Sudoku) GUI ゲーム - tkinter 版

特長:
- 難易度選択 (初級 / 中級 / 上級 / エキスパート)
- 一意解をもつ問題をリアルタイム自動生成
- キーボード (数字, 矢印, BackSpace, N, Ctrl+Z 等) & マウス完全対応
- メモ (ペンシルマーク) モード搭載
- 同一行・列・ブロック & 同一数字のスマートハイライト
- 重複・ミスのリアルタイム検出
- 残り数字カウント表示
- アンドゥ (元に戻す) 機能
- ヒント機能 & 自動候補入力
- タイマー & 一時停止
- クリア時の紙吹雪演出
"""

import math
import random
import time
import tkinter as tk
from tkinter import messagebox, ttk
from typing import List, Optional, Set, Tuple

# ---- 定数・カラーパレット ----
FONT_FAMILY = "Segoe UI" if "Segoe UI" in tk.Tk().call("font", "families") else "Meiryo"

# カラー
COLOR_BG = "#f8fafc"            # 全体背景 (淡いスレートグレー)
COLOR_CARD = "#ffffff"          # パネル背景 (ホワイト)
COLOR_BORDER = "#cbd5e1"        # グリッドの細線
COLOR_BLOCK_BORDER = "#1e293b"  # 3x3ブロックの太線
COLOR_CELL_BG = "#ffffff"       # セルの基本背景

COLOR_CELL_SELECTED = "#bfdbfe" # 選択中セル (薄いブルー)
COLOR_CELL_RELATED = "#eff6ff"  # 関連セル (行・列・ブロック、極薄ブルー)
COLOR_CELL_SAME_NUM = "#dcfce7" # 同じ数字のセル (淡いグリーン)
COLOR_CELL_CONFLICT = "#fee2e2" # 重複・エラーセル (淡いレッド)

COLOR_TEXT_GIVEN = "#0f172a"    # 初期数字 (濃いネイビー、太字)
COLOR_TEXT_USER = "#2563eb"     # ユーザー入力数字 (ブルー)
COLOR_TEXT_CONFLICT = "#dc2626" # 重複数字 (レッド)
COLOR_TEXT_NOTE = "#64748b"     # メモ文字 (スレートグレー)

COLOR_BTN_PRIMARY = "#3b82f6"
COLOR_BTN_NOTE_ACTIVE = "#8b5cf6" # メモON時のハイライト色


# ==============================================================================
# 1. 数独ロジック & 問題生成クラス
# ==============================================================================
class SudokuGenerator:
    """数独の生成、検証、求解を行うクラス"""

    @staticmethod
    def get_candidates(grid: List[List[int]], r: int, c: int) -> List[int]:
        used = set(grid[r]) | {grid[i][c] for i in range(9)}
        br, bc = (r // 3) * 3, (c // 3) * 3
        for i in range(3):
            for j in range(3):
                used.add(grid[br + i][bc + j])
        return [n for n in range(1, 10) if n not in used]

    @classmethod
    def count_solutions(cls, grid: List[List[int]], limit: int = 2) -> int:
        """MRVヒューリスティックを用いた解の個数カウント (limitに達したら早期終了)"""
        min_cands = None
        min_pos = None
        min_count = 10

        for r in range(9):
            for c in range(9):
                if grid[r][c] == 0:
                    cands = cls.get_candidates(grid, r, c)
                    if not cands:
                        return 0
                    if len(cands) < min_count:
                        min_count = len(cands)
                        min_pos = (r, c)
                        min_cands = cands
                        if min_count == 1:
                            break
            if min_count == 1:
                break

        if min_pos is None:
            return 1

        r, c = min_pos
        count = 0
        for val in min_cands:
            grid[r][c] = val
            count += cls.count_solutions(grid, limit - count)
            grid[r][c] = 0
            if count >= limit:
                break
        return count

    @classmethod
    def generate_puzzle(cls, clues_target: int) -> Tuple[List[List[int]], List[List[int]]]:
        """唯一解を持つ数独問題を生成する"""
        grid = [[0] * 9 for _ in range(9)]

        # 対角線上の3つの3x3ブロックをランダムに埋める
        for k in range(0, 9, 3):
            nums = list(range(1, 10))
            random.shuffle(nums)
            idx = 0
            for i in range(3):
                for j in range(3):
                    grid[k + i][k + j] = nums[idx]
                    idx += 1

        # 完全盤面を生成
        def fill(g: List[List[int]]) -> bool:
            for r in range(9):
                for c in range(9):
                    if g[r][c] == 0:
                        cands = cls.get_candidates(g, r, c)
                        random.shuffle(cands)
                        for v in cands:
                            g[r][c] = v
                            if fill(g):
                                return True
                            g[r][c] = 0
                        return False
            return True

        fill(grid)
        solution = [row[:] for row in grid]

        # ランダム順にマスを抜き、一意解を維持する
        cells = [(r, c) for r in range(9) for c in range(9)]
        random.shuffle(cells)

        removed = 0
        target_removed = 81 - clues_target

        for r, c in cells:
            if removed >= target_removed:
                break
            val = grid[r][c]
            grid[r][c] = 0
            if cls.count_solutions(grid, limit=2) == 1:
                removed += 1
            else:
                grid[r][c] = val

        return grid, solution


# ==============================================================================
# 2. 紙吹雪演出 (Confetti) クラス
# ==============================================================================
class ConfettiEffect:
    """クリア時に画面上に舞う紙吹雪パーティクル"""

    COLORS = ["#f43f5e", "#ec4899", "#8b5cf6", "#3b82f6", "#06b6d4", "#10b981", "#f59e0b", "#fbbf24"]

    def __init__(self, canvas: tk.Canvas, width: int, height: int):
        self.canvas = canvas
        self.width = width
        self.height = height
        self.particles: List[dict] = []
        self.is_running = False

    def start(self, count: int = 70, duration_seconds: float = 4.0):
        self.stop()
        self.is_running = True
        self.start_time = time.time()
        self.duration = duration_seconds

        for _ in range(count):
            x = random.uniform(20, self.width - 20)
            y = random.uniform(-100, -10)
            w = random.uniform(6, 12)
            h = random.uniform(6, 12)
            color = random.choice(self.COLORS)
            tag = f"confetti_{random.randint(10000, 99999)}"
            item = self.canvas.create_rectangle(x, y, x + w, y + h, fill=color, outline="", tags=("confetti", tag))
            self.particles.append({
                "item": item,
                "x": x,
                "y": y,
                "vx": random.uniform(-1.5, 1.5),
                "vy": random.uniform(2.5, 6.0),
                "w": w,
                "h": h,
                "angle": random.uniform(0, 360),
                "v_angle": random.uniform(-5, 5),
            })
        self._animate()

    def _animate(self):
        if not self.is_running:
            return

        elapsed = time.time() - self.start_time
        if elapsed > self.duration:
            self.stop()
            return

        for p in self.particles:
            p["x"] += p["vx"] + math.sin(p["angle"] * 0.05) * 0.8
            p["y"] += p["vy"]
            p["angle"] += p["v_angle"]

            # 下に落ちたら上から再登場
            if p["y"] > self.height + 10:
                p["y"] = random.uniform(-40, -10)
                p["x"] = random.uniform(20, self.width - 20)

            x, y, w, h = p["x"], p["y"], p["w"], p["h"]
            self.canvas.coords(p["item"], x, y, x + w, y + h)

        self.canvas.tag_raise("confetti")
        self.canvas.after(30, self._animate)

    def stop(self):
        self.is_running = False
        self.canvas.delete("confetti")
        self.particles.clear()


# ==============================================================================
# 3. メインGUI アプリケーション
# ==============================================================================
class SudokuApp:
    CELL_SIZE = 56
    GRID_SIZE = CELL_SIZE * 9

    DIFFICULTIES = {
        "初級 (Easy)": 42,
        "中級 (Medium)": 34,
        "上級 (Hard)": 28,
        "エキスパート (Expert)": 23,
    }

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("数独 - SUDOKU")
        self.root.configure(bg=COLOR_BG)
        self.root.resizable(False, False)

        # 状態データ
        self.initial_grid = [[0] * 9 for _ in range(9)]
        self.grid = [[0] * 9 for _ in range(9)]
        self.solution = [[0] * 9 for _ in range(9)]
        self.notes: List[List[Set[int]]] = [[set() for _ in range(9)] for _ in range(9)]

        self.selected_cell: Optional[Tuple[int, int]] = (0, 0)
        self.note_mode = False
        self.auto_clear_notes = True
        self.highlight_duplicates = True
        self.history: List[dict] = []  # Undo履歴

        # タイマー関連
        self.timer_seconds = 0
        self.timer_running = False
        self.is_paused = False
        self.mistakes = 0
        self.hints_used = 0
        self.game_cleared = False

        self._init_ui()
        self._bind_events()
        self.start_new_game("初級 (Easy)")

    def _init_ui(self):
        main_container = tk.Frame(self.root, bg=COLOR_BG, padx=20, pady=16)
        main_container.pack(fill="both", expand=True)

        # ---- 1. ヘッダー (タイトル、難易度、タイマー) ----
        header = tk.Frame(main_container, bg=COLOR_BG)
        header.pack(fill="x", pady=(0, 10))

        # 左: タイトル
        title_frame = tk.Frame(header, bg=COLOR_BG)
        title_frame.pack(side="left")
        lbl_title = tk.Label(
            title_frame, text="SUDOKU", font=(FONT_FAMILY, 20, "bold"), fg="#1e293b", bg=COLOR_BG
        )
        lbl_title.pack(side="left")

        # 中央: 難易度選択 & 新規ゲーム
        control_frame = tk.Frame(header, bg=COLOR_BG)
        control_frame.pack(side="left", padx=(30, 0))

        self.diff_var = tk.StringVar(value="初級 (Easy)")
        diff_combo = ttk.Combobox(
            control_frame,
            textvariable=self.diff_var,
            values=list(self.DIFFICULTIES.keys()),
            state="readonly",
            width=15,
            font=(FONT_FAMILY, 10),
        )
        diff_combo.pack(side="left", padx=4)

        btn_new = tk.Button(
            control_frame,
            text="新規ゲーム",
            font=(FONT_FAMILY, 9, "bold"),
            bg="#2563eb",
            fg="white",
            activebackground="#1d4ed8",
            activeforeground="white",
            relief="flat",
            padx=10,
            pady=3,
            cursor="hand2",
            command=lambda: self.start_new_game(self.diff_var.get()),
        )
        btn_new.pack(side="left", padx=4)

        # 右: タイマー & 一時停止 & ミス
        stat_frame = tk.Frame(header, bg=COLOR_BG)
        stat_frame.pack(side="right")

        self.lbl_mistakes = tk.Label(
            stat_frame, text="ミス: 0", font=(FONT_FAMILY, 11), fg="#dc2626", bg=COLOR_BG
        )
        self.lbl_mistakes.pack(side="left", padx=(0, 15))

        self.lbl_timer = tk.Label(
            stat_frame, text="⏱ 00:00", font=(FONT_FAMILY, 12, "bold"), fg="#334155", bg=COLOR_BG
        )
        self.lbl_timer.pack(side="left", padx=(0, 8))

        self.btn_pause = tk.Button(
            stat_frame,
            text="⏸",
            font=(FONT_FAMILY, 9),
            bg="#e2e8f0",
            relief="flat",
            padx=6,
            pady=2,
            cursor="hand2",
            command=self.toggle_pause,
        )
        self.btn_pause.pack(side="left")

        # ---- 2. メイン盤面 (Canvas) ----
        board_container = tk.Frame(main_container, bg=COLOR_BLOCK_BORDER, bd=2)
        board_container.pack(pady=6)

        self.canvas = tk.Canvas(
            board_container,
            width=self.GRID_SIZE,
            height=self.GRID_SIZE,
            bg=COLOR_CELL_BG,
            highlightthickness=0,
            cursor="hand2",
        )
        self.canvas.pack()

        self.confetti = ConfettiEffect(self.canvas, self.GRID_SIZE, self.GRID_SIZE)

        # ---- 3. 操作パネル (数字ボタン 1〜9) ----
        num_frame = tk.Frame(main_container, bg=COLOR_BG)
        num_frame.pack(fill="x", pady=(12, 6))

        self.num_buttons: List[tk.Button] = []
        self.count_labels: List[tk.Label] = []

        num_inner = tk.Frame(num_frame, bg=COLOR_BG)
        num_inner.pack(anchor="center")

        for num in range(1, 10):
            item_box = tk.Frame(num_inner, bg=COLOR_BG)
            item_box.pack(side="left", padx=4)

            btn = tk.Button(
                item_box,
                text=str(num),
                font=(FONT_FAMILY, 16, "bold"),
                width=3,
                height=1,
                bg="#ffffff",
                fg="#1e293b",
                activebackground="#dbeafe",
                relief="ridge",
                bd=1,
                cursor="hand2",
                command=lambda n=num: self.on_number_input(n),
            )
            btn.pack()
            self.num_buttons.append(btn)

            cnt_lbl = tk.Label(item_box, text="9", font=(FONT_FAMILY, 8), fg="#64748b", bg=COLOR_BG)
            cnt_lbl.pack(pady=(2, 0))
            self.count_labels.append(cnt_lbl)

        # ---- 4. アクションボタン群 ----
        action_frame = tk.Frame(main_container, bg=COLOR_BG)
        action_frame.pack(fill="x", pady=(8, 0))

        action_inner = tk.Frame(action_frame, bg=COLOR_BG)
        action_inner.pack(anchor="center")

        btn_style = {
            "font": (FONT_FAMILY, 10),
            "bg": "#ffffff",
            "activebackground": "#f1f5f9",
            "relief": "ridge",
            "bd": 1,
            "cursor": "hand2",
            "padx": 10,
            "pady": 5,
        }

        # ↩ 元に戻す
        self.btn_undo = tk.Button(
            action_inner, text="↩ 元に戻す", command=self.undo, **btn_style
        )
        self.btn_undo.pack(side="left", padx=3)

        # ⌫ 消去
        self.btn_erase = tk.Button(
            action_inner, text="⌫ 消去", command=self.erase_current_cell, **btn_style
        )
        self.btn_erase.pack(side="left", padx=3)

        # ✏ メモモード切替
        self.btn_note = tk.Button(
            action_inner,
            text="✏ メモ: OFF",
            command=self.toggle_note_mode,
            **btn_style,
        )
        self.btn_note.pack(side="left", padx=3)

        # 💡 ヒント
        self.btn_hint = tk.Button(
            action_inner, text="💡 ヒント", command=self.give_hint, **btn_style
        )
        self.btn_hint.pack(side="left", padx=3)

        # 🔄 やり直す
        self.btn_restart = tk.Button(
            action_inner, text="🔄 リセット", command=self.restart_current_game, **btn_style
        )
        self.btn_restart.pack(side="left", padx=3)

        # 📝 候補全表示
        self.btn_auto_notes = tk.Button(
            action_inner, text="📝 全候補メモ", command=self.fill_all_candidates, **btn_style
        )
        self.btn_auto_notes.pack(side="left", padx=3)

        # 👁 答えを見る
        self.btn_solve = tk.Button(
            action_inner, text="👁 解答", command=self.confirm_solve, **btn_style
        )
        self.btn_solve.pack(side="left", padx=3)

        # 下部ステータス/ヒント案内
        guide_lbl = tk.Label(
            main_container,
            text="[操作] クリック/矢印キーで選択 | 1-9で入力 | BackSpaceで消去 | Nでメモ切替 | Ctrl+Zで元に戻す",
            font=(FONT_FAMILY, 8),
            fg="#94a3b8",
            bg=COLOR_BG,
        )
        guide_lbl.pack(pady=(10, 0))

    def _bind_events(self):
        """マウスおよびキーボードイベントのバインド"""
        self.canvas.bind("<Button-1>", self.on_canvas_click)

        # キーボード入力
        self.root.bind("<Key>", self.on_key_press)
        self.root.bind("<Control-z>", lambda e: self.undo())
        self.root.bind("<Control-Z>", lambda e: self.undo())

    # ==========================================================================
    # ゲームループ & タイマー
    # ==========================================================================
    def _timer_tick(self):
        if self.timer_running and not self.is_paused and not self.game_cleared:
            self.timer_seconds += 1
            m = self.timer_seconds // 60
            s = self.timer_seconds % 60
            self.lbl_timer.config(text=f"⏱ {m:02d}:{s:02d}")
            self.root.after(1000, self._timer_tick)

    def toggle_pause(self):
        if self.game_cleared:
            return
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.btn_pause.config(text="▶ 再開", bg="#fed7aa")
            self.draw_board()
        else:
            self.btn_pause.config(text="⏸", bg="#e2e8f0")
            self.draw_board()
            self._timer_tick()

    # ==========================================================================
    # 新規ゲーム生成
    # ==========================================================================
    def start_new_game(self, diff_name: str):
        self.confetti.stop()
        self.game_cleared = False
        self.is_paused = False
        self.btn_pause.config(text="⏸", bg="#e2e8f0")

        # 生成中のローディング表示
        self.canvas.delete("all")
        self.canvas.create_text(
            self.GRID_SIZE / 2,
            self.GRID_SIZE / 2,
            text="パズル生成中...",
            font=(FONT_FAMILY, 16, "bold"),
            fill="#64748b",
        )
        self.root.update()

        clues = self.DIFFICULTIES.get(diff_name, 34)
        puzzle, solution = SudokuGenerator.generate_puzzle(clues)

        self.initial_grid = [row[:] for row in puzzle]
        self.grid = [row[:] for row in puzzle]
        self.solution = solution
        self.notes = [[set() for _ in range(9)] for _ in range(9)]
        self.history.clear()
        self.mistakes = 0
        self.hints_used = 0
        self.lbl_mistakes.config(text="ミス: 0")

        self.selected_cell = (4, 4)  # 盤面中央を選択
        self.timer_seconds = 0
        self.lbl_timer.config(text="⏱ 00:00")

        if not self.timer_running:
            self.timer_running = True
            self._timer_tick()

        self.update_remaining_counts()
        self.draw_board()

    # ==========================================================================
    # 描画ロジック
    # ==========================================================================
    def draw_board(self):
        self.canvas.delete("all")

        # 一時停止中は盤面を隠す
        if self.is_paused:
            self.canvas.create_rectangle(
                0, 0, self.GRID_SIZE, self.GRID_SIZE, fill="#f1f5f9", outline=""
            )
            self.canvas.create_text(
                self.GRID_SIZE / 2,
                self.GRID_SIZE / 2,
                text="一時停止中\n「▶ 再開」ボタンを押してください",
                font=(FONT_FAMILY, 15, "bold"),
                fill="#475569",
                justify="center",
            )
            return

        conflicts = self.find_conflicts() if self.highlight_duplicates else set()
        sel_r, sel_c = self.selected_cell if self.selected_cell else (-1, -1)
        sel_val = self.grid[sel_r][sel_c] if (sel_r >= 0 and sel_c >= 0) else 0

        # 1. 各マスの背景色を描画
        for r in range(9):
            for c in range(9):
                x1 = c * self.CELL_SIZE
                y1 = r * self.CELL_SIZE
                x2 = x1 + self.CELL_SIZE
                y2 = y1 + self.CELL_SIZE

                val = self.grid[r][c]
                bg_color = COLOR_CELL_BG

                is_selected = (r == sel_r and c == sel_c)
                is_related = (
                    sel_r >= 0
                    and (
                        r == sel_r
                        or c == sel_c
                        or (r // 3 == sel_r // 3 and c // 3 == sel_c // 3)
                    )
                )
                is_same_num = (sel_val > 0 and val == sel_val)
                is_conflict = (r, c) in conflicts

                if is_selected:
                    bg_color = COLOR_CELL_SELECTED
                elif is_conflict:
                    bg_color = COLOR_CELL_CONFLICT
                elif is_same_num:
                    bg_color = COLOR_CELL_SAME_NUM
                elif is_related:
                    bg_color = COLOR_CELL_RELATED

                self.canvas.create_rectangle(
                    x1, y1, x2, y2, fill=bg_color, outline=COLOR_BORDER, width=1
                )

        # 2. 3x3ブロックの境界線（太線）を描画
        for i in range(10):
            line_w = 3 if i % 3 == 0 else 1
            line_col = COLOR_BLOCK_BORDER if i % 3 == 0 else COLOR_BORDER
            # 垂直線
            x = i * self.CELL_SIZE
            self.canvas.create_line(x, 0, x, self.GRID_SIZE, width=line_w, fill=line_col)
            # 水平線
            y = i * self.CELL_SIZE
            self.canvas.create_line(0, y, self.GRID_SIZE, y, width=line_w, fill=line_col)

        # 3. マス内の数字およびメモを描画
        for r in range(9):
            for c in range(9):
                cx = c * self.CELL_SIZE + self.CELL_SIZE / 2
                cy = r * self.CELL_SIZE + self.CELL_SIZE / 2
                val = self.grid[r][c]

                if val > 0:
                    # 確定数字
                    is_initial = (self.initial_grid[r][c] > 0)
                    is_conflict = (r, c) in conflicts

                    if is_conflict:
                        text_col = COLOR_TEXT_CONFLICT
                    elif is_initial:
                        text_col = COLOR_TEXT_GIVEN
                    else:
                        text_col = COLOR_TEXT_USER

                    font_spec = (
                        (FONT_FAMILY, 20, "bold") if is_initial else (FONT_FAMILY, 20)
                    )
                    self.canvas.create_text(
                        cx, cy, text=str(val), font=font_spec, fill=text_col
                    )
                else:
                    # メモの描画 (3x3グリッドで配置)
                    notes_set = self.notes[r][c]
                    if notes_set:
                        sub_size = self.CELL_SIZE / 3
                        for n in notes_set:
                            nr = (n - 1) // 3
                            nc = (n - 1) % 3
                            nx = c * self.CELL_SIZE + (nc + 0.5) * sub_size
                            ny = r * self.CELL_SIZE + (nr + 0.5) * sub_size

                            # 選択中の数字と同じメモは強調
                            note_col = "#2563eb" if n == sel_val else COLOR_TEXT_NOTE
                            note_font = (
                                (FONT_FAMILY, 9, "bold")
                                if n == sel_val
                                else (FONT_FAMILY, 8)
                            )
                            self.canvas.create_text(
                                nx, ny, text=str(n), font=note_font, fill=note_col
                            )

    def find_conflicts(self) -> Set[Tuple[int, int]]:
        """現在入力されている数字で重複ルール違反しているマスの座標セットを返す"""
        conflicts = set()

        # 行チェック
        for r in range(9):
            seen: dict[int, List[int]] = {}
            for c in range(9):
                v = self.grid[r][c]
                if v > 0:
                    seen.setdefault(v, []).append(c)
            for v, cols in seen.items():
                if len(cols) > 1:
                    for c in cols:
                        conflicts.add((r, c))

        # 列チェック
        for c in range(9):
            seen = {}
            for r in range(9):
                v = self.grid[r][c]
                if v > 0:
                    seen.setdefault(v, []).append(r)
            for v, rows in seen.items():
                if len(rows) > 1:
                    for r in rows:
                        conflicts.add((r, c))

        # 3x3ブロックチェック
        for br in range(0, 9, 3):
            for bc in range(0, 9, 3):
                seen = {}
                for dr in range(3):
                    for dc in range(3):
                        r, c = br + dr, bc + dc
                        v = self.grid[r][c]
                        if v > 0:
                            seen.setdefault(v, []).append((r, c))
                for v, cells in seen.items():
                    if len(cells) > 1:
                        for cell in cells:
                            conflicts.add(cell)

        return conflicts

    def update_remaining_counts(self):
        """盤面に置かれている数字の数を数え、残り個数バッジとボタンスタイルを更新"""
        counts = {n: 0 for n in range(1, 10)}
        for r in range(9):
            for c in range(9):
                v = self.grid[r][c]
                if 1 <= v <= 9:
                    counts[v] += 1

        for num in range(1, 10):
            placed = counts[num]
            remaining = 9 - placed
            lbl = self.count_labels[num - 1]
            btn = self.num_buttons[num - 1]

            if remaining <= 0:
                lbl.config(text="完了 ✓", fg="#10b981")
                btn.config(bg="#f1f5f9", fg="#94a3b8")
            else:
                lbl.config(text=f"残 {remaining}", fg="#64748b")
                btn.config(bg="#ffffff", fg="#1e293b")

    # ==========================================================================
    # ユーザー入力・操作処理
    # ==========================================================================
    def on_canvas_click(self, event):
        if self.is_paused or self.game_cleared:
            return

        c = event.x // self.CELL_SIZE
        r = event.y // self.CELL_SIZE

        if 0 <= r < 9 and 0 <= c < 9:
            self.selected_cell = (r, c)
            self.draw_board()

    def on_key_press(self, event):
        if self.is_paused or self.game_cleared:
            return

        key = event.keysym.lower()

        # 矢印キー移動
        if self.selected_cell:
            r, c = self.selected_cell
            if key in ("up", "w", "k"):
                self.selected_cell = ((r - 1) % 9, c)
                self.draw_board()
                return
            elif key in ("down", "s", "j"):
                self.selected_cell = ((r + 1) % 9, c)
                self.draw_board()
                return
            elif key in ("left", "a", "h"):
                self.selected_cell = (r, (c - 1) % 9)
                self.draw_board()
                return
            elif key in ("right", "d", "l"):
                self.selected_cell = (r, (c + 1) % 9)
                self.draw_board()
                return

        # 数字入力 (メインキーボードまたはテンキー)
        if event.char in "123456789":
            self.on_number_input(int(event.char))
        elif key.startswith("kp_") and key[3:] in "123456789":
            self.on_number_input(int(key[3:]))
        elif key in ("backspace", "delete", "0", "kp_0"):
            self.erase_current_cell()
        elif key in ("n", "m"):
            self.toggle_note_mode()
        elif key == "h":
            self.give_hint()

    def on_number_input(self, num: int):
        if not self.selected_cell or self.is_paused or self.game_cleared:
            return

        r, c = self.selected_cell
        # 初期セルは変更不可
        if self.initial_grid[r][c] > 0:
            return

        if self.note_mode:
            # メモモード: 候補数字のトグル
            old_notes = set(self.notes[r][c])
            if num in self.notes[r][c]:
                self.notes[r][c].remove(num)
            else:
                self.notes[r][c].add(num)

            self.history.append({
                "type": "note",
                "r": r,
                "c": c,
                "old_notes": old_notes,
                "new_notes": set(self.notes[r][c]),
            })
            self.draw_board()
        else:
            # 通常モード: 数字入力
            old_val = self.grid[r][c]
            old_notes = set(self.notes[r][c])

            if old_val == num:
                # 同じ数字を押したら消去
                self.grid[r][c] = 0
                self.history.append({
                    "type": "val",
                    "r": r,
                    "c": c,
                    "old_val": old_val,
                    "new_val": 0,
                    "old_notes": old_notes,
                    "cleared_notes": {},
                })
            else:
                self.grid[r][c] = num
                self.notes[r][c].clear()

                # ミス判定（解と違っていたらミス加算）
                if self.solution[r][c] != num:
                    self.mistakes += 1
                    self.lbl_mistakes.config(text=f"ミス: {self.mistakes}")

                # 自動メモ消去（同じ行・列・3x3ブロックから入力された数字のメモを消す）
                cleared_notes = {}
                if self.auto_clear_notes:
                    for i in range(9):
                        if num in self.notes[r][i]:
                            cleared_notes.setdefault((r, i), set()).add(num)
                            self.notes[r][i].remove(num)
                        if num in self.notes[i][c]:
                            cleared_notes.setdefault((i, c), set()).add(num)
                            self.notes[i][c].remove(num)
                    br, bc = (r // 3) * 3, (c // 3) * 3
                    for dr in range(3):
                        for dc in range(3):
                            nr, nc = br + dr, bc + dc
                            if num in self.notes[nr][nc]:
                                cleared_notes.setdefault((nr, nc), set()).add(num)
                                self.notes[nr][nc].remove(num)

                self.history.append({
                    "type": "val",
                    "r": r,
                    "c": c,
                    "old_val": old_val,
                    "new_val": num,
                    "old_notes": old_notes,
                    "cleared_notes": cleared_notes,
                })

            self.update_remaining_counts()
            self.draw_board()
            self.check_game_completion()

    def erase_current_cell(self):
        """選択中セルの数字またはメモを消去"""
        if not self.selected_cell or self.is_paused or self.game_cleared:
            return

        r, c = self.selected_cell
        if self.initial_grid[r][c] > 0:
            return

        old_val = self.grid[r][c]
        old_notes = set(self.notes[r][c])

        if old_val == 0 and not old_notes:
            return

        self.grid[r][c] = 0
        self.notes[r][c].clear()

        self.history.append({
            "type": "erase",
            "r": r,
            "c": c,
            "old_val": old_val,
            "old_notes": old_notes,
        })

        self.update_remaining_counts()
        self.draw_board()

    def toggle_note_mode(self):
        """メモモードのON/OFF切り替え"""
        self.note_mode = not self.note_mode
        if self.note_mode:
            self.btn_note.config(
                text="✏ メモ: ON", bg=COLOR_BTN_NOTE_ACTIVE, fg="white"
            )
        else:
            self.btn_note.config(
                text="✏ メモ: OFF", bg="#ffffff", fg="#1e293b"
            )

    def undo(self):
        """アンドゥ（1つ前の操作を取り消す）"""
        if not self.history or self.is_paused or self.game_cleared:
            return

        action = self.history.pop()
        r, c = action["r"], action["c"]

        if action["type"] == "note":
            self.notes[r][c] = action["old_notes"]
        elif action["type"] == "val":
            self.grid[r][c] = action["old_val"]
            self.notes[r][c] = action["old_notes"]
            # 自動消去されたメモを復元
            for (cr, cc), note_set in action.get("cleared_notes", {}).items():
                self.notes[cr][cc].update(note_set)
        elif action["type"] == "erase":
            self.grid[r][c] = action["old_val"]
            self.notes[r][c] = action["old_notes"]

        self.selected_cell = (r, c)
        self.update_remaining_counts()
        self.draw_board()

    def give_hint(self):
        """ヒント: 空いているセルまたは間違っているセルに正解を入力"""
        if self.is_paused or self.game_cleared:
            return

        # 優先度1: 現在選択中のセルが空または間違っている場合
        target = None
        if self.selected_cell:
            sr, sc = self.selected_cell
            if self.initial_grid[sr][sc] == 0 and self.grid[sr][sc] != self.solution[sr][sc]:
                target = (sr, sc)

        # 優先度2: 間違っているセルを探す
        if not target:
            for r in range(9):
                for c in range(9):
                    if self.grid[r][c] > 0 and self.grid[r][c] != self.solution[r][c]:
                        target = (r, c)
                        break
                if target:
                    break

        # 優先度3: まだ空いているセルを探す
        if not target:
            empty_cells = [
                (r, c) for r in range(9) for c in range(9) if self.grid[r][c] == 0
            ]
            if empty_cells:
                target = random.choice(empty_cells)

        if not target:
            return

        r, c = target
        correct_val = self.solution[r][c]
        old_val = self.grid[r][c]
        old_notes = set(self.notes[r][c])

        self.grid[r][c] = correct_val
        self.notes[r][c].clear()
        self.selected_cell = (r, c)
        self.hints_used += 1

        self.history.append({
            "type": "val",
            "r": r,
            "c": c,
            "old_val": old_val,
            "new_val": correct_val,
            "old_notes": old_notes,
            "cleared_notes": {},
        })

        self.update_remaining_counts()
        self.draw_board()
        self.check_game_completion()

    def fill_all_candidates(self):
        """すべての空きセルに現在のルール上置ける候補数字を自動メモ"""
        if self.is_paused or self.game_cleared:
            return

        for r in range(9):
            for c in range(9):
                if self.grid[r][c] == 0:
                    cands = SudokuGenerator.get_candidates(self.grid, r, c)
                    self.notes[r][c] = set(cands)

        self.draw_board()

    def restart_current_game(self):
        """現在の問題を初期状態にリセット"""
        if self.game_cleared:
            return

        if messagebox.askyesno("リセット", "現在の盤面を初期状態に戻しますか？"):
            self.grid = [row[:] for row in self.initial_grid]
            self.notes = [[set() for _ in range(9)] for _ in range(9)]
            self.history.clear()
            self.mistakes = 0
            self.hints_used = 0
            self.lbl_mistakes.config(text="ミス: 0")
            self.update_remaining_counts()
            self.draw_board()

    def confirm_solve(self):
        """答えを表示する"""
        if self.game_cleared:
            return

        if messagebox.askyesno("確認", "本当に解答を表示しますか？\n現在の進行状況は終了します。"):
            for r in range(9):
                for c in range(9):
                    self.grid[r][c] = self.solution[r][c]
                    self.notes[r][c].clear()

            self.update_remaining_counts()
            self.draw_board()
            self.game_cleared = True
            self.timer_running = False

    # ==========================================================================
    # クリア判定
    # ==========================================================================
    def check_game_completion(self):
        """盤面がすべて正解で埋まっているか検証"""
        for r in range(9):
            for c in range(9):
                if self.grid[r][c] != self.solution[r][c]:
                    return

        # クリア達成！
        self.game_cleared = True
        self.timer_running = False

        m = self.timer_seconds // 60
        s = self.timer_seconds % 60
        time_str = f"{m}分{s:02d}秒" if m > 0 else f"{s}秒"

        # 紙吹雪スタート
        self.confetti.start(count=80, duration_seconds=5.0)

        # クリアメッセージ
        msg = (
            f"🎉 おめでとうございます！ 数独クリア！ 🎉\n\n"
            f"難易度: {self.diff_var.get()}\n"
            f"クリアタイム: {time_str}\n"
            f"ミス回数: {self.mistakes}回\n"
            f"ヒント使用: {self.hints_used}回"
        )
        self.root.after(300, lambda: messagebox.showinfo("CLEAR!!", msg))


# ==============================================================================
# メインエントリーポイント
# ==============================================================================
def center_window(root: tk.Tk):
    """ウィンドウを画面中央に配置"""
    root.update_idletasks()
    w = root.winfo_reqwidth()
    h = root.winfo_reqheight()
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    x = max(0, (screen_w - w) // 2)
    y = max(0, (screen_h - h) // 2 - 20)
    root.geometry(f"{w}x{h}+{x}+{y}")


def main():
    root = tk.Tk()
    app = SudokuApp(root)
    center_window(root)
    root.mainloop()


if __name__ == "__main__":
    main()

