# 📄 Product Requirements Document (PRD)

## 🧠 Project Title: Upwork Job Sniper

### 👤 Owner: Mohamed Khaled  
### 🛠️ Developer: Assigned per sprint  
### 📅 Start Date: [Insert Date]  
### 📍Status: Ready for Development  

---

## 🎯 1. Objective

Build an automated system that monitors Upwork job posts using specific keywords, scores and summarizes relevant jobs, and sends mobile push notifications in real-time. The user can then view each job's summary, a score, and an AI-generated video proposal script.

---

## 🧩 2. Problem Statement

Freelancers on Upwork need to monitor job posts constantly to catch high-quality leads early. Doing this manually is time-consuming and inefficient. 

---

## ✅ 3. Success Criteria

- Receive real-time Pushover alerts for jobs matching specified keywords.
- Each alert includes a score, job summary, and AI-generated video script.
- Interface displays recent jobs with summaries and actions.
- Achieve at least one qualified job proposal submitted weekly.

---

## 🔍 4. Functional Requirements

### 4.1 Job Fetcher
- Poll Upwork GraphQL API every 5–10 minutes.
- Use stored keywords to filter relevant job posts.
- Parse job details: title, description, budget, hourly rate, client info, etc.

### 4.2 AI Summarization & Proposal Script
- Send job details to OpenAI GPT-4o.
- Prompt should return:
  1. Job Summary
  2. Score (0–10)
  3. 30-second video script

### 4.3 Notification System
- Send notification via Pushover for high-score jobs.
- Notification must contain:
  - Job title
  - Score
  - Link to job viewer/dashboard

### 4.4 Dashboard Interface (Gradio MVP)
- Show recent job posts
- Display:
  - Summary
  - Score
  - Generated script
- Allow clicking link to open original Upwork post

---

## 📡 5. Non-Functional Requirements

- Polling frequency: every 10 mins
- AI latency: <5s acceptable
- Notifications: real-time
- Security: store API keys in `.env` file
- Hosting: local/VPS for MVP; cloud optional

---

## 🔐 6. Integration Tokens (.env)

```
UPWORK_TOKEN=xxx
OPENAI_API_KEY=xxx
PUSHOVER_TOKEN=xxx
PUSHOVER_USER_KEY=xxx
```

---

## 📦 7. File Structure

```
upwork-sniper/
├── main.py                # Main loop and entry point
├── fetcher.py             # Upwork API fetcher
├── notifier.py            # Pushover notification handler
├── ai_engine.py           # OpenAI summarizer, scorer, script generator
├── scorer.py              # Score calculator
├── ui.py                  # Gradio dashboard
├── utils.py               # Token management, helpers
├── .env                   # Config and API secrets
├── requirements.txt
└── jobs.json              # Local store of recent jobs
```

---

## 📡 8. Sample OpenAI Prompt

```
You are an expert proposal writer.

Here is a job post:
---
{job_title}
{job_description}
Budget: {budget}
Client rating: {client_feedback} | Hire rate: {hire_rate}% | Location: {client_location}
---

Return:
1. A one-paragraph summary of the job.
2. A score between 0 and 10 based on job quality.
3. A 30-second script to use in a video proposal.
```

---

## 📍 9. Development Milestones

| Day | Task                                         | Owner        |
|-----|----------------------------------------------|--------------|
| 1   | Set up repo + fetcher.py                     | Developer    |
| 2   | Pushover integration                         | Developer    |
| 3   | OpenAI summarizer + scoring logic            | Developer    |
| 4   | Script generation + prompt tuning            | Developer    |
| 5   | Build Gradio UI                              | Developer    |
| 6   | Connect all components & run tests           | Developer    |
| 7   | Buffer day for bug fixes and polish          | Developer    |

---

## 🧠 10. Future Enhancements (Post-MVP)

- Multiple keyword groups (segmented per niche)
- Admin interface to adjust scoring logic
- Log job outcomes for future training signals
- WordPress plugin embedding this dashboard
