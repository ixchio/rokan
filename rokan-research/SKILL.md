# rokan-research

**Rokan's Research Agent** — Deep research with Tavily, Crawl4AI, Reddit, and Twitter scraping. Real-time info extraction.

## Description

Advanced research capabilities combining search engines, web crawling, and social media monitoring. Extracts structured data from any source for RAG and analysis.

## Capabilities

| Source | Method | Rate Limit | Use Case |
|--------|--------|------------|----------|
| **Tavily** | API | 1000/mo (free) | General search |
| **Crawl4AI** | Local crawl | Unlimited | Deep page extraction |
| **Reddit** | PRAW | 60/min | Community discussions |
| **Twitter/X** | API v2 | 500/mo (free) | Real-time updates |
| **SearXNG** | Self-hosted | Unlimited | Private search |

## When to Use

- "Search for latest AI papers"
- "What's trending on Reddit about Linux?"
- "Find Twitter posts about remote jobs"
- "Research this company before interview"
- "Summarize this article"

## Setup

```bash
# 1. Install dependencies
pip install tavily-python crawl4ai praw tweepy newspaper3k

# 2. Set API keys (optional, can use SearXNG as fallback)
export TAVILY_API_KEY="your_key"      # Free: tavily.com
export REDDIT_CLIENT_ID="your_id"     # Free: reddit.com/prefs/apps
export REDDIT_CLIENT_SECRET="your_secret"
export TWITTER_BEARER_TOKEN="your_token"  # Free: developer.twitter.com

# 3. Optional: Self-host SearXNG (fallback search)
docker run -d -p 8080:8080 searxng/searxng
```

## Configuration

Add to `~/.openclaw/config.yaml`:

```yaml
skills:
  rokan-research:
    search:
      primary: tavily
      fallback: searxng
      searxng_url: http://localhost:8080
    crawl:
      engine: crawl4ai
      timeout: 30
      max_pages: 10
      respect_robots: true
    social:
      reddit:
        enabled: true
        subreddits:
          - technology
          - linux
          - programming
          - machinelearning
      twitter:
        enabled: true
        track_keywords:
          - "AI breakthrough"
          - "hiring engineers"
    extraction:
      summarize: true
      extract_links: true
      extract_images: false
```

## Usage

### Web Search
```
User: "Search for latest Linux kernel features"
→ Tavily search → Crawl top results → Summarize findings
```

### Reddit Monitoring
```
User: "What's the sentiment on Wayland in r/linux?"
→ Scrape r/linux posts about Wayland → Analyze sentiment
```

### Twitter Tracking
```
User: "Find tweets about remote AI jobs from today"
→ Twitter API search → Filter by keywords → Present results
```

### Deep Research
```
User: "Research this URL and extract key points"
→ Crawl4AI extraction → Markdown conversion → Summary
```

## API

### `research.search(query, source="tavily", limit=5)`
Search using specified source.

### `research.crawl(url, depth=1)`
Deep crawl a URL with Crawl4AI.

### `research.reddit(subreddit, sort="hot", limit=25)`
Get posts from a subreddit.

### `research.twitter(query, since=None, limit=100)`
Search tweets matching query.

### `research.summarize(text_or_url)`
Generate summary of content.

### `research.extract_structured(url, schema)`
Extract structured data using LLM.

## Example Queries

```python
# Multi-source research
results = await research.multi_search(
    query="Rust vs Go performance 2025",
    sources=["tavily", "reddit", "twitter"],
    synthesize=True
)

# Monitor keywords
await research.monitor(
    keywords=["hiring", "remote", "AI engineer"],
    sources=["reddit:r/forhire", "twitter"],
    callback=notify_user
)
```

## Files

- `research_agent.py` — Main research orchestrator
- `search.py` — Search engine wrappers
- `crawler.py` — Crawl4AI integration
- `reddit_scraper.py` — Reddit data extraction
- `twitter_scraper.py` — Twitter/X API client
- `summarizer.py` — Content summarization

## License

MIT — Part of Rokan Skill Pack for OpenClaw
