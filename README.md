# 🎤 Voice-Based E-Commerce Billing System

An AI-powered Point-of-Sale (POS) solution that enables shopkeepers to generate bills using voice commands in **Hindi and English**.

---

## 📌 Overview

Traditional billing systems require manual product entry, which is slow and error-prone.  
This project introduces a **voice-enabled billing system** that automates cart creation using AI.

It leverages:
- Speech-to-text conversion
- Natural Language Processing (NLP)
- Real-time cart management

---

## 🚀 Features

- 🎙️ Voice-based product entry
- 🌐 Bilingual support (Hindi + English)
- ⚡ Fast and accurate billing
- 🛒 Dynamic cart updates
- 📦 Intelligent product detection & variant handling
- ➕ AI-assisted addition of missing products
- 📄 Instant PDF receipt generation
- 🔄 Quantity normalization (kg, units, etc.)

---

## 🧠 How It Works

The system follows a processing pipeline:

1. **Audio Capture**
2. **Speech-to-Text Conversion (Whisper)**
3. **Entity Extraction (LLM)**
4. **Text Normalization**
5. **Cart Update & Billing**

---

## 🛠️ Tech Stack

### Backend
- Python (Flask)

### Database
- MongoDB (PyMongo)

### AI / ML
- OpenAI Whisper (Speech-to-Text)
- Ollama LLM (Entity Extraction)

### Frontend
- Modern Web Stack (API-based integration)

---

## 🏗️ System Architecture

- Multi-tenant SaaS platform
- RESTful API-based backend
- Real-time AI processing pipeline
- Local AI inference support

---

## 📊 Use Case

Ideal for:
- Grocery stores 🛒
- Retail shops 🏬
- Small businesses 🧾

---

## 🎯 Objectives

- Reduce billing time
- Improve accessibility using voice
- Minimize manual errors
- Enable smart inventory handling

---

## 📸 Demo Highlights

- Detects product variants (e.g., *Basmati Rice*)
- Handles unavailable products via AI assistant
- Automatically adjusts quantities and pricing

---

## ⚙️ Installation

```bash
# Clone the repository
git clone https://github.com/your-username/voice-billing-system.git

# Navigate into the project
cd voice-billing-system

# Install dependencies
pip install -r requirements.txt

# Run the server
python app.py
