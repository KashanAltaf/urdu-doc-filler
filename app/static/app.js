(() => {
  const uploadZone = document.getElementById("uploadZone");
  const bookFile = document.getElementById("bookFile");
  const fileName = document.getElementById("fileName");
  const lessonDate = document.getElementById("lessonDate");
  const promptBox = document.getElementById("promptBox");
  const generateBtn = document.getElementById("generateBtn");
  const generateStatus = document.getElementById("generateStatus");

  // Default to today
  const today = new Date();
  const yyyy = today.getFullYear();
  const mm = String(today.getMonth() + 1).padStart(2, "0");
  const dd = String(today.getDate()).padStart(2, "0");
  lessonDate.value = `${yyyy}-${mm}-${dd}`;

  function show(message, isError = false) {
    generateStatus.hidden = false;
    generateStatus.textContent = message;
    generateStatus.classList.toggle("error", isError);
  }

  function setFileLabel(file) {
    if (!file) {
      fileName.hidden = true;
      fileName.textContent = "";
      uploadZone.classList.remove("has-file");
      return;
    }
    fileName.hidden = false;
    fileName.textContent = file.name;
    uploadZone.classList.add("has-file");
  }

  function acceptFile(file) {
    if (!file) return;
    const name = (file.name || "").toLowerCase();
    if (!(name.endsWith(".pdf") || name.endsWith(".docx"))) {
      show("صرف PDF یا DOCX فائلیں قبول ہیں۔", true);
      return;
    }
    const dt = new DataTransfer();
    dt.items.add(file);
    bookFile.files = dt.files;
    setFileLabel(file);
    show("", false);
    generateStatus.hidden = true;
  }

  bookFile.addEventListener("change", () => {
    const file = bookFile.files && bookFile.files[0];
    setFileLabel(file || null);
  });

  ["dragenter", "dragover"].forEach((evt) => {
    uploadZone.addEventListener(evt, (e) => {
      e.preventDefault();
      uploadZone.classList.add("is-drag");
    });
  });

  ["dragleave", "drop"].forEach((evt) => {
    uploadZone.addEventListener(evt, (e) => {
      e.preventDefault();
      uploadZone.classList.remove("is-drag");
    });
  });

  uploadZone.addEventListener("drop", (e) => {
    const file = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
    acceptFile(file);
  });

  function formatDateForDoc(iso) {
    if (!iso) return "";
    const [y, m, d] = iso.split("-");
    if (!y || !m || !d) return iso;
    return `${d}/${m}/${y}`;
  }

  async function generate() {
    const file = bookFile.files && bookFile.files[0];
    const prompt = (promptBox.value || "").trim();
    const date = (lessonDate.value || "").trim();

    if (!file) {
      show("پہلے دستاویز اپ لوڈ کریں۔", true);
      return;
    }
    if (!prompt) {
      show("پرامپٹ لکھیں۔", true);
      return;
    }

    show("دستاویز تیار ہو رہی ہے…");
    generateBtn.disabled = true;

    try {
      const body = new FormData();
      body.append("prompt", prompt);
      body.append("file", file, file.name);
      if (date) body.append("date", formatDateForDoc(date));

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
