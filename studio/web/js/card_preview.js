/**
 * aiduPOP Visual Studio — 1:1 Feishu CardKit 2.0 DOM Simulator
 */

// v2.3.1: HTML escape — 配置值一律转义后再进 innerHTML，杜绝注入
function escapeHtml(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

const CardPreview = {
  mode: "completed", // 'completed' | 'streaming'
  panelExpanded: false,
  userToggled: false,   // true once the user manually expands/collapses in preview

  render(state) {
    const cardEl = document.getElementById("feishuCardContent");
    if (!cardEl) return;

    const theme = state.theme || {};
    const thPanel = theme.panel || {
      model_prefix: "👸🏻",
      rounds_icon: "🌊",
      tools_icon: "🫧",
      elapsed_icon: "✨",
      separator: " · "
    };
    const toolIcons = theme.tool_icons || {};
    const collapseIcon = theme.collapse_icon || "💦";
    const roundIcon = theme.round_icon || "🌊";
    const footerCfg = state.footer || {};
    const thFooter = theme.footer || {
      model_prefix: "⚕",
      reasoning_icon: "🫧"
    };

    // 1. Panel Header 统计组装
    const modelStr = "claude-opus-5";
    const parts = [
      `${thPanel.model_prefix || ""}${modelStr}`,
      `${thPanel.rounds_icon || ""}1`,
      `${thPanel.tools_icon || ""}3`,
      `${thPanel.elapsed_icon || ""}1.4s`
    ];
    const statsText = parts.join(thPanel.separator || " · ");

    // 2. 模拟工具步
    const demoSteps = [
      { tool: "read", title: "读取文件", detail: "cardkit/theme.py" },
      { tool: "exec", title: "执行命令", detail: "git status --short" },
      { tool: "write", title: "修改代码", detail: "studio/server.py" }
    ];

    let stepsHtml = "";
    demoSteps.forEach(s => {
      const icon = toolIcons[s.tool] || "👩🏻‍🔧";
      stepsHtml += `
        <div class="tool-step-item">
          <span class="tool-step-icon">${escapeHtml(icon)}</span>
          <span class="tool-step-text"><b class="tool-step-title">${escapeHtml(s.title)}</b> <code>${escapeHtml(s.detail)}</code></span>
        </div>
      `;
    });

    // 展开状态：优先用用户在预览里的手动切换（userToggled），否则跟随配置，
    // 流式模式跟随 streaming_panel_expanded，终态跟随 panel_expanded。
    const configExpanded = this.mode === "streaming"
      ? !!state.streaming_panel_expanded
      : !!state.panel_expanded;
    const isExpanded = this.userToggled ? this.panelExpanded : configExpanded;

    // 3. 正文内容（根据模式展示）
    let bodyHtml = "";
    if (this.mode === "streaming") {
      bodyHtml = `
        <div class="card-content-body">
          <p>正在为您分析 aiduPOP 的可视化配置工作坊... 正在处理 CardKit 2.0 节点<span class="card-cursor"></span></p>
        </div>
      `;
    } else {
      bodyHtml = `
        <div class="card-content-body">
          <p>你好！aiduPOP v${window.AIDUPOP_VERSION || "…"} 可视化配置工作坊已就绪。所有 Emoji、Panel 统计栏及 Footer 排布已实时同步。</p>
        </div>
      `;
    }

    // 4. Panel DOM
    const panelHtml = `
      <div class="card-panel ${isExpanded ? 'expanded' : ''}" id="simPanel">
        <div class="card-panel-header" onclick="CardPreview.togglePanel()">
          <span class="card-panel-title">
            <span class="card-panel-arrow">▶</span>
            <span>${escapeHtml(statsText)}</span>
          </span>
          <span>展开 / 收起</span>
        </div>
        <div class="card-panel-body">
          <div class="card-collapse-hint">${escapeHtml(collapseIcon)} 还有 0 项已折叠</div>
          <div class="tool-steps-wrap">
            ${stepsHtml}
          </div>
        </div>
      </div>
    `;

    // 5. Footer 渲染
    let footerHtml = "";
    const showLabel = !!footerCfg.show_label;
    const fieldsMatrix = footerCfg.fields || [];

    if (Array.isArray(fieldsMatrix) && fieldsMatrix.length > 0) {
      const footerLines = [];
      fieldsMatrix.forEach(row => {
        if (!Array.isArray(row)) return;
        const rowParts = [];
        row.forEach(field => {
          if (field === "model") {
            rowParts.push(`${thFooter.model_prefix || ""}${modelStr}`);
          } else if (field === "tokens") {
            const tokStr = `↑ 1.2k ↓ 3.8k ${thFooter.reasoning_icon || ""} 420`;
            rowParts.push(tokStr);
          } else if (field === "elapsed") {
            rowParts.push(showLabel ? "耗时: 1.4s" : "1.4s");
          } else if (field === "status") {
            rowParts.push("已完成");
          } else if (field === "context") {
            rowParts.push(showLabel ? "上下文: 48k/200k" : "48k/200k (24%)");
          }
        });
        if (rowParts.length > 0) {
          footerLines.push(rowParts.join(" · "));
        }
      });

      if (footerLines.length > 0) {
        footerHtml = `
          <div class="card-hr"></div>
          <div class="card-footer">
            ${footerLines.map(l => `<div>${escapeHtml(l)}</div>`).join("")}
          </div>
        `;
      }
    }

    // 组装整张卡片（嘟嘟定制：无 header，正文置顶）
    cardEl.innerHTML = `
      <div class="feishu-card-inner">
        ${bodyHtml}
        ${panelHtml}
        ${footerHtml}
      </div>
    `;
  },

  togglePanel() {
    this.userToggled = true;
    this.panelExpanded = !this.panelExpanded;
    const panel = document.getElementById("simPanel");
    if (panel) {
      panel.classList.toggle("expanded", this.panelExpanded);
    }
  },

  setMode(mode) {
    this.mode = mode;
    this.userToggled = false;
    document.querySelectorAll(".btn-mode").forEach(btn => {
      btn.classList.toggle("active", btn.dataset.mode === mode);
    });
    if (window.App) {
      window.App.onStateChange();
    }
  }
};
