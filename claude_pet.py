#!/usr/bin/env python3
"""Claude Pixel 桌面宠物 - 与 Claude Code 状态联动"""

import tkinter as tk
from PIL import Image, ImageTk
import random
import os
import json
import time
import ctypes
import ctypes.wintypes

# ── 配置 ──
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SPRITESHEET = os.path.join(BASE_DIR, "claude-pixel-spritesheet.webp")
STATE_FILE = os.path.join(BASE_DIR, ".pet_state")
SCALE = 0.5
FPS = 8
WALK_SPEED = 2
STATE_CHECK_INTERVAL = 500
BUBBLE_HIDE_DELAY = 3000
BUBBLE_MAX_W = 200
BUBBLE_PAD = 12
BUBBLE_TRI_H = 8
BUBBLE_TOP_MARGIN = 0  # 气泡离精灵的间距

# 动画行定义
ANIMS = {
    "idle": 0, "run_r": 1, "run_l": 2, "wave": 3, "jump": 4,
    "failed": 5, "waiting": 6, "running": 7, "review": 8,
}
FRAME_COUNT = 8

STATE_TO_ANIM = {
    "idle": "idle", "running": "running", "reading": "review",
    "writing": "running", "waiting": "waiting", "failed": "failed", "wave": "wave",
}


def load_frames(path, scale):
    img = Image.open(path).convert("RGBA")
    fw, fh = img.width // FRAME_COUNT, img.height // len(ANIMS)
    sw, sh = int(fw * scale), int(fh * scale)
    frames = {}
    for name, row in ANIMS.items():
        frames[name] = []
        for col in range(FRAME_COUNT):
            box = (col * fw, row * fh, (col + 1) * fw, (row + 1) * fh)
            frame = img.crop(box).resize((sw, sh), Image.NEAREST)
            frames[name].append(ImageTk.PhotoImage(frame))
    return frames, sw, sh


def focus_claude_terminal():
    """查找并置顶 Claude Code 终端窗口"""
    try:
        user32 = ctypes.windll.user32
        result = {"found": False}

        def enum_cb(hwnd, _):
            if user32.IsWindowVisible(hwnd):
                cls = ctypes.create_unicode_buffer(256)
                user32.GetClassNameW(hwnd, cls, 256)
                if "CASCADIA" in cls.value.upper() or "WINDOWSTERMINAL" in cls.value.upper():
                    fg = user32.GetForegroundWindow()
                    fg_tid = user32.GetWindowThreadProcessId(fg, None)
                    my_tid = ctypes.windll.kernel32.GetCurrentThreadId()
                    user32.AttachThreadInput(my_tid, fg_tid, True)
                    user32.SetForegroundWindow(hwnd)
                    user32.AttachThreadInput(my_tid, fg_tid, False)
                    result["found"] = True
                    return False
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
        user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
        return result["found"]
    except Exception:
        return False


class ClaudePet:
    def __init__(self, root):
        self.root = root
        self.root.title("Claude Pixel Pet")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparentcolor", "#010101")
        self.root.config(bg="#010101")

        self.frames, self.fw, self.fh = load_frames(SPRITESHEET, SCALE)

        # 画布固定大小：上方留气泡空间 + 精灵
        self.bubble_area_h = 60  # 气泡最大高度
        self.canvas_w = max(self.fw, BUBBLE_MAX_W + BUBBLE_PAD * 2)
        self.canvas_h = self.bubble_area_h + BUBBLE_TOP_MARGIN + self.fh
        self.sprite_y0 = self.bubble_area_h + BUBBLE_TOP_MARGIN  # 精灵在画布中的固定 y

        self.canvas = tk.Canvas(root, width=self.canvas_w, height=self.canvas_h,
                                bg="#010101", highlightthickness=0)
        self.canvas.pack()

        # 状态
        self.current_anim = "idle"
        self.frame_idx = 0
        self.facing_right = True
        self.drag_data = {"x": 0, "y": 0}
        self.auto_move = True
        self.last_state = ""
        self.locked_by_hook = False

        # 气泡状态
        self.bubble_visible = False
        self.bubble_text = ""
        self.bubble_hide_id = None

        # 初始位置（屏幕右下角）
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        self.x = sw - self.canvas_w - 20
        self.y = sh - self.canvas_h - 80
        root.geometry(f"{self.canvas_w}x{self.canvas_h}+{self.x}+{self.y}")

        # 事件绑定
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Double-Button-1>", self.on_double_click)
        self.canvas.bind("<Button-3>", self.on_right_click)

        # 右键菜单
        self.menu = tk.Menu(root, tearoff=0)
        self.menu.add_command(label="👋 挥手", command=lambda: self.switch_anim("wave"))
        self.menu.add_command(label="🦘 跳跃", command=lambda: self.switch_anim("jump"))
        self.menu.add_command(label="🔍 审阅代码", command=lambda: self.switch_anim("review"))
        self.menu.add_command(label="⏳ 等待中", command=lambda: self.switch_anim("waiting"))
        self.menu.add_command(label="😵 失败了", command=lambda: self.switch_anim("failed"))
        self.menu.add_separator()
        self.menu.add_command(label="❌ 退出", command=root.destroy)

        self.check_state()
        self.animate()

    # ── 气泡 ──

    def draw_bubble(self, text):
        """在精灵头顶绘制对话气泡"""
        font = ("Microsoft YaHei", 9)

        # 估算文字尺寸
        tmp = tk.Label(self.root, text=text, font=font, wraplength=BUBBLE_MAX_W - 20)
        tmp.pack()
        tmp.update_idletasks()
        tw, th = tmp.winfo_reqwidth(), tmp.winfo_reqheight()
        tmp.destroy()

        bw = min(tw + BUBBLE_PAD * 2, BUBBLE_MAX_W)
        bh = th + BUBBLE_PAD

        # 气泡区域居中
        bx = (self.canvas_w - bw) // 2
        by = self.bubble_area_h - bh - BUBBLE_TRI_H

        # 圆角矩形
        r = 8
        x1, y1, x2, y2 = bx, by, bx + bw, by + bh
        self.canvas.create_polygon(
            x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
            x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
            x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
            fill="#FFFFFF", outline="#CCCCCC", smooth=True, tags="bubble"
        )

        # 三角箭头（朝下指向精灵）
        cx = self.canvas_w // 2
        self.canvas.create_polygon(
            cx - 6, y2, cx + 6, y2, cx, y2 + BUBBLE_TRI_H,
            fill="#FFFFFF", outline="#CCCCCC", tags="bubble"
        )

        # 文字
        self.canvas.create_text(
            bx + bw // 2, by + bh // 2,
            text=text, font=font, fill="#333333",
            width=BUBBLE_MAX_W - 20, justify="center", tags="bubble"
        )

        self.bubble_visible = True
        self.bubble_text = text

    def hide_bubble(self):
        if not self.bubble_visible:
            return
        self.canvas.delete("bubble")
        self.bubble_visible = False
        self.bubble_text = ""

    def schedule_bubble_hide(self):
        if self.bubble_hide_id:
            self.root.after_cancel(self.bubble_hide_id)
        self.bubble_hide_id = self.root.after(BUBBLE_HIDE_DELAY, self.hide_bubble)

    # ── 状态联动 ──

    def check_state(self):
        try:
            if os.path.exists(STATE_FILE):
                mtime = os.path.getmtime(STATE_FILE)
                if mtime != self.last_state:
                    self.last_state = mtime
                    with open(STATE_FILE, "r") as f:
                        data = json.load(f)
                    state = data.get("state", "idle")
                    message = data.get("message", "") or data.get("detail", "")
                    anim = STATE_TO_ANIM.get(state, "idle")

                    if state == "idle":
                        self.locked_by_hook = False
                        self.auto_move = True
                        if self.current_anim not in ("run_r", "run_l"):
                            self.current_anim = "idle"
                        if self.bubble_visible:
                            self.schedule_bubble_hide()
                    else:
                        self.locked_by_hook = True
                        self.auto_move = False
                        if self.current_anim != anim:
                            self.current_anim = anim
                            self.frame_idx = 0
                        if message:
                            self.draw_bubble(message)
                            if self.bubble_hide_id:
                                self.root.after_cancel(self.bubble_hide_id)
                                self.bubble_hide_id = None
        except Exception:
            pass
        self.root.after(STATE_CHECK_INTERVAL, self.check_state)

    # ── 事件 ──

    def switch_anim(self, name):
        self.current_anim = name
        self.frame_idx = 0

    def on_click(self, event):
        # 点击气泡区域跳转终端
        if self.bubble_visible and event.y < self.bubble_area_h:
            focus_claude_terminal()
            return
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y

    def on_drag(self, event):
        dx = event.x - self.drag_data["x"]
        dy = event.y - self.drag_data["y"]
        self.x += dx
        self.y += dy
        self.root.geometry(f"+{self.x}+{self.y}")

    def on_release(self, event):
        if not self.locked_by_hook:
            self.root.after(1500, self.restore_idle)

    def on_double_click(self, event):
        self.switch_anim("wave")

    def on_right_click(self, event):
        self.menu.post(event.x_root, event.y_root)

    def restore_idle(self):
        if not self.locked_by_hook:
            self.current_anim = "idle"
            self.frame_idx = 0
            self.auto_move = True

    def auto_walk(self):
        if not self.auto_move or self.locked_by_hook:
            return
        sw = self.root.winfo_screenwidth()
        if self.facing_right:
            self.x += WALK_SPEED
            if self.x + self.canvas_w >= sw - 10:
                self.facing_right = False
                self.current_anim = "run_l"
        else:
            self.x -= WALK_SPEED
            if self.x <= 10:
                self.facing_right = True
                self.current_anim = "run_r"
        self.root.geometry(f"+{self.x}+{self.y}")

    def animate(self):
        anim = self.current_anim
        frames_list = self.frames[anim]

        # 只删精灵，保留气泡
        self.canvas.delete("sprite")
        self.canvas.create_image(
            self.canvas_w // 2, self.sprite_y0,
            anchor="n", image=frames_list[self.frame_idx], tags="sprite"
        )

        if not self.locked_by_hook:
            self.auto_walk()

        self.frame_idx = (self.frame_idx + 1) % len(frames_list)

        if self.frame_idx == 0:
            if not self.locked_by_hook:
                if anim == "idle":
                    r = random.random()
                    if r < 0.6:
                        self.current_anim = "idle"
                    elif r < 0.7:
                        self.current_anim = "wave"
                        self.root.after(1200, self.restore_idle)
                    elif r < 0.75:
                        self.current_anim = "jump"
                        self.root.after(800, self.restore_idle)
                    else:
                        self.current_anim = "run_r" if self.facing_right else "run_l"
                elif anim in ("wave", "jump", "failed", "waiting", "review"):
                    self.current_anim = "idle"
                    self.auto_move = True
            elif anim == "wave":
                # wave 动画播完，自动恢复 idle（Stop hook 场景）
                self.locked_by_hook = False
                self.auto_move = True
                self.current_anim = "idle"
                self.hide_bubble()

        self.root.after(int(1000 / FPS), self.animate)


def main():
    root = tk.Tk()
    root.withdraw()
    ClaudePet(root)
    root.deiconify()
    root.mainloop()


if __name__ == "__main__":
    main()
