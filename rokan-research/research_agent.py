"""
Rokan Research Agent
Deep research with Tavily, Crawl4AI, Reddit, and Twitter
"""

import os
import re
import json
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

# Optional imports - handle gracefully if not installed
try:
    from tavily import TavilyClient
    HAS_TAVILY = True
except ImportError:
    HAS_TAVILY = False

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


@dataclass
class ResearchResult:
    """Research result container"""
    source: str
    title: str
    content: str
    url: str
    timestamp: datetime
    metadata: Dict[str, Any]


class ResearchAgent:
    """
    Multi-source research agent
    Combines search engines, web crawling, and social media
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # Initialize search clients
        self.tavily_client = None
        if HAS_TAVILY:
            api_key = os.getenv("TAVILY_API_KEY") or self.config.get("search", {}).get("tavily_api_key")
            if api_key:
                self.tavily_client = TavilyClient(api_key=api_key)
        
        # Initialize Reddit
        self.reddit = None
        if HAS_REDDIT:
            client_id = os.getenv("REDDIT_CLIENT_ID")
            client_secret = os.getenv("REDDIT_CLIENT_SECRET")
            if client_id and client_secret:
                self.reddit = praw.Reddit(
                    client_id=client_id,
                    client_secret=client_secret,
                    user_agent="Rokan/1.0"
                )
        
        # Initialize Twitter
        self.twitter = None
        if HAS_TWITTER:
            bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
            if bearer_token:
                self.twitter = tweepy.Client(bearer_token=bearer_token)
    
    async def search(self, 
                     query: str, 
                     source: str = "tavily",
                     limit: int = 5) -> List[ResearchResult]:
        """
        Search using specified source
        
        Args:
            query: Search query
            source: tavily, searxng, or auto
            limit: Max results
        
        Returns:
            List of research results
        """
        if source == "tavily" and self.tavily_client:
            return await self._search_tavily(query, limit)
        elif source == "reddit":
            return await self._search_reddit(query, limit)
        elif source == "twitter":
            return await self._search_twitter(query, limit)
        else:
            # Fallback to basic web search
            return await self._search_basic(query, limit)
    
    async def _search_tavily(self, query: str, limit: int) -> List[ResearchResult]:
        """Search using Tavily"""
        if not self.tavily_client:
            return []
        
        try:
            response = self.tavily_client.search(
                query=query,
                max_results=limit,
                include_answer=True
            )
            
            results = []
            for result in response.get("results", []):
                results.append(ResearchResult(
                    source="tavily",
                    title=result.get("title", ""),
                    content=result.get("content", ""),
                    url=result.get("url", ""),
                    timestamp=datetime.now(),
                    metadata={"score": result.get("score")}
                ))
            
            return results
        except Exception as e:
            print(f"Tavily search error: {e}")
            return []
    
    async def _search_reddit(self, 
                             query: str, 
                             limit: int,
                             subreddit: str = None) -> List[ResearchResult]:
        """Search Reddit posts"""
        if not self.reddit:
            return []
        
        try:
            results = []
            
            if subreddit:
                # Search specific subreddit
                sub = self.reddit.subreddit(subreddit)
                posts = sub.search(query, limit=limit, sort="new")
            else:
                # Search all of Reddit
                posts = self.reddit.subreddit("all").search(query, limit=limit, sort="new")
            
            for post in posts:
                results.append(ResearchResult(
                    source=f"reddit:r/{post.subreddit.display_name}",
                    title=post.title,
                    content=post.selftext[:1000] if post.selftext else "",
                    url=f"https://reddit.com{post.permalink}",
                    timestamp=datetime.fromtimestamp(post.created_utc),
                    metadata={
                        "score": post.score,
                        "comments": post.num_comments,
                        "author": str(post.author)
                    }
                ))
            
            return results
        except Exception as e:
            print(f"Reddit search error: {e}")
            return []
    
    async def _search_twitter(self, query: str, limit: int) -> List[ResearchResult]:
        """Search Twitter/X posts"""
        if not self.twitter:
            return []
        
        try:
            # Search recent tweets
            tweets = self.twitter.search_recent_tweets(
                query=query,
                max_results=min(limit, 100),
                tweet_fields=["created_at", "author_id", "public_metrics"]
            )
            
            results = []
            if tweets.data:
                for tweet in tweets.data:
                    results.append(ResearchResult(
                        source="twitter",
                        title=f"Tweet by {tweet.author_id}",
                        content=tweet.text,
                        url=f"https://twitter.com/i/web/status/{tweet.id}",
                        timestamp=tweet.created_at,
                        metadata={
                            "author_id": tweet.author_id,
                            "metrics": tweet.public_metrics
                        }
                    ))
            
            return results
        except Exception as e:
            print(f"Twitter search error: {e}")
            return []
    
    async def _search_basic(self, query: str, limit: int) -> List[ResearchResult]:
        """Basic search fallback using SearXNG or DuckDuckGo"""
        results = []
        
        # Try SearXNG if configured
        searxng_url = self.config.get("search", {}).get("searxng_url")
        if searxng_url:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{searxng_url}/search",
                        params={"q": query, "format": "json"}
                    ) as response:
                        data = await response.json()
                        for result in data.get("results", [])[:limit]:
                            results.append(ResearchResult(
                                source="searxng",
                                title=result.get("title", ""),
                                content=result.get("content", ""),
                                url=result.get("url", ""),
                                timestamp=datetime.now(),
                                metadata={}
                            ))
            except Exception as e:
                print(f"SearXNG search error: {e}")
        
        return results
    
    async def multi_search(self,
                           query: str,
                           sources: List[str] = None,
                           limit_per_source: int = 5) -> Dict[str, List[ResearchResult]]:
        """
        Search across multiple sources
        
        Args:
            query: Search query
            sources: List of sources to search
            limit_per_source: Results per source
        
        Returns:
            Dict mapping source to results
        """
        sources = sources or ["tavily", "reddit", "twitter"]
        
        tasks = []
        for source in sources:
            tasks.append(self.search(query, source, limit_per_source))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            source: result if not isinstance(result, Exception) else []
            for source, result in zip(sources, results)
        }
    
    async def get_subreddit_posts(self,
                                  subreddit: str,
                                  sort: str = "hot",
                                  limit: int = 25,
                                  time_filter: str = "day") -> List[ResearchResult]:
        """Get posts from a subreddit"""
        if not self.reddit:
            return []
        
        try:
            sub = self.reddit.subreddit(subreddit)
            
            if sort == "hot":
                posts = sub.hot(limit=limit)
            elif sort == "new":
                posts = sub.new(limit=limit)
            elif sort == "top":
                posts = sub.top(time_filter=time_filter, limit=limit)
            else:
                posts = sub.hot(limit=limit)
            
            results = []
            for post in posts:
                results.append(ResearchResult(
                    source=f"reddit:r/{subreddit}",
                    title=post.title,
                    content=post.selftext[:2000] if post.selftext else "",
                    url=f"https://reddit.com{post.permalink}",
                    timestamp=datetime.fromtimestamp(post.created_utc),
                    metadata={
                        "score": post.score,
                        "comments": post.num_comments
                    }
                ))
            
            return results
        except Exception as e:
            print(f"Reddit fetch error: {e}")
            return []
    
    async def monitor_keywords(self,
                               keywords: List[str],
                               sources: List[str],
                               callback: callable = None,
                               interval_minutes: int = 5):
        """
        Monitor keywords across sources
        
        Args:
            keywords: Keywords to track
            sources: Sources to monitor
            callback: Function to call with new results
            interval_minutes: Check interval
        """
        seen_ids = set()
        
        while True:
            for keyword in keywords:
                for source in sources:
                    try:
                        results = await self.search(keyword, source, limit=10)
                        
                        for result in results:
                            result_id = hash(result.url)
                            if result_id not in seen_ids:
                                seen_ids.add(result_id)
                                
                                if callback:
                                    await callback(result)
                    except Exception as e:
                        print(f"Monitor error: {e}")
            
            await asyncio.sleep(interval_minutes * 60)
    
    def format_results(self, results: List[ResearchResult]) -> str:
        """Format results for display"""
        if not results:
            return "No results found."
        
        output = []
        for i, result in enumerate(results, 1):
            output.append(f"\n{'='*60}")
            output.append(f"{i}. {result.title}")
            output.append(f"   Source: {result.source}")
            output.append(f"   URL: {result.url}")
            output.append(f"   Time: {result.timestamp.strftime('%Y-%m-%d %H:%M')}")
            output.append(f"\n{result.content[:500]}...")
        
        return "\n".join(output)


# OpenClaw skill interface
class RokanResearchSkill:
    """OpenClaw skill interface for rokan-research"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.agent = ResearchAgent(config)
    
    async def search(self, query: str, source: str = "tavily", limit: int = 5) -> str:
        """Search and return formatted results"""
        results = await self.agent.search(query, source, limit)
        return self.agent.format_results(results)
    
    async def reddit(self, subreddit: str, query: str = None, limit: int = 25) -> str:
        """Get Reddit posts"""
        if query:
            results = await self.agent._search_reddit(query, limit, subreddit)
        else:
            results = await self.agent.get_subreddit_posts(subreddit, limit=limit)
        return self.agent.format_results(results)
    
    async def twitter(self, query: str, limit: int = 20) -> str:
        """Search Twitter"""
        results = await self.agent._search_twitter(query, limit)
        return self.agent.format_results(results)
    
    async def multi_search(self, query: str, sources: List[str] = None) -> str:
        """Search across multiple sources"""
        results = await self.agent.multi_search(query, sources)
        
        output = []
        for source, source_results in results.items():
            output.append(f"\n{'='*60}")
            output.append(f"Source: {source.upper()}")
            output.append(f"{'='*60}")
            output.append(self.agent.format_results(source_results))
        
        return "\n".join(output)


# Export for OpenClaw
skill = RokanResearchSkill
