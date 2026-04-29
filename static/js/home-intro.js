(function () {
  const intro = document.querySelector("[data-home-intro]");
  if (!intro) return;

  const storageKey = "nagham-home-intro-seen";
  const dismissButtons = Array.from(intro.querySelectorAll("[data-intro-dismiss]"));
  const soundButton = intro.querySelector("[data-intro-sound]");
  const enterButton = intro.querySelector("[data-intro-enter]");
  const counter = intro.querySelector("[data-intro-counter]");
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const introDurationMs = reducedMotion ? 1800 : 4000;

  let timeoutId = null;
  let intervalId = null;
  let audioContext = null;
  let closed = false;
  let startedAt = 0;

  function safeGetSeen() {
    try {
      return localStorage.getItem(storageKey) === "1";
    } catch (error) {
      console.error("Failed to read intro state", error);
      return false;
    }
  }

  function safeSetSeen() {
    try {
      localStorage.setItem(storageKey, "1");
    } catch (error) {
      console.error("Failed to persist intro state", error);
    }
  }

  function clearTimers() {
    if (timeoutId) {
      window.clearTimeout(timeoutId);
      timeoutId = null;
    }

    if (intervalId) {
      window.clearInterval(intervalId);
      intervalId = null;
    }
  }

  function updateCountdown() {
    if (!counter || !startedAt) return;
    const elapsed = Date.now() - startedAt;
    const remaining = Math.max(0, Math.ceil((introDurationMs - elapsed) / 1000));
    counter.textContent = `${String(remaining).padStart(2, "0")}s`;
  }

  function revealSite() {
    if (closed) return;
    closed = true;
    clearTimers();
    safeSetSeen();
    intro.classList.add("is-exiting");
    document.body.classList.add("intro-revealed");
    document.body.classList.remove("intro-open");

    window.setTimeout(() => {
      intro.hidden = true;
      intro.classList.remove("is-visible", "is-exiting");
    }, reducedMotion ? 40 : 900);
  }

  function playAmbientCue() {
    try {
      if (!audioContext) {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
      }

      const now = audioContext.currentTime;
      const master = audioContext.createGain();
      master.gain.setValueAtTime(0.0001, now);
      master.gain.exponentialRampToValueAtTime(0.026, now + 0.12);
      master.gain.exponentialRampToValueAtTime(0.0001, now + 3.8);
      master.connect(audioContext.destination);

      [174.61, 220, 261.63, 329.63].forEach((frequency, index) => {
        const oscillator = audioContext.createOscillator();
        const gain = audioContext.createGain();
        oscillator.type = index % 2 === 0 ? "sine" : "triangle";
        oscillator.frequency.value = frequency;
        gain.gain.value = 0.08;
        oscillator.connect(gain);
        gain.connect(master);
        oscillator.start(now + index * 0.18);
        oscillator.stop(now + 2.6 + index * 0.18);
      });
    } catch (error) {
      console.error("Ambient cue failed", error);
    }
  }

  function startSequence() {
    startedAt = Date.now();
    updateCountdown();
    intervalId = window.setInterval(updateCountdown, 250);
    timeoutId = window.setTimeout(revealSite, introDurationMs);
  }

  if (safeGetSeen()) {
    intro.hidden = true;
    document.body.classList.add("intro-revealed");
    return;
  }

  intro.hidden = false;
  document.body.classList.add("intro-open");

  window.requestAnimationFrame(() => {
    intro.classList.add("is-visible");
  });

  startSequence();

  dismissButtons.forEach((button) => {
    button.addEventListener("click", revealSite);
  });

  if (soundButton) {
    soundButton.addEventListener("click", () => {
      playAmbientCue();
      soundButton.textContent = "تم تشغيل الصوت";
      soundButton.disabled = true;
      if (enterButton && !closed) {
        enterButton.focus({ preventScroll: true });
      }
    });
  }

  if (enterButton) {
    enterButton.addEventListener("click", () => {
      playAmbientCue();
      revealSite();
    });
  }
})();
