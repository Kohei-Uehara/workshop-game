"""OXゲーム（三目並べ） (tkinter 版)

2人で交互に 3×3 のマスをクリックして O と X を配置し、
縦・横・斜めのいずれかに3つそろえたプレイヤーの勝利となります。
"""

import tkinter as tk
from tkinter import font


class TicTacToe:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("OXゲーム (三目並べ)")
        self.root.resizable(False, False)

        # ゲーム状態の初期化
        self.current_player = "O"
        self.board = [""] * 9
        self.game_over = False

        # 勝利ラインの定義（インデックス）
        self.win_lines = [
            (0, 1, 2),  # 行
            (3, 4, 5),
            (6, 7, 8),
            (0, 3, 6),  # 列
            (1, 4, 7),
            (2, 5, 8),
            (0, 4, 8),  # 斜め
            (2, 4, 6),
        ]

        self.setup_ui()

    def setup_ui(self) -> None:
        # メインフレーム
        main_frame = tk.Frame(self.root, padx=20, pady=20, bg="#f5f6fa")
        main_frame.pack()

        # タイトル & 手番/結果表示ラベル
        self.status_label = tk.Label(
            main_frame,
            text=f"プレイヤー {self.current_player} の番です",
            font=("Arial", 16, "bold"),
            bg="#f5f6fa",
            fg="#2c3e50",
            pady=10,
        )
        self.status_label.pack()

        # 3×3 のマス目フレーム
        grid_frame = tk.Frame(main_frame, bg="#dcdde1", padx=4, pady=4)
        grid_frame.pack(pady=10)

        self.buttons: list[tk.Button] = []
        for i in range(9):
            row, col = divmod(i, 3)
            btn = tk.Button(
                grid_frame,
                text="",
                font=("Arial", 32, "bold"),
                width=3,
                height=1,
                relief="raised",
                bg="#ffffff",
                activebackground="#f1f2f6",
                cursor="hand2",
                command=lambda idx=i: self.on_cell_click(idx),
            )
            btn.grid(row=row, column=col, padx=4, pady=4)
            self.buttons.append(btn)

        # リセットボタン
        self.reset_btn = tk.Button(
            main_frame,
            text="リセット（もう一度遊ぶ）",
            font=("Arial", 12),
            bg="#3498db",
            fg="#ffffff",
            activebackground="#2980b9",
            activeforeground="#ffffff",
            relief="flat",
            padx=10,
            pady=6,
            cursor="hand2",
            command=self.reset_game,
        )
        self.reset_btn.pack(pady=(10, 5))

    def on_cell_click(self, index: int) -> None:
        # すでに埋まっているマス、またはゲーム終了時は何もしない
        if self.board[index] != "" or self.game_over:
            return

        # マークを配置
        self.board[index] = self.current_player
        btn = self.buttons[index]
        btn.config(
            text=self.current_player,
            fg="#2980b9" if self.current_player == "O" else "#e74c3c",
        )

        # 勝敗判定
        winner_line = self.check_winner()
        if winner_line is not None:
            self.game_over = True
            self.status_label.config(
                text=f"🎉 プレイヤー {self.current_player} の勝ち！",
                fg="#27ae60",
            )
            # そろったマスをハイライト
            for idx in winner_line:
                self.buttons[idx].config(bg="#a8e6cf")
            return

        # 引き分け判定（すべてのマスが埋まった場合）
        if "" not in self.board:
            self.game_over = True
            self.status_label.config(
                text="引き分けです！",
                fg="#7f8c8d",
            )
            return

        # 手番交代
        self.current_player = "X" if self.current_player == "O" else "O"
        self.status_label.config(
            text=f"プレイヤー {self.current_player} の番です",
            fg="#2c3e50",
        )

    def check_winner(self) -> tuple[int, int, int] | None:
        for a, b, c in self.win_lines:
            if (
                self.board[a] != ""
                and self.board[a] == self.board[b] == self.board[c]
            ):
                return (a, b, c)
        return None

    def reset_game(self) -> None:
        self.current_player = "O"
        self.board = [""] * 9
        self.game_over = False

        self.status_label.config(
            text=f"プレイヤー {self.current_player} の番です",
            fg="#2c3e50",
        )

        for btn in self.buttons:
            btn.config(
                text="",
                bg="#ffffff",
                fg="#000000",
                relief="raised",
            )


def main() -> None:
    root = tk.Tk()
    app = TicTacToe(root)
    root.mainloop()


if __name__ == "__main__":
    main()

