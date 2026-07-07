(function () {
  function track(event) {
    const payload = JSON.stringify({ event });
    try {
      if (navigator.sendBeacon) {
        const blob = new Blob([payload], { type: "application/json" });
        navigator.sendBeacon("/track", blob);
        return;
      }
    } catch (e) {
      // fall through to fetch
    }
    fetch("/track", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: payload,
      keepalive: true,
    }).catch(() => {});
  }

  window.ResumeIQTrack = track;

  const page = document.body.getAttribute("data-page");
  if (page) {
    track(`pageview_${page}`);
  }
})();
