# AI Lecturer System - Quick Start Guide

## 🚀 Get Up and Running in 5 Minutes

### Prerequisites

- Python 3.11 (in venv)
- PDF lecture slides
- Gemini API key (free at https://makersuite.google.com/app/apikey)

---

## Step 1: Set Up Environment

```bash
cd /Users/skandavyassrinivasan/ai-lecturer-system/backend

# Activate virtual environment
source venv/bin/activate

# Install dependencies (if not already done)
pip install -r requirements.txt
```

---

## Step 2: Configure API Key

Edit `.env` file:

```bash
AI_PROVIDER=gemini
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

---

## Step 3: Test PDF Parsing

```bash
# Parse your PDF to see extracted content
python test_parse.py "/path/to/your/lecture.pdf"
```

**What you'll see**:
- Slide titles and bullet points
- Special academic content (definitions, theorems, etc.)
- Image count per slide
- Total slides parsed

---

## Step 4: Generate Narrations

```bash
# Generate narrations for first 5 slides (or more with --num-narrations N)
python test_gemini.py "/path/to/your/lecture.pdf" --num-narrations 5
```

**What happens**:
1. Parses all slides from PDF
2. Analyzes entire lecture with Gemini AI
3. Generates contextual narration for each slide
4. **Automatically caches results** to `cache/narrations/`
5. Shows token usage and cost (FREE!)

**Expected output**:
```
🚀 GEMINI 2.0 FLASH - FULL PIPELINE TEST
📄 PDF: /path/to/lecture.pdf
🤖 Model: Gemini 2.5 Flash
📝 Generating 5 sample narrations
💰 Cost: FREE! (1,500 requests/day limit)

📖 PHASE 1: Parsing PDF...
✅ Parsed 135 slides
📚 Found 112 special content items

🧠 PHASE 2: Building Global Context...
✓ Analysis complete

🎤 PHASE 3: Generating 5 Sample Narrations...
[Progress for each slide]

💾 Caching narrations...
✅ Cached 5 narrations
📁 Cache location: cache/narrations/Your_Lecture_narrations.json
```

---

## Step 5: Generate Audio

```bash
# Generate MP3 audio files from cached narrations
python test_tts.py
```

**Important**: Must run Step 4 first to have cached narrations!

**What happens**:
1. Loads cached narrations from `cache/narrations/`
2. Converts each narration to speech using Edge TTS
3. Saves MP3 files to `output/audio/slide_000.mp3`, etc.

**Expected output**:
```
🎤 EDGE TTS - AUDIO GENERATION TEST

✅ Found cached narrations for 'Your Lecture'
   Available slides: [0, 1, 2, 3, 4]

🔊 Generating audio for 5 slides...

📝 Slide 0:
   Text: Welcome to this course on Linear Optimization...
   Length: 250 chars, ~45 words
   Generating audio...
   ✅ Saved: output/audio/slide_000.mp3 (42.3 KB)

[Repeats for all slides]

📁 Audio files saved to: /Users/.../backend/output/audio
```

---

## Step 6: Listen to Generated Audio

Play any audio file:

```bash
# macOS
open output/audio/slide_000.mp3

# Or use any media player
```

---

## 🎯 What's Next?

### Option A: Generate Full Lecture

```bash
# Generate narrations for ALL slides (be mindful of free tier limit!)
python test_gemini.py "/path/to/lecture.pdf" --num-narrations 50

# Then generate audio for all
python test_tts.py  # Will process all cached narrations
```

**Note**: Watch your daily quota (1,500 requests/day on Gemini free tier)

### Option B: Build the Viewer UI

Next phase is to create a web interface that:
- Displays slide content
- Plays audio automatically
- Auto-advances to next slide
- Provides manual navigation

See `PROJECT_STATUS.md` for detailed next steps.

---

## 🔧 Common Commands

### Activate Virtual Environment
```bash
source venv/bin/activate
```

### Check Cached Narrations
```bash
ls -lh cache/narrations/
```

### Check Generated Audio
```bash
ls -lh output/audio/
```

### Clear Cache (Force Regeneration)
```bash
rm -rf cache/narrations/*
```

### Clear Audio Files
```bash
rm -rf output/audio/*
```

---

## ⚠️ Troubleshooting

### Module Not Found Error

**Problem**: `ModuleNotFoundError: No module named 'X'`

**Solution**:
```bash
source venv/bin/activate  # Make sure venv is activated!
pip install -r requirements.txt
```

### No Cached Narrations Found

**Problem**: `test_tts.py` says "No cached narrations found"

**Solution**: Run `test_gemini.py` first to generate narrations:
```bash
python test_gemini.py "/path/to/lecture.pdf" --num-narrations 5
```

### pydantic-core Build Failed

**Problem**: Wheel build error during pip install

**Solution**: Make sure you're using Python 3.11 in venv, not system Python:
```bash
source venv/bin/activate  # This uses Python 3.11
python --version  # Should show 3.11.x
pip install -r requirements.txt
```

### API Quota Exceeded

**Problem**: "Quota exceeded" error from Gemini

**Solution**:
- Wait until next day (quota resets daily)
- Or use a different API key
- Or upgrade to paid tier

---

## 📊 Current Capabilities

### ✅ Working Features

- [x] PDF parsing with academic content extraction
- [x] Global context analysis with Gemini AI
- [x] Context-aware narration generation
- [x] Privacy-safe output (no personal info)
- [x] TTS-compatible output (LaTeX converted to speech)
- [x] Narration caching (avoid regeneration)
- [x] Audio generation with Edge TTS
- [x] Free tier operation ($0 cost)

### 🚧 Coming Soon

- [ ] Web-based slide viewer
- [ ] Auto-advancing audio playback
- [ ] Manual slide navigation
- [ ] Progress indicators
- [ ] Session management
- [ ] Upload interface

---

## 💰 Cost Summary

| Service | Model/Provider | Cost |
|---------|---------------|------|
| **Analysis** | Gemini 2.5 Flash | $0 (free tier) |
| **Narration** | Gemini 2.5 Flash | $0 (free tier) |
| **TTS** | Edge TTS | $0 (always free) |
| **Storage** | Local files | $0 |
| **TOTAL** | - | **$0** |

**Free Tier Limits**:
- Gemini: 1,500 requests/day
- For 50-slide lecture: ~52 requests
- Can process ~28 lectures/day

---

## 📖 Additional Resources

- **Full Documentation**: `PROJECT_STATUS.md`
- **Example Scripts**: `test_parse.py`, `test_gemini.py`, `test_tts.py`
- **Data Models**: `app/models/slide.py`, `app/models/global_plan.py`
- **AI Providers**: `app/services/ai/` directory
- **TTS Service**: `app/services/tts/edge_tts_provider.py`

---

## 🎓 Example Workflow

Here's a complete workflow from PDF to audio:

```bash
# 1. Activate environment
source venv/bin/activate

# 2. Parse PDF to verify it works
python test_parse.py "Linear_Optimization_Slides.pdf"

# 3. Generate narrations (first 10 slides)
python test_gemini.py "Linear_Optimization_Slides.pdf" --num-narrations 10

# 4. Generate audio files
python test_tts.py

# 5. Listen to first slide
open output/audio/slide_000.mp3

# 6. (Optional) Generate narrations for all slides
python test_gemini.py "Linear_Optimization_Slides.pdf" --num-narrations 135

# 7. (Optional) Generate all audio
python test_tts.py
```

---

## 🆘 Need Help?

1. Check `PROJECT_STATUS.md` for detailed documentation
2. Review error messages carefully (they're usually informative)
3. Verify you activated venv (`source venv/bin/activate`)
4. Check `.env` file has correct API key
5. Make sure PDF path is correct (use absolute path or quotes for spaces)

---

**Last Updated**: December 26, 2025
**Status**: Core pipeline complete, viewer UI pending
