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

  if (dot) dot.className = "status-dot " + type;
  if (text) text.textContent = msg;
}

function showToast(msg, color = "green") {
  const toast = qs("toast");
  const toastMsg = qs("toast-msg");

  if (!toast || !toastMsg) return;

  toastMsg.textContent = msg;
  toast.style.borderColor = color === "red" ? "var(--red)" : "var(--green)";
  toast.style.color = color === "red" ? "var(--red)" : "var(--green)";
  toast.classList.add("show");

  setTimeout(() => toast.classList.remove("show"), 3000);
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
  if (intervalId) clearInterval(intervalId);
  const container = qs(containerId);
  if (!container) return;
  const bars = container.querySelectorAll(".wave-bar");
  bars.forEach((bar) => bar.style.height = "4px");
}

function showProcessingBar() {
  const bar = qs("processing-bar");
  if (!bar) return;
  bar.classList.remove("active");
  void bar.offsetWidth;
  bar.classList.add("active");
}

async function fetchCart() {
  try {
    const res = await fetch("/cart");
    const data = await res.json();
    updateCartData(data);
  } catch (err) {
    showToast("Failed to fetch cart", "red");
  }
}

function updateCartData(data) {
  currentCart = {
    items: Array.isArray(data.items) ? data.items : [],
    subtotal: Number(data.subtotal || 0),
    gst: Number(data.gst || 0),
    total: Number(data.total || 0)
  };
  renderCart();
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
    if (receiptPreview) receiptPreview.textContent = "No receipt preview available";
    return;
  }

  container.innerHTML = currentCart.items.map((item) => {

    let variantHTML = "";
    if (item.available_variants && item.available_variants.length > 0) {
      let options = `<option value="">Select Variant</option>`;
      item.available_variants.forEach(v => {
        let vName = typeof v === 'string' ? v : v.name;
        let vPrice = typeof v === 'string' ? '' : ` (₹${v.price})`;
        let selected = (item.variant === vName) ? "selected" : "";
        options += `<option value="${jsSafe(vName)}" ${selected}>${escapeHtml(vName)}${vPrice}</option>`;
      });
      let reqClass = item.needs_variant ? 'variant-req' : '';
      variantHTML = `<select class="variant-drop ${reqClass}" onchange="changeVariant('${jsSafe(item.name)}', '${jsSafe(item.variant || '')}', this.value)">
            ${options}
        </select>`;
    } else {
      variantHTML = item.variant ? `<span style="font-size:12px;color:var(--accent);">${escapeHtml(item.variant)}</span>` : "";
    }

    return `
    <div class="cart-item">
      <div class="item-name">
        ${escapeHtml(item.display_name || item.name)}
        <span class="item-name-en" style="display:flex; align-items:center; gap:2px; margin-top:4px;">
          ₹<input type="number" step="0.01" value="${Number(item.price).toFixed(2)}" 
             onchange="changePrice('${jsSafe(item.name)}', '${jsSafe(item.variant || '')}', this.value)" 
             style="width: 60px; background: var(--surface2); color: var(--text); border: 1px solid var(--border); padding: 2px 4px; border-radius: 4px; font-size: 11px; outline: none; font-family: 'JetBrains Mono', monospace;" title="Edit Price">
          /${escapeHtml(item.unit)}
        </span>
      </div>
      <div>${variantHTML}</div>
      <div class="qty-control">
        <button class="qty-btn" onclick="changeQty('${jsSafe(item.name)}', '${jsSafe(item.variant || '')}', ${Number(item.quantity) - 1})">−</button>
        <span class="qty-num">${Number(item.quantity)}</span>
        <button class="qty-btn" onclick="changeQty('${jsSafe(item.name)}', '${jsSafe(item.variant || '')}', ${Number(item.quantity) + 1})">+</button>
      </div>
      <div class="item-price">₹${Number(item.line_total ?? item.total ?? 0).toFixed(2)}</div>
      <button class="remove-btn" onclick="removeItem('${jsSafe(item.name)}', '${jsSafe(item.variant || '')}')">✕</button>
    </div>
  `}).join("");

  totals.style.display = "block";

  if (qs("subtotal")) qs("subtotal").textContent = `₹${Number(currentCart.subtotal).toFixed(2)}`;
  if (qs("gst")) qs("gst").textContent = `₹${Number(currentCart.gst).toFixed(2)}`;
  if (qs("total")) qs("total").textContent = `₹${Number(currentCart.total).toFixed(2)}`;
}

async function changeVariant(name, oldVariant, newVariant) {
  if (newVariant === undefined || newVariant === null) return;
  try {
    const res = await fetch("/cart/update_variant", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, old_variant: oldVariant, new_variant: newVariant })
    });
    const data = await res.json();
    if (res.ok) { updateCartData(data); await previewReceipt(); }
  } catch (e) { showToast("Failed to update variant", "red"); }
}

async function changePrice(name, variant, price) {
  try {
    const res = await fetch("/cart/update_price", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, variant, price: Number(price) })
    });
    const data = await res.json();
    if (!res.ok) {
      showToast(data.error || "Failed to update price", "red");
      return;
    }
    updateCartData(data);
    await previewReceipt();
  } catch (err) {
    showToast("Failed to update price", "red");
  }
}

async function changeQty(name, variant, quantity) {
  try {
    if (quantity < 1) {
      await removeItem(name, variant);
      return;
    }
    const res = await fetch("/cart/update", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, variant, quantity })
    });
    const data = await res.json();
    if (!res.ok) {
      showToast(data.error || "Failed to update quantity", "red");
      return;
    }
    updateCartData(data);
    await previewReceipt();
  } catch (err) {
    showToast("Failed to update quantity", "red");
  }
}

async function removeItem(name, variant) {
  try {
    const res = await fetch("/cart/remove", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, variant })
    });
    const data = await res.json();
    if (!res.ok) {
      showToast(data.error || "Failed to remove item", "red");
      return;
    }
    updateCartData(data);
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
    updateCartData(data.cart || { items: [] });
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

// ------ CHATBOT LOGIC ------
function showChatSetup(message, lang = 'en-IN') {
  qs('chat-setup').style.display = 'block';
  qs('chat-message').textContent = message;
  qs('chat-input').value = '';
  qs('chat-input').focus();

  if ('speechSynthesis' in window) {
    window.speechSynthesis.cancel();
    const msg = new SpeechSynthesisUtterance(message);
    msg.lang = lang;
    window.speechSynthesis.speak(msg);
  }
}

function hideChatSetup() {
  qs('chat-setup').style.display = 'none';
}

async function sendChatReply(speechOverride = null) {
  const text = speechOverride || qs("chat-input").value.trim();
  if (!text) return;

  qs("chat-message").textContent = "Thinking...";
  qs("chat-input").value = "";

  try {
    const res = await fetch("/chatbot/turn", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ speech: text })
    });
    const data = await res.json();

    if (data.cart) {
      updateCartData(data.cart);
      await previewReceipt();
    }

    if (data.chat_response) {
      qs("chat-message").textContent = data.chat_response;

      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        const msg = new SpeechSynthesisUtterance(data.chat_response);
        msg.lang = data.lang || 'en-IN';
        window.speechSynthesis.speak(msg);
      }

      if (data.chat_response.includes("जुड़ गया") || data.chat_response.includes("छोड़ रही") || data.chat_response.includes("skipping") || data.chat_response.includes("Added")) {
        setTimeout(hideChatSetup, 3000);
      }
    } else {
      hideChatSetup();
    }
  } catch (e) {
    showToast("Chat error", "red");
  }
}

function startChatVoice() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) { showToast("Speech API not supported", "red"); return; }

  let chatRec = new SpeechRecognition();
  chatRec.lang = 'en-IN';
  const btn = qs("chat-mic-btn");
  btn.classList.add("recording");

  chatRec.onresult = (e) => {
    let final = "";
    for (let i = e.resultIndex; i < e.results.length; i++) {
      if (e.results[i].isFinal) final += e.results[i][0].transcript;
    }
    if (final) {
      btn.classList.remove("recording");
      sendChatReply(final);
    }
  };

  chatRec.onend = () => btn.classList.remove("recording");
  chatRec.onerror = () => btn.classList.remove("recording");
  chatRec.start();
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
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ speech: text })
    });

    const data = await res.json();

    if (!res.ok) {
      showToast(data.error || "Processing failed", "red");
      setStatus("ready", "Ready to listen...");
      return;
    }

    updateCartData(data.cart || { items: [] });
    await previewReceipt();

    if (data.chat_response) {
      showChatSetup(data.chat_response, data.lang);
    } else {
      hideChatSetup();
      if (data.added && data.added.length) {
        showToast(`Added ${data.added.length} item(s)`);
      } else if (data.not_found && data.not_found.length) {
        showToast(`Not found: ${data.not_found.join(", ")}`, "red");
      } else {
        showToast("No items matched", "red");
      }
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

  if (box) box.classList.add("streaming");

  const wave = animateWave(waveId);
  setStatus("listening", `Listening in ${lang === "hi" ? "हिंदी" : "English"}...`);

  recognition.onresult = (event) => {
    let finalText = "";
    let interimText = "";
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const t = event.results[i][0].transcript;
      if (event.results[i].isFinal) finalText += t;
      else interimText += t;
    }
    if (txt) txt.textContent = finalText + interimText;
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

let whisperMediaRecorder = null;
let whisperAudioChunks = [];
let isWhisperRecording = false;

async function toggleWhisperVoice() {
  const btn = qs("server-btn");
  const waveId = "server-wave";
  const wave = animateWave(waveId);
  const txt = qs("transcript-text");
  const box = qs("transcript-box");

  if (isWhisperRecording) {
    if (whisperMediaRecorder && whisperMediaRecorder.state !== "inactive") {
      whisperMediaRecorder.stop();
    }
    return;
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    whisperMediaRecorder = new MediaRecorder(stream);
    whisperAudioChunks = [];
    isWhisperRecording = true;

    if (btn) {
      btn.classList.add("recording");
      btn.textContent = "⏹";
    }
    if (txt) {
      txt.textContent = "";
      txt.classList.add("cursor-blink");
      txt.style.color = "var(--text)";
    }
    if (box) box.classList.add("streaming");
    setStatus("listening", "Listening (AI Whisper)...");

    whisperMediaRecorder.ondataavailable = event => {
      whisperAudioChunks.push(event.data);
    };

    whisperMediaRecorder.onstop = async () => {
      isWhisperRecording = false;
      stopWave(waveId, wave);
      stream.getTracks().forEach(track => track.stop());

      if (btn) {
        btn.classList.remove("recording");
        btn.textContent = "🧠";
      }
      if (txt) txt.classList.remove("cursor-blink");
      if (box) box.classList.remove("streaming");

      setStatus("processing", "Transcribing with AI...");
      showProcessingBar();

      const audioBlob = new Blob(whisperAudioChunks, { type: 'audio/webm' });
      const form = new FormData();
      form.append("audio", audioBlob, "recording.webm");

      try {
        const res = await fetch("/upload_audio", { method: "POST", body: form });
        const data = await res.json();
        
        if (data.speech) {
            await processSpeechToBackend(data.speech);
        } else {
            setStatus("ready", "Ready to listen...");
            showToast(data.error || "No speech detected", "red");
        }
      } catch (err) {
        showToast("AI Transcription failed", "red");
        setStatus("ready", "Ready to listen...");
      }
    };

    whisperMediaRecorder.start();
  } catch (err) {
    stopWave(waveId, wave);
    showToast("Mic access denied", "red");
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

    if (data.speech) {
      await processSpeechToBackend(data.speech);
    } else {
      setStatus("ready", "Ready to listen...");
    }

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
      updateCartData(data.cart);
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
fetchCart();
previewReceipt();
setStatus("ready", "Ready to listen...");