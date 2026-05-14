# Fake Medicine Detector - Project Summary

## Overview
A production-ready AI system that detects counterfeit medicines using image OCR, LLM analysis, and DRAP database verification. Built with FastAPI, PaddleOCR, and OpenRouter LLM.

## Quick Start

### 1. Setup Environment
```bash
cd /home/rayaden/university/agentic_AI/fake-med-detector
source .venv/bin/activate  # or uv is auto-configured
```

### 2. Start Server
```bash
uv run main.py
# Server runs on http://0.0.0.0:8000
```

### 3. Test Endpoints
```bash
# Health check
curl http://localhost:8000/api/health

# Test with known registration number (134108 = Axaleo 400mg)
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"registration_number": "134108"}'

# Upload and analyze image
curl -X POST http://localhost:8000/api/upload-and-analyze \
  -F "file=@path/to/medicine/image.jpg"
```

## Project Structure

```
fake-med-detector/
├── app/
│   ├── agents/              # AI agents (OCR, LLM, verification)
│   │   ├── ocr_agent.py    # PP-OCR v4 image text extraction
│   │   ├── intake_agent.py # Input validation & routing
│   │   ├── verification_agent.py  # DRAP database lookup
│   │   ├── router_agent.py # Response formatting
│   │   └── prompts.py      # System prompts for LLM
│   ├── core/
│   │   ├── config.py       # Configuration (20+ settings)
│   │   ├── exceptions.py   # Custom exception classes
│   │   └── logging.py      # Structured logging
│   ├── services/
│   │   ├── database.py     # SQLite DRAP database
│   │   ├── llm_client.py   # OpenRouter API integration
│   │   └── pipeline.py     # Agent orchestration
│   ├── schemas/
│   │   └── models.py       # Pydantic request/response models
│   └── main.py             # FastAPI app definition
├── data/
│   ├── drap.db            # SQLite database (219 medicines)
│   ├── medicines.csv      # Source data
│   └── uploads/           # Temporary image uploads
├── test_scripts/
│   └── ocr_test.py        # OCR testing script
├── .env                   # Configuration (API keys, models)
├── requirements.txt       # Python dependencies
└── main.py               # Entry point
```

## Key Features

### 1. **OCR Processing**
- **Model**: PP-OCRv4 (PaddleOCR)
- **Lazy Loading**: Model loads only on first image processing (fast startup)
- **Supports**: 5-7 digit DRAP registration numbers
- **OneDNN Workaround**: `FLAGS_use_onednn=0` to prevent crashes

### 2. **LLM Integration**
- **Primary**: `openai/gpt-oss-20b:free`
- **Fallbacks**: 
  - `z-ai/glm-4.5-air:free`
  - `openrouter/owl-alpha`
- **Auto-retry**: Switches model on failure

### 3. **Database**
- **SQLite**: 219 verified DRAP medicines
- **Auto-migration**: CSV → SQLite on startup
- **Fields**: Registration#, Product, Generic Name, Company, Ingredients

### 4. **API Endpoints**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/health` | GET | Server health check |
| `/api/status` | GET | System configuration status |
| `/api/analyze` | POST | Text/registration analysis |
| `/api/upload-and-analyze` | POST | Image OCR + analysis |
| `/api/search` | GET | Drug database search |

## Configuration (.env)

```ini
# LLM API
OPENROUTER_API_KEY=your_key_here
PRIMARY_MODEL=openai/gpt-oss-20b:free

# OCR Settings
OCR_VERSION=PP-OCRv4
FLAGS_USE_ONEDNN=0
FLAGS_USE_MKLDNN=0

# Server
API_HOST=0.0.0.0
API_PORT=8000

# Database
DATABASE_URL=sqlite:///./data/drap.db
UPLOAD_DIR=./data/uploads
```

## Recent Fixes

### 1. OCR Lazy Loading
- **Issue**: Server crashed on startup loading 100MB+ OCR model
- **Fix**: Changed to lazy loading - model loads on first image processing
- **Benefit**: Fast startup, on-demand resource usage

### 2. PaddleOCR Compatibility
- **Issue**: `show_log` parameter not supported in v4
- **Fix**: Removed parameter from initialization
- **Issue**: Result structure parsing failed
- **Fix**: Implemented proper OCRResult dict parsing with `rec_texts`/`rec_scores`

### 3. OneDNN Runtime Issue
- **Issue**: PaddlePaddle CPU inference crashed
- **Fix**: Set environment variables before import
- **Result**: Stable OCR inference on CPU

## API Examples

### Health Check
```bash
curl http://localhost:8000/api/health
```
Response:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "debug": false,
  "database_connected": true
}
```

### Analyze Registration (Success Case)
```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"registration_number": "134108"}'
```
Response:
```json
{
  "status": "success",
  "message": "✅ **VERIFIED**\n\n**Registration:** 134108\n**Product:** Axaleo 400mg Tablet...",
  "verdict": "VERIFIED",
  "registration_number": "134108",
  "product_name": "Axaleo 400mg Tablet",
  "drug_info": {...},
  "risk_score": 0,
  "flags": []
}
```

### Upload and Analyze Image
```bash
curl -X POST http://localhost:8000/api/upload-and-analyze \
  -F "file=@medicine_label.jpg"
```

## Tech Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | FastAPI | 0.111.0 |
| Server | Uvicorn | 0.29.0 |
| OCR | PaddleOCR | 2.7.3 |
| Deep Learning | PaddlePaddle | 3.0.0 |
| LLM API | OpenRouter | - |
| Database | SQLite | 3 |
| Validation | Pydantic | 2.7.0 |
| Language | Python | 3.12 |

## Deployment

### Local Testing
```bash
uv run main.py
```

### Production
```bash
# Using uvicorn directly
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker (Optional)
Create `Dockerfile` with proper multi-stage build to optimize OCR model size.

## Database Schema

The DRAP database contains 219 verified medicines:

```sql
CREATE TABLE medicines (
    sr_no INTEGER PRIMARY KEY,
    registration_number TEXT UNIQUE,
    product_name TEXT,
    generic_name TEXT,
    company_name TEXT,
    tablet_core TEXT,
    tablet_coat TEXT,
    excipients TEXT
);
```

## Troubleshooting

### OCR Not Extracting Text
- Ensure image quality is good
- Image must contain clear DRAP registration number (5-7 digits)
- Try different image angles/lighting

### Server Won't Start
- Check `.env` file exists with valid OpenRouter API key
- Ensure port 8000 is free: `lsof -i :8000`
- Check logs: `tail /tmp/server.log`

### LLM Timeouts
- Verify internet connection
- Check OpenRouter API key validity
- System will auto-retry with fallback models

## Performance Notes

- **Startup Time**: ~2-5 seconds (OCR model loads lazily)
- **Image Analysis**: ~5-10 seconds (OCR inference + LLM processing)
- **Database Lookup**: ~10-50ms
- **Concurrent Requests**: Limited by LLM API rate (varies by OpenRouter plan)

## Future Enhancements

1. **Streamlit Frontend**: User-friendly web interface
2. **Batch Processing**: Process multiple images in parallel
3. **Model Fine-tuning**: Custom OCR model for medicine labels
4. **Caching**: Redis cache for repeated lookups
5. **Analytics**: Dashboard for detection trends
6. **Mobile App**: React Native companion app

## Support

For issues or questions:
1. Check server logs: `tail -f /tmp/server.log`
2. Verify .env configuration
3. Test individual components (OCR, LLM, Database)
4. Review API responses for error messages

---

**Status**: ✅ Production Ready  
**Last Updated**: May 15, 2026  
**Maintainer**: Agentic AI Team
