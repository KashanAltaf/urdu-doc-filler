(() => {
  const uploadZone = document.getElementById("uploadZone");
  const bookFile = document.getElementById("bookFile");
  const fileName = document.getElementById("fileName");
  const lessonDate = document.getElementById("lessonDate");
  const promptBox = document.getElementById("promptBox");
  const generateBtn = document.getElementById("generateBtn");
  const generateStatus = document.getElementById("generateStatus");

  const MAX_TEXT_CHARS = 160000;

  const today = new Date();
  lessonDate.value = [
    today.getFullYear(),
    String(today.getMonth() + 1).padStart(2, "0"),
    String(today.getDate()).padStart(2, "0"),
  ].join("-");

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
    generateStatus.hidden = true;
  }

  bookFile.addEventListener("change", () => {
    setFileLabel((bookFile.files && bookFile.files[0]) || null);
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

  function ensurePdfJs() {
    if (window.pdfjsLib) return Promise.resolve(window.pdfjsLib);
    return new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js";
      script.onload = () => {
        if (!window.pdfjsLib) {
          reject(new Error("PDF لائبریری لوڈ نہیں ہوئی"));
          return;
        }
        window.pdfjsLib.GlobalWorkerOptions.workerSrc =
          "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";
        resolve(window.pdfjsLib);
      };
      script.onerror = () => reject(new Error("PDF لائبریری لوڈ نہیں ہوئی"));
      document.head.appendChild(script);
    });
  }

  function ensureMammoth() {
    if (window.mammoth) return Promise.resolve(window.mammoth);
    return new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = "https://cdnjs.cloudflare.com/ajax/libs/mammoth/1.8.0/mammoth.browser.min.js";
      script.onload = () => {
        if (!window.mammoth) {
          reject(new Error("DOCX لائبریری لوڈ نہیں ہوئی"));
          return;
        }
        resolve(window.mammoth);
      };
      script.onerror = () => reject(new Error("DOCX لائبریری لوڈ نہیں ہوئی"));
      document.head.appendChild(script);
    });
  }

  async function extractPdfText(file) {
    const pdfjsLib = await ensurePdfJs();
    const buffer = await file.arrayBuffer();
    const pdf = await pdfjsLib.getDocument({ data: buffer }).promise;
    const parts = [];
    for (let i = 1; i <= pdf.numPages; i += 1) {
      const page = await pdf.getPage(i);
      const content = await page.getTextContent();
      const pageText = content.items.map((item) => item.str).join(" ").trim();
      if (pageText) parts.push(`[صفحہ ${i}]\n${pageText}`);
      if (parts.join("\n\n").length > MAX_TEXT_CHARS) break;
    }
    return parts.join("\n\n").trim();
  }

  async function extractDocxText(file) {
    const mammoth = await ensureMammoth();
    const buffer = await file.arrayBuffer();
    const result = await mammoth.extractRawText({ arrayBuffer: buffer });
    return (result.value || "").trim();
  }

  async function extractBookText(file) {
    const name = (file.name || "").toLowerCase();
    let text = "";
    if (name.endsWith(".pdf")) text = await extractPdfText(file);
    else if (name.endsWith(".docx")) text = await extractDocxText(file);
    else throw new Error("صرف PDF یا DOCX فائلیں قبول ہیں۔");

    if (!text) {
      throw new Error("کتاب سے متن نہیں نکلا۔ اسکین شدہ PDF ہو تو پہلے OCR کریں۔");
    }
    if (text.length > MAX_TEXT_CHARS) {
      text = text.slice(0, MAX_TEXT_CHARS);
    }
    return text;
  }

  async function readError(res) {
    const raw = await res.text();
    if (!raw) return "تیاری ناکام";
    try {
      const data = JSON.parse(raw);
      const detail = data.detail || data.error || data.message;
      if (typeof detail === "string") return detail;
      if (detail) return JSON.stringify(detail);
    } catch (_) {}
    if (/FUNCTION_PAYLOAD_TOO_LARGE|Request Entity Too Large/i.test(raw)) {
      return "فائل بہت بڑی ہے۔ اب متن براؤزر میں نکالا جاتا ہے — صفحہ ریفریش کر کے دوبارہ کوشش کریں۔";
    }
    return raw.slice(0, 240);
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

    show("کتاب سے متن نکال رہے ہیں…");
    generateBtn.disabled = true;

    try {
      const bookText = await extractBookText(file);
      show("سبق منصوبہ تیار ہو رہا ہے…");

      // Text only — avoids Vercel FUNCTION_PAYLOAD_TOO_LARGE on big PDFs
      const body = new FormData();
      body.append("prompt", prompt);
      body.append("book_text", bookText);
      if (date) body.append("date", formatDateForDoc(date));

      const res = await fetch("/api/rag-generate", { method: "POST", body });
      if (!res.ok) throw new Error(await readError(res));

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
