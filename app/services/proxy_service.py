
import httpx
from bs4 import BeautifulSoup
import re
import asyncio
import random
from typing import List, Optional

class ProxyService:
    _instance = None
    _proxies: List[str] = []
    _last_updated = 0
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ProxyService, cls).__new__(cls)
        return cls._instance

    async def get_proxies(self) -> List[str]:
        """Fetch proxies from multiple free sources"""
        async with self._lock:
            # Refresh if empty or older than 10 minutes
            import time
            if not self._proxies or time.time() - self._last_updated > 600:
                print("[ProxyService] Fetching new proxies...")
                proxies = set()
                
                try:
                    # Source 1: spys.me
                    async with httpx.AsyncClient() as client:
                        response = await client.get("https://spys.me/proxy.txt", timeout=10)
                        if response.status_code == 200:
                            regex = r"[0-9]+(?:\.[0-9]+){3}:[0-9]+"
                            found = re.findall(regex, response.text)
                            proxies.update(found)
                            print(f"[ProxyService] Fetched {len(found)} from spys.me")
                except Exception as e:
                    print(f"[ProxyService] Error fetching from spys.me: {e}")

                try:
                    # Source 2: free-proxy-list.net
                    async with httpx.AsyncClient() as client:
                        response = await client.get("https://free-proxy-list.net/", timeout=10)
                        if response.status_code == 200:
                            soup = BeautifulSoup(response.content, 'html.parser')
                            # The table structure might vary, looking for the main list
                            rows = soup.select('.table tbody tr')
                            count = 0
                            for row in rows:
                                cols = row.find_all('td')
                                if len(cols) >= 2:
                                    ip = cols[0].text.strip()
                                    port = cols[1].text.strip()
                                    # Basic IP validation
                                    if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ip):
                                        proxy = f"{ip}:{port}"
                                        proxies.add(proxy)
                                        count += 1
                            print(f"[ProxyService] Fetched {count} from free-proxy-list.net")
                except Exception as e:
                    print(f"[ProxyService] Error fetching from free-proxy-list.net: {e}")

                self._proxies = list(proxies)
                self._last_updated = time.time()
                print(f"[ProxyService] Total unique proxies: {len(self._proxies)}")

        return self._proxies

    async def get_next_proxy(self) -> Optional[str]:
        """Get a random proxy from the list"""
        proxies = await self.get_proxies()
        if not proxies:
            return None
        return random.choice(proxies)

proxy_service = ProxyService()
