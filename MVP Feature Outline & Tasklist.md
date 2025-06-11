# 🧩 IELTS AI Speaking Coach – MVP Feature Outline & Tasklist

## 🎯 Goal

A cloud-deployed, voice-based web app to help Bangladeshi learners improve English speaking proficiency, with a focus on IELTS Speaking preparation and general fluency practice.

---

## ✅ Feature Outline

### 🎛️ Modes

#### 1. IELTS Practice Mode
- Structured sequence: Part 1 → Part 2 → Part 3
- Voice input for each answer
- Transcription via STT
- Band-based feedback (aligned to IELTS descriptors)
- Summary report at end of session

#### 2. Free Chat Mode
- Open-ended conversation with AI
- Voice input and AI responses
- General fluency feedback every 5 turns
- Optional TTS output of AI replies

---

## 🛠️ System Components

- **STT (Speech-to-Text)**  
  - Accepts voice input from mic (Gradio or alternative UI)
  - Transcribes into text using Whisper, Google STT, or similar

- **LLM (Language Model)**  
  - Handles AI dialogue and feedback generation
  - Initially API-based (OpenAI / HF), later switch to local model

- **TTS (Text-to-Speech)**  
  - Optional for reading AI responses aloud
  - Targeted for Free Chat mode

- **Feedback Engine**  
  - IELTS-specific prompts to generate band-based feedback
  - General fluency tips for Free Chat mode
  - Adapted to Bangladeshi learner patterns (pronunciation, structure, etc.)

- **UI/UX**  
  - Mode selector: IELTS / Free Chat
  - Voice recorder
  - Chat transcript display
  - Feedback panel
  - Scrollable chat history

---

## 📋 Tasklist (Dev Roadmap)

### 🧱 Setup & Structure
- [ ] Create GitHub repo and scaffold folders (`/data`, `/src`, `/notebooks`, etc.)
- [ ] Add `project_prompt.md`, `FEATURES_AND_TASKLIST.md`, and `README.md`
- [ ] Initialize Gradio (or chosen) UI with mic input and mode switch
- [ ] Prepare JSON file with IELTS Part 1–3 questions

### 🔊 Voice Input & STT
- [ ] Integrate mic input
- [ ] Transcribe using chosen STT tool
- [ ] Display transcript before sending to AI

### 🧠 AI Interaction (LLM)
- [ ] Connect to LLM (OpenAI or HF Inference API)
- [ ] Implement question-answer loop in IELTS mode
- [ ] Implement Free Chat interaction loop

### 📈 Feedback System
- [ ] Design prompt templates for IELTS feedback (per part + summary)
- [ ] Implement feedback scoring and response display
- [ ] Implement general fluency feedback (Free Chat mode, every 5 turns)

### 📦 TTS Output (Optional for MVP)
- [ ] Integrate TTS for AI responses (Free Chat mode)
- [ ] Play back AI response after each turn

### 🎯 MVP Polish
- [ ] Display chat history above input
- [ ] Show turn-based state in IELTS mode
- [ ] Add basic styling and instruction text
- [ ] Create requirements.txt and push to GitHub
- [ ] Deploy to cloud (e.g., Hugging Face or better alternative)

---

> Final Goal: A working, cloud-deployed web app + foundation for a publishable research paper.

