(() => {
  "use strict";
  const script = document.currentScript;
  if (!script || document.querySelector("xraydent-support-widget")) return;

  const origin = new URL(script.src, window.location.href).origin;
  const apiUrl = (script.dataset.apiUrl || origin).replace(/\/$/, "");
  const position = script.dataset.position === "left" ? "left" : "right";
  const theme = script.dataset.theme === "dark" ? "dark" : "light";
  const sessionId = (crypto.randomUUID && crypto.randomUUID()) || `session-${Date.now()}`;

  class XRayDentWidget extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: "open" });
      this.history = [];
      this.opened = false;
      this.busy = false;
      this.render();
    }

    render() {
      const side = position === "left" ? "left: 22px" : "right: 22px";
      const dark = theme === "dark";
      this.shadowRoot.innerHTML = `
        <style>
          :host { --blue:#246bfd; --blue2:#0c4fe6; --ink:${dark ? "#eef5ff" : "#14213d"};
            --muted:${dark ? "#a7b5cc" : "#667085"}; --panel:${dark ? "#13213a" : "#fff"};
            --soft:${dark ? "#1d2d49" : "#f2f6fd"}; --line:${dark ? "#30415f" : "#dce5f2"};
            position:fixed; z-index:2147483000; ${side}; bottom:22px; font-family:Inter,Segoe UI,Arial,sans-serif;
            color:var(--ink); font-size:14px; line-height:1.45; }
          * { box-sizing:border-box; }
          button,input,textarea,select { font:inherit; }
          .launcher { width:58px; height:58px; margin-left:auto; border:0; border-radius:50%; color:#fff;
            background:linear-gradient(145deg,var(--blue),var(--blue2)); box-shadow:0 12px 30px #1747a84d;
            display:grid; place-items:center; cursor:pointer; transition:transform .18s ease; }
          .launcher:hover { transform:translateY(-2px); } .launcher:focus-visible,.icon:focus-visible,.send:focus-visible { outline:3px solid #9dbbff; outline-offset:2px; }
          .launcher svg { width:27px; height:27px; }
          .panel { position:absolute; bottom:72px; ${position === "left" ? "left:0" : "right:0"}; width:min(390px,calc(100vw - 28px));
            height:min(620px,calc(100vh - 112px)); background:var(--panel); border:1px solid var(--line); border-radius:22px;
            box-shadow:0 24px 70px #16294d38; overflow:hidden; display:none; flex-direction:column; transform-origin:bottom ${position}; }
          .panel.open { display:flex; animation:appear .18s ease-out; } @keyframes appear { from {opacity:0;transform:translateY(10px) scale(.98)} }
          .header { padding:16px 16px 14px; color:#fff; background:linear-gradient(125deg,#0f4dc4,#2c7cf6); display:flex; align-items:center; gap:11px; }
          .brand { width:38px;height:38px;border-radius:12px;background:#ffffff20;display:grid;place-items:center;font-weight:800;font-size:18px; }
          .title { flex:1; } .title strong {display:block;font-size:15px} .title span {font-size:12px;color:#dbe8ff;display:flex;align-items:center;gap:6px}
          .dot {width:7px;height:7px;border-radius:50%;background:#6ee7a5;box-shadow:0 0 0 3px #6ee7a533}
          .icon { width:34px;height:34px;border:0;border-radius:10px;color:#fff;background:#ffffff16;cursor:pointer;font-size:20px; }
          .messages { flex:1; overflow:auto; padding:17px 14px 10px; scroll-behavior:smooth; background:linear-gradient(180deg,var(--soft),var(--panel) 25%); }
          .row { display:flex; gap:8px; margin:0 0 12px; align-items:flex-end; } .row.user {justify-content:flex-end}
          .avatar {width:25px;height:25px;flex:0 0 25px;border-radius:9px;background:#e5edff;color:#245edb;display:grid;place-items:center;font-size:11px;font-weight:800}
          .bubble { max-width:84%; border:1px solid var(--line); background:var(--panel); border-radius:17px 17px 17px 5px; padding:10px 12px; white-space:pre-wrap; }
          .user .bubble {color:#fff;background:var(--blue);border-color:var(--blue);border-radius:17px 17px 5px 17px}
          .meta { margin-top:8px;padding-top:7px;border-top:1px solid var(--line);font-size:11px;color:var(--muted) }
          details summary {cursor:pointer;list-style:none;color:#336fe1;font-weight:600} details p {margin:5px 0 0}
          .actions {display:flex;gap:5px;margin-top:8px}.rate {border:1px solid var(--line);background:var(--panel);color:var(--muted);border-radius:8px;padding:3px 7px;cursor:pointer}.rate.done{color:#27764f;border-color:#83c9a7}
          .typing {display:flex;gap:4px;padding:6px 2px}.typing i{width:6px;height:6px;background:#8ba2c5;border-radius:50%;animation:blink 1s infinite}.typing i:nth-child(2){animation-delay:.15s}.typing i:nth-child(3){animation-delay:.3s}@keyframes blink{50%{opacity:.25;transform:translateY(-2px)}}
          .chips {padding:0 14px 10px;display:flex;gap:7px;overflow:auto;scrollbar-width:none}.chip{white-space:nowrap;border:1px solid #bad0fb;color:#245fcf;background:${dark ? "#192d50" : "#f5f8ff"};border-radius:999px;padding:7px 10px;cursor:pointer;font-size:12px}
          .composer {padding:10px 12px 12px;border-top:1px solid var(--line);background:var(--panel)} .inputrow{display:flex;align-items:flex-end;gap:8px}
          textarea {flex:1;min-height:42px;max-height:100px;resize:none;border:1px solid var(--line);background:var(--soft);color:var(--ink);border-radius:13px;padding:10px 11px;outline:none}
          textarea:focus{border-color:#77a0f4;box-shadow:0 0 0 3px #77a0f426}.send{width:42px;height:42px;border:0;border-radius:13px;background:var(--blue);color:#fff;cursor:pointer}.send:disabled{opacity:.45;cursor:default}
          .privacy{text-align:center;color:var(--muted);font-size:10px;margin-top:6px}.support-link{color:#2a67d6;background:none;border:0;padding:0;cursor:pointer;text-decoration:underline}
          .support {position:absolute;inset:0;background:var(--panel);z-index:3;display:none;flex-direction:column}.support.open{display:flex}.support-body{padding:18px;overflow:auto}.support h3{margin:0 0 7px;font-size:18px}.support p{color:var(--muted);font-size:12px}
          label{display:block;font-size:12px;font-weight:700;margin:14px 0 6px}select,.support textarea{width:100%;border:1px solid var(--line);border-radius:11px;background:var(--soft);color:var(--ink);padding:10px}.support textarea{min-height:125px}
          .warning{border-radius:11px;background:#fff6df;color:#724f00;padding:10px;font-size:11px}.primary{width:100%;border:0;border-radius:11px;padding:11px;background:var(--blue);color:#fff;font-weight:700;cursor:pointer;margin-top:12px}
          @media(max-width:520px){:host{${position}:8px;bottom:8px}.panel{position:fixed;inset:8px;width:auto;height:auto;border-radius:18px}.launcher{width:54px;height:54px}}
          @media(prefers-reduced-motion:reduce){*{animation:none!important;scroll-behavior:auto!important;transition:none!important}}
        </style>
        <section class="panel" role="dialog" aria-label="Чат поддержки X-RayDent" aria-hidden="true">
          <header class="header"><div class="brand">X</div><div class="title"><strong>Помощник X-RayDent</strong><span><i class="dot"></i> Локальная тестовая версия</span></div><button class="icon close" aria-label="Закрыть">×</button></header>
          <main class="messages" aria-live="polite"></main>
          <div class="chips"><button class="chip">Что такое X-RayDent?</button><button class="chip">Как загрузить снимок?</button><button class="chip">Не открывается PDF</button></div>
          <footer class="composer"><div class="inputrow"><textarea maxlength="2000" rows="1" placeholder="Напишите вопрос…" aria-label="Ваш вопрос"></textarea><button class="send" aria-label="Отправить">➤</button></div><div class="privacy">Не отправляйте персональные или медицинские данные · <button class="support-link">Поддержка</button></div></footer>
          <section class="support" aria-label="Демо-обращение"><header class="header"><button class="icon back" aria-label="Назад">‹</button><div class="title"><strong>Связаться с поддержкой</strong><span>Демонстрационная форма</span></div></header><div class="support-body"><h3>Опишите ситуацию</h3><p>Форма проверит обращение, но ничего не отправит и не сохранит.</p><div class="warning">Не указывайте пароли, коды, ФИО пациента, снимки или медицинские документы.</div><label for="category">Категория</label><select id="category"><option value="technical">Техническая проблема</option><option value="service">Работа сервиса</option><option value="report">Отчёт</option><option value="access">Доступ</option><option value="payment">Оплата</option><option value="other">Другое</option></select><label for="description">Описание без персональных данных</label><textarea id="description" maxlength="1000" placeholder="На какой странице и после какого действия возникла проблема?"></textarea><button class="primary submit-support">Проверить демо-обращение</button><p class="support-status" role="status"></p></div></section>
        </section>
        <button class="launcher" aria-label="Открыть чат" aria-expanded="false"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a4 4 0 0 1-4 4H8l-5 3 1.7-5.1A7 7 0 0 1 3 12V8a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4z"/><path d="M8 10h.01M12 10h.01M16 10h.01"/></svg></button>`;
      this.$ = (q) => this.shadowRoot.querySelector(q);
      this.$(".launcher").addEventListener("click", () => this.toggle());
      this.$(".close").addEventListener("click", () => this.toggle(false));
      this.$(".send").addEventListener("click", () => this.send());
      this.$("textarea").addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); this.send(); } });
      this.shadowRoot.querySelectorAll(".chip").forEach((b) => b.addEventListener("click", () => { this.$("textarea").value = b.textContent; this.send(); }));
      this.$(".support-link").addEventListener("click", () => this.$(".support").classList.add("open"));
      this.$(".back").addEventListener("click", () => this.$(".support").classList.remove("open"));
      this.$(".submit-support").addEventListener("click", () => this.submitSupport());
      this.addMessage("assistant", "Здравствуйте! Я помогу разобраться с X-RayDent: загрузкой ОПТГ, отчётами, доступом и техническими вопросами. Что хотите узнать?");
    }

    toggle(force) {
      this.opened = typeof force === "boolean" ? force : !this.opened;
      this.$(".panel").classList.toggle("open", this.opened);
      this.$(".panel").setAttribute("aria-hidden", String(!this.opened));
      this.$(".launcher").setAttribute("aria-expanded", String(this.opened));
      if (this.opened) setTimeout(() => this.$("textarea").focus(), 30);
    }

    addMessage(role, text, data) {
      const row = document.createElement("div"); row.className = `row ${role}`;
      if (role === "assistant") { const avatar = document.createElement("div"); avatar.className = "avatar"; avatar.textContent = "XR"; row.append(avatar); }
      const bubble = document.createElement("div"); bubble.className = "bubble"; bubble.textContent = text; row.append(bubble);
      if (data && role === "assistant") {
        const meta = document.createElement("div"); meta.className = "meta";
        const label = data.source_type === "faq" ? `По базе X-RayDent · уверенность ${Math.round(data.confidence * 100)}%` : data.source_type === "general" ? "Общий ответ — не из справки X-RayDent" : data.source_type === "safety" ? "Правило безопасности" : "Режим без локальной LLM";
        meta.textContent = label;
        if (data.sources && data.sources.length) { const details = document.createElement("details"); const summary = document.createElement("summary"); summary.textContent = "Показать источники"; details.append(summary); data.sources.forEach((s) => { const p = document.createElement("p"); p.textContent = `FAQ #${s.id}: ${s.question}`; details.append(p); }); meta.append(details); }
        const actions = document.createElement("div"); actions.className = "actions"; ["up", "down"].forEach((rating) => { const b = document.createElement("button"); b.className = "rate"; b.textContent = rating === "up" ? "Полезно" : "Не помогло"; b.addEventListener("click", () => this.rate(b, data.response_id, rating)); actions.append(b); }); meta.append(actions); bubble.append(meta);
      }
      this.$(".messages").append(row); this.$(".messages").scrollTop = this.$(".messages").scrollHeight; return row;
    }

    async send() {
      const input = this.$(".composer textarea"); const message = input.value.trim(); if (!message || this.busy) return;
      this.busy = true; this.$(".send").disabled = true; input.value = ""; this.addMessage("user", message);
      const typing = this.addMessage("assistant", ""); typing.querySelector(".bubble").innerHTML = '<span class="typing"><i></i><i></i><i></i></span>';
      try {
        const response = await fetch(`${apiUrl}/api/chat`, { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({message,session_id:sessionId,history:this.history.slice(-6)}) });
        if (!response.ok) throw new Error(`HTTP ${response.status}`); const data = await response.json(); typing.remove(); this.addMessage("assistant", data.answer, data);
        this.history.push({role:"user",content:message},{role:"assistant",content:data.answer}); this.history = this.history.slice(-6);
      } catch (error) { typing.remove(); this.addMessage("assistant", "Не удалось связаться с локальным сервером. Проверьте, что backend запущен, и попробуйте ещё раз."); }
      finally { this.busy = false; this.$(".send").disabled = false; input.focus(); }
    }

    async rate(button, responseId, rating) { try { await fetch(`${apiUrl}/api/feedback`, {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({response_id:responseId,rating})}); button.parentElement.querySelectorAll("button").forEach((b) => b.disabled = true); button.classList.add("done"); button.textContent = "Спасибо"; } catch (_) {} }

    async submitSupport() {
      const status = this.$(".support-status"); const description = this.$("#description").value.trim(); status.textContent = "Проверяем…";
      try { const response = await fetch(`${apiUrl}/api/support/demo`, {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({category:this.$("#category").value,description})}); const data = await response.json(); if (!response.ok) throw new Error(data.detail || "Проверьте описание"); status.textContent = data.message; this.$("#description").value = ""; } catch (e) { status.textContent = e.message; }
    }
  }
  customElements.define("xraydent-support-widget", XRayDentWidget);
  document.body.append(document.createElement("xraydent-support-widget"));
})();
