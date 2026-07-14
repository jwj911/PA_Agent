"""Single source of truth for strategy / prompt .txt filenames (task R1).

`ai/router.py` (Stage 1 → Stage 2 file routing) and `ai/prompt_assembler.py`
(prompt construction) both referenced the same filename literals independently.
Defining each name once here removes that duplication: adding or renaming a
strategy file now only requires editing this module.

Values are kept byte-identical to the previous inline literals — the Stage 2
prompt prefix is DeepSeek KV-cache sensitive, so consuming modules must build
the exact same ordered file lists as before.

`ai/pattern_routing.py` embeds these names inside KV-cache-sensitive prompt
markdown prose (not code literals) and is intentionally left untouched.
"""
from __future__ import annotations

# ── Common system files (both stages) ───────────────────────────────────────────
PERSONA = "提示词大纲_人设与思维方式.txt"
BINARY_DECISION = "二元决策.txt"

# ── Stage 1 task files ───────────────────────────────────────────────────────────
MARKET_DIAGNOSIS = "市场诊断框架.txt"

# ── Stage 2 base files ───────────────────────────────────────────────────────────
BAR_CHECKLIST = "逐棒分析检查单.txt"
KLINE_SIGNAL = "文件16-K线信号识别.txt"
STOP_TARGET_POSITION = "文件17-止损和止盈与仓位管理.txt"
MEASURED_MOVE = "文件23-MeasuredMove与结构目标.txt"

# ── Directional channel files ────────────────────────────────────────────────────
BULLISH_CHANNEL_ID = "上涨通道分析识别.txt"
BULLISH_CHANNEL_STRATEGY = "上涨通道交易策略.txt"
BEARISH_CHANNEL_ID = "下跌通道分析识别.txt"
BEARISH_CHANNEL_STRATEGY = "下跌通道交易策略.txt"

# ── Directional spike files ──────────────────────────────────────────────────────
BULLISH_SPIKE_ID = "极速上涨分析识别.txt"
BULLISH_SPIKE_STRATEGY = "极速上涨交易策略.txt"
BEARISH_SPIKE_ID = "极速下跌分析识别.txt"
BEARISH_SPIKE_STRATEGY = "极速下跌交易策略.txt"

# ── Range files ──────────────────────────────────────────────────────────────────
RANGE_ID = "震荡区间分析识别.txt"
RANGE_STRATEGY = "震荡区间交易策略.txt"

# ── Numbered pattern / structure playbooks ───────────────────────────────────────
CHANNEL_WIDTH = "文件13-窄通道与宽通道策略.txt"
WEDGE = "文件14-楔形形态分析交易.txt"
REVERSAL = "文件15-二次入场机会.txt"
BREAKOUT_FAILURE = "文件18-突破失败与突破测试.txt"
H1H2 = "文件19-H1H2-L1L2计数.txt"
ALWAYS_IN = "文件20-AlwaysIn与20GB.txt"
BARBWIRE = "文件21-铁丝网与无交易环境.txt"
MAGNET = "文件22-信号失败后的磁力位.txt"
FINAL_FLAG = "文件24-最终旗形与趋势末端.txt"
MTR = "文件25-主要趋势反转MTR.txt"
TRIANGLE = "文件27-三角形与收敛形态.txt"
DOUBLE_TOP_BOTTOM = "文件28-双重顶底与微型结构.txt"
