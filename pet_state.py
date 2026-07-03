#!/usr/bin/env python3
"""Claude Code hook → 写桌宠状态到 .pet_state 文件"""
import sys, os, json, time, fnmatch

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".pet_state")
SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".claude", "settings.json")

TOOL_ANIM = {
    "Write": "writing", "Edit": "writing", "NotebookEdit": "writing",
    "Read": "reading", "Grep": "reading", "Glob": "reading",
    "WebFetch": "reading", "WebSearch": "reading",
    "Bash": "running", "PowerShell": "running",
    "Agent": "running", "Workflow": "running",
}

TOOL_MSG = {
    "Bash": "执行命令中…",
    "PowerShell": "执行命令中…",
    "Read": "读取文件中…",
    "Write": "写入文件中…",
    "Edit": "编辑文件中…",
    "NotebookEdit": "编辑笔记本…",
    "Grep": "搜索内容中…",
    "Glob": "查找文件中…",
    "WebFetch": "访问网页中…",
    "WebSearch": "搜索网络中…",
    "Agent": "思考中…",
    "Workflow": "执行任务中…",
}

def get_message(tool, inp):
    """返回中文气泡消息"""
    return TOOL_MSG.get(tool, "处理中…")

def load_allowed_patterns():
    """从 settings.json 读取已授权的 Bash 命令模式"""
    try:
        with open(SETTINGS_FILE, "r") as f:
            settings = json.load(f)
        allow_list = settings.get("permissions", {}).get("allow", [])
        patterns = []
        for item in allow_list:
            if "(" in item and item.endswith(")"):
                tool = item.split("(")[0]
                pattern = item[len(tool)+1:-1]
                patterns.append((tool, pattern))
        return patterns
    except:
        return []

def needs_permission(tool_name, tool_input, allowed, permission_mode=""):
    """判断工具是否需要权限确认"""
    # acceptEdits/bypassPermissions 模式下，工具自动放行，不需要等待
    if permission_mode in ("acceptEdits", "bypassPermissions"):
        return False
    if tool_name not in TOOL_ANIM:
        return True
    if tool_name in ("Bash", "PowerShell"):
        cmd = tool_input.get("command", "")
        for t, pattern in allowed:
            if t == tool_name and fnmatch.fnmatch(cmd, pattern):
                return False
        return True
    return False

def write_state(state, detail="", message=""):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump({"state": state, "detail": detail, "message": message, "ts": time.time()}, f)
    except:
        pass

def main():
    raw = ""
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except:
        data = {}

    hook_event = data.get("hook_event_name", "") or data.get("event", "") or data.get("type", "")
    tool_name = data.get("tool_name", "") or data.get("tool", "")

    if not hook_event:
        for key in ["CLAUDE_HOOK_EVENT", "CLAUDE_EVENT", "CLAUDE_HOOK_TYPE"]:
            hook_event = os.environ.get(key, "")
            if hook_event:
                break

    tool_input = data.get("tool_input", {})

    if "PreToolUse" in hook_event:
        permission_mode = data.get("permission_mode", "")
        allowed = load_allowed_patterns()
        if needs_permission(tool_name, tool_input, allowed, permission_mode):
            write_state("waiting", tool_name, "❗")
        else:
            anim = TOOL_ANIM.get(tool_name, "waiting")
            msg = get_message(tool_name, tool_input)
            write_state(anim, tool_name, msg)
    elif "PostToolUse" in hook_event:
        write_state("idle")
    elif "Stop" in hook_event:
        write_state("wave", "finished", "finished")
    else:
        write_state("idle")

if __name__ == "__main__":
    main()
