# 🎓 AI Lecturer System

> Transform static lecture slides into engaging, narrated presentations with AI-powered global context understanding.

**Status**: ✅ Core pipeline complete | 🚧 Web viewer pending

---

## 🌟 Overview

An autonomous AI lecturer system that:
1. **Ingests** PDF lecture slides with academic content extraction
2. **Analyzes** the entire lecture to build global context (BEFORE generating narration)
3. **Generates** contextual, pedagogical narration for each slide
4. **Converts** narration to natural-sounding speech (TTS)
5. **Delivers** synchronized slide viewer with auto-advancing audio (coming soon)

**Key Innovation**: Global-first approach ensures narrative continuity and pedagogical coherence across the entire lecture.

---

## ✨ Features

### ✅ Currently Working

- **PDF Parsing** with special content extraction (definitions, theorems, proofs, examples, etc.)
- **Global Context Building** using Gemini 2.5 Flash (FREE tier)
- **Context-Aware Narration** that references prior material and prepares for what's next
- **Privacy-Safe Output** (no instructor names, universities, or personal info)
- **TTS-Compatible** (all LaTeX converted to spoken form)
- **Narration Caching** to avoid regenerating expensive AI calls
- **Audio Generation** with Edge TTS (FREE, no API key needed)
- **Model-Agnostic Architecture** (easy to swap AI providers)

### 🚧 Coming Soon

- Web-based slide viewer with synchronized audio playback
- Auto-advancing slides based on narration length
- Manual navigation controls
- Upload interface for PDFs
- Session management and persistence

---

## 🚀 Quick Start

### 1. Setup (One-time)

```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt

# Add your Gemini API key to .env
echo "GEMINI_API_KEY=your_key_here" >> .env
```

Get a free API key: https://makersuite.google.com/app/apikey

### 2. Generate Narrations

```bash
python test_gemini.py "/path/to/lecture.pdf" --num-narrations 5
```

This will:
- Parse your PDF slides
- Build global context with AI
- Generate narrations for first 5 slides
- Cache results automatically

### 3. Generate Audio

```bash
python test_tts.py
```

This will:
- Load cached narrations
- Convert to speech using Edge TTS
- Save MP3 files to `output/audio/`

### 4. Listen

```bash
open output/audio/slide_000.mp3
```

**For detailed instructions**, see [QUICKSTART.md](QUICKSTART.md)

---

## 📖 Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Get up and running in 5 minutes
- **[PROJECT_STATUS.md](PROJECT_STATUS.md)** - Comprehensive documentation, architecture, and development history

---

## 🏗️ Architecture

```
PDF Input → Parser → Global Context Builder → Narration Generator → TTS → Audio Output
              ↓              ↓                         ↓              ↓
         SlideContent  GlobalContextPlan      NarrationSegments   MP3 Files
                                                     ↓
                                              Narration Cache
                                              (avoid regen)
```

**Three-Phase Processing**:
1. **Phase 1**: Slide ingestion with academic content extraction
2. **Phase 2**: Global context building (structure + vision analysis)
3. **Phase 3**: Per-slide narration generation with full context

---

## 🛠️ Tech Stack

### Backend (Current)
- **Framework**: FastAPI (Python 3.11)
- **PDF Parsing**: PyMuPDF + pymupdf4llm
- **AI Provider**: Gemini 2.5 Flash (FREE tier, 1,500 req/day)
- **TTS**: Edge TTS (FREE, no API key)
- **Data Models**: Pydantic v2
- **Storage**: JSON caching (session-only, no database)

### Frontend (Planned)
- **Framework**: Next.js 14+ with App Router
- **UI**: shadcn/ui + Tailwind CSS
- **State**: Zustand or React Context
- **Communication**: Server-Sent Events (SSE)

---

## 💰 Cost

**Completely FREE** for prototyping:
- ✅ Gemini 2.5 Flash analysis & narration: $0
- ✅ Edge TTS audio generation: $0
- ✅ Local caching & storage: $0

**Free Tier Limits**:
- 1,500 Gemini requests/day
- Can process ~28 full lectures per day (50 slides each)

**Production Upgrade** (optional):
- Claude Sonnet 4.5: ~$1-2 per 50-slide lecture
- Claude Opus 4.5: ~$5-6 per 50-slide lecture
- DeepSeek: ~$0.10-0.20 per 50-slide lecture

---

## 📊 Example Output

### Phase 1: PDF Parsing
```
📖 PHASE 1: Parsing PDF...
✅ Parsed 135 slides
📚 Found 112 special content items
   Breakdown:
      • definition: 45
      • theorem: 28
      • corollary: 18
      • example: 21
🖼️  Found 47 images across all slides
```

### Phase 2: Global Context
```
🧠 PHASE 2: Building Global Context...
✅ Analysis complete

📋 GLOBAL CONTEXT SUMMARY:
   Title: Linear Optimization
   Total Slides: 135
   Sections: 8
   Learning Objectives: 12
   Terminology: 67 terms
   Key Diagrams: 23
```

### Phase 3: Narration Generation
```
🎤 PHASE 3: Generating 5 Sample Narrations...
   [1/5] Slide 1: Introduction to Linear Programming...
         ✓ Generated 287 words
   [2/5] Slide 2: Mathematical Formulation...
         ✓ Generated 245 words
   ...

💾 Caching narrations...
✅ Cached 5 narrations
```

### Audio Generation
```
🔊 Generating audio for 5 slides...

📝 Slide 0:
   Length: 287 words
   ✅ Saved: output/audio/slide_000.mp3 (42.3 KB)

✅ Audio generation complete!
📁 Audio files saved to: /Users/.../backend/output/audio
```

---

## 🎯 Use Cases

- **Professors**: Convert lecture slides into narrated videos
- **Students**: Study with auto-narrated lecture content
- **Course Designers**: Create online course materials quickly
- **MOOCs**: Generate narrated lectures at scale
- **Corporate Training**: Transform slide decks into engaging training modules
- **Accessibility**: Provide audio alternatives for visual learners

---

## 🔬 What Makes This Different?

### 1. Global-First Approach
Unlike slide-by-slide generation, we analyze the ENTIRE lecture first:
- ✅ Maintains narrative continuity
- ✅ Enables accurate cross-references
- ✅ Consistent terminology usage
- ✅ Pedagogically coherent progression

### 2. Academic Content Awareness
Extracts and preserves special content types:
- Definitions, Theorems, Corollaries, Lemmas
- Proofs, Examples, Remarks, Axioms
- Enables richer, more accurate narration

### 3. Privacy & Reusability
- ❌ No instructor names, universities, or personal info
- ✅ Generic, professional narration
- ✅ Reusable across institutions
- ✅ TTS-compatible (no LaTeX syntax)

### 4. Free to Prototype
- $0 cost during development
- Test and iterate without budget constraints
- Scale to paid models only when ready

---

## 📁 Project Structure

```
backend/
├── app/
│   ├── models/           # Data models (Pydantic)
│   ├── services/
│   │   ├── parsers/      # PDF parsing
│   │   ├── ai/           # AI provider implementations
│   │   ├── tts/          # Text-to-speech
│   │   └── global_context_builder.py
│   └── api/              # FastAPI endpoints (coming soon)
├── cache/                # Cached narrations
├── output/               # Generated audio files
├── test_parse.py         # Test PDF parsing
├── test_gemini.py        # Test full pipeline
└── test_tts.py           # Test audio generation

frontend/                 # Coming soon
```

---

## 🧪 Testing

### Test PDF Parsing
```bash
python test_parse.py "/path/to/lecture.pdf"
```

### Test Full Pipeline
```bash
python test_gemini.py "/path/to/lecture.pdf" --num-narrations 10
```

### Test TTS Audio
```bash
python test_tts.py
```

All test scripts include detailed output and progress tracking.

---

## 🛣️ Roadmap

### Phase 1-5: ✅ Complete
- [x] PDF parsing with academic content extraction
- [x] Global context building
- [x] Narration generation
- [x] TTS integration
- [x] Narration caching

### Phase 6: 🚧 In Progress
- [ ] Web-based slide viewer
- [ ] Audio playback with auto-advance
- [ ] Manual navigation controls
- [ ] Progress tracking UI

### Future Enhancements
- [ ] Multi-language support
- [ ] Custom voice selection
- [ ] Narration editing & regeneration
- [ ] Export to video (slides + audio)
- [ ] Database persistence
- [ ] User accounts & lecture libraries
- [ ] Mobile-responsive viewer

---

## 🤝 Contributing

This is currently a personal project. Documentation and code are provided for reference.

---

## 📝 License

Private project - not yet licensed for public use.

---

## 🆘 Support

See [QUICKSTART.md](QUICKSTART.md) for common issues and troubleshooting.

For detailed documentation, see [PROJECT_STATUS.md](PROJECT_STATUS.md).

---

## 📊 Statistics

- **Lines of Code**: ~3,500 (Python backend)
- **AI Providers**: 3 (Gemini, Claude, DeepSeek)
- **Special Content Types**: 11 academic categories
- **Test Coverage**: PDF parsing, global context, narration, TTS
- **Development Time**: ~1 intensive session (December 2025)

---

## 🎓 Example Lecture Processing

**Input**: 135-slide Linear Optimization PDF

**Output**:
- 135 parsed slides with titles, bullets, and content
- 112 special academic items extracted (definitions, theorems, etc.)
- 47 images identified for vision analysis
- 8 sections detected with learning objectives
- 67 terminology terms defined
- 23 key diagrams highlighted
- Context-aware narration for each slide
- Natural-sounding MP3 audio files

**Processing Time**: ~3-5 minutes for full lecture

**Cost**: $0.00 (using free tiers)

---

**Built with ❤️ for better education delivery**

Last Updated: December 26, 2025
