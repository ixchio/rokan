"""
Rokan Job Monitor
Real-time job monitoring across Reddit, Twitter, and job boards
"""

import os
import re
import json
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from difflib import SequenceMatcher

# Optional imports
try:
    import praw
    HAS_REDDIT = True
except ImportError:
    HAS_REDDIT = False

try:
    import tweepy
    HAS_TWITTER = True
except ImportError:
    HAS_TWITTER = False

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    HAS_SCHEDULER = True
except ImportError:
    HAS_SCHEDULER = False


@dataclass
class JobPosting:
    """Job posting data"""
    id: str
    title: str
    company: Optional[str]
    description: str
    url: str
    source: str
    posted_at: datetime
    location: Optional[str]
    remote: bool
    job_type: Optional[str]  # full-time, contract, etc.
    salary: Optional[str]
    skills: List[str]
    raw_text: str


@dataclass
class MatchResult:
    """Job match result"""
    job: JobPosting
    score: float
    breakdown: Dict[str, float]
    recommendation: str  # "Apply", "Research", "Skip"


class JobMatcher:
    """Matches job postings against user profile"""
    
    def __init__(self, profile: Dict):
        self.profile = profile
        self.skills = [s.lower() for s in profile.get("skills", [])]
        self.title = profile.get("title", "").lower()
        self.preferences = profile.get("preferences", {})
    
    def calculate_match(self, job: JobPosting) -> MatchResult:
        """Calculate match score for a job"""
        scores = {}
        
        # Skills match (40%)
        if self.skills:
            job_skills = [s.lower() for s in job.skills]
            matched = sum(1 for s in self.skills if any(
                s in js or js in s for js in job_skills
            ))
            scores["skills"] = (matched / len(self.skills)) * 100
        else:
            scores["skills"] = 50
        
        # Title/role match (30%)
        title_keywords = self.title.split()
        job_title_words = job.title.lower().split()
        title_match = sum(1 for kw in title_keywords if kw in job_title_words)
        scores["title"] = (title_match / max(len(title_keywords), 1)) * 100
        
        # Location/remote match (20%)
        if self.preferences.get("remote_only"):
            scores["location"] = 100 if job.remote else 0
        else:
            scores["location"] = 50
        
        # Keywords match (10%)
        keywords = self.preferences.get("keywords", [])
        if keywords:
            text = f"{job.title} {job.description}".lower()
            kw_matches = sum(1 for kw in keywords if kw.lower() in text)
            scores["keywords"] = (kw_matches / len(keywords)) * 100
        else:
            scores["keywords"] = 50
        
        # Calculate weighted total
        weights = {"skills": 0.4, "title": 0.3, "location": 0.2, "keywords": 0.1}
        total_score = sum(scores[k] * weights[k] for k in scores)
        
        # Determine recommendation
        if total_score >= 80:
            recommendation = "Apply"
        elif total_score >= 60:
            recommendation = "Research"
        else:
            recommendation = "Skip"
        
        return MatchResult(
            job=job,
            score=total_score,
            breakdown=scores,
            recommendation=recommendation
        )


class JobMonitor:
    """
    Job monitoring system
    Scans multiple sources for job postings
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # User profile
        self.profile = self.config.get("profile", {})
        self.matcher = JobMatcher(self.profile)
        
        # Keywords
        self.keywords = self.config.get("keywords", {})
        
        # Sources
        self.sources = self.config.get("sources", {})
        
        # Matching settings
        self.matching = self.config.get("matching", {})
        self.min_score = self.matching.get("min_score", 70)
        
        # Initialize clients
        self.reddit = None
        if HAS_REDDIT:
            client_id = os.getenv("REDDIT_CLIENT_ID")
            client_secret = os.getenv("REDDIT_CLIENT_SECRET")
            if client_id and client_secret:
                self.reddit = praw.Reddit(
                    client_id=client_id,
                    client_secret=client_secret,
                    user_agent="RokanJobBot/1.0"
                )
        
        self.twitter = None
        if HAS_TWITTER:
            bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
            if bearer_token:
                self.twitter = tweepy.Client(bearer_token=bearer_token)
        
        # Scheduler
        self.scheduler = None
        if HAS_SCHEDULER:
            self.scheduler = AsyncIOScheduler()
        
        # Storage
        self.seen_jobs = set()
        self.matches = []
        self.is_running = False
    
    def _extract_skills(self, text: str) -> List[str]:
        """Extract skills from job text"""
        common_skills = [
            "python", "javascript", "typescript", "rust", "go", "golang",
            "java", "c++", "c#", "ruby", "php", "swift", "kotlin",
            "react", "vue", "angular", "node.js", "django", "flask",
            "docker", "kubernetes", "aws", "gcp", "azure",
            "machine learning", "ai", "deep learning", "nlp",
            "sql", "postgresql", "mongodb", "redis",
            "linux", "devops", "ci/cd", "git"
        ]
        
        text_lower = text.lower()
        found = []
        for skill in common_skills:
            if skill in text_lower:
                found.append(skill)
        return found
    
    def _detect_remote(self, text: str) -> bool:
        """Detect if job is remote"""
        remote_keywords = ["remote", "work from home", "wfh", "anywhere"]
        text_lower = text.lower()
        return any(kw in text_lower for kw in remote_keywords)
    
    async def scan_reddit(self, subreddits: List[str] = None) -> List[JobPosting]:
        """Scan Reddit for job postings"""
        if not self.reddit:
            return []
        
        subreddits = subreddits or self.sources.get("reddit", ["forhire", "hiring"])
        jobs = []
        
        # Job-related keywords
        job_keywords = self.keywords.get("must_have", []) + ["hiring", "job", "position", "opportunity"]
        
        for sub_name in subreddits:
            try:
                sub = self.reddit.subreddit(sub_name.replace("r/", ""))
                
                # Get recent posts
                for post in sub.new(limit=50):
                    # Check if it's a job post
                    title_lower = post.title.lower()
                    is_job = any(kw.lower() in title_lower for kw in job_keywords)
                    
                    if not is_job:
                        continue
                    
                    # Create job posting
                    job = JobPosting(
                        id=f"reddit_{post.id}",
                        title=post.title,
                        company=None,
                        description=post.selftext[:2000],
                        url=f"https://reddit.com{post.permalink}",
                        source=f"reddit:{sub_name}",
                        posted_at=datetime.fromtimestamp(post.created_utc),
                        location=None,
                        remote=self._detect_remote(post.selftext),
                        job_type=None,
                        salary=None,
                        skills=self._extract_skills(post.selftext),
                        raw_text=post.selftext
                    )
                    
                    jobs.append(job)
            
            except Exception as e:
                print(f"Reddit scan error ({sub_name}): {e}")
        
        return jobs
    
    async def scan_twitter(self, searches: List[str] = None) -> List[JobPosting]:
        """Scan Twitter for job postings"""
        if not self.twitter:
            return []
        
        searches = searches or self.sources.get("twitter", {}).get("searches", [])
        if not searches:
            searches = ["hiring AI engineer", "remote developer job"]
        
        jobs = []
        
        for search in searches:
            try:
                tweets = self.twitter.search_recent_tweets(
                    query=search,
                    max_results=25,
                    tweet_fields=["created_at", "author_id"]
                )
                
                if tweets.data:
                    for tweet in tweets.data:
                        # Check if it's a job post
                        text_lower = tweet.text.lower()
                        is_job = any(kw in text_lower for kw in ["hiring", "join us", "we're looking", "job"])
                        
                        if not is_job:
                            continue
                        
                        job = JobPosting(
                            id=f"twitter_{tweet.id}",
                            title=f"Job from @{tweet.author_id}",
                            company=None,
                            description=tweet.text,
                            url=f"https://twitter.com/i/web/status/{tweet.id}",
                            source="twitter",
                            posted_at=tweet.created_at,
                            location=None,
                            remote=self._detect_remote(tweet.text),
                            job_type=None,
                            salary=None,
                            skills=self._extract_skills(tweet.text),
                            raw_text=tweet.text
                        )
                        
                        jobs.append(job)
            
            except Exception as e:
                print(f"Twitter scan error: {e}")
        
        return jobs
    
    async def scan_all(self) -> List[JobPosting]:
        """Scan all configured sources"""
        all_jobs = []
        
        # Reddit
        reddit_jobs = await self.scan_reddit()
        all_jobs.extend(reddit_jobs)
        
        # Twitter
        twitter_jobs = await self.scan_twitter()
        all_jobs.extend(twitter_jobs)
        
        # Filter seen jobs
        new_jobs = []
        for job in all_jobs:
            if job.id not in self.seen_jobs:
                self.seen_jobs.add(job.id)
                new_jobs.append(job)
        
        return new_jobs
    
    async def find_matches(self, jobs: List[JobPosting] = None) -> List[MatchResult]:
        """Find jobs matching user profile"""
        if jobs is None:
            jobs = await self.scan_all()
        
        matches = []
        for job in jobs:
            match = self.matcher.calculate_match(job)
            if match.score >= self.min_score:
                matches.append(match)
        
        # Sort by score
        matches.sort(key=lambda m: m.score, reverse=True)
        
        # Store
        self.matches.extend(matches)
        
        return matches
    
    async def start_monitoring(self, callback: callable = None):
        """Start background monitoring"""
        if self.is_running:
            return
        
        self.is_running = True
        interval = self.config.get("check_interval_minutes", 5)
        
        if self.scheduler:
            self.scheduler.add_job(
                self._check_and_notify,
                "interval",
                minutes=interval,
                args=[callback]
            )
            self.scheduler.start()
        else:
            # Fallback to simple loop
            while self.is_running:
                await self._check_and_notify(callback)
                await asyncio.sleep(interval * 60)
    
    async def _check_and_notify(self, callback: callable = None):
        """Check for new jobs and notify"""
        matches = await self.find_matches()
        
        if matches and callback:
            for match in matches:
                await callback(match)
    
    def stop_monitoring(self):
        """Stop background monitoring"""
        self.is_running = False
        if self.scheduler:
            self.scheduler.shutdown()
    
    def format_match(self, match: MatchResult) -> str:
        """Format a match for display"""
        job = match.job
        
        output = []
        output.append(f"\n{'='*60}")
        output.append(f"🎯 MATCH SCORE: {match.score:.0f}% - {match.recommendation}")
        output.append(f"{'='*60}")
        output.append(f"📋 {job.title}")
        if job.company:
            output.append(f"🏢 {job.company}")
        output.append(f"🔗 {job.url}")
        output.append(f"📍 {'Remote ✓' if job.remote else 'On-site'}")
        output.append(f"⏰ Posted: {job.posted_at.strftime('%Y-%m-%d %H:%M')}")
        output.append(f"📊 Score breakdown:")
        for category, score in match.breakdown.items():
            output.append(f"   • {category}: {score:.0f}%")
        if job.skills:
            output.append(f"🛠 Skills: {', '.join(job.skills[:10])}")
        output.append(f"\n{job.description[:500]}...")
        
        return "\n".join(output)
    
    def get_recent_matches(self, limit: int = 10) -> str:
        """Get recent matches as formatted string"""
        if not self.matches:
            return "No job matches yet. Start monitoring to find opportunities."
        
        recent = sorted(self.matches, key=lambda m: m.job.posted_at, reverse=True)[:limit]
        return "\n\n".join(self.format_match(m) for m in recent)


# OpenClaw skill interface
class RokanJobsSkill:
    """OpenClaw skill interface for rokan-jobs"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.monitor = JobMonitor(config)
    
    async def search(self, query: str = None) -> str:
        """Instant job search"""
        jobs = await self.monitor.scan_all()
        matches = await self.monitor.find_matches(jobs)
        
        if not matches:
            return "No matching jobs found. Try adjusting your profile or keywords."
        
        return self.monitor.get_recent_matches(limit=10)
    
    async def start_monitoring(self) -> str:
        """Start background monitoring"""
        await self.monitor.start_monitoring()
        interval = self.config.get("check_interval_minutes", 5)
        return f"Job monitoring started. Checking every {interval} minutes."
    
    async def stop_monitoring(self) -> str:
        """Stop background monitoring"""
        self.monitor.stop_monitoring()
        return "Job monitoring stopped."
    
    async def get_matches(self, limit: int = 10) -> str:
        """Get recent matches"""
        return self.monitor.get_recent_matches(limit)
    
    async def update_profile(self, **kwargs) -> str:
        """Update user profile"""
        self.monitor.profile.update(kwargs)
        return "Profile updated."


# Export for OpenClaw
skill = RokanJobsSkill
