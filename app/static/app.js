(() => {
  const bookFile = document.getElementById("bookFile");
  const promptBox = document.getElementById("promptBox");
  const generateBtn = document.getElementById("generateBtn");
  const generateStatus = document.getElementById("generateStatus");

  function show(message, isError = false) {
    generateStatus.hidden = false;
    generateStatus.textContent = message;
    generateStatus.classList.toggle("error", isError);
  }

  async function generate() {
    const file = bookFile.files && bookFile.files[0];
    const prompt = (promptBox.value || "").trim();

    if (!file) {
      show("پہلے کتاب (PDF یا DOCX) اپ لوڈ کریں۔", true);
      return;
    }
    if (!prompt) {
      show("پرامپٹ لکھیں۔", true);
      return;
    }

    show("کتاب پڑھ رہے ہیں، متعلقہ حصے ڈھونڈ رہے ہیں، اور سبق منصوبہ بنا رہے ہیں…");
    generateBtn.disabled = true;

    try {
      const body = new FormData();
      body.append("prompt", prompt);
      body.append("file", file, file.name);

      const res = await fetch("/api/rag-generate", { method: "POST", body });
      if (!res.ok) {
        let detail = "تیاری ناکام";
        try {
          const data = await res.json();
          detail = data.detail || detail;
        } catch (_) {}
        throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
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
      generateBtn.disabled = false;
    }
  }

  generateBtn.addEventListener("click", generate);
})();
