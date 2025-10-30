"""
Base classes for OSINT modules
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime
import aiohttp


class OSINTModule(ABC):
    """Base class for all OSINT modules"""

    def __init__(self, timeout: int = 30, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries
        self.logger = logging.getLogger(self.__class__.__name__)
        self.results: List[Dict[str, Any]] = []

    @abstractmethod
    async def search(self, query: str) -> Dict[str, Any]:
        """Execute search for the given query"""
        pass

    @abstractmethod
    def get_module_name(self) -> str:
        """Return the module name"""
        pass

    async def fetch(self, session: aiohttp.ClientSession, url: str,
                   method: str = "GET", **kwargs) -> Optional[Dict]:
        """Fetch data from URL with retry logic"""
        headers = kwargs.get('headers', {})
        headers.setdefault('User-Agent',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        kwargs['headers'] = headers

        for attempt in range(self.max_retries):
            try:
                async with session.request(
                    method, url, timeout=self.timeout, **kwargs
                ) as response:
                    if response.status == 200:
                        if 'application/json' in response.headers.get('Content-Type', ''):
                            return await response.json()
                        else:
                            return {'text': await response.text()}
                    elif response.status == 429:  # Rate limited
                        wait_time = 2 ** attempt
                        self.logger.warning(f"Rate limited, waiting {wait_time}s")
                        await asyncio.sleep(wait_time)
                    else:
                        self.logger.warning(f"HTTP {response.status} for {url}")

            except asyncio.TimeoutError:
                self.logger.warning(f"Timeout on attempt {attempt + 1} for {url}")
            except Exception as e:
                self.logger.error(f"Error fetching {url}: {str(e)}")

        return None

    def format_result(self, source: str, data: Any,
                     status: str = "success") -> Dict[str, Any]:
        """Format result in standard structure"""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "module": self.get_module_name(),
            "source": source,
            "status": status,
            "data": data
        }


class EmailModule(OSINTModule):
    """Base class for email investigation modules"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @abstractmethod
    async def check_email(self, email: str) -> Dict[str, Any]:
        """Check email across various sources"""
        pass


class PhoneModule(OSINTModule):
    """Base class for phone investigation modules"""

    @abstractmethod
    async def check_phone(self, phone: str) -> Dict[str, Any]:
        """Check phone number across various sources"""
        pass


class UsernameModule(OSINTModule):
    """Base class for username investigation modules"""

    @abstractmethod
    async def check_username(self, username: str) -> Dict[str, Any]:
        """Check username across various sources"""
        pass


class BreachModule(OSINTModule):
    """Base class for breach checking modules"""

    @abstractmethod
    async def check_breach(self, identifier: str) -> Dict[str, Any]:
        """Check if identifier appears in breaches"""
        pass
