"""
Phone Investigation Module
Integrates: PhoneInfoga, Numverify, TrueCaller
"""

import asyncio
import os
from typing import Dict, List, Any, Optional
import aiohttp
import phonenumbers
from phonenumbers import geocoder, carrier, timezone

from ..core.base import PhoneModule


class PhoneInfogaChecker(PhoneModule):
    """PhoneInfoga-style phone number investigation"""

    def get_module_name(self) -> str:
        return "PhoneInfoga"

    async def search(self, query: str) -> Dict[str, Any]:
        return await self.check_phone(query)

    async def check_phone(self, phone: str) -> Dict[str, Any]:
        """Comprehensive phone number analysis"""
        try:
            # Parse phone number
            parsed = phonenumbers.parse(phone, None)

            # Validate
            is_valid = phonenumbers.is_valid_number(parsed)
            is_possible = phonenumbers.is_possible_number(parsed)

            # Get metadata
            country = geocoder.description_for_number(parsed, "en")
            carrier_name = carrier.name_for_number(parsed, "en")
            timezones = timezone.time_zones_for_number(parsed)
            number_type = phonenumbers.number_type(parsed)

            # Type mapping
            type_map = {
                0: "FIXED_LINE",
                1: "MOBILE",
                2: "FIXED_LINE_OR_MOBILE",
                3: "TOLL_FREE",
                4: "PREMIUM_RATE",
                5: "SHARED_COST",
                6: "VOIP",
                7: "PERSONAL_NUMBER",
                8: "PAGER",
                9: "UAN",
                10: "VOICEMAIL",
                -1: "UNKNOWN"
            }

            # Format variations
            formats = {
                "E164": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164),
                "INTERNATIONAL": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL),
                "NATIONAL": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL),
                "RFC3966": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.RFC3966)
            }

            data = {
                "number": phone,
                "valid": is_valid,
                "possible": is_possible,
                "country": country,
                "country_code": f"+{parsed.country_code}",
                "carrier": carrier_name,
                "line_type": type_map.get(number_type, "UNKNOWN"),
                "timezones": list(timezones),
                "formats": formats
            }

            # Search on Google (dorks)
            async with aiohttp.ClientSession() as session:
                google_results = await self._search_google(session, phone)
                data["google_results"] = google_results

            return self.format_result(source="phoneinfoga", data=data)

        except phonenumbers.NumberParseException as e:
            return self.format_result(
                source="phoneinfoga",
                data={"error": f"Invalid phone number: {str(e)}"},
                status="error"
            )

    async def _search_google(self, session: aiohttp.ClientSession,
                           phone: str) -> Dict[str, Any]:
        """Search for phone number on Google using dorks"""
        # Note: Real implementation would use Google Custom Search API
        # or scraping (which requires more complex implementation)

        dorks = [
            f'"{phone}"',
            f'"{phone}" site:facebook.com',
            f'"{phone}" site:twitter.com',
            f'"{phone}" site:linkedin.com',
            f'"{phone}" site:instagram.com'
        ]

        return {
            "dorks_generated": len(dorks),
            "dorks": dorks,
            "note": "Use these dorks manually or with Google Custom Search API"
        }


class NumverifyChecker(PhoneModule):
    """Numverify API phone validation"""

    def __init__(self, api_key: Optional[str] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_key = api_key or os.getenv('NUMVERIFY_API_KEY')
        self.base_url = "http://apilayer.net/api"

    def get_module_name(self) -> str:
        return "Numverify"

    async def search(self, query: str) -> Dict[str, Any]:
        return await self.check_phone(query)

    async def check_phone(self, phone: str) -> Dict[str, Any]:
        """Validate phone using Numverify"""
        if not self.api_key:
            return self.format_result(
                source="numverify",
                data={"note": "API key not provided, skipping"},
                status="skipped"
            )

        url = f"{self.base_url}/validate"
        params = {
            "access_key": self.api_key,
            "number": phone
        }

        async with aiohttp.ClientSession() as session:
            result = await self.fetch(session, url, params=params)

        if result and result.get('valid'):
            return self.format_result(
                source="numverify",
                data={
                    "number": phone,
                    "valid": result.get('valid'),
                    "country_code": result.get('country_code'),
                    "country_name": result.get('country_name'),
                    "location": result.get('location'),
                    "carrier": result.get('carrier'),
                    "line_type": result.get('line_type')
                }
            )

        return self.format_result(
            source="numverify",
            data={"error": "Unable to validate", "response": result},
            status="error"
        )


class TrueCallerChecker(PhoneModule):
    """TrueCaller-style lookup"""

    def get_module_name(self) -> str:
        return "TrueCaller"

    async def search(self, query: str) -> Dict[str, Any]:
        return await self.check_phone(query)

    async def check_phone(self, phone: str) -> Dict[str, Any]:
        """
        Note: TrueCaller doesn't have a public API.
        This is a placeholder for potential integration methods.
        """
        return self.format_result(
            source="truecaller",
            data={
                "number": phone,
                "note": "TrueCaller requires manual checking or unofficial APIs",
                "suggestion": "Use TrueCaller mobile app or unofficial Python libraries"
            },
            status="partial"
        )


class PhoneInvestigator:
    """Orchestrates all phone investigation modules"""

    def __init__(self):
        self.modules = [
            PhoneInfogaChecker(),
            NumverifyChecker(),
            TrueCallerChecker()
        ]

    async def investigate(self, phone: str) -> Dict[str, Any]:
        """Run all phone checks"""
        # Clean phone number
        phone = phone.strip().replace(" ", "").replace("-", "")

        # Run all modules
        tasks = [module.search(phone) for module in self.modules]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate results
        successful = [r for r in results if isinstance(r, dict) and r.get('status') == 'success']

        return {
            "target": phone,
            "type": "phone",
            "modules_run": len(self.modules),
            "successful_checks": len(successful),
            "results": results
        }
