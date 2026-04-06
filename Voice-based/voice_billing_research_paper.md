# Research Paper: Voice-Based E-Commerce Billing System - An AI-Powered Point-of-Sale Solution

## Abstract
Traditional Point-of-Sale (POS) systems require manual entry of products, quantities, and prices, which can be time-consuming and prone to human error, particularly in fast-paced retail and grocery environments. This paper presents a Voice-Based E-commerce Billing System, a multi-tenant SaaS that employs conversational AI to streamline the billing process. Using OpenAI's Whisper for robust speech-to-text transcription and an Ollama-backed Large Language Model for entity extraction, the system automatically translates bilingual (Hindi and English) spoken commands into actionable cart operations. The system dynamically handles missing products through an interactive chatbot, supports temporary item creation, handles variants organically, and features robust fallback parsing to ensure uninterrupted billing.

---

## 1. Introduction
The objective of this project is to create an intuitive, voice-activated billing assistant for shopkeepers. By allowing merchants to simply state items they are selling in natural language (e.g., "Add one kilo of basmati rice and two packets of maggi"), the system aims to minimize checkout times.

### 1.1 Core Objectives
*   **Speed:** Reduce the time to populate a shopping cart using voice input.
*   **Accessibility:** Enable billing using vernacular languages (Hindi and Hinglish) alongside English.
*   **Dynamic Inventory:** Identify when a spoken product does not exist in the database and autonomously launch a conversational flow to seamlessly add it.
*   **Usability:** Allow smooth value correction, variant handling (e.g., Kolam Rice vs. Basmati Rice), and instant PDF receipt generation.

---

## 2. System Architecture & Methodology
The system architecture spans a Next-Generation web stack combined with local AI inferencing.

### 2.1 Technology Stack
*   **Backend:** Python (Flask) providing RESTful APIs.
*   **Database:** MongoDB (PyMongo) handling users, multi-tenant shops, products, temporary products, chat sessions, and generated bills.
*   **Speech-to-Text (STT):** OpenAI's Whisper model (`whisper` base model) processes real-time uploaded audio locally for transcription.
*   **Natural Language Processing (NLP):** A local LLM powered by Ollama converts speech strings into structured JSON payloads parsing product names, prices, quantities, and valid units.

### 2.2 Input Pipeline and Conversational Flow
1.  **Audio Capture & STT:** Audio captured from the frontend is uploaded via the `/upload_audio` endpoint and transcribed by Whisper.
2.  **Normalization:** The Hindi/English text is normalized using a custom `HINDI_MAP` and `NUMBER_WORDS` mapping routine to convert colloquial measurements and item names directly into database-friendly formats.
3.  **LLM Entity Extraction:** The normalized text, along with a dynamic list of shop products, is fed to the Ollama model. The system prompts the LLM to output a JSON containing quantities, product names, and units—ignoring extraneous grammar or bullet numbering.
4.  **Fallback Heuristics:** In scenarios where the LLM times out or fails to return valid JSON, a regex-based fallback extractor (`fallback_extract`) kicks in capable of segmenting items by newline, "and", or "aur", and reliably parsing fractions and attached units.
5.  **Stateful Fallback Chatbot:** If extracted items do not heavily match existing database entries (via `difflib.SequenceMatcher`), the system updates a `chat_sessions` document, initiating an interactive fallback to ask the user, "Item X not found. Should I add it?" and subsequent queries for price and weights.

---

## 3. Key Implementations & Overcoming Challenges

Throughout the project lifecycle, several critical challenges were addressed as noted during testing phases:

### 3.1 Resolving Entity Extraction Failures
*   **Multi-Word Products:** Initial implementations split complex product names (e.g., "besan peda" or "kolam rice"). The LLM prompts and deterministic fallback extractors were revamped to enforce single-entity treatment for descriptive nouns. 
*   **Bulk Product Parsing:** Heavy grocery lists spanning fractions (e.g., 1.5kg, 1/4kg) and bulleted patterns often derailed the LLM. We hardened the `fallback_extract` pipeline to replace fractional text strings ("1/4" -> 0.25) before regex tokenization. System timeouts were elevated to 120 seconds for processing highly dense bulk lists reliably.

### 3.2 Product Value Verification and Correction System
*   **Cart Price Modification:** A dedicated API endpoint (`/cart/update_price`) and database update logic was established. This allows shopkeepers to manually intervene, updating prices within the active session cart—a crucial component for price fluctuations or bad acoustic parses.
*   **Unit Conversions:** Implemented logic within the `chatbot_turn` state machine to seamlessly handle dimensional normalization. For an input of "200 grams", the system mathematically adapts it in association with standard structural formats like kilograms during temporary product addition.

### 3.3 Dynamic Variant Creation Framework
Instead of forcing hard schemas for product varieties, we implemented string-matching heuristic checks across base items. For instance, parsing "kolam rice" checks existing suffixes toward base catalog items ("rice") and organically establishes "kolam" as a valid variant mapping containing its own pricing array.

---

## 4. Test Cases and Methodologies

The project primarily utilizes comprehensive input stress-testing. Important parameters validated include:
1.  **Bilingual Handling Test:** E.g., User prompt: *"एड वन इयररिंग"* (Add one earring) or *"आई वांट टू टूथपेस्ट"*. Ensured `extract_entities` returns positive translation without failing out on Devanagari script processing.
2.  **Complex Metrics Check:** Test input: "Kaju Katli at 200 per 200gm". Tested the dynamic addition routing ensuring "Kaju Katli" triggers variant creation or temporary creation correctly recording dimensional units inside MongoDB.
3.  **Bulk List Resilience Check:** Passed continuous list arrays exceeding 20+ items (mixing Devanagari and decimals) ensuring fallback functions engage when LLM processing hits token or length barriers.

---

## 5. Limitations

1.  **Acoustic & Hardware Dependencies:** Effectiveness relies heavily on the microphone quality of the user's terminal to prevent false positives generated by background market noise.
2.  **Latency Spikes:** Relying on extensive LLM prompts mapping out complete shop inventory references for every NLP translation inherently triggers inference delay linearly tied to shop inventory size.
3.  **Lack of Disambiguation on Synonyms:** Certain vernacular dialect shifts for the same item might create redundant separate temporary products if they breach the fuzzy-matching 0.65 threshold logic.

---

## 6. Future Scope

1.  **Retrieval-Augmented Generation (RAG) implementation:** Transitioning from injecting the entire available shop inventory into the Prompt to using vector-embedded similarity checks to supply the LLM with only the statistically likely closest products, sharply cutting down token cost and latency.
2.  **Streaming Architecture:** Implementing websocket-enabled STT streams to parallelize voice-transcription and text entity extraction before the user has finished speaking their entire order. 
3.  **Audio Noise Filtering Algorithms:** Implement real-time spectral subtraction or voice-activity detection (VAD) algorithms immediately before the Whisper handler to drastically clean raw files.
4.  **Hardware Extension:** Interface the resulting PDF and system calls directly with thermal ESC/POS receipt printers for physical output.

## 7. Attached Screenshots / Supplemental Material
*(To be inserted by author - Include screenshots demonstrating Dashboard, Fallback Chat flow, Cart UI price modification, and Bilingual transcriptions in this final documentation).*
