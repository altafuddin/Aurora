# 🎯 Project Prompt for AI Co-Development

I'm building a voice-based AI web app to help non-native English speakers, especially(*not especially, like) learners from Bangladesh, improve their English speaking proficiency. The app has two main modes:

1. **IELTS Practice Mode** – with structured Parts 1–3 speaking questions and feedback aligned to IELTS Band Descriptors (fluency, coherence, lexical resource, grammar, pronunciation).  
2. **Free Chat Mode** – where the user speaks freely with the AI and receives periodic fluency tips and general feedback.

The app will use:
- **Voice input (mic)** → Transcription via STT  
- **LLM (via API initially)** → to handle conversation and generate feedback  
- **TTS** → for speaking responses in Free Chat Mode  
- The UI and backend will be deployed in the cloud; currently considering Gradio for simplicity, but open to better frameworks.

🔧 Architecture should prioritize performance, (*prioritize free of cost) and remain lightweight enough for free or low-tier cloud environments.

👥 Please consider common speech patterns of Bangladeshi English learners when designing feedback logic.(* exclude this)

💡 I want help with:
- Suggesting a modular architecture for both modes (IELTS and Free Chat)  
- Selecting lightweight, accurate STT and TTS tools (e.g., Whisper, Google STT, Nari, Coqui)  
- Building the system step-by-step using clean, testable Python modules  
- Writing feedback evaluation prompts and logic based on IELTS band descriptors  
- Designing general feedback strategies for Free Chat Mode  
- Keeping the system optimized for cloud deployment  

🚨 I want to approach this as a research-grade project — the final goal is a fully working web app and a publishable paper. Please guide me like a co-developer and research assistant.

(* I want to build prototype by 30 days, today is -(*date), start user test by 15th July, Present By 25th july)






