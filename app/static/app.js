(() => {
  const pasteBox = document.getElementById("pasteBox");
  const generateBtn = document.getElementById("generateBtn");
  const generateStatus = document.getElementById("generateStatus");

  let token = null;
  let defaults = {};

  function show(message, isError = false) {
    generateStatus.hidden = false;
    generateStatus.textContent = message;
    generateStatus.classList.toggle("error", isError);
  }

  async function boot() {
    try {
      const res = await fetch("/api/form");
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "لوڈ نہیں ہوا");
      token = data.token;
      defaults = data.defaults || {};
      generateBtn.disabled = false;
    } catch (err) {
      show(err.message || "خرابی", true);
    }
  }

  async function generate() {
    if (!token) return;
    const content = pasteBox.value.trim();
    if (!content) {
      show("پہلے مواد چسپاں کریں۔", true);
      return;
    }

    show("مواد میپ ہو رہا ہے اور دستاویز تیار ہو رہی ہے…");
    generateBtn.disabled = true;

    try {
      const parseRes = await fetch("/api/parse", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content }),
      });
      const parsed = await parseRes.json();
      if (!parseRes.ok) throw new Error(parsed.detail || "میپنگ ناکام");

      const fields = { ...defaults, ...parsed.fields };
      const body = new FormData();
      body.append("token", token);
      body.append("content", "");
      body.append("fields_json", JSON.stringify(fields));

      const res = await fetch("/api/generate", { method: "POST", body });
      if (!res.ok) {
        let detail = "تیاری ناکام";
        try {
          const data = await res.json();
          detail = data.detail || detail;
        } catch (_) {}
        throw new Error(detail);
      }

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "بھرا_ہوا_دستاویز.docx";
      document.body.append(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      show("ڈاؤن لوڈ شروع ہو گیا۔");
    } catch (err) {
      show(err.message || "خرابی", true);
    } finally {
      generateBtn.disabled = !token;
    }
  }

  generateBtn.addEventListener("click", generate);
  boot();
})();
