let recognition = null;
let isRecording = false;
let currentCart = {
  items: [],
  subtotal: 0,
  gst: 0,
  total: 0
};

function qs(id) {
  return document.getElementById(id);
}

function setStatus(type, msg) {
  const dot = qs("status-dot");
  const text = qs("status-text");

  if (dot) {
    dot.className = "status-dot " + type;
  }

  if (text) {
    text.textContent = msg;
  }
}

function showToast(msg, color = "green") {
  const toast = qs("toast");
  const toastMsg = qs("toast-msg");

  if (!toast || !toastMsg) return;

  toastMsg.textContent = msg;
  toast.style.borderColor = color === "red" ? "var(--red)" : "var(--green)";
  toast.style.color = color === "red" ? "var(--red)" : "var(--green)";
  toast.classList.add("show");

  setTimeout(() => {
    toast.classList.remove("show");
  }, 3000);
}

function createWaveform(containerId) {
  const container = qs(containerId);
  if (!container) return;

  container.innerHTML = "";

  for (let i = 0; i < 16; i++) {
    const bar = document.createElement("div");
    bar.className = "wave-bar";
    bar.style.height = "4px";
    container.appendChild(bar);
  }
}

function animateWave(containerId) {
  const container = qs(containerId);
  if (!container) return null;

  const bars = container.querySelectorAll(".wave-bar");

  return setInterval(() => {
    bars.forEach((bar) => {
      bar.style.height = `${Math.random() * 28 + 4}px`;
    });
  }, 120);
}

function stopWave(containerId, intervalId) {
  if (intervalId) {
    clearInterval(intervalId);
  }

  const container = qs(containerId);
  if (!container) return;

  const bars = container.querySelectorAll(".wave-bar");
  bars.forEach((bar) => {
    bar.style.height = "4px";
  });
}

function showProcessingBar() {
  const bar = qs("processing-bar");
  if (!bar) return;

  bar.classList.remove("active");
  void bar.offsetWidth;
  bar.classList.add("active");
}

async function loadShopInfo() {
  try {
    const res = await fetch("/shop");
    const data = await res.json();

    if (qs("shop-name")) qs("shop-name").value = data.name || "";
    if (qs("shop-phone")) qs("shop-phone").value = data.phone || "";
    if (qs("shop-address")) qs("shop-address").value = data.address || "";
  } catch (err) {
    showToast("Failed to load shop info", "red");
  }
}

async function saveShopInfo() {
  try {
    const payload = {
      name: qs("shop-name") ? qs("shop-name").value.trim() : "",
      phone: qs("shop-phone") ? qs("shop-phone").value.trim() : "",
      address: qs("shop-address") ? qs("shop-address").value.trim() : ""
    };

    const res = await fetch("/shop", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });

    const data = await res.json();

    if (!res.ok) {
      showToast(data.error || "Failed to save shop", "red");
      return;
    }

    showToast("Shop information saved");
    await previewReceipt();
  } catch (err) {
    showToast("Failed to save shop", "red");
  }
}

async function fetchCart() {
  try {
    const res = await fetch("/cart");
    const data = await res.json();

    currentCart = {
      items: Array.isArray(data.items) ? data.items : [],
      subtotal: Number(data.subtotal || 0),
      gst: Number(data.gst || 0),
      total: Number(data.total || 0)
    };

    renderCart();
  } catch (err) {
    showToast("Failed to fetch cart", "red");
  }
}

function renderCart() {
  const container = qs("cart-items");
  const count = qs("cart-count");
  const totals = qs("totals-section");
  const receiptPreview = qs("receipt-preview");

  if (!container || !count || !totals) return;

  count.textContent = currentCart.items.length;

  if (!currentCart.items.length) {
    container.innerHTML = `
      <div class="cart-empty">
        <div class="emoji">🎤</div>
        Speak your shopping list to add items
      </div>
    `;
    totals.style.display = "none";

    if (receiptPreview) {
      receiptPreview.textContent = "No receipt preview available";
    }
    return;
  }

  container.innerHTML = currentCart.items.map((item) => `
    <div class="cart-item">
      <div class="item-name">
        ${escapeHtml(item.name)}
        <span class="item-name-en">₹${Number(item.price).toFixed(2)}/${escapeHtml(item.unit)}</span>
      </div>
      <div class="qty-control">
        <button class="qty-btn" onclick="changeQty('${jsSafe(item.name)}', ${Number(item.quantity) - 1})">−</button>
        <span class="qty-num">${Number(item.quantity)}</span>
        <button class="qty-btn" onclick="changeQty('${jsSafe(item.name)}', ${Number(item.quantity) + 1})">+</button>
      </div>
      <div class="item-price">₹${Number(item.line_total ?? item.total ?? 0).toFixed(2)}</div>
      <button class="remove-btn" onclick="removeItem('${jsSafe(item.name)}')">✕</button>
    </div>
  `).join("");

  totals.style.display = "block";

  if (qs("subtotal")) qs("subtotal").textContent = `₹${Number(currentCart.subtotal).toFixed(2)}`;
  if (qs("gst")) qs("gst").textContent = `₹${Number(currentCart.gst).toFixed(2)}`;
  if (qs("total")) qs("total").textContent = `₹${Number(currentCart.total).toFixed(2)}`;
}

async function changeQty(name, quantity) {
  try {
    if (quantity < 1) {
      await removeItem(name);
      return;
    }

    const res = await fetch("/cart/update", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ name, quantity })
    });

    const data = await res.json();

    if (!res.ok) {
      showToast(data.error || "Failed to update quantity", "red");
      return;
    }

    currentCart = {
      items: Array.isArray(data.items) ? data.items : [],
      subtotal: Number(data.subtotal || 0),
      gst: Number(data.gst || 0),
      total: Number(data.total || 0)
    };

    renderCart();
    await previewReceipt();
  } catch (err) {
    showToast("Failed to update quantity", "red");
  }
}

async function removeItem(name) {
  try {
    const res = await fetch("/cart/remove", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ name })
    });

    const data = await res.json();

    if (!res.ok) {
      showToast(data.error || "Failed to remove item", "red");
      return;
    }

    currentCart = {
      items: Array.isArray(data.items) ? data.items : [],
      subtotal: Number(data.subtotal || 0),
      gst: Number(data.gst || 0),
      total: Number(data.total || 0)
    };

    renderCart();
    await previewReceipt();
  } catch (err) {
    showToast("Failed to remove item", "red");
  }
}

async function clearCartServer() {
  try {
    const res = await fetch("/cart/reset", { method: "POST" });
    const data = await res.json();

    if (!res.ok) {
      showToast(data.error || "Failed to clear cart", "red");
      return;
    }

    if (data.cart) {
      currentCart = {
        items: Array.isArray(data.cart.items) ? data.cart.items : [],
        subtotal: Number(data.cart.subtotal || 0),
        gst: Number(data.cart.gst || 0),
        total: Number(data.cart.total || 0)
      };
    } else {
      currentCart = { items: [], subtotal: 0, gst: 0, total: 0 };
    }

    renderCart();

    const transcript = qs("transcript-text");
    if (transcript) {
      transcript.textContent = "Tap the mic and speak your shopping list...";
      transcript.style.color = "var(--muted)";
    }

    await previewReceipt();
    showToast("Cart cleared");
  } catch (err) {
    showToast("Failed to clear cart", "red");
  }
}

async function processSpeechToBackend(text) {
  try {
    showProcessingBar();
    setStatus("processing", "Extracting items...");

    const transcript = qs("transcript-text");
    if (transcript) {
      transcript.textContent = text;
      transcript.style.color = "var(--text)";
    }

    const res = await fetch("/process_text", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ speech: text })
    });

    const data = await res.json();

    if (!res.ok) {
      showToast(data.error || "Processing failed", "red");
      setStatus("ready", "Ready to listen...");
      return;
    }

    if (data.cart) {
      currentCart = {
        items: Array.isArray(data.cart.items) ? data.cart.items : [],
        subtotal: Number(data.cart.subtotal || 0),
        gst: Number(data.cart.gst || 0),
        total: Number(data.cart.total || 0)
      };
    } else {
      currentCart = { items: [], subtotal: 0, gst: 0, total: 0 };
    }

    renderCart();
    await previewReceipt();

    if (data.added && data.added.length) {
      showToast(`Added ${data.added.length} item(s)`);
    } else if (data.not_found && data.not_found.length) {
      showToast(`Not found: ${data.not_found.join(", ")}`, "red");
    } else {
      showToast("No items matched", "red");
    }

    setStatus("ready", "Ready to listen...");
  } catch (err) {
    showToast("Processing failed", "red");
    setStatus("ready", "Ready to listen...");
  }
}

function startVoice(lang) {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  if (!SpeechRecognition) {
    showToast("Speech API not supported in this browser", "red");
    return;
  }

  if (isRecording) {
    if (recognition) recognition.stop();
    return;
  }

  recognition = new SpeechRecognition();
  recognition.lang = lang === "hi" ? "hi-IN" : "en-IN";
  recognition.interimResults = true;
  recognition.continuous = false;
  recognition.maxAlternatives = 1;

  const cardId = lang === "hi" ? "hindi-card" : "english-card";
  const btnId = lang === "hi" ? "hindi-btn" : "english-btn";
  const waveId = lang === "hi" ? "hindi-wave" : "english-wave";

  const card = qs(cardId);
  const btn = qs(btnId);
  const txt = qs("transcript-text");
  const box = qs("transcript-box");

  if (card) card.classList.add("active");
  if (btn) {
    btn.classList.add("recording");
    btn.textContent = "⏹";
  }

  isRecording = true;

  if (txt) {
    txt.textContent = "";
    txt.classList.add("cursor-blink");
    txt.style.color = "var(--text)";
  }

  if (box) {
    box.classList.add("streaming");
  }

  const wave = animateWave(waveId);
  setStatus("listening", `Listening in ${lang === "hi" ? "हिंदी" : "English"}...`);

  recognition.onresult = (event) => {
    let finalText = "";
    let interimText = "";

    for (let i = event.resultIndex; i < event.results.length; i++) {
      const t = event.results[i][0].transcript;
      if (event.results[i].isFinal) {
        finalText += t;
      } else {
        interimText += t;
      }
    }

    if (txt) {
      txt.textContent = finalText + interimText;
    }
  };

  recognition.onend = async () => {
    stopWave(waveId, wave);

    if (card) card.classList.remove("active");
    if (btn) {
      btn.classList.remove("recording");
      btn.textContent = "🎤";
    }
    if (txt) txt.classList.remove("cursor-blink");
    if (box) box.classList.remove("streaming");

    isRecording = false;

    const finalText = txt ? txt.textContent.trim() : "";
    if (finalText) {
      await processSpeechToBackend(finalText);
    } else {
      setStatus("ready", "Ready to listen...");
    }
  };

  recognition.onerror = () => {
    stopWave(waveId, wave);

    if (card) card.classList.remove("active");
    if (btn) {
      btn.classList.remove("recording");
      btn.textContent = "🎤";
    }
    if (txt) txt.classList.remove("cursor-blink");
    if (box) box.classList.remove("streaming");

    isRecording = false;
    setStatus("ready", "Ready to listen...");
    showToast("Speech recognition error", "red");
  };

  recognition.start();
}

async function recordServerMic() {
  try {
    setStatus("processing", "Recording from server mic...");
    showProcessingBar();

    const res = await fetch("/record", { method: "POST" });
    const data = await res.json();

    if (!res.ok) {
      showToast(data.error || "Server mic failed", "red");
      setStatus("ready", "Ready to listen...");
      return;
    }

    const transcript = qs("transcript-text");
    if (transcript) {
      transcript.textContent = data.speech || "";
      transcript.style.color = "var(--text)";
    }

    if (data.cart) {
      currentCart = {
        items: Array.isArray(data.cart.items) ? data.cart.items : [],
        subtotal: Number(data.cart.subtotal || 0),
        gst: Number(data.cart.gst || 0),
        total: Number(data.cart.total || 0)
      };
    }

    renderCart();
    await previewReceipt();
    showToast("Audio processed");
    setStatus("ready", "Ready to listen...");
  } catch (err) {
    showToast("Server mic failed", "red");
    setStatus("ready", "Ready to listen...");
  }
}

async function uploadAudio() {
  try {
    const file = qs("audioFile").files[0];
    if (!file) {
      showToast("Select an audio file first", "red");
      return;
    }

    const form = new FormData();
    form.append("audio", file);

    setStatus("processing", "Uploading audio...");
    showProcessingBar();

    const res = await fetch("/upload_audio", {
      method: "POST",
      body: form
    });

    const data = await res.json();

    if (!res.ok) {
      showToast(data.error || "Upload failed", "red");
      setStatus("ready", "Ready to listen...");
      return;
    }

    const transcript = qs("transcript-text");
    if (transcript) {
      transcript.textContent = data.speech || "";
      transcript.style.color = "var(--text)";
    }

    if (data.cart) {
      currentCart = {
        items: Array.isArray(data.cart.items) ? data.cart.items : [],
        subtotal: Number(data.cart.subtotal || 0),
        gst: Number(data.cart.gst || 0),
        total: Number(data.cart.total || 0)
      };
    }

    renderCart();
    await previewReceipt();
    showToast("Audio uploaded and processed");
    setStatus("ready", "Ready to listen...");
  } catch (err) {
    showToast("Upload failed", "red");
    setStatus("ready", "Ready to listen...");
  }
}

async function previewReceipt() {
  try {
    const res = await fetch("/bill/preview");
    const data = await res.json();

    if (data.cart) {
      currentCart = {
        items: Array.isArray(data.cart.items) ? data.cart.items : [],
        subtotal: Number(data.cart.subtotal || 0),
        gst: Number(data.cart.gst || 0),
        total: Number(data.cart.total || 0)
      };
      renderCart();
    }

    const preview = qs("receipt-preview");
    if (preview) {
      preview.textContent = data.receipt_text || "No receipt preview available";
    }
  } catch (err) {
    showToast("Failed to preview receipt", "red");
  }
}

async function downloadBill() {
  try {
    const res = await fetch("/generate_bill", { method: "POST" });

    if (!res.ok) {
      const data = await res.json();
      showToast(data.error || "Bill generation failed", "red");
      return;
    }

    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = "receipt.pdf";
    document.body.appendChild(a);
    a.click();
    a.remove();

    window.URL.revokeObjectURL(url);

    await fetchCart();
    await previewReceipt();
    showToast("PDF bill downloaded");
  } catch (err) {
    showToast("Bill generation failed", "red");
  }
}

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function jsSafe(text) {
  return String(text).replaceAll("\\", "\\\\").replaceAll("'", "\\'");
}

createWaveform("hindi-wave");
createWaveform("english-wave");
createWaveform("server-wave");
loadShopInfo();
fetchCart();
previewReceipt();
setStatus("ready", "Ready to listen...");