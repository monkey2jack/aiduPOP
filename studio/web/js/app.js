/**
 * aiduPOP Visual Studio — Application Controller
 */

// Emoji-only validator: rejects plain ASCII tokens (feishu standard_icon tokens),
// accepts pictographic emoji / symbols.
function isEmojiOnly(str) {
  if (!str || typeof str !== "string") return false;
  const s = str.trim();
  if (!s) return false;
  // Reject pure ASCII tokens like "tool_02" / "edit_outlined" (Feishu standard_icon tokens)
  if (/^[\x20-\x7e]+$/.test(s)) return false;
  // Otherwise treat as emoji / pictographic
  return true;
}

// v2.3.1: HTML escape — 配置值一律转义后再进 innerHTML，杜绝注入
function escapeHtml(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

window.App = {
  state: {
    enabled: true, linear: true,
    panel_expanded: false, streaming_panel_expanded: false,
    max_tool_steps: 20, flush_interval_ms: 200, print_step: 4,
    theme: {
      round_icon: "🌊", collapse_icon: "💦",
      tool_icons: {
        skill: "🤹🏻‍♀️", read: "👩🏻‍🏫", write: "👩🏻‍🎨", web_search: "🕵🏻‍♀️",
        web_fetch: "👩🏻‍🚀", grep: "👩🏻‍🔬", glob: "👮🏻‍♀️", exec: "👩🏻‍💻",
        browser: "🥷🏻", agent: "👷🏻‍♀️", check: "👩🏻‍⚖️", analyze: "👩🏻‍🎓", fallback: "👩🏻‍🔧"
      },
      panel: { model_prefix: "👸🏻", rounds_icon: "🌊", tools_icon: "🫧", elapsed_icon: "✨", separator: " · " },
      footer: { model_prefix: "⚕", reasoning_icon: "🫧" }
    },
    footer: { show_label: false, fields: [] },
    // v2.3.1: 空映射 = 不写入 text_sizes，沿用插件内置默认（normal_v2 等
    // 历史默认值不在 CardKit 2.0 白名单内，写入会被运行时拒绝）
    text_sizes: {}
  },

  presets: {},
  currentPickTarget: null,

  async loadVersion() {
    // 版本单一真相源 = plugin.yaml，经 /api/health 注入前端（禁止硬编码）
    try {
      const res = await fetch("/api/health");
      const json = await res.json();
      if (json && json.version) {
        window.AIDUPOP_VERSION = json.version;
        const badge = document.getElementById("badgeVersion");
        if (badge) badge.textContent = "v" + json.version;
      }
    } catch (e) {
      console.warn("version probe failed:", e);
    }
  },

  async init() {
    this.loadVersion();
    this.renderPresetBtns();
    this.renderEmojiRows();
    this.renderEmojiModal();
    this.renderFooterTags();
    this.bindEvents();
    try {
      await this.loadPresets();
      await this.loadConfig();
    } catch (e) {
      console.warn("API unavailable, using local defaults:", e);
      this.syncFormFromState();
      this.onStateChange();
    }
  },

  // ── Emoji swap widget: 当前 → 替换 ──
  emojiSwapHtml(slotId, currentVal) {
    const safeSlot = escapeHtml(slotId);
    const safeVal = escapeHtml(currentVal || "");
    return `
      <div class="emoji-current">
        <span class="emoji-mini-label now">当前</span>
        <span class="emoji-display-now" data-now="${safeSlot}">${safeVal || "—"}</span>
      </div>
      <span class="emoji-arrow">→</span>
      <div class="emoji-next">
        <span class="emoji-mini-label next">替换</span>
        <input type="text" class="emoji-input" data-emoji-slot="${safeSlot}" value="${safeVal}"
               placeholder="😀" title="仅接受 Emoji，可手动输入" />
      </div>
      <button class="btn-pick" data-pick="${safeSlot}" title="打开 Emoji 挑选器">🎨</button>
    `;
  },

  renderEmojiRows() {
    // Tools
    const toolWrap = document.getElementById("toolRows");
    if (toolWrap) {
      toolWrap.innerHTML = TOOL_DEFINITIONS.map(t => `
        <div class="emoji-row compact">
          <div class="emoji-row-info">
            <span class="emoji-row-label">${t.label}</span>
          </div>
          <div class="emoji-swap">${this.emojiSwapHtml("tool:" + t.key, this.state.theme.tool_icons[t.key] || "")}</div>
        </div>
      `).join("");
    }

    // Misc round/collapse
    const miscWrap = document.getElementById("miscIconRows");
    if (miscWrap) {
      miscWrap.innerHTML = [
        { slot: "path:theme.round_icon", label: "推理轮次标题图标", hint: "轮次标题前缀", val: this.state.theme.round_icon },
        { slot: "path:theme.collapse_icon", label: "折叠提示图标", hint: "「还有 N 项已折叠」", val: this.state.theme.collapse_icon }
      ].map(r => `
        <div class="emoji-row compact">
          <div class="emoji-row-info">
            <span class="emoji-row-label">${r.label}</span>
          </div>
          <div class="emoji-swap">${this.emojiSwapHtml(r.slot, r.val || "")}</div>
        </div>
      `).join("");
    }

    // Panel icons
    const panelWrap = document.getElementById("panelIconRows");
    if (panelWrap) {
      panelWrap.innerHTML = [
        { slot: "path:theme.panel.rounds_icon", label: "轮次数图标 (rounds_icon)", hint: "轮次计数值前（默认 🫧）", val: this.state.theme.panel.rounds_icon },
        { slot: "path:theme.panel.tools_icon", label: "工具数图标 (tools_icon)", hint: "工具调用步数前（默认 ✨）", val: this.state.theme.panel.tools_icon },
        { slot: "path:theme.panel.elapsed_icon", label: "耗时图标 (elapsed_icon)", hint: "总耗时前（默认 🎶）", val: this.state.theme.panel.elapsed_icon }
      ].map(r => `
        <div class="emoji-row">
          <div class="emoji-row-info">
            <span class="emoji-row-label">${r.label}</span>
            <span class="emoji-row-hint">${r.hint}</span>
          </div>
          <div class="emoji-swap">${this.emojiSwapHtml(r.slot, r.val || "")}</div>
        </div>
      `).join("");
    }

    // Footer icon
    const footerWrap = document.getElementById("footerIconRows");
    if (footerWrap) {
      footerWrap.innerHTML = `
        <div class="emoji-row">
          <div class="emoji-row-info">
            <span class="emoji-row-label">推理 Token 图标 (reasoning_icon)</span>
            <span class="emoji-row-hint">底部展示推理消耗 Token 时的前缀（默认 🫧）</span>
          </div>
          <div class="emoji-swap">${this.emojiSwapHtml("path:theme.footer.reasoning_icon", this.state.theme.footer.reasoning_icon || "")}</div>
        </div>
      `;
    }
  },

  renderPresetBtns() {
    const wrap = document.getElementById("presetBtns");
    if (!wrap) return;
    wrap.style.display = "inline-flex";
    wrap.style.gap = "8px";
    wrap.style.flexWrap = "wrap";
  },

  renderEmojiModal() {
    const body = document.getElementById("emojiModalBody");
    if (!body) return;
    body.innerHTML = EMOJI_CATEGORIES.map(cat => `
      <div class="emoji-cat-title">${escapeHtml(cat.name)}</div>
      <div class="emoji-grid">
        ${cat.emojis.map(e => `<button class="emoji-btn" data-emoji="${escapeHtml(e)}">${escapeHtml(e)}</button>`).join("")}
      </div>
    `).join("");
    body.querySelectorAll(".emoji-btn").forEach(btn => {
      btn.addEventListener("click", () => this.selectEmoji(btn.dataset.emoji));
    });
  },

  bindEvents() {
    // Emoji input (manual, emoji-only validated)
    document.addEventListener("input", (e) => {
      const slot = e.target.dataset.emojiSlot;
      if (slot) {
        const val = e.target.value.trim();
        if (val === "" || isEmojiOnly(val)) {
          e.target.classList.remove("invalid");
          this.setSlotValue(slot, val);
          this.updateNowDisplay(slot, val);
          this.onStateChange();
        } else {
          e.target.classList.add("invalid");
          this.toast("仅接受 Emoji，请勿输入普通文字或字母", "error");
        }
        return;
      }
      const prop = e.target.dataset.prop;
      if (prop) {
        let v = e.target.value;
        if (e.target.type === "number") v = e.target.value;
        this.setDeepProp(this.state, prop, v);
        this.onStateChange();
      }
    });

    document.addEventListener("change", (e) => {
      const boolProp = e.target.dataset.bool;
      if (boolProp) {
        this.setDeepProp(this.state, boolProp, e.target.checked);
        this.onStateChange();
      }
      const selProp = e.target.dataset.prop;
      if (selProp && e.target.tagName === "SELECT") {
        this.setDeepProp(this.state, selProp, e.target.value);
        this.onStateChange();
      }
    });

    // Emoji picker trigger
    document.addEventListener("click", (e) => {
      const pick = e.target.dataset.pick;
      if (pick) this.openEmojiPicker(pick);
    });

    // Tabs
    document.querySelectorAll(".tab-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
        document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
        btn.classList.add("active");
        const target = document.getElementById(btn.dataset.tab);
        if (target) target.classList.add("active");
      });
    });
  },

  // slot format: "tool:<key>" or "path:<dot.path>"
  setSlotValue(slot, val) {
    if (slot.startsWith("tool:")) {
      this.state.theme.tool_icons[slot.slice(5)] = val;
    } else if (slot.startsWith("path:")) {
      this.setDeepProp(this.state, slot.slice(5), val);
    }
  },
  getSlotValue(slot) {
    if (slot.startsWith("tool:")) return this.state.theme.tool_icons[slot.slice(5)] || "";
    if (slot.startsWith("path:")) {
      const parts = slot.slice(5).split(".");
      let v = this.state;
      for (const p of parts) v = v?.[p];
      return v || "";
    }
    return "";
  },
  updateNowDisplay(slot, val) {
    const nowEl = document.querySelector(`[data-now="${CSS.escape(slot)}"]`);
    // 当前显示反映生效值；替换预览后即为新的当前
    if (nowEl) nowEl.textContent = val || "—";
  },

  setDeepProp(obj, path, value) {
    const parts = path.split(".");
    let curr = obj;
    for (let i = 0; i < parts.length - 1; i++) {
      if (!curr[parts[i]]) curr[parts[i]] = {};
      curr = curr[parts[i]];
    }
    curr[parts[parts.length - 1]] = value;
  },

  async loadConfig() {
    const res = await fetch("/api/config");
    const json = await res.json();
    if (json.ok && json.data) {
      const d = json.data;
      this.state.enabled = d.enabled;
      this.state.linear = d.linear;
      this.state.panel_expanded = d.panel_expanded;
      this.state.streaming_panel_expanded = d.streaming_panel_expanded;
      this.state.max_tool_steps = d.max_tool_steps;
      this.state.flush_interval_ms = d.flush_interval_ms;
      this.state.print_step = d.print_step;
      this.state.theme = d.theme || this.state.theme;
      this.state.footer = d.footer || this.state.footer;
      // v2.3.1: 只保留非空字号值；空映射 = 下拉框显示「默认」
      const ts = d.text_sizes || {};
      this.state.text_sizes = Object.fromEntries(
        Object.entries(ts).filter(([, v]) => typeof v === "string" && v !== "")
      );
      this.renderEmojiRows();
      this.syncFormFromState();
      this.onStateChange();
      this.toast("已加载当前网关配置", "success");
    }
  },

  async loadPresets() {
    const res = await fetch("/api/presets");
    const json = await res.json();
    if (json.ok && json.data) {
      this.presets = json.data;
      const wrap = document.getElementById("presetBtns");
      if (wrap) {
        wrap.innerHTML = Object.values(this.presets).map(p =>
          `<button class="preset-btn" data-preset="${escapeHtml(p.id)}" title="${escapeHtml(p.desc)}">${escapeHtml(p.name)}</button>`
        ).join("");
        wrap.querySelectorAll(".preset-btn").forEach(btn => {
          btn.addEventListener("click", () => this.applyPreset(btn.dataset.preset));
        });
      }
    }
  },

  applyPreset(presetId) {
    if (!presetId || !this.presets[presetId]) return;
    const p = this.presets[presetId];
    this.state.theme = JSON.parse(JSON.stringify(p.theme));
    this.renderEmojiRows();
    this.syncFormFromState();
    this.onStateChange();
    document.querySelectorAll(".preset-btn").forEach(b =>
      b.classList.toggle("active", b.dataset.preset === presetId));
    this.toast(`已应用预设：${p.name}`, "success");
  },

  syncFormFromState() {
    document.querySelectorAll("input[data-prop], select[data-prop]").forEach(input => {
      const parts = input.dataset.prop.split(".");
      let val = this.state;
      for (const p of parts) val = val?.[p];
      if (val !== undefined && val !== null) input.value = val;
    });
    document.querySelectorAll("input[data-bool]").forEach(input => {
      const parts = input.dataset.bool.split(".");
      let val = this.state;
      for (const p of parts) val = val?.[p];
      input.checked = !!val;
    });
    document.querySelectorAll("input[data-emoji-slot]").forEach(input => {
      input.value = this.getSlotValue(input.dataset.emojiSlot);
    });
    this.renderFooterTags();
  },

  renderFooterTags() {
    const container = document.getElementById("footerTagsWrap");
    if (!container) return;
    const allFields = [
      { id: "model", name: "模型名称" }, { id: "tokens", name: "Token 吞吐" },
      { id: "elapsed", name: "运行耗时" }, { id: "status", name: "完成状态" },
      { id: "context", name: "上下文容量" }
    ];
    const active = new Set();
    (this.state.footer?.fields || []).forEach(row => {
      if (Array.isArray(row)) row.forEach(f => active.add(f));
    });
    container.innerHTML = allFields.map(f =>
      `<span class="footer-tag ${active.has(f.id) ? 'active' : ''}" data-field="${escapeHtml(f.id)}">${active.has(f.id) ? '✓ ' : '+ '}${escapeHtml(f.name)} (${escapeHtml(f.id)})</span>`
    ).join("");
    container.querySelectorAll(".footer-tag").forEach(tag => {
      tag.addEventListener("click", () => this.toggleFooterField(tag.dataset.field));
    });
  },

  toggleFooterField(fieldId) {
    if (!this.state.footer) this.state.footer = { show_label: false, fields: [] };
    if (!Array.isArray(this.state.footer.fields)) this.state.footer.fields = [];
    if (this.state.footer.fields.length === 0) this.state.footer.fields.push([]);
    const row = this.state.footer.fields[0];
    const idx = row.indexOf(fieldId);
    if (idx >= 0) row.splice(idx, 1);
    else row.push(fieldId);
    this.state.footer.fields = this.state.footer.fields.filter(r => r.length > 0);
    this.renderFooterTags();
    this.onStateChange();
  },

  onStateChange() {
    if (window.CardPreview) CardPreview.render(this.state);
  },

  openEmojiPicker(slot) { this.currentPickTarget = slot; document.getElementById("emojiModal").classList.add("open"); },
  closeEmojiPicker() { document.getElementById("emojiModal").classList.remove("open"); },
  selectEmoji(emoji) {
    if (!this.currentPickTarget) return;
    const slot = this.currentPickTarget;
    this.setSlotValue(slot, emoji);
    const input = document.querySelector(`input[data-emoji-slot="${CSS.escape(slot)}"]`);
    if (input) { input.value = emoji; input.classList.remove("invalid"); }
    this.updateNowDisplay(slot, emoji);
    this.closeEmojiPicker();
    this.onStateChange();
  },

  openPreview() {
    if (window.CardPreview) CardPreview.userToggled = false;
    this.onStateChange();
    document.getElementById("previewModal").classList.add("open");
  },
  closePreview() { document.getElementById("previewModal").classList.remove("open"); },

  async saveConfig() {
    try {
      // v2.3.1: 字号「默认」（空值）不进 payload，避免把非法/冗余值写进配置
      const textSizes = Object.fromEntries(
        Object.entries(this.state.text_sizes || {}).filter(([, v]) => v)
      );
      const payload = {
        enabled: this.state.enabled, linear: this.state.linear,
        panel_expanded: this.state.panel_expanded,
        streaming_panel_expanded: this.state.streaming_panel_expanded,
        max_tool_steps: parseInt(this.state.max_tool_steps) || 20,
        flush_interval_ms: parseFloat(this.state.flush_interval_ms) || 200,
        print_step: parseInt(this.state.print_step) || 4,
        theme: this.state.theme, footer: this.state.footer, text_sizes: textSizes
      };
      const res = await fetch("/api/config", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload)
      });
      const json = await res.json();
      // v2.3.1: 如实文案——配置写入磁盘即成功，但网关是独立进程，
      // 需 /aowen config reload 或重启网关后新卡片才按新配置渲染。
      this.toast(
        json.ok
          ? "✅ 配置已保存。在飞书群发送 /aowen config reload（或重启网关）后生效"
          : (json.error || "保存失败"),
        json.ok ? "success" : "error"
      );
    } catch (e) {
      this.toast(`保存请求失败: ${e.message}`, "error");
    }
  },

  async restartGateway() {
    if (!confirm("确定要重启 Hermes 网关服务吗？（通常热重载已生效，无需重启）")) return;
    try {
      const res = await fetch("/api/restart", { method: "POST" });
      const json = await res.json();
      const kind = json.ok ? (json.restarted === false ? "info" : "success") : "error";
      this.toast(json.ok ? json.message : (json.error || "重启失败"), kind);
    } catch (e) {
      this.toast(`重启请求失败: ${e.message}`, "error");
    }
  },

  toast(msg, type = "info") {
    const wrap = document.getElementById("toastWrap");
    if (!wrap) return;
    const el = document.createElement("div");
    el.className = `toast ${type}`;
    el.innerText = msg;
    wrap.appendChild(el);
    setTimeout(() => { el.style.opacity = "0"; setTimeout(() => el.remove(), 250); }, 2600);
  }
};

window.addEventListener("DOMContentLoaded", () => App.init());
