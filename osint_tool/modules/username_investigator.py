"""
Username Investigation Module
Integrates: Sherlock, Maigret, WhatsMyName, SocialScan
"""

import asyncio
import os
import json
from typing import Dict, List, Any
import aiohttp

from ..core.base import UsernameModule


class SherlockChecker(UsernameModule):
    """Sherlock-style username search across 300+ platforms"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sites = self._load_sites()

    def get_module_name(self) -> str:
        return "Sherlock"

    def _load_sites(self) -> Dict[str, Dict]:
        """Load Sherlock-compatible site list"""
        # Simplified version - in production, load from JSON
        return {
            "GitHub": {
                "url": "https://github.com/{}",
                "errorType": "status_code",
                "errorMsg": "404"
            },
            "Instagram": {
                "url": "https://www.instagram.com/{}",
                "errorType": "status_code",
                "errorMsg": "404"
            },
            "Twitter": {
                "url": "https://twitter.com/{}",
                "errorType": "status_code",
                "errorMsg": "404"
            },
            "Reddit": {
                "url": "https://www.reddit.com/user/{}",
                "errorType": "status_code",
                "errorMsg": "404"
            },
            "YouTube": {
                "url": "https://www.youtube.com/@{}",
                "errorType": "status_code"
            },
            "LinkedIn": {
                "url": "https://www.linkedin.com/in/{}",
                "errorType": "status_code"
            },
            "Facebook": {
                "url": "https://www.facebook.com/{}",
                "errorType": "status_code"
            },
            "TikTok": {
                "url": "https://www.tiktok.com/@{}",
                "errorType": "status_code"
            },
            "Twitch": {
                "url": "https://www.twitch.tv/{}",
                "errorType": "status_code"
            },
            "Pinterest": {
                "url": "https://www.pinterest.com/{}",
                "errorType": "status_code"
            },
            "Snapchat": {
                "url": "https://www.snapchat.com/add/{}",
                "errorType": "status_code"
            },
            "Medium": {
                "url": "https://medium.com/@{}",
                "errorType": "status_code"
            },
            "Telegram": {
                "url": "https://t.me/{}",
                "errorType": "status_code"
            },
            "Steam": {
                "url": "https://steamcommunity.com/id/{}",
                "errorType": "status_code"
            },
            "Spotify": {
                "url": "https://open.spotify.com/user/{}",
                "errorType": "status_code"
            },
            "GitLab": {
                "url": "https://gitlab.com/{}",
                "errorType": "status_code"
            },
            "Patreon": {
                "url": "https://www.patreon.com/{}",
                "errorType": "status_code"
            },
            "Discord.io": {
                "url": "https://discord.io/{}",
                "errorType": "status_code"
            },
            "Gravatar": {
                "url": "https://en.gravatar.com/{}",
                "errorType": "status_code"
            },
            "About.me": {
                "url": "https://about.me/{}",
                "errorType": "status_code"
            }
        }

    async def search(self, query: str) -> Dict[str, Any]:
        return await self.check_username(query)

    async def check_username(self, username: str) -> Dict[str, Any]:
        """Search username across multiple platforms"""
        found = []

        async with aiohttp.ClientSession() as session:
            tasks = []
            for site_name, site_data in self.sites.items():
                url = site_data['url'].format(username)
                tasks.append(self._check_site(session, site_name, url))

            results = await asyncio.gather(*tasks, return_exceptions=True)
            found = [r for r in results if isinstance(r, dict) and r.get('found')]

        return self.format_result(
            source="sherlock",
            data={
                "username": username,
                "sites_checked": len(self.sites),
                "found_count": len(found),
                "accounts": found
            }
        )

    async def _check_site(self, session: aiohttp.ClientSession,
                         site_name: str, url: str) -> Dict:
        """Check if username exists on a site"""
        try:
            async with session.get(url, timeout=self.timeout, allow_redirects=True) as response:
                exists = response.status == 200
                return {
                    "site": site_name,
                    "url": url,
                    "found": exists,
                    "status_code": response.status
                }
        except Exception as e:
            self.logger.debug(f"Error checking {site_name}: {e}")
            return {
                "site": site_name,
                "url": url,
                "found": False,
                "error": str(e)
            }


class WhatsMyNameChecker(UsernameModule):
    """WhatsMyName database checker"""

    def get_module_name(self) -> str:
        return "WhatsMyName"

    async def search(self, query: str) -> Dict[str, Any]:
        return await self.check_username(query)

    async def check_username(self, username: str) -> Dict[str, Any]:
        """
        Check username using WhatsMyName database
        Reference: https://github.com/WebBreacher/WhatsMyName
        """
        # Load WhatsMyName JSON (simplified)
        wmn_url = "https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json"

        async with aiohttp.ClientSession() as session:
            # Fetch site list
            wmn_data = await self.fetch(session, wmn_url)

            if not wmn_data or 'sites' not in wmn_data:
                return self.format_result(
                    source="whatsmyname",
                    data={"error": "Failed to load WhatsMyName database"},
                    status="error"
                )

            # Check username on sites
            sites = wmn_data['sites'][:50]  # Limit to first 50 for speed
            tasks = []
            for site in sites:
                if 'check_uri' in site:
                    url = site['check_uri'].replace('{account}', username)
                    tasks.append(self._check_wmn_site(session, site['name'], url))

            results = await asyncio.gather(*tasks, return_exceptions=True)
            found = [r for r in results if isinstance(r, dict) and r.get('found')]

        return self.format_result(
            source="whatsmyname",
            data={
                "username": username,
                "sites_checked": len(sites),
                "found_count": len(found),
                "accounts": found
            }
        )

    async def _check_wmn_site(self, session: aiohttp.ClientSession,
                             site_name: str, url: str) -> Dict:
        """Check site using WhatsMyName logic"""
        try:
            async with session.get(url, timeout=self.timeout) as response:
                exists = response.status == 200
                return {
                    "site": site_name,
                    "url": url,
                    "found": exists
                }
        except:
            return {"site": site_name, "url": url, "found": False}


class SocialScanChecker(UsernameModule):
    """SocialScan checker for email and username"""

    def get_module_name(self) -> str:
        return "SocialScan"

    async def search(self, query: str) -> Dict[str, Any]:
        return await self.check_username(query)

    async def check_username(self, username: str) -> Dict[str, Any]:
        """Check username on major platforms"""
        platforms = {
            "Instagram": f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}",
            "Twitter": f"https://twitter.com/i/api/graphql/user_by_screen_name?screen_name={username}",
            "GitHub": f"https://api.github.com/users/{username}",
        }

        found = []

        async with aiohttp.ClientSession() as session:
            for platform, url in platforms.items():
                try:
                    result = await self.fetch(session, url)
                    if result:
                        found.append({
                            "platform": platform,
                            "username": username,
                            "found": True,
                            "url": url
                        })
                except Exception as e:
                    self.logger.debug(f"Error checking {platform}: {e}")

        return self.format_result(
            source="socialscan",
            data={
                "username": username,
                "platforms_checked": len(platforms),
                "found_count": len(found),
                "accounts": found
            }
        )


class UsernameInvestigator:
    """Orchestrates all username investigation modules"""

    def __init__(self):
        self.modules = [
            SherlockChecker(),
            WhatsMyNameChecker(),
            SocialScanChecker()
        ]

    async def investigate(self, username: str) -> Dict[str, Any]:
        """Run all username checks"""
        # Clean username
        username = username.strip().replace("@", "")

        # Run all modules
        tasks = [module.search(username) for module in self.modules]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate results
        successful = [r for r in results if isinstance(r, dict) and r.get('status') == 'success']

        # Deduplicate found accounts
        all_accounts = []
        seen_urls = set()
        for result in successful:
            if 'data' in result and 'accounts' in result['data']:
                for account in result['data']['accounts']:
                    url = account.get('url', '')
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_accounts.append(account)

        return {
            "target": username,
            "type": "username",
            "modules_run": len(self.modules),
            "successful_checks": len(successful),
            "unique_accounts_found": len(all_accounts),
            "accounts": all_accounts,
            "results": results
        }
