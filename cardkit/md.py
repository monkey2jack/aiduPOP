"""Markdown 文本处理 — 标题降级、表格降级、图片 key 剥离、长文本分块."""

from __future__ import annotations

import logging
import re

_logger = logging.getLogger("hermes_lark_streaming")

_MAX_CARD_TABLES = 20  # 流式卡片：20表降级阈值（流式增量内容，飞书宽松执行）
_MAX_CRON_TABLES = 5   # 静态卡片：5表降级阈值（飞书 Card 2.0 单卡硬限）
_MAX_CHUNK_CHARS = 2400

# 【嘟嘟定制 v23.3】通用内容钳制（防爆）— 单块显示上限，头尾保留中段省略
_MAX_DISPLAY_CHARS = 3000
_CLAMP_HEAD = 2200
_CLAMP_TAIL = 600

def clamp_content(content: str, max_chars: int = _MAX_DISPLAY_CHARS) -> str:
    """超限内容保留头尾、中段省略 — 防止单个元素撑爆整卡（飞书 ~30K JSON 上限，溢出断屏根因）."""
    if len(content) <= max_chars:
        return content
    omitted = len(content) - _CLAMP_HEAD - _CLAMP_TAIL
    return (
        content[:_CLAMP_HEAD]
        + f"\n\n…（中段省略 {omitted} 字符，防卡片溢出）…\n\n"
        + content[-_CLAMP_TAIL:]
    )

_ANSWER_MAX_BYTES = 18000   # 【嘟嘟定制 v23.4】answer 总预算（UTF-8 字节，≈6000汉字）— 与 panel 动态共享，留足 ~10KB 给 panel 和结构开销，严守 <30KB 硬限

def clamp_utf8(text: str, max_bytes: int = _ANSWER_MAX_BYTES, preserve_tail: bool = True) -> str:
    """按 UTF-8 字节钳制长文 — 支持首尾双保（保留开头背景 + 省略中间过程 + 保留最后核心结论）.

    preserve_tail=True 用于封卡完成态（确保最终结论不丢失）；
    preserve_tail=False 用于流式进行时（渐进截断）.
    """
    raw_len = len(text.encode("utf-8"))
    if raw_len <= max_bytes:
        return text

    if not preserve_tail:
        suffix = "\n\n…（内容过长已截断，防卡片溢出）…"
        budget = max_bytes - len(suffix.encode("utf-8"))
        lo, hi = 0, len(text)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if len(text[:mid].encode("utf-8")) <= budget:
                lo = mid
            else:
                hi = mid - 1
        return text[:lo] + suffix

    # 封卡完成态：首尾双保（前 60% 头部 + 后 40% 尾部，中段分析省略）
    omission_tag = "\n\n…（中段分析已省略，保留开头背景与末尾核心结论，防卡片溢出）…\n\n"
    tag_bytes = len(omission_tag.encode("utf-8"))
    net_budget = max_bytes - tag_bytes
    if net_budget <= 0:
        return text[:100] + omission_tag

    head_budget = int(net_budget * 0.60)
    tail_budget = net_budget - head_budget

    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if len(text[:mid].encode("utf-8")) <= head_budget:
            lo = mid
        else:
            hi = mid - 1
    head_text = text[:lo]

    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if len(text[-mid:].encode("utf-8")) <= tail_budget:
            lo = mid
        else:
            hi = mid - 1
    tail_text = text[-lo:] if lo > 0 else ""

    return head_text + omission_tag + tail_text

# ── Pre-compiled regex patterns (P2-01: avoid recompilation on every call) ──
_RE_FENCED_CODE = re.compile(r'```[\s\S]*?```')
_RE_INLINE_CODE = re.compile(r'`[^`]+`')
_RE_BOLD = re.compile(r'\*{2,3}(?!\s)((?:(?!\*{2,3}).)+?)(?<!\s)\*{2,3}', re.DOTALL)
_RE_VALID_ITALIC = re.compile(r'(?<![a-zA-Z0-9_])\*(?!\s)((?:(?!\*).)+?)(?<!\s)\*', re.DOTALL)
_RE_UNPAIRED_ASTERISK = re.compile(r'(?<!\\)\*(?=[^\s*])')
_RE_TABLE_ROW = re.compile(r"\|.+\|\n\|[-:| ]+\|[\s\S]*?(?=\n\n|\n(?!\|)|$)")
_RE_IMAGE_REF = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")
_RE_CODE_BLOCK_EXTRACT = re.compile(r"(^|\n)(`{3,})([^\n]*)\n[\s\S]*?\n\2(?=\n|$)")
_RE_H1_TO_H3 = re.compile(r"^#{1,3} ", re.MULTILINE)
_RE_HEADING_DEMOTE = re.compile(r"^#{2,6} (.+)$", re.MULTILINE)
_RE_H1_DEMOTE = re.compile(r"^# (.+)$", re.MULTILINE)
_RE_MULTI_NEWLINE = re.compile(r"\n{3,}")
_RE_SHORT_MD_CHECK = re.compile(r'^#{1,6} |\n#{1,6} |```|!\[|\n{3,}')
# v1.3.0: placeholder pattern for restoring protected code/bold/italic blocks
_RE_PROTECTED_PLACEHOLDER = re.compile(r'\x00P(\d+)P\x00')

__all__ = [
    "_MAX_CRON_TABLES",
    "_downgrade_tables",
    "_find_tables_outside_code_blocks",
    "_split_long_text",
    "_strip_invalid_image_keys",
    "escape_markdown_asterisks",
    "clamp_content",
    "clamp_utf8",
    "optimize_markdown_style",
]


# ==========================================
# 【嘟嘟定制 v23.0】贝氏卡片无损降级防爆引擎
# ==========================================
import re
from dataclasses import dataclass

@dataclass
class MarkdownBlock:
    kind: str
    text: str
    start: int
    end: int

LIST_BOUNDARY_RE = re.compile(r"(\n[ \t]*[-*+]\s|\n[ \t]*\d+\.\s)")

def _fence_opening(line: str) -> tuple[str, int] | None:
    stripped = line.lstrip(" \t")
    if not stripped.startswith(("`", "~")):
        return None
    char = stripped[0]
    count = 1
    while count < len(stripped) and stripped[count] == char:
        count += 1
    if count >= 3:
        return char, count
    return None

def _is_fence_closing(line: str, marker_char: str, marker_size: int) -> bool:
    stripped = line.lstrip(" \t").rstrip("\r\n")
    if not stripped.startswith(marker_char * marker_size):
        return False
    return not stripped[marker_size:].strip(marker_char).strip()

def _parse_table_separator(row: str) -> list[str] | None:
    stripped = row.strip()
    if not stripped:
        return None
    if not re.match(r"^\|?[\s\-|:]+\|?$", stripped):
        return None
    cells = _parse_markdown_row(stripped)
    if not cells:
        return None
    for cell in cells:
        clean = cell.replace("-", "").replace(":", "").strip()
        if clean:
            return None
    return cells

def scan_markdown_blocks(text: str) -> list[MarkdownBlock]:
    if not text:
        return [MarkdownBlock(kind="plain", text="", start=0, end=0)]

    lines = text.splitlines(keepends=True)
    offsets: list[int] = []
    cursor = 0
    for line in lines:
        offsets.append(cursor)
        cursor += len(line)

    blocks: list[MarkdownBlock] = []
    paragraph: list[str] = []
    paragraph_start = 0

    def flush_paragraph(end: int) -> None:
        nonlocal paragraph
        if paragraph:
            blocks.append(
                MarkdownBlock(
                    kind="plain",
                    text="".join(paragraph),
                    start=paragraph_start,
                    end=end,
                )
            )
            paragraph = []

    index = 0
    while index < len(lines):
        line = lines[index]
        opening = _fence_opening(line)
        if opening is not None:
            flush_paragraph(offsets[index])
            fence_start = offsets[index]
            fence_lines = [line]
            marker_char, marker_size = opening
            index += 1
            while index < len(lines):
                candidate = lines[index]
                fence_lines.append(candidate)
                index += 1
                if _is_fence_closing(candidate, marker_char, marker_size):
                    break
            fence_text = "".join(fence_lines)
            blocks.append(
                MarkdownBlock(
                    kind="fence",
                    text=fence_text,
                    start=fence_start,
                    end=fence_start + len(fence_text),
                )
            )
            continue

        if index + 1 < len(lines):
            headers = _parse_markdown_row(line.rstrip("\r\n"))
            separator = _parse_table_separator(lines[index + 1].rstrip("\r\n"))
            if (
                headers is not None
                and separator is not None
                and len(headers) == len(separator)
            ):
                flush_paragraph(offsets[index])
                table_start = offsets[index]
                table_lines = [line, lines[index + 1]]
                index += 2
                while index < len(lines):
                    candidate = lines[index].rstrip("\r\n")
                    if not candidate:
                        break
                    row_cells = _parse_markdown_row(candidate)
                    if row_cells is None:
                        break
                    if len(row_cells) != len(headers):
                        break
                    table_lines.append(lines[index])
                    index += 1
                table_text = "".join(table_lines)
                blocks.append(
                    MarkdownBlock(
                        kind="table",
                        text=table_text,
                        start=table_start,
                        end=table_start + len(table_text),
                    )
                )
                continue
        paragraph.append(line)
        index += 1
    flush_paragraph(len(text))
    return blocks


def _find_tables_outside_code_blocks(text: str) -> list[tuple[int, int, str]]:
    """Return markdown table ranges while ignoring fenced code blocks.

    Aegis 2.1 replaced the regex scanner with ``scan_markdown_blocks`` but
    accidentally removed this public compatibility helper while leaving it in
    ``__all__``. Keep one parser as the source of truth and adapt its output.
    """
    return [
        (block.start, block.end, block.text)
        for block in scan_markdown_blocks(text)
        if block.kind == "table"
    ]


def _parse_markdown_row(row: str) -> list[str] | None:
    stripped = row.strip()
    if not stripped:
        return None
    cells: list[str] = []
    current: list[str] = []
    delimiter_count = 0
    inline_code_size = 0
    index = 0
    while index < len(stripped):
        char = stripped[index]
        if char == "\\" and index + 1 < len(stripped):
            current.append(char)
            current.append(stripped[index + 1])
            index += 2
            continue
        if char == "`":
            run_end = index + 1
            while run_end < len(stripped) and stripped[run_end] == "`":
                run_end += 1
            run_size = run_end - index
            current.append(stripped[index:run_end])
            if inline_code_size == 0:
                inline_code_size = run_size
            elif inline_code_size == run_size:
                inline_code_size = 0
            index = run_end
            continue
        if char == "|" and inline_code_size == 0:
            cells.append("".join(current).strip())
            current = []
            delimiter_count += 1
            index += 1
            continue
        current.append(char)
        index += 1
    cells.append("".join(current).strip())
    if delimiter_count == 0:
        return None
    if stripped.startswith("|"):
        cells = cells[1:]
    if stripped.endswith("|") and cells:
        cells = cells[:-1]
    return cells or None

@dataclass
class TableOverflowResult:
    text: str
    original_tables: int
    tables_remaining: int
    compacted: bool

def transform_table_overflow(
    text: str,
    *,
    mode: str = "compact",
    max_tables: int = 5,
) -> TableOverflowResult:
    blocks = scan_markdown_blocks(text)
    table_indices = [i for i, b in enumerate(blocks) if b.kind == "table"]
    original_tables = len(table_indices)

    if original_tables <= max_tables:
        return TableOverflowResult(
            text=text,
            original_tables=original_tables,
            tables_remaining=original_tables,
            compacted=False,
        )

    notice_added = False
    result_parts: list[str] = []
    for i, block in enumerate(blocks):
        if block.kind == "table":
            table_number = table_indices.index(i) + 1
            if table_number > max_tables:
                if not notice_added:
                    result_parts.append(
                        "\n> 后续表格已转换为紧凑字段列表，以兼容飞书卡片限制；内容完整保留。\n\n"
                    )
                    notice_added = True
                result_parts.append(_compact_table(block.text, table_number))
                continue
        result_parts.append(block.text)

    return TableOverflowResult(
        text="".join(result_parts),
        original_tables=original_tables,
        tables_remaining=max_tables,
        compacted=True,
    )

def _compact_table(table_text: str, table_number: int) -> str:
    lines = table_text.splitlines()
    if len(lines) < 2:
        return table_text
    header = _parse_markdown_row(lines[0])
    if not header:
        return table_text
    compact_lines: list[str] = []
    row_count = 1
    for row in lines[2:]:
        if not row.strip():
            continue
        cells = _parse_markdown_row(row)
        if not cells:
            continue
        compact_lines.append(f"**Table {table_number} · Row {row_count}**")
        for i, cell in enumerate(cells):
            col_name = header[i] if i < len(header) else f"Column {i+1}"
            compact_lines.append(f"- {col_name}: {cell.strip()}")
        compact_lines.append("")
        row_count += 1
    return "\n".join(compact_lines) + "\n"


def _downgrade_tables(text: str, limit: int = _MAX_CARD_TABLES) -> str:
    """
    超级防爆表格降级: 超过 limit 的表格不再加 ```, 而是转为文本列表
    """
    if '|' not in text:
        return text
    
    try:
        # 调用新引擎进行降级
        result = transform_table_overflow(text, mode="compact", max_tables=limit)
        return result.text
    except Exception as e:
        _logger.warning("嘟嘟防爆引擎降级表格失败，回退原文: %s", e)
        return text

def _strip_invalid_image_keys(text: str) -> str:
    """移除非 img_ 前缀的图片引用."""
    if "![" not in text:
        return text

    def _replace(m: re.Match) -> str:
        return m.group(0) if m.group(2).startswith("img_") else ""

    return _RE_IMAGE_REF.sub(_replace, text)

def escape_markdown_asterisks(text: str) -> str:
    """飞书 Markdown 解析器比 CommonMark 更激进——会把 2*4000+4*3000"""
    if '\x00' in text:
        text = text.replace('\x00', '')

    if '*' not in text:
        return text

    _protected: list[str] = []

    def _save(m: re.Match) -> str:
        _protected.append(m.group(0))
        return f'\x00P{len(_protected) - 1}P\x00'

    # Step 1: 保护代码区域
    text = _RE_FENCED_CODE.sub(_save, text)
    text = _RE_INLINE_CODE.sub(_save, text)

    # Step 2: 保护粗体 **...** 和 ***...***
    text = _RE_BOLD.sub(_save, text)

    text = _RE_VALID_ITALIC.sub(_save, text)

    # Step 4: 转义剩余 *（飞书可能误配对的）
    text = _RE_UNPAIRED_ASTERISK.sub(r'\\*', text)

    if _protected:
        for i in range(len(_protected) - 1, -1, -1):
            text = text.replace(f'\x00P{i}P\x00', _protected[i])

    # Null bytes render as boxes (□) in Feishu and must never reach the API.
    if '\x00' in text:
        text = text.replace('\x00', '')

    return text

def optimize_markdown_style(text: str) -> str:
    """1. 提取代码块用占位符保护"""
    if len(text) < 100 and not _RE_SHORT_MD_CHECK.search(text):
        return text
    try:
        # 1. 提取代码块
        mark = "___CB_"
        code_blocks: list[str] = []

        def _extract(m: re.Match) -> str:
            prefix = m.group(1) or ""
            block = m.group(0)[len(prefix) :]
            idx = len(code_blocks)
            code_blocks.append(block)
            return f"{prefix}{mark}{idx}___"

        r = _RE_CODE_BLOCK_EXTRACT.sub(_extract, text)

        # 2. 标题降级（仅当存在 H1-H3 时）
        if _RE_H1_TO_H3.search(text):
            r = _RE_HEADING_DEMOTE.sub(r'##### \1', r)
            r = _RE_H1_DEMOTE.sub(r'#### \1', r)

        # 3. 还原代码块
        for i, block in enumerate(code_blocks):
            r = r.replace(f"{mark}{i}___", block)

        # 4. 压缩多余空行
        r = _RE_MULTI_NEWLINE.sub("\n\n", r)

        # 5. 剥离无效图片 key
        r = _strip_invalid_image_keys(r)

        return r
    except Exception:
        _logger.debug("optimize_markdown_style failed", exc_info=True)
        return text


# ==========================================
# 【嘟嘟定制 v23.1】贝氏智能长文代码块保护切片引擎
# ==========================================
import re

LIST_BOUNDARY_RE = re.compile(r"(\n[ \t]*[-*+]\s|\n[ \t]*\d+\.\s)")

def _adjust_split_for_inline_code(text: str, split_at: int) -> int:
    prefix = text[:split_at]
    if prefix.count("`") % 2 == 0:
        return split_at
    before_code = text.rfind("`", 0, split_at)
    while before_code > 0:
        if text[:before_code].count("`") % 2 == 0:
            return before_code
        before_code = text.rfind("`", 0, before_code)
    return 0

def _separator_split_index(text: str, separator: str) -> int:
    index = text.rfind(separator)
    if index <= 0:
        return 0
    return index + len(separator)

def _safe_plain_split_index(text: str, max_block_size: int) -> int:
    window = text[: max_block_size + 1]
    candidate_groups = (
        sorted({match.start() + 1 for match in LIST_BOUNDARY_RE.finditer(window)}, reverse=True),
        [_separator_split_index(window, "\n\n")],
        [_separator_split_index(window, "\n")],
        [_separator_split_index(window, " ")],
    )
    for candidates in candidate_groups:
        for split_at in candidates:
            if split_at <= 0:
                continue
            safe_split = _adjust_split_for_inline_code(window, split_at)
            if safe_split > 0:
                return safe_split
    return max_block_size

def _split_long_text(text: str, limit: int = _MAX_CHUNK_CHARS) -> list[str]:
    """将超长文本按段落/换行拆分为多个不超过 limit 字符的块 (嘟嘟智能防爆版)."""
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    remaining = text
    while len(remaining) > limit:
        split_at = _safe_plain_split_index(remaining, limit)
        chunks.append(remaining[:split_at])
        remaining = remaining[split_at:]
    if remaining:
        chunks.append(remaining)
    return chunks


