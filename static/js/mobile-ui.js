(function () {
  if (!window.matchMedia('(max-width: 960px)').matches) return;

(function () {
  const root = document.documentElement;
  const body = document.body;
  const topbar = document.querySelector("[data-topbar]");
  const backToTop = document.querySelector("[data-back-to-top]");
  const sidebar = document.querySelector("[data-sidebar]");
  const sidebarToggle = document.querySelector("[data-sidebar-toggle]");
  const sidebarBackdrop = document.querySelector("[data-sidebar-backdrop]");
  const themeToggle = document.querySelector("[data-theme-toggle]");
  const themeIcon = document.querySelector("[data-theme-icon]");
  const searchInput = document.querySelector("#topbar-search-input");
  const themeStorageKey = "nagham-theme";
  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const finePointer = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
  const compactDevice = window.matchMedia("(max-width: 960px)").matches;
  const enhancedMotionEnabled = !prefersReducedMotion && finePointer && !compactDevice;
  const performanceMode = root.getAttribute("data-performance") || "full";
  const liquidTargets = Array.from(
    document.querySelectorAll(
      ".liquid-surface, .liquid-control, .filters, .topbar-search, .profile-chip, .player-queue-item"
    )
  );
  const revealTargets = Array.from(
    document.querySelectorAll(
      ".hero-copy, .hero-panel, .section, .page-banner, .detail-panel, .announcement, .notice-banner, .showcase-panel"
    )
  );

  let ambientFrame = null;
  let ambientPointer = { x: 0.5, y: 0.5 };
  let scrollFrame = null;

  function safeStorageGet(key) {
    try {
      return localStorage.getItem(key);
    } catch (error) {
      return null;
    }
  }

  function safeStorageSet(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch (error) {
      return null;
    }
    return value;
  }

  function setTheme(theme) {
    root.setAttribute("data-theme", theme);
    if (themeIcon) {
      themeIcon.className = theme === "dark" ? "fa-solid fa-sun" : "fa-solid fa-moon";
    }
  }

  function getPreferredTheme() {
    const storedTheme = safeStorageGet(themeStorageKey);
    if (storedTheme === "light" || storedTheme === "dark") return storedTheme;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function applyPerformanceProfile() {
    const deviceMemory = Number(navigator.deviceMemory || 0);
    const hardwareThreads = Number(navigator.hardwareConcurrency || 0);
    const lowPowerDevice =
      compactDevice ||
      (deviceMemory > 0 && deviceMemory <= 4) ||
      (hardwareThreads > 0 && hardwareThreads <= 4);

    root.setAttribute("data-performance", lowPowerDevice ? "lite" : "full");
  }

  function openSidebar() {
    body.classList.add("sidebar-open");
    if (sidebarToggle) sidebarToggle.setAttribute("aria-expanded", "true");
    if (sidebarBackdrop) sidebarBackdrop.hidden = false;
  }

  function closeSidebar() {
    body.classList.remove("sidebar-open");
    if (sidebarToggle) sidebarToggle.setAttribute("aria-expanded", "false");
    if (sidebarBackdrop) sidebarBackdrop.hidden = true;
  }

  function toggleTopbarState() {
    if (!topbar) return;
    topbar.classList.toggle("is-scrolled", window.scrollY > 18);
    const shift = Math.min(window.scrollY * 0.08, 14);
    topbar.style.setProperty("--pointer-y", `${40 + shift}%`);
    body.style.setProperty("--scroll-lift", `${Math.max(-6, window.scrollY * -0.015)}px`);
  }

  function toggleBackToTop() {
    if (!backToTop) return;
    backToTop.classList.toggle("is-visible", window.scrollY > 560);
  }

  function updatePointerGlow(element, event) {
    const rect = element.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * 100;
    const y = ((event.clientY - rect.top) / rect.height) * 100;
    element.style.setProperty("--pointer-x", `${Math.max(0, Math.min(100, x))}%`);
    element.style.setProperty("--pointer-y", `${Math.max(0, Math.min(100, y))}%`);
  }

  function setupLiquidTracking() {
    if (!enhancedMotionEnabled || performanceMode !== "full") return;

    liquidTargets.forEach((element) => {
      element.addEventListener("pointermove", (event) => {
        updatePointerGlow(element, event);
        element.classList.add("is-liquid-active");

        if (element.matches(".card, .quick-action-card, .post-card, .media-row, .stat, .dashboard-card, .spotlight-card")) {
          const rect = element.getBoundingClientRect();
          const rotateY = ((event.clientX - rect.left) / rect.width - 0.5) * -8;
          const rotateX = ((event.clientY - rect.top) / rect.height - 0.5) * 6;
          element.style.setProperty("--card-rotate-x", `${rotateX}deg`);
          element.style.setProperty("--card-rotate-y", `${rotateY}deg`);
        }
      });

      element.addEventListener("pointerleave", () => {
        element.style.setProperty("--pointer-x", "50%");
        element.style.setProperty("--pointer-y", "50%");
        element.style.setProperty("--card-rotate-x", "0deg");
        element.style.setProperty("--card-rotate-y", "0deg");
        element.classList.remove("is-liquid-active");
      });
    });
  }

  function setupRevealAnimation() {
    if (!("IntersectionObserver" in window)) return;

    revealTargets.forEach((element, index) => {
      element.classList.add("reveal-on-scroll");
      element.style.transitionDelay = prefersReducedMotion ? "0ms" : `${Math.min(index % 6, 5) * 45}ms`;
    });

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        });
      },
      {
        threshold: 0.16,
        rootMargin: "0px 0px -8% 0px",
      }
    );

    revealTargets.forEach((element) => observer.observe(element));
  }

  function setupPressStates() {
    document.querySelectorAll(".button, .icon-button, .player-control, .player-tool, .player-rate").forEach((element) => {
      element.addEventListener("pointerdown", () => {
        if (prefersReducedMotion) return;
        element.classList.add("is-pressed");
      });

      const reset = () => {
        element.classList.remove("is-pressed");
      };

      element.addEventListener("pointerup", reset);
      element.addEventListener("pointercancel", reset);
      element.addEventListener("pointerleave", reset);
    });
  }

  function updateAmbientMotion() {
    ambientFrame = null;
    body.style.setProperty("--pointer-x", `${ambientPointer.x * 100}%`);
    body.style.setProperty("--pointer-y", `${ambientPointer.y * 100}%`);
    body.style.setProperty("--orb-shift-x", `${(ambientPointer.x - 0.5) * 32}px`);
    body.style.setProperty("--orb-shift-y", `${(ambientPointer.y - 0.5) * 18}px`);
  }

  function queueAmbientMotion(event) {
    if (!enhancedMotionEnabled) return;
    ambientPointer = {
      x: window.innerWidth ? event.clientX / window.innerWidth : 0.5,
      y: window.innerHeight ? event.clientY / window.innerHeight : 0.5,
    };

    if (ambientFrame) return;
    ambientFrame = window.requestAnimationFrame(updateAmbientMotion);
  }

  function runScrollEffects() {
    scrollFrame = null;
    toggleTopbarState();
    toggleBackToTop();
  }

  function queueScrollEffects() {
    if (scrollFrame) return;
    scrollFrame = window.requestAnimationFrame(runScrollEffects);
  }

  function showToast(message) {
    const existingToast = document.querySelector(".floating-toast");
    if (existingToast) existingToast.remove();

    const toast = document.createElement("div");
    toast.className = "floating-toast";
    toast.textContent = message;
    body.appendChild(toast);

    window.requestAnimationFrame(() => {
      toast.classList.add("is-visible");
    });

    window.setTimeout(() => {
      toast.classList.remove("is-visible");
      window.setTimeout(() => toast.remove(), 220);
    }, 2200);
  }

  let shareDialog = null;
  let lastActiveShareButton = null;

  async function copyShareUrl(url) {
    if (navigator.clipboard && window.isSecureContext) {
      try {
        await navigator.clipboard.writeText(url);
        showToast("تم نسخ الرابط");
        return true;
      } catch (error) {
        // fall back below
      }
    }

    window.prompt("انسخ الرابط:", url);
    return false;
  }

  async function openNativeShare(url, title) {
    if (!navigator.share) {
      showToast("المشاركة عبر النظام غير مدعومة هنا");
      return;
    }

    try {
      await navigator.share({ title, url });
    } catch (error) {
      if (error && error.name === "AbortError") return;
      showToast("تعذر فتح مشاركة النظام");
    }
  }

  function buildShareDialog() {
    if (shareDialog) return shareDialog;

    const dialog = document.createElement("div");
    dialog.className = "share-sheet";
    dialog.hidden = true;
    dialog.innerHTML = `
      <div class="share-sheet-backdrop" data-share-close></div>
      <div class="share-sheet-panel glass-panel" role="dialog" aria-modal="true" aria-labelledby="share-sheet-title">
        <div class="share-sheet-head">
          <div>
            <div class="eyebrow">مشاركة</div>
            <h2 id="share-sheet-title">شارك هذا الرابط</h2>
          </div>
          <button class="icon-button" type="button" data-share-close aria-label="إغلاق نافذة المشاركة">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>
        <div class="share-sheet-preview">
          <div class="share-sheet-art" data-share-preview-art>
            <span class="media-placeholder-mark mini"><span class="media-placeholder-note"></span><span class="media-placeholder-core">ن</span></span>
          </div>
          <div class="share-sheet-copy">
            <strong data-share-preview-title></strong>
            <span class="muted" data-share-preview-url></span>
          </div>
        </div>
        <div class="share-sheet-actions">
          <button class="button primary" type="button" data-share-action="copy">
            <i class="fa-solid fa-link"></i>
            نسخ الرابط
          </button>
          <button class="button ghost" type="button" data-share-action="native">
            <i class="fa-solid fa-tower-broadcast"></i>
            بلوتوث والجهاز
          </button>
          <button class="button ghost" type="button" data-share-action="compose">
            <i class="fa-solid fa-feather-pointed"></i>
            أضف إلى منشورك
          </button>
          <a class="button ghost" href="#" target="_blank" rel="noopener" data-share-action="open">
            <i class="fa-solid fa-arrow-up-right-from-square"></i>
            فتح الصفحة
          </a>
        </div>
        <form class="share-compose-form" method="post" hidden data-share-compose-form>
          <input type="hidden" name="csrfmiddlewaretoken" value="">
          <input type="hidden" name="shared_track" value="">
          <textarea name="body" rows="3" maxlength="1200" placeholder="أضف رأيًا سريعًا قبل نشر الأغنية في مجتمعك"></textarea>
          <div class="share-compose-actions">
            <button class="button primary" type="submit">
              <i class="fa-solid fa-paper-plane"></i>
              نشر الآن
            </button>
          </div>
        </form>
        <div class="share-sheet-grid">
          <a class="share-option" href="#" target="_blank" rel="noopener" data-share-target="whatsapp">
            <i class="fa-brands fa-whatsapp"></i>
            <span>واتساب</span>
          </a>
          <a class="share-option" href="#" target="_blank" rel="noopener" data-share-target="telegram">
            <i class="fa-brands fa-telegram"></i>
            <span>تيليجرام</span>
          </a>
          <a class="share-option" href="#" target="_blank" rel="noopener" data-share-target="x">
            <i class="fa-brands fa-x-twitter"></i>
            <span>إكس</span>
          </a>
          <a class="share-option" href="#" target="_blank" rel="noopener" data-share-target="email">
            <i class="fa-solid fa-envelope"></i>
            <span>البريد</span>
          </a>
        </div>
      </div>
    `;

    dialog.addEventListener("click", async (event) => {
      const closeTrigger = event.target.closest("[data-share-close]");
      if (closeTrigger) {
        closeShareDialog();
        return;
      }

      const action = event.target.closest("[data-share-action]");
      if (!action) return;

      const url = dialog.dataset.shareUrl;
      const title = dialog.dataset.shareTitle;
      const actionType = action.dataset.shareAction;

      if (actionType === "open") {
        return;
      }

      event.preventDefault();

      if (actionType === "copy") {
        await copyShareUrl(url);
        closeShareDialog();
        return;
      }

      if (actionType === "native") {
        await openNativeShare(url, title);
        return;
      }

      if (actionType === "compose") {
        const composeForm = dialog.querySelector("[data-share-compose-form]");
        const authenticated = body.dataset.userAuthenticated === "true";
        const trackId = dialog.dataset.shareTrackId || "";
        if (!authenticated) {
          window.location.href = body.dataset.loginUrl || "/accounts/login/";
          return;
        }
        if (!trackId) {
          showToast("هذه المشاركة لا تدعم الإرسال إلى منشور");
          return;
        }
        composeForm.hidden = !composeForm.hidden;
        if (!composeForm.hidden) {
          composeForm.querySelector("textarea").focus();
        }
      }
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && shareDialog && !shareDialog.hidden) {
        closeShareDialog();
      }
    });

    body.appendChild(dialog);
    shareDialog = dialog;
    return shareDialog;
  }

  function closeShareDialog() {
    if (!shareDialog || shareDialog.hidden) return;
    shareDialog.classList.remove("is-visible");
    body.classList.remove("share-sheet-open");
    window.setTimeout(() => {
      if (!shareDialog) return;
      shareDialog.hidden = true;
      shareDialog.querySelector("[data-share-compose-form]").hidden = true;
      if (lastActiveShareButton) lastActiveShareButton.focus();
      lastActiveShareButton = null;
    }, 180);
  }

  function getShareArtwork(button) {
    const card = button.closest(".track-card, .track-row, .detail-grid, .shared-track-preview");
    const image = card ? card.querySelector("img") : null;
    return image ? image.getAttribute("src") : "";
  }

  function openShareDialog(button) {
    const relativeUrl = button.dataset.shareUrl;
    if (!relativeUrl) return;

    const dialog = buildShareDialog();
    const url = new URL(relativeUrl, window.location.origin).href;
    const title = button.dataset.shareTitle || document.title;
    const artwork = getShareArtwork(button);
    const trackId = button.dataset.shareTrackId || "";
    const encodedUrl = encodeURIComponent(url);
    const encodedTitle = encodeURIComponent(title);
    const csrfTokenInput = document.querySelector("input[name='csrfmiddlewaretoken']");
    const composeForm = dialog.querySelector("[data-share-compose-form]");

    dialog.dataset.shareUrl = url;
    dialog.dataset.shareTitle = title;
    dialog.dataset.shareTrackId = trackId;
    dialog.querySelector("[data-share-preview-title]").textContent = title;
    dialog.querySelector("[data-share-preview-url]").textContent = url;
    dialog.querySelector("[data-share-action='open']").href = url;
    dialog.querySelector("[data-share-target='whatsapp']").href = `https://wa.me/?text=${encodedTitle}%20${encodedUrl}`;
    dialog.querySelector("[data-share-target='telegram']").href = `https://t.me/share/url?url=${encodedUrl}&text=${encodedTitle}`;
    dialog.querySelector("[data-share-target='x']").href = `https://twitter.com/intent/tweet?text=${encodedTitle}&url=${encodedUrl}`;
    dialog.querySelector("[data-share-target='email']").href = `mailto:?subject=${encodedTitle}&body=${encodedTitle}%0A${encodedUrl}`;
    dialog.querySelector("[data-share-action='native']").hidden = !navigator.share;
    dialog.querySelector("[data-share-action='compose']").hidden = !trackId;

    composeForm.action = body.dataset.createPostUrl || "/profile/posts/create/";
    composeForm.hidden = true;
    composeForm.querySelector("input[name='shared_track']").value = trackId;
    composeForm.querySelector("input[name='csrfmiddlewaretoken']").value = csrfTokenInput ? csrfTokenInput.value : "";
    composeForm.querySelector("textarea").value = "";

    const artNode = dialog.querySelector("[data-share-preview-art]");
    artNode.innerHTML = artwork
      ? `<img src="${artwork}" alt="${title}">`
      : `<span class="media-placeholder-mark mini"><span class="media-placeholder-note"></span><span class="media-placeholder-core">ن</span></span>`;

    lastActiveShareButton = button;
    dialog.hidden = false;
    body.classList.add("share-sheet-open");
    window.requestAnimationFrame(() => {
      dialog.classList.add("is-visible");
    });
  }

  function setupShareButtons() {
    document.addEventListener("click", (event) => {
      const button = event.target.closest("[data-share-url]");
      if (!button) return;

      event.preventDefault();
      try {
        openShareDialog(button);
      } catch (error) {
        const relativeUrl = button.dataset.shareUrl;
        if (!relativeUrl) return;
        const url = new URL(relativeUrl, window.location.origin).href;
        copyShareUrl(url);
      }
    });
  }

  function focusSearch() {
    if (!searchInput) return;
    searchInput.focus();
    searchInput.select();
  }

  function isTypingContext(element) {
    return Boolean(
      element &&
      (element.tagName === "INPUT" ||
        element.tagName === "TEXTAREA" ||
        element.tagName === "SELECT" ||
        element.isContentEditable)
    );
  }

  setTheme(getPreferredTheme());
  applyPerformanceProfile();

  if (themeToggle) {
    themeToggle.addEventListener("click", () => {
      const nextTheme = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
      safeStorageSet(themeStorageKey, nextTheme);
      setTheme(nextTheme);
      showToast(nextTheme === "dark" ? "تم تفعيل الوضع الداكن" : "تم تفعيل الوضع الفاتح");
    });
  }

  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener("click", () => {
      if (body.classList.contains("sidebar-open")) closeSidebar();
      else openSidebar();
    });

    sidebar.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", closeSidebar);
    });

    if (sidebarBackdrop) {
      sidebarBackdrop.addEventListener("click", closeSidebar);
    }

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") closeSidebar();
    });

    window.addEventListener("resize", () => {
      if (window.innerWidth > 1180) closeSidebar();
    });
  }

  if (backToTop) {
    backToTop.addEventListener("click", () => {
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  }

  document.addEventListener("keydown", (event) => {
    if (isTypingContext(document.activeElement)) return;

    if (event.key === "/" && !event.ctrlKey && !event.metaKey && !event.altKey) {
      event.preventDefault();
      focusSearch();
      return;
    }

    if (event.key.toLowerCase() === "k" && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      focusSearch();
    }
  });

  setupLiquidTracking();
  setupRevealAnimation();
  setupPressStates();
  setupShareButtons();

  if (enhancedMotionEnabled) {
    window.addEventListener("pointermove", queueAmbientMotion, { passive: true });
    updateAmbientMotion();
  }

  window.addEventListener("scroll", queueScrollEffects, { passive: true });

  runScrollEffects();

  requestAnimationFrame(() => {
    body.setAttribute("data-ui-ready", "true");
  });
})();


(function () {
  const audio = document.querySelector(".player-audio");
  if (!audio) return;

  const storageKey = "nagham-player-state";
  const queueKey = "nagham-player-queue";
  const playButtons = Array.from(document.querySelectorAll("[data-player-track]"));
  const titleNode = document.querySelector("[data-player-title]");
  const artistNode = document.querySelector("[data-player-artist]");
  const artNode = document.querySelector("[data-player-art]");
  const kickerNode = document.querySelector(".player-kicker");
  const progress = document.querySelector("[data-player-progress]");
  const progressFill = document.querySelector("[data-player-progress-fill]");
  const currentTimeNode = document.querySelector("[data-player-current]");
  const durationNode = document.querySelector("[data-player-duration]");
  const volume = document.querySelector("[data-player-volume]");
  const icon = document.querySelector("[data-player-icon]");
  const volumeIcon = document.querySelector("[data-player-volume-icon]");
  const rateButton = document.querySelector("[data-player-action='rate']");
  const statusNode = document.querySelector("[data-player-status]");
  const playerShell = document.querySelector("[data-player-shell]");
  const closeButton = document.querySelector("[data-player-close]");
  const shuffleButton = document.querySelector("[data-player-action='shuffle']");
  const repeatButton = document.querySelector("[data-player-action='repeat']");
  const repeatIcon = document.querySelector("[data-player-repeat-icon]");
  const queueToggleButton = document.querySelector("[data-player-action='queue']");
  const queueCountNode = document.querySelector("[data-player-queue-count]");
  const modeNode = document.querySelector("[data-player-mode]");
  const queuePanel = document.querySelector("[data-player-queue-panel]");
  const queueList = document.querySelector("[data-player-queue-list]");
  const transportButtons = Array.from(
    document.querySelectorAll("[data-player-action='prev'], [data-player-action='next']")
  );

  let queue = [];
  let currentIndex = -1;
  let pendingRestoreTime = null;
  let dismissed = true;
  let shuffleEnabled = false;
  let repeatMode = "off";
  let queueOpen = false;
  let lastPersistSecond = -1;
  const countedTracks = new Set();

  function safeStorageGet(key) {
    try {
      return localStorage.getItem(key);
    } catch (error) {
      return null;
    }
  }

  function safeStorageSet(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch (error) {
      return null;
    }
    return value;
  }

  function getCsrfToken() {
    const csrfField = document.querySelector("input[name='csrfmiddlewaretoken']");
    return csrfField ? csrfField.value : "";
  }

  function normalizeUrl(url) {
    try {
      return new URL(url, window.location.href).href;
    } catch (error) {
      return url;
    }
  }

  function normalizeQueue(items) {
    const seen = new Set();
    return items.filter((track) => {
      const key = normalizeUrl(track.src || track.id || "");
      if (!track.src || seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }

  function getTrackData(button) {
    return {
      id: button.dataset.trackId || "",
      title: button.dataset.trackTitle || "جاهز للاستماع",
      artist: button.dataset.trackArtist || "صوت بلا موسيقى",
      src: button.dataset.trackSrc || "",
      art: button.dataset.trackArt || "",
      autoplay: button.dataset.autoplay === "true",
    };
  }

  function formatTime(value) {
    if (!Number.isFinite(value) || value < 0) return "0:00";
    const minutes = Math.floor(value / 60);
    const seconds = Math.floor(value % 60)
      .toString()
      .padStart(2, "0");
    return `${minutes}:${seconds}`;
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function announceStatus(message) {
    if (statusNode) statusNode.textContent = message;
  }

  function setPlayerDismissed(isDismissed) {
    dismissed = Boolean(isDismissed);
    if (!playerShell) return;
    playerShell.dataset.playerClosed = dismissed ? "true" : "false";
  }

  function setQueueOpen(isOpen) {
    queueOpen = Boolean(isOpen) && queue.length > 0;
    if (queuePanel) queuePanel.hidden = !queueOpen;
    if (playerShell) playerShell.classList.toggle("has-queue-open", queueOpen);
    if (queueToggleButton) {
      queueToggleButton.classList.toggle("is-active", queueOpen);
      queueToggleButton.setAttribute("aria-pressed", queueOpen ? "true" : "false");
    }
  }

  function formatModeLabel() {
    if (repeatMode === "one") return "إعادة مقطع";
    if (repeatMode === "all") return shuffleEnabled ? "عشوائي مع إعادة" : "إعادة الطابور";
    if (shuffleEnabled) return "تشغيل عشوائي";
    return queue.length ? "الطابور جاهز" : "وضع هادئ";
  }

  function updateTimeUI() {
    const duration = Number.isFinite(audio.duration) ? audio.duration : 0;
    const current = Number.isFinite(audio.currentTime) ? audio.currentTime : 0;
    if (currentTimeNode) currentTimeNode.textContent = formatTime(current);
    if (durationNode) durationNode.textContent = formatTime(duration);
    if (progress) {
      const ratio = duration ? (current / duration) * 100 : 0;
      progress.value = String(ratio);
      if (progressFill) progressFill.style.width = `${ratio}%`;
      const shell = progress.closest(".player-progress-shell");
      if (shell) shell.style.setProperty("--progress", `${ratio}%`);
    }
  }

  function renderQueue() {
    if (!queueList) return;

    if (!queue.length) {
      queueList.innerHTML = '<div class="player-queue-empty">أضف مقطعًا ليظهر هنا ويُدار من المشغل مباشرة.</div>';
      setQueueOpen(false);
      return;
    }

    queueList.innerHTML = queue
      .map((track, index) => {
        const isActive = index === currentIndex;
        const status = isActive ? (audio.paused ? "متوقف مؤقتًا" : "يعمل الآن") : "تشغيل";
        return `
          <button class="player-queue-item ${isActive ? "is-active" : ""}" type="button" data-player-queue-index="${index}">
            <span class="player-queue-index">${index + 1}</span>
            <span class="player-queue-copy">
              <strong>${escapeHtml(track.title)}</strong>
              <span>${escapeHtml(track.artist)}</span>
            </span>
            <span class="player-queue-state">${status}</span>
          </button>
        `;
      })
      .join("");
  }

  function updateIcons() {
    if (icon) {
      icon.className = audio.paused ? "fa-solid fa-play" : "fa-solid fa-pause";
    }

    if (volumeIcon) {
      volumeIcon.className =
        audio.muted || audio.volume === 0
          ? "fa-solid fa-volume-xmark"
          : audio.volume < 0.5
            ? "fa-solid fa-volume-low"
            : "fa-solid fa-volume-high";
    }

    if (repeatIcon) {
      repeatIcon.className = repeatMode === "one" ? "fa-solid fa-repeat-1" : "fa-solid fa-repeat";
    }

    if (playerShell) {
      playerShell.classList.toggle("is-playing", !audio.paused && Boolean(audio.src));
      playerShell.classList.toggle("is-empty", !audio.src && !queue.length);
    }

    transportButtons.forEach((button) => {
      button.disabled = queue.length < 2;
    });

    if (shuffleButton) {
      shuffleButton.classList.toggle("is-active", shuffleEnabled);
      shuffleButton.setAttribute("aria-pressed", shuffleEnabled ? "true" : "false");
    }

    if (repeatButton) {
      const repeatActive = repeatMode !== "off";
      repeatButton.classList.toggle("is-active", repeatActive);
      repeatButton.setAttribute("aria-pressed", repeatActive ? "true" : "false");
    }

    if (queueCountNode) {
      queueCountNode.textContent = queue.length ? `${queue.length} في الطابور` : "الطابور فارغ";
    }

    if (modeNode) {
      modeNode.textContent = formatModeLabel();
    }

    setQueueOpen(queueOpen);
  }

  function setCurrentButtonState(activeTrackId) {
    playButtons.forEach((button) => {
      const isActive = button.dataset.trackId === activeTrackId;
      button.classList.toggle("is-active", isActive);
      button.classList.toggle("is-playing-track", isActive && !audio.paused);
      const parentCard = button.closest(".card, .detail-panel, .media-row");
      if (parentCard) parentCard.classList.toggle("is-active-glow", isActive);
      const localIcon = button.querySelector("i");
      if (localIcon) {
        localIcon.className = isActive && !audio.paused ? "fa-solid fa-pause" : "fa-solid fa-play";
      }
    });
  }

  function updateTrackMeta(track) {
    if (titleNode) titleNode.textContent = track.title;
    if (artistNode) artistNode.textContent = track.artist;
    if (kickerNode) kickerNode.textContent = audio.paused ? "استئناف جاهز" : "يعمل الآن";
    if (artNode) {
      artNode.textContent = "";
      if (track.art) {
        const image = document.createElement("img");
        image.src = track.art;
        image.alt = track.title;
        image.decoding = "async";
        artNode.appendChild(image);
      } else {
        artNode.innerHTML =
          '<div class="media-placeholder mini"><div class="media-placeholder-mark mini"><span class="media-placeholder-note"></span><span class="media-placeholder-core">ن</span></div></div>';
      }
    }
  }

  function syncMediaSession(track) {
    if (!("mediaSession" in navigator) || !track) return;

    navigator.mediaSession.metadata = new window.MediaMetadata({
      title: track.title,
      artist: track.artist,
      album: "Nagham",
      artwork: track.art
        ? [
            {
              src: track.art,
              sizes: "512x512",
              type: "image/png",
            },
          ]
        : [],
    });

    navigator.mediaSession.setActionHandler("play", () => audio.play().catch(() => {}));
    navigator.mediaSession.setActionHandler("pause", () => audio.pause());
    navigator.mediaSession.setActionHandler("previoustrack", () => playPrevious());
    navigator.mediaSession.setActionHandler("nexttrack", () => playNext());
    navigator.mediaSession.setActionHandler("seekbackward", () => {
      audio.currentTime = Math.max(audio.currentTime - 10, 0);
      updateTimeUI();
      saveState(true);
    });
    navigator.mediaSession.setActionHandler("seekforward", () => {
      audio.currentTime = Math.min(audio.currentTime + 10, audio.duration || audio.currentTime + 10);
      updateTimeUI();
      saveState(true);
    });
  }

  function saveState(force = false) {
    const currentSecond = Math.floor(audio.currentTime || 0);
    if (!force && currentSecond === lastPersistSecond) return;
    lastPersistSecond = currentSecond;

    const state = {
      src: audio.currentSrc || audio.getAttribute("src") || "",
      currentTime: audio.currentTime || 0,
      paused: audio.paused,
      volume: audio.volume,
      muted: audio.muted,
      playbackRate: audio.playbackRate,
      currentIndex,
      queue,
      title: titleNode ? titleNode.textContent : "",
      artist: artistNode ? artistNode.textContent : "",
      art: artNode && artNode.querySelector("img") ? artNode.querySelector("img").src : "",
      dismissed,
      shuffleEnabled,
      repeatMode,
      queueOpen,
    };

    safeStorageSet(storageKey, JSON.stringify(state));
    safeStorageSet(queueKey, JSON.stringify(queue));
  }

  function sendPlayPing(track) {
    if (!track || !track.id || countedTracks.has(track.id)) return;
    const csrfToken = getCsrfToken();
    if (!csrfToken) return;

    fetch(`/track/${track.id}/play/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,
      },
      credentials: "same-origin",
      body: JSON.stringify({ source: "player", threshold_seconds: 20 }),
    })
      .then((response) => {
        if (!response.ok) return;
        countedTracks.add(track.id);
      })
      .catch(() => {});
  }

  function getRandomIndex() {
    if (queue.length < 2) return currentIndex;
    let nextIndex = currentIndex;
    while (nextIndex === currentIndex) {
      nextIndex = Math.floor(Math.random() * queue.length);
    }
    return nextIndex;
  }

  function getNextIndex(mode) {
    if (!queue.length) return -1;

    if (mode === "prev") {
      return currentIndex <= 0 ? queue.length - 1 : currentIndex - 1;
    }

    if (mode === "ended" && repeatMode === "one") {
      return currentIndex;
    }

    if (shuffleEnabled && queue.length > 1) {
      return getRandomIndex();
    }

    const nextIndex = currentIndex + 1;
    if (nextIndex < queue.length) return nextIndex;
    if (repeatMode === "all" || mode === "manual") return 0;
    return -1;
  }

  function loadTrack(track, shouldPlay) {
    if (!track || !track.src) return;

    const normalizedSrc = normalizeUrl(track.src);
    const sameTrack = normalizeUrl(audio.currentSrc || audio.getAttribute("src") || "") === normalizedSrc;

    setPlayerDismissed(false);
    queue = normalizeQueue(queue.concat(track));
    currentIndex = queue.findIndex((item) => normalizeUrl(item.src) === normalizedSrc);

    if (!sameTrack) {
      audio.src = track.src;
      pendingRestoreTime = null;
    }

    updateTrackMeta(track);
    syncMediaSession(track);
    setCurrentButtonState(track.id);
    renderQueue();
    updateIcons();
    updateTimeUI();

    if (shouldPlay) {
      audio.play().catch(() => {
        announceStatus("تعذر تشغيل المقطع الآن.");
        updateIcons();
      });
    }

    announceStatus(`تم تجهيز ${track.title} للفنان ${track.artist}.`);
    saveState(true);
  }

  function playByIndex(index, shouldPlay = true) {
    if (!queue.length || index < 0) return;
    currentIndex = index;
    loadTrack(queue[currentIndex], shouldPlay);
  }

  function playNext(mode = "manual") {
    const nextIndex = getNextIndex(mode);
    if (nextIndex < 0) {
      audio.pause();
      audio.currentTime = 0;
      updateTimeUI();
      saveState(true);
      return;
    }
    playByIndex(nextIndex, true);
  }

  function playPrevious() {
    if (audio.currentTime > 5) {
      audio.currentTime = 0;
      updateTimeUI();
      saveState(true);
      return;
    }

    const previousIndex = getNextIndex("prev");
    if (previousIndex >= 0) {
      playByIndex(previousIndex, true);
    }
  }

  function clearLocalQueue() {
    const activeTrack = queue[currentIndex] || null;
    queue = activeTrack ? [activeTrack] : [];
    currentIndex = activeTrack ? 0 : -1;
    renderQueue();
    updateIcons();
    saveState(true);
    announceStatus("تم تنظيف الطابور المحلي.");
  }

  function restoreState() {
    const raw = safeStorageGet(storageKey);
    if (!raw) return false;

    try {
      const state = JSON.parse(raw);
      queue = Array.isArray(state.queue) ? normalizeQueue(state.queue) : [];

      if (!state.src && !queue.length) return false;

      audio.src = state.src || audio.getAttribute("src") || "";
      audio.volume = typeof state.volume === "number" ? state.volume : 0.85;
      audio.muted = Boolean(state.muted);
      audio.playbackRate = state.playbackRate || 1;
      currentIndex = Number.isInteger(state.currentIndex) ? state.currentIndex : -1;
      pendingRestoreTime = state.currentTime || 0;
      shuffleEnabled = Boolean(state.shuffleEnabled);
      repeatMode = ["off", "all", "one"].includes(state.repeatMode) ? state.repeatMode : "off";
      dismissed = Boolean(state.dismissed);
      queueOpen = Boolean(state.queueOpen);

      const restoredTrack =
        queue[currentIndex] ||
        (state.src
          ? {
              id: "",
              title: state.title || "جاهز للاستماع",
              artist: state.artist || "صوت بلا موسيقى",
              src: state.src,
              art: state.art || "",
            }
          : null);

      if (restoredTrack) {
        updateTrackMeta(restoredTrack);
        syncMediaSession(restoredTrack);
      }

      if (volume) volume.value = String(audio.muted ? 0 : audio.volume);
      if (rateButton) rateButton.textContent = `${audio.playbackRate}x`;

      renderQueue();
      setPlayerDismissed(dismissed && !audio.currentSrc ? true : dismissed);
      updateIcons();
      updateTimeUI();
      return true;
    } catch (error) {
      return false;
    }
  }

  function buildPageQueue() {
    const pageQueue = normalizeQueue(playButtons.map(getTrackData));
    if (!pageQueue.length) {
      const storedQueue = safeStorageGet(queueKey);
      if (!storedQueue || queue.length) return;
      try {
        const parsed = JSON.parse(storedQueue);
        if (Array.isArray(parsed)) queue = normalizeQueue(parsed);
      } catch (error) {
        return;
      }
      return;
    }

    if (!queue.length) {
      queue = pageQueue;
    }
  }

  function hydrateFromTemplateTrack() {
    const templateSrc = audio.getAttribute("src");
    if (!templateSrc || queue.length && currentIndex >= 0) return;

    const templateTrack = {
      id: playButtons.find((button) => button.dataset.autoplay === "true")?.dataset.trackId || "",
      title: titleNode ? titleNode.textContent.trim() : "جاهز للاستماع",
      artist: artistNode ? artistNode.textContent.trim() : "صوت بلا موسيقى",
      src: templateSrc,
      art: artNode && artNode.querySelector("img") ? artNode.querySelector("img").src : "",
    };

    queue = normalizeQueue([templateTrack].concat(queue));
    currentIndex = 0;
    updateTrackMeta(templateTrack);
    renderQueue();
    setPlayerDismissed(false);
    updateIcons();
    saveState(true);
  }

  document.querySelectorAll("[data-player-action]").forEach((button) => {
    button.addEventListener("click", () => {
      const action = button.dataset.playerAction;

      if (action === "toggle") {
        if (!audio.src && queue.length) {
          playByIndex(Math.max(currentIndex, 0), true);
          return;
        }

        if (audio.paused) {
          setPlayerDismissed(false);
          audio.play().catch(() => {
            announceStatus("تعذر تشغيل المقطع الآن.");
          });
        } else {
          audio.pause();
        }
      }

      if (action === "prev") playPrevious();
      if (action === "next") playNext();

      if (action === "mute") {
        audio.muted = !audio.muted;
        updateIcons();
        saveState(true);
      }

      if (action === "rate") {
        const steps = [1, 1.25, 1.5, 1.75, 2];
        const nextRate = steps[(steps.indexOf(audio.playbackRate) + 1) % steps.length];
        audio.playbackRate = nextRate;
        button.textContent = `${nextRate}x`;
        announceStatus(`تم ضبط السرعة على ${nextRate}x.`);
        saveState(true);
      }

      if (action === "shuffle") {
        shuffleEnabled = !shuffleEnabled;
        updateIcons();
        saveState(true);
      }

      if (action === "repeat") {
        repeatMode = repeatMode === "off" ? "all" : repeatMode === "all" ? "one" : "off";
        announceStatus(
          repeatMode === "off"
            ? "تم إيقاف الإعادة."
            : repeatMode === "all"
              ? "تم تفعيل إعادة الطابور."
              : "تم تفعيل إعادة المقطع الحالي."
        );
        updateIcons();
        saveState(true);
      }

      if (action === "queue") {
        setQueueOpen(!queueOpen);
        saveState(true);
      }

      if (action === "clear-local-queue") {
        clearLocalQueue();
      }
    });
  });

  if (closeButton) {
    closeButton.addEventListener("click", () => {
      setPlayerDismissed(true);
      setQueueOpen(false);
      audio.pause();
      announceStatus("تم إخفاء المشغل.");
      saveState(true);
    });
  }

  if (queueList) {
    queueList.addEventListener("click", (event) => {
      const queueButton = event.target.closest("[data-player-queue-index]");
      if (!queueButton) return;
      const index = Number.parseInt(queueButton.dataset.playerQueueIndex || "-1", 10);
      if (Number.isNaN(index) || index < 0) return;
      playByIndex(index, true);
    });
  }

  playButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const track = getTrackData(button);
      const pageQueue = normalizeQueue(playButtons.map(getTrackData));
      queue = pageQueue.length ? pageQueue : normalizeQueue(queue.concat(track));

      const sameTrack =
        normalizeUrl(audio.currentSrc || audio.getAttribute("src") || "") === normalizeUrl(track.src);

      if (sameTrack) {
        setPlayerDismissed(false);
        if (audio.paused) audio.play().catch(() => {});
        else audio.pause();
        return;
      }

      loadTrack(track, true);
    });
  });

  audio.addEventListener("loadedmetadata", () => {
    if (pendingRestoreTime !== null) {
      audio.currentTime = pendingRestoreTime;
      pendingRestoreTime = null;
    }
    updateTimeUI();
  });

  audio.addEventListener("play", () => {
    setPlayerDismissed(false);
    if (kickerNode) kickerNode.textContent = "يعمل الآن";
    const active = queue[currentIndex];
    setCurrentButtonState(active ? active.id : "");
    renderQueue();
    updateIcons();
    if (active) {
      syncMediaSession(active);
      announceStatus(`يعمل الآن ${active.title} للفنان ${active.artist}.`);
    }
    saveState(true);
  });

  audio.addEventListener("pause", () => {
    if (kickerNode) kickerNode.textContent = "متوقف مؤقتًا";
    const active = queue[currentIndex];
    setCurrentButtonState(active ? active.id : "");
    renderQueue();
    updateIcons();
    saveState(true);
  });

  audio.addEventListener("timeupdate", () => {
    updateTimeUI();
    const active = queue[currentIndex];
    if (active && audio.currentTime >= 20) {
      sendPlayPing(active);
    }
    saveState();
  });

  audio.addEventListener("ended", () => {
    playNext("ended");
  });

  audio.addEventListener("volumechange", () => {
    if (volume) volume.value = String(audio.muted ? 0 : audio.volume);
    updateIcons();
    saveState(true);
  });

  audio.addEventListener("error", () => {
    announceStatus("تعذر تحميل الملف الصوتي.");
  });

  document.addEventListener("keydown", (event) => {
    const activeElement = document.activeElement;
    const isTyping =
      activeElement &&
      (activeElement.tagName === "INPUT" ||
        activeElement.tagName === "TEXTAREA" ||
        activeElement.tagName === "SELECT" ||
        activeElement.isContentEditable);

    if (isTyping) return;

    const key = event.key.toLowerCase();

    if (event.code === "Space") {
      event.preventDefault();
      const toggleButton = document.querySelector("[data-player-action='toggle']");
      if (toggleButton) toggleButton.click();
    }

    if (key === "m") {
      event.preventDefault();
      const muteButton = document.querySelector("[data-player-action='mute']");
      if (muteButton) muteButton.click();
    }

    if (key === "n") {
      event.preventDefault();
      playNext();
    }

    if (key === "b") {
      event.preventDefault();
      playPrevious();
    }

    if (key === "s") {
      event.preventDefault();
      if (shuffleButton) shuffleButton.click();
    }

    if (key === "r") {
      event.preventDefault();
      if (repeatButton) repeatButton.click();
    }

    if (key === "q") {
      event.preventDefault();
      if (queueToggleButton) queueToggleButton.click();
    }

    if (event.key === "ArrowRight" && audio.duration) {
      event.preventDefault();
      audio.currentTime = Math.min(audio.currentTime + 10, audio.duration);
      updateTimeUI();
      saveState(true);
    }

    if (event.key === "ArrowLeft" && audio.duration) {
      event.preventDefault();
      audio.currentTime = Math.max(audio.currentTime - 10, 0);
      updateTimeUI();
      saveState(true);
    }
  });

  if (progress) {
    progress.addEventListener("input", () => {
      const duration = Number.isFinite(audio.duration) ? audio.duration : 0;
      const value = Number.parseFloat(progress.value || "0");
      audio.currentTime = duration ? (value / 100) * duration : 0;
      updateTimeUI();
      saveState(true);
    });
  }

  if (volume) {
    volume.addEventListener("input", () => {
      audio.volume = Number.parseFloat(volume.value || "0.85");
      audio.muted = audio.volume === 0;
      updateIcons();
      saveState(true);
    });
  }

  const restored = restoreState();
  buildPageQueue();
  if (!restored) hydrateFromTemplateTrack();
  renderQueue();
  updateIcons();
  updateTimeUI();
  if (volume && !volume.value) volume.value = String(audio.volume || 0.85);
})();


(function () {
  if (!window.matchMedia("(max-width: 960px)").matches) return;

  const root = document.documentElement;
  const body = document.body;
  const topbar = document.querySelector("[data-topbar]");
  const playerShell = document.querySelector("[data-player-shell]");

  function setViewportUnit() {
    root.style.setProperty("--vh", `${window.innerHeight * 0.01}px`);
  }

  root.setAttribute("data-device", "mobile");
  body.setAttribute("data-device", "mobile");
  body.classList.remove("sidebar-open");

  if (topbar) topbar.classList.add("is-mobile-ui");
  if (playerShell) playerShell.classList.add("is-mobile-player");

  setViewportUnit();
  window.addEventListener("resize", setViewportUnit, { passive: true });
  window.addEventListener("orientationchange", setViewportUnit, { passive: true });
})();

})();
