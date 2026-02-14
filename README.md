# The AI Internship

Welcome to the repository for **The AI Internship**. This monorepository contains coursework, assignments, and projects developed during the AI Engineering Bootcamp.

## Repository Structure

The repository is organized hierarchically by course modules and timeline:

- **AI Engineering Bootcamp & Certificate**
  - **Week 1**
    - `Assignment 1`: Build & Deploy FastAPI LLM API

---

## Projects Overview

### Week 1: Build & Deploy FastAPI LLM API

**Location:** `AI Engineering Bootcamp & Certificate/Week 1/Assignment 1/Build & Deploy FastAPI LLM API`

This project is a FastAPI-based application that serves as an LLM gateway, providing endpoints for text summarization, sentiment analysis, and chat. It supports multiple LLM providers including OpenAI, Anthropic, and Google Gemini.

#### Features
- **Summarization**: Summarize long texts with customizable prompt versions.
- **Sentiment Analysis**: Determine the sentiment (Positive/Negative/Neutral) of a given text.
- **Chat Interface**: Interactive chat capability.
- **Prompt Enhancement**: specialized endpoint to improve prompt quality.
- **Multi-Provider Support**: Seamlessly switch between OpenAI, Anthropic, and Google GenAI.

#### Getting Started

**Prerequisites**
- Python 3.10+
- `pip` package manager

**Installation**

1. Navigate to the project directory:
   ```bash
   cd "AI Engineering Bootcamp & Certificate/Week 1/Assignment 1/Build & Deploy FastAPI LLM API"
   ```

2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Environment Setup:
   Create a `.env` file in the project root (you can copy `.env.example` if available) and add your API keys:
   ```env
   OPENAI_API_KEY=your_key_here
   ANTHROPIC_API_KEY=your_key_here
   GOOGLE_API_KEY=your_key_here
   ```

**Running the Application**

Start the development server using Uvicorn:

```bash
uvicorn main:app --reload
```

- **Web Interface**: `http://localhost:8000`
- **API Documentation**: `http://localhost:8000/docs`
