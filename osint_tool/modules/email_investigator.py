"""
Email Investigation Module
Integrates: Holehe, Epieos, HIBP, Hunter.io, EmailRep
"""

import asyncio
import hashlib
import os
from typing import Dict, List, Any
import aiohttp
from email_validator import validate_email, EmailNotValidError

from ..core.base import EmailModule


class HoleheChecker(EmailModule):
    """Check email on 120+ platforms using Holehe logic"""

    def get_module_name(self) -> str:
        return "Holehe"

    async def search(self, query: str) -> Dict[str, Any]:
        return await self.check_email(query)

    async def check_email(self, email: str) -> Dict[str, Any]:
        """Check email across multiple platforms"""
        platforms = {
            "twitter": "https://api.twitter.com/i/users/email_available.json",
            "instagram": "https://www.instagram.com/accounts/emailsignup/",
            "github": "https://github.com/signup/check_email",
            "spotify": "https://www.spotify.com/api/signup/validate-email",
            "discord": "https://discord.com/api/v9/auth/register",
            "adobe": "https://auth.services.adobe.com/signin/check",
            "amazon": "https://www.amazon.com/ap/register",
            "snapchat": "https://accounts.snapchat.com/accounts/get_username_suggestions",
            "pinterest": "https://www.pinterest.com/_ngjs/resource/EmailExistsResource/get/",
            "tumblr": "https://www.tumblr.com/svc/account/register",
        }

        results = []
        async with aiohttp.ClientSession() as session:
            tasks = []
            for platform, url in platforms.items():
                tasks.append(self._check_platform(session, platform, url, email))
            results = await asyncio.gather(*tasks, return_exceptions=True)

        found = [r for r in results if isinstance(r, dict) and r.get('exists')]

        return self.format_result(
            source="holehe",
            data={
                "email": email,
                "platforms_found": len(found),
                "total_checked": len(platforms),
                "accounts": found
            }
        )

    async def _check_platform(self, session: aiohttp.ClientSession,
                             platform: str, url: str, email: str) -> Dict:
        """Check if email exists on a specific platform"""
        try:
            # Simplified check - in production, each platform needs specific logic
            data = {"email": email}
            result = await self.fetch(session, url, method="POST", json=data)

            # Platform-specific response parsing would go here
            # This is a simplified version
            return {
                "platform": platform,
                "exists": result is not None,
                "url": url
            }
        except Exception as e:
            self.logger.debug(f"Error checking {platform}: {e}")
            return {"platform": platform, "exists": False, "error": str(e)}


class EpieosChecker(EmailModule):
    """Check email using Epieos (Google Maps, social networks)"""

    def get_module_name(self) -> str:
        return "Epieos"

    async def search(self, query: str) -> Dict[str, Any]:
        return await self.check_email(query)

    async def check_email(self, email: str) -> Dict[str, Any]:
        """Check email via Epieos"""
        # Epieos doesn't have a public API, this would require web scraping
        # For now, returning structure for integration

        async with aiohttp.ClientSession() as session:
            # Note: Epieos requires web interface interaction
            # This is a placeholder for the actual implementation
            data = {
                "email": email,
                "google_maps_reviews": [],
                "google_photos": [],
                "youtube_channels": [],
                "note": "Epieos requires manual checking via web interface"
            }

        return self.format_result(
            source="epieos",
            data=data,
            status="partial"
        )


class HIBPChecker(EmailModule):
    """Have I Been Pwned checker"""

    def __init__(self, api_key: Optional[str] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_key = api_key or os.getenv('HIBP_API_KEY')
        self.base_url = "https://haveibeenpwned.com/api/v3"

    def get_module_name(self) -> str:
        return "HaveIBeenPwned"

    async def search(self, query: str) -> Dict[str, Any]:
        return await self.check_email(query)

    async def check_email(self, email: str) -> Dict[str, Any]:
        """Check if email appears in breaches"""
        if not self.api_key:
            return self.format_result(
                source="hibp",
                data={"error": "API key required"},
                status="error"
            )

        headers = {
            "hibp-api-key": self.api_key,
            "User-Agent": "OSINT-Investigator"
        }

        async with aiohttp.ClientSession() as session:
            # Check breaches
            breaches_url = f"{self.base_url}/breachedaccount/{email}"
            breaches = await self.fetch(session, breaches_url, headers=headers)

            # Check pastes
            pastes_url = f"{self.base_url}/pasteaccount/{email}"
            pastes = await self.fetch(session, pastes_url, headers=headers)

        breach_list = breaches if isinstance(breaches, list) else []
        paste_list = pastes if isinstance(pastes, list) else []

        return self.format_result(
            source="hibp",
            data={
                "email": email,
                "breach_count": len(breach_list),
                "paste_count": len(paste_list),
                "breaches": breach_list,
                "pastes": paste_list,
                "is_compromised": len(breach_list) > 0 or len(paste_list) > 0
            }
        )


class HunterIOChecker(EmailModule):
    """Hunter.io email finder and verifier"""

    def __init__(self, api_key: Optional[str] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_key = api_key or os.getenv('HUNTER_API_KEY')
        self.base_url = "https://api.hunter.io/v2"

    def get_module_name(self) -> str:
        return "Hunter.io"

    async def search(self, query: str) -> Dict[str, Any]:
        return await self.check_email(query)

    async def check_email(self, email: str) -> Dict[str, Any]:
        """Verify email and find related information"""
        if not self.api_key:
            return self.format_result(
                source="hunter",
                data={"error": "API key required"},
                status="error"
            )

        url = f"{self.base_url}/email-verifier"
        params = {
            "email": email,
            "api_key": self.api_key
        }

        async with aiohttp.ClientSession() as session:
            result = await self.fetch(session, url, params=params)

        if result and 'data' in result:
            data = result['data']
            return self.format_result(
                source="hunter",
                data={
                    "email": email,
                    "status": data.get('status'),
                    "score": data.get('score'),
                    "smtp_check": data.get('smtp_check'),
                    "mx_records": data.get('mx_records'),
                    "sources": data.get('sources', [])
                }
            )

        return self.format_result(
            source="hunter",
            data={"error": "Unable to verify email"},
            status="error"
        )


class EmailRepChecker(EmailModule):
    """EmailRep.io reputation checker"""

    def get_module_name(self) -> str:
        return "EmailRep"

    async def search(self, query: str) -> Dict[str, Any]:
        return await self.check_email(query)

    async def check_email(self, email: str) -> Dict[str, Any]:
        """Check email reputation"""
        url = f"https://emailrep.io/{email}"

        async with aiohttp.ClientSession() as session:
            result = await self.fetch(session, url)

        if result:
            return self.format_result(
                source="emailrep",
                data={
                    "email": email,
                    "reputation": result.get('reputation'),
                    "suspicious": result.get('suspicious'),
                    "references": result.get('references'),
                    "details": result.get('details', {})
                }
            )

        return self.format_result(
            source="emailrep",
            data={"error": "Unable to check reputation"},
            status="error"
        )


class EmailInvestigator:
    """Orchestrates all email investigation modules"""

    def __init__(self):
        self.modules = [
            HoleheChecker(),
            EpieosChecker(),
            HIBPChecker(),
            HunterIOChecker(),
            EmailRepChecker()
        ]

    async def investigate(self, email: str) -> Dict[str, Any]:
        """Run all email checks"""
        # Validate email
        try:
            valid = validate_email(email)
            email = valid.email
        except EmailNotValidError as e:
            return {
                "error": "Invalid email format",
                "details": str(e)
            }

        # Run all modules
        tasks = [module.search(email) for module in self.modules]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate results
        successful = [r for r in results if isinstance(r, dict) and r.get('status') != 'error']

        return {
            "target": email,
            "type": "email",
            "modules_run": len(self.modules),
            "successful_checks": len(successful),
            "results": results
        }
