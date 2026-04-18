# rokan-jobs

**Rokan's Job Hunter** — Monitors Reddit, Twitter, and job boards in real-time. Matches jobs to your skills and notifies instantly.

## Description

Continuously scans multiple sources for job opportunities, filters by your skills and preferences, and delivers instant notifications. The Sung Jin-Woo approach to job hunting — silent, efficient, deadly effective.

## Monitored Sources

| Source | Check Interval | Coverage |
|--------|---------------|----------|
| Reddit r/forhire | 5 min | Freelance, contract |
| Reddit r/hiring | 5 min | Full-time, remote |
| Reddit r/remotejs | 5 min | Remote dev jobs |
| Reddit r/devopsjobs | 5 min | DevOps/SRE |
| Reddit r/cscareerquestions | 10 min | Career discussions |
| Twitter/X | 5 min | Real-time postings |
| Hacker News "Who is Hiring" | 1 hour | Monthly thread |
| GitHub Jobs API | 1 hour | Tech companies |

## When to Use

- "Find me remote Python jobs"
- "Notify when AI engineer positions open"
- "Scan today's job posts"
- "Which jobs match my skills?"
- "Track this company for openings"

## Setup

```bash
# 1. Install dependencies
pip install praw tweepy apscheduler discord-webhook

# 2. Configure Reddit API (free)
# Create app at: reddit.com/prefs/apps
export REDDIT_CLIENT_ID="your_client_id"
export REDDIT_CLIENT_SECRET="your_client_secret"
export REDDIT_USER_AGENT="RokanJobBot/1.0"

# 3. Configure Twitter/X API (free tier)
# Get at: developer.twitter.com
export TWITTER_BEARER_TOKEN="your_bearer_token"

# 4. Optional: Notification channels
export TELEGRAM_BOT_TOKEN="your_token"  # @BotFather
export TELEGRAM_CHAT_ID="your_chat_id"
export DISCORD_WEBHOOK_URL="your_webhook"
```

## Configuration

Add to `~/.openclaw/config.yaml`:

```yaml
skills:
  rokan-jobs:
    enabled: true
    check_interval_minutes: 5
    
    # Your profile
    profile:
      title: "AI Engineer"  # or "Full Stack Dev", etc.
      skills:
        - python
        - machine learning
        - linux
        - docker
        - kubernetes
        - rust
        - golang
      experience: "5 years"  # for filtering
      preferences:
        remote_only: true
        timezone: "UTC-8"
        salary_min: 120000
        contract_ok: true
        fulltime_ok: true
    
    # Keywords to track
    keywords:
      must_have:
        - "AI engineer"
        - "machine learning"
        - "MLOps"
        - "backend engineer"
      nice_to_have:
        - "remote"
        - "flexible hours"
        - "startup"
      exclude:
        - "senior"  # if not looking for senior roles
        - "5+ years required"
    
    # Sources
    sources:
      reddit:
        - r/forhire
        - r/hiring
        - r/remotejs
        - r/devopsjobs
        - r/cscareerquestions
        - r/MachineLearning
      twitter:
        searches:
          - "hiring AI engineer"
          - "remote ML job"
          - "we're looking for backend"
        accounts:
          - "RemoteOK"
          - "WeWorkRemotely"
    
    # Matching algorithm
    matching:
      min_score: 70  # 0-100 match score threshold
      skill_weight: 0.4
      keyword_weight: 0.3
      location_weight: 0.2
      salary_weight: 0.1
    
    # Notifications
    notifications:
      telegram:
        enabled: false
        instant: true
        digest: false
      discord:
        enabled: false
        instant: true
        digest: true
        digest_time: "18:00"
      desktop:
        enabled: true
        urgency: normal
      email:
        enabled: false
        smtp_server: ""
        to_address: ""
```

## Usage

### Start Monitoring
```
User: "Start job monitoring"
→ Begins background scanning every 5 minutes
→ Notifications for matches >70% score
```

### Instant Search
```
User: "Find remote AI jobs posted today"
→ Scans all sources immediately
→ Returns ranked matches with scores
```

### Skill Match Analysis
```
User: "Which of these jobs suits me best?"
→ Analyzes job descriptions
→ Scores each against your profile
→ Recommends top 3 with reasoning
```

### Track Company
```
User: "Notify me when OpenAI posts new jobs"
→ Adds company to watchlist
→ Checks career pages daily
```

## API

### `jobs.start_monitoring()`
Begin background job monitoring.

### `jobs.stop_monitoring()`
Stop background monitoring.

### `jobs.search_now(query=None, sources=None)`
Immediate search across all sources.

### `jobs.get_matches(limit=10, min_score=70)`
Get recent job matches above threshold.

### `jobs.analyze_fit(job_description)`
Score a job against your profile.

### `jobs.add_keyword(keyword, weight=1.0)`
Add keyword to tracking list.

### `jobs.add_source(source_type, config)`
Add new source to monitor.

## Job Match Score

```python
{
  "job_id": "reddit_abc123",
  "title": "AI Engineer - Remote",
  "company": "TechCorp",
  "source": "reddit:r/forhire",
  "posted_at": "2025-04-05T14:30:00Z",
  "match_score": 87,
  "breakdown": {
    "skills_match": 90,      # 4/5 skills found
    "keywords_match": 85,    # "remote", "AI engineer"
    "location_match": 100,   # remote OK
    "salary_match": 75       # above minimum
  },
  "url": "https://reddit.com/r/forhire/comments/...",
  "action": "Apply"  # or "Skip", "Research"
}
```

## Files

- `job_monitor.py` — Main monitoring orchestrator
- `scraper_reddit.py` — Reddit job extraction
- `scraper_twitter.py` — Twitter job extraction
- `matcher.py` — Profile matching algorithm
- `notifier.py` — Notification dispatcher
- `scheduler.py` — Background task scheduling

## License

MIT — Part of Rokan Skill Pack for OpenClaw
