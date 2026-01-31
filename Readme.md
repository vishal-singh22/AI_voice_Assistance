# 🎤 Voice-Based Interview System

A production-ready voice interview platform built with FastAPI, Deepgram (STT/TTS), and Groq LLM. Conduct technical interviews using voice interaction with automatic scoring and results tracking.

## 📋 Features

### Admin Dashboard
- Create interviews with customizable settings
- Toggle between database questions and LLM-generated questions
- Auto-generate candidate credentials
- View all candidates and their results
- Detailed scoring breakdown
- Soft delete candidates

### Candidate Experience
- Simple email/password login
- Pre-interview instructions
- Real-time voice interview with WebSocket
- Speech-to-text transcription
- Text-to-speech questions
- Automatic scoring
- Detailed results page

### Terminal Demo
- Run demo interviews from command line
- 5 pre-configured questions
- Voice interaction via microphone
- Real-time scoring
- Results summary in terminal

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Microphone (for voice input)
- Speaker/headphones (for audio output)
- Groq API key
- Deepgram API key

### Installation

1. **Clone and setup**
```bash
git clone <repository>
cd voice-interview-system
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure environment**
```bash
cp .env.example .env
# Edit .env and add your API keys
```

3. **Create directories**
```bash
mkdir -p logs data static/css static/js templates/admin templates/candidate
```

4. **Run the application**
```bash
python main.py
```

Access the application at: `http://localhost:8000`

## 📁 Project Structure

```
voice-interview-system/
├── app/
│   ├── config.py              # Configuration
│   ├── database.py            # Database setup
│   ├── models.py              # SQLAlchemy models
│   ├── schemas.py             # Pydantic schemas
│   ├── crud.py                # Database operations
│   ├── auth.py                # Authentication
│   ├── scoring.py             # Keyword-based scoring
│   ├── questions.py           # Question management
│   ├── assistant.py           # Base voice assistant
│   ├── interview_assistant.py # Interview-specific assistant
│   └── local_assistant.py     # Terminal demo assistant
├── routers/
│   ├── admin.py               # Admin endpoints
│   ├── candidate.py           # Candidate endpoints
│   └── interview.py           # WebSocket interview
├── templates/                 # HTML templates
├── static/                    # CSS and JavaScript
├── data/
│   └── questions.json         # Question database
├── logs/                      # Application logs
├── main.py                    # FastAPI application
├── terminal_demo.py           # Terminal demo script
└── requirements.txt
```

## 🎯 Usage Guide

### Admin Workflow

1. **Access admin dashboard**: `http://localhost:8000/admin`

2. **Create interview**:
   - Click "Create Interview"
   - Fill in: Name, Role, Number of Questions
   - Toggle LLM questions ON/OFF
   - Click "Create Interview"
   - Copy generated credentials

3. **Share credentials** with candidate:
   - Email
   - Password
   - Interview URL

4. **Monitor candidates**:
   - Click "View Candidates"
   - See real-time status
   - View detailed results
   - Remove candidates if needed

### Candidate Workflow

1. **Login**: Navigate to candidate login page
2. **Read instructions**: Review requirements and tips
3. **Start interview**: Click "Start Interview"
4. **Answer questions**:
   - Listen to each question
   - Speak your answer clearly
   - Wait for system to detect completion
5. **View results**: See score and pass/fail status

### Terminal Demo

Run the terminal demo for testing:

```bash
python terminal_demo.py
```

The demo will:
- Load 5 questions for software engineers
- Use your microphone for answers
- Score each answer
- Display final results

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GROQ_API_KEY` | Groq API key (required) | - |
| `DEEPGRAM_API_KEY` | Deepgram API key (required) | - |
| `LLM` | Groq model to use | llama-3.1-8b-instant |
| `DATABASE_URL` | Database connection | sqlite:///./interview_system.db |
| `INTERVIEW_TIMEOUT` | Max interview duration (seconds) | 1800 |
| `PASSING_SCORE` | Minimum passing percentage | 70.0 |
| `ADMIN_USERNAME` | Admin login username | admin |
| `ADMIN_PASSWORD` | Admin login password | admin123 |

### Question Configuration

Edit `data/questions.json` to customize questions:

```json
{
  "software_engineer": [
    {
      "question": "What is the difference between a list and a tuple?",
      "keywords": ["immutable", "mutable", "performance", "hashable"]
    }
  ]
}
```

## 🔧 Scoring System

Simple keyword-based scoring:
- **90%**: Keyword matching (percentage of keywords found in answer)
- **10%**: Length bonus (detailed answers get bonus points)
- **Pass threshold**: 70%

Keywords are matched case-insensitively with normalized text.

## 🗄️ Database Schema

### Interview
- id, name, role, num_questions, use_llm, created_at

### Candidate
- id, interview_id, name, email, password
- has_started, has_completed, is_deleted
- total_questions, score, passed
- created_at, started_at, completed_at

### Response
- id, candidate_id, question_text, answer_text
- score, keywords_found, created_at

## 🚢 Deployment

### Using Docker (Recommended)

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p logs data

CMD ["python", "main.py"]
```

### Using Systemd

```ini
[Unit]
Description=Voice Interview System
After=network.target

[Service]
User=interview
WorkingDirectory=/opt/interview-system
ExecStart=/opt/interview-system/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### Production Checklist

- [ ] Change default admin credentials
- [ ] Use PostgreSQL instead of SQLite
- [ ] Set strong SECRET_KEY
- [ ] Configure proper CORS origins
- [ ] Enable HTTPS
- [ ] Set up log rotation
- [ ] Configure firewall
- [ ] Set up monitoring
- [ ] Configure backup strategy

## 🐛 Troubleshooting

### Microphone not working
- Check browser permissions
- Ensure microphone is selected in system settings
- Test microphone with other applications

### WebSocket connection fails
- Check firewall settings
- Verify WebSocket is not blocked by proxy
- Check browser console for errors

### Audio playback issues
- Check speaker/headphone connection
- Verify audio output device
- Test with other audio

### Database errors
- Ensure database file has write permissions
- Check disk space
- Verify DATABASE_URL is correct

## 📝 API Documentation

Once running, visit:
- **API docs**: `http://localhost:8000/docs`
- **Alternative docs**: `http://localhost:8000/redoc`

## 🔒 Security Considerations

- Candidate passwords are stored in plain text (for demo purposes)
- In production, use password hashing (bcrypt/argon2)
- Implement rate limiting
- Add CSRF protection
- Use secure session management
- Validate all user inputs
- Sanitize database queries

## 📄 License

This project is for educational and interview purposes.

## 🤝 Support

For issues or questions:
1. Check the troubleshooting section
2. Review logs in `logs/app.log`
3. Check browser console for errors
4. Verify API keys are valid

## 🎯 Roadmap

Future enhancements:
- [ ] Email notifications
- [ ] Advanced analytics dashboard
- [ ] Multi-language support
- [ ] Video interview integration
- [ ] Custom scoring algorithms
- [ ] Interview recording/playback
- [ ] Batch candidate imports
- [ ] Scheduled interviews

---

Built with ❤️ using FastAPI, Deepgram, and Groq