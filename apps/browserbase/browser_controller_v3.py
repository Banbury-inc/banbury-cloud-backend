"""
Browser controller using the official Browserbase SDK properly
"""
import asyncio
import json
import os
from typing import Dict, Any, Optional
from browserbase import Browserbase
from playwright.async_api import async_playwright
import logging
import time
from django.core.cache import cache

logger = logging.getLogger(__name__)

class BrowserbaseController:
    """Controller for automating Browserbase sessions using official SDK"""
    
    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self._playwright = None
        self._running = False
        self._bb = None
        self._cache_timeout = 3600  # 1 hour cache timeout
    
    async def start(self):
        """Start the Playwright instance and Browserbase client"""
        if not self._running:
            api_key = os.environ.get('BROWSERBASE_API_KEY')
            if not api_key:
                raise Exception('Browserbase API key not configured')
            
            self._bb = Browserbase(api_key=api_key)
            self._playwright = await async_playwright().start()
            self._running = True
    
    async def stop(self):
        """Stop the Playwright instance and close all sessions"""
        if self._running:
            for session_id in list(self.sessions.keys()):
                await self.close_session(session_id)
            if self._playwright:
                await self._playwright.stop()
            self._running = False
    
    def _get_session_cache_key(self, session_id: str) -> str:
        """Get cache key for session data"""
        return f"browserbase_session_{session_id}"
    
    def _save_session_to_cache(self, session_id: str, session_data: Dict[str, Any]):
        """Save session data to Django cache for persistence across requests"""
        try:
            # Only save serializable data
            cache_data = {
                'session_id': session_id,
                'connection_url': session_data.get('connection_url'),
                'created_at': session_data.get('created_at'),
                'connected_at': session_data.get('connected_at'),
            }
            cache_key = self._get_session_cache_key(session_id)
            
            print(f"[DEBUG] Attempting to save session {session_id} to cache with key: {cache_key}")
            print(f"[DEBUG] Cache data: {cache_data}")
            
            # Try to save to cache
            result = cache.set(cache_key, cache_data, timeout=self._cache_timeout)
            print(f"[DEBUG] Cache.set returned: {result}")
            
            # Immediately verify it was saved
            verification = cache.get(cache_key)
            if verification:
                print(f"[DEBUG] ✅ Session {session_id} successfully saved and verified in cache")
            else:
                print(f"[DEBUG] ❌ Session {session_id} cache verification failed!")
                # Also try to save to a simple file as backup
                self._save_session_to_file_backup(session_id, cache_data)
                
        except Exception as e:
            print(f"[DEBUG] Error saving session {session_id} to cache: {str(e)}")
            # Fallback to file storage
            self._save_session_to_file_backup(session_id, cache_data)
    
    def _save_session_to_file_backup(self, session_id: str, cache_data: Dict[str, Any]):
        """Backup session data to file when cache fails"""
        try:
            backup_dir = "/tmp/browserbase_sessions"
            os.makedirs(backup_dir, exist_ok=True)
            backup_file = os.path.join(backup_dir, f"{session_id}.json")
            
            with open(backup_file, 'w') as f:
                json.dump(cache_data, f)
            print(f"[DEBUG] Session {session_id} saved to file backup: {backup_file}")
        except Exception as e:
            print(f"[DEBUG] Failed to save session {session_id} to file backup: {str(e)}")
    
    def _load_session_from_file_backup(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load session data from file backup"""
        try:
            backup_file = f"/tmp/browserbase_sessions/{session_id}.json"
            if os.path.exists(backup_file):
                with open(backup_file, 'r') as f:
                    data = json.load(f)
                print(f"[DEBUG] Loaded session {session_id} from file backup")
                return data
        except Exception as e:
            print(f"[DEBUG] Failed to load session {session_id} from file backup: {str(e)}")
        return None
    
    def _load_session_from_cache(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load session data from Django cache with file backup fallback"""
        cache_key = self._get_session_cache_key(session_id)
        print(f"[DEBUG] Attempting to load session {session_id} from cache with key: {cache_key}")
        
        try:
            cache_data = cache.get(cache_key)
            if cache_data:
                print(f"[DEBUG] Loaded session {session_id} from cache")
                return cache_data
        except Exception as e:
            print(f"[DEBUG] Error loading session {session_id} from cache: {str(e)}")
        
        print(f"[DEBUG] Session {session_id} not found in cache, trying file backup...")
        # Try file backup
        backup_data = self._load_session_from_file_backup(session_id)
        if backup_data:
            # Restore to cache if possible
            try:
                cache.set(cache_key, backup_data, timeout=self._cache_timeout)
                print(f"[DEBUG] Restored session {session_id} from backup to cache")
            except Exception as e:
                print(f"[DEBUG] Failed to restore session {session_id} to cache: {str(e)}")
            return backup_data
        
        print(f"[DEBUG] Session {session_id} not found in cache or backup")
        return None
    
    def _remove_session_from_cache(self, session_id: str):
        """Remove session data from cache and backup files"""
        cache_key = self._get_session_cache_key(session_id)
        try:
            cache.delete(cache_key)
            print(f"[DEBUG] Removed session {session_id} from cache")
        except Exception as e:
            print(f"[DEBUG] Error removing session {session_id} from cache: {str(e)}")
        
        # Also remove backup file
        try:
            backup_file = f"/tmp/browserbase_sessions/{session_id}.json"
            if os.path.exists(backup_file):
                os.remove(backup_file)
                print(f"[DEBUG] Removed session {session_id} backup file")
        except Exception as e:
            print(f"[DEBUG] Error removing session {session_id} backup file: {str(e)}")
    
    def _fetch_session_from_api(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Fetch session information from Browserbase API"""
        try:
            import requests
            
            api_key = os.environ.get('BROWSERBASE_API_KEY')
            if not api_key:
                print(f"[DEBUG] No API key available to fetch session {session_id}")
                return None
            
            url = f"https://api.browserbase.com/v1/sessions/{session_id}"
            headers = {'x-bb-api-key': api_key}
            
            print(f"[DEBUG] Fetching session info from: {url}")
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                print(f"[DEBUG] Fetched session {session_id} from API: {data}")
                
                # Get connection URL from the response
                connection_url = data.get('connectUrl')
                if connection_url:
                    return {
                        'session_id': session_id,
                        'connection_url': connection_url,
                        'created_at': time.time(),  # Approximate since we don't have exact creation time
                        'status': data.get('status')
                    }
                else:
                    print(f"[DEBUG] No connectUrl found in API response for session {session_id}")
            else:
                print(f"[DEBUG] Failed to fetch session {session_id} from API: {response.status_code} - {response.text}")
                        
        except Exception as e:
            print(f"[DEBUG] Error fetching session {session_id} from API: {str(e)}")
        
        return None
    
    async def _ensure_on_google(self, page) -> None:
        """Guarantee that the given Playwright page is navigated to Google.
        
        If it is still blank (typical values: about:blank, "", chrome-internal URLs)
        then we perform a best-effort navigation to https://www.google.com and wait
        up to 15 seconds. We silently swallow navigation errors because the rest of
        the pipeline should keep running even if Google fails to load.
        
        This is based on Athena Intelligence's implementation.
        """
        try:
            url: str = page.url or ""
            # Treat about:blank or empty as blank for our purposes
            is_blank = url in ("about:blank", "")
            print(f"[DEBUG] Page URL: {url}, is_blank: {is_blank}")
            
            if is_blank:
                print(f"[DEBUG] Page is blank, navigating to Google...")
                await page.goto(
                    "https://www.google.com",
                    timeout=15000,  # 15 seconds
                    wait_until="domcontentloaded",
                )
                page_title = await page.title()
                print(f"[DEBUG] Successfully navigated to Google: {page_title}")
            else:
                page_title = await page.title()
                print(f"[DEBUG] Page already has content: {page_title} ({url})")
        except Exception as nav_err:
            # Do not raise – just log and continue like Athena Intelligence does
            print(f"[DEBUG] _ensure_on_google failed navigation attempt: {nav_err}")
    
    async def create_and_connect_session(self, project_id: str, start_url: str = 'https://www.google.com') -> Dict[str, Any]:
        """Create a new Browserbase session and connect Playwright to it"""
        try:
            await self.start()
            
            print(f"[DEBUG] Creating new Browserbase session with project {project_id}")
            
            # Create session using SDK with proper configuration
            session = self._bb.sessions.create(
                project_id=project_id,
                keep_alive=True
            )
            
            session_id = session.id
            connection_url = session.connection_url
            print(f"[DEBUG] Created session {session_id}")
            print(f"[DEBUG] Connection URL: {connection_url}")
            
            # Store session info immediately (before connection attempt)
            session_data = {
                'session': session,
                'browser': None,
                'context': None,
                'page': None,
                'connection_url': connection_url,
                'created_at': time.time()
            }
            self.sessions[session_id] = session_data
            
            # Save to cache for persistence across requests
            self._save_session_to_cache(session_id, session_data)
            
            # Connect Playwright immediately (documentation recommends prompt connection)
            print(f"[DEBUG] Connecting Playwright to session {session_id}")
            browser = await self._playwright.chromium.connect_over_cdp(connection_url)
            print(f"[DEBUG] Browser connected successfully")
            
            # Always use default context for stealth features (per documentation)
            # Get the first context and first page like Athena Intelligence does
            contexts = browser.contexts
            if contexts and len(contexts) > 0:
                context = contexts[0]  # Use default context
                pages = context.pages
                page = pages[0] if pages and len(pages) > 0 else await context.new_page()
                print(f"[DEBUG] Using existing default context with {len(pages)} pages")
            else:
                print(f"[DEBUG] Creating new default context")
                context = await browser.new_context()
                page = await context.new_page()
            
            # Update session info with connected resources
            # Set up download behavior like Athena Intelligence
            try:
                cdp = await browser.new_browser_cdp_session()
                await cdp.send(
                    "Browser.setDownloadBehavior",
                    {
                        "behavior": "allow",
                        "downloadPath": "/tmp/downloads",
                        "eventsEnabled": True,
                    },
                )
                print(f"[DEBUG] CDP session configured for downloads")
            except Exception as cdp_error:
                print(f"[DEBUG] Warning: Failed to configure CDP session: {cdp_error}")
            
            self.sessions[session_id].update({
                'browser': browser,
                'context': context,
                'page': page,
                'connected_at': time.time()
            })
            
            # Update cache with connection info
            self._save_session_to_cache(session_id, self.sessions[session_id])
            
            # Ensure we navigate to Google if page is blank (like Athena Intelligence does)
            await self._ensure_on_google(page)
            
            # If a custom start URL was specified and it's not Google, navigate to it
            if start_url != 'https://www.google.com':
                try:
                    print(f"[DEBUG] Navigating to custom start page: {start_url}")
                    await page.goto(start_url, wait_until='domcontentloaded', timeout=30000)
                    page_title = await page.title()
                    current_url = page.url
                    print(f"[DEBUG] Successfully navigated to: {page_title} ({current_url})")
                except Exception as nav_error:
                    print(f"[DEBUG] Warning: Failed to navigate to start page: {str(nav_error)}")
                    # Don't fail the session creation if navigation fails
            
            print(f"[DEBUG] Session {session_id} connected successfully")
            
            return {
                'success': True,
                'id': session_id,
                'connection_url': connection_url,
                'debug_url': getattr(session, 'debug_url', None)
            }
            
        except Exception as e:
            print(f"[DEBUG] Failed to create session: {str(e)}")
            # Clean up failed session
            if 'session_id' in locals() and session_id in self.sessions:
                del self.sessions[session_id]
            return {'success': False, 'error': str(e)}
    
    async def connect_to_existing_session(self, session_id: str, connection_url: str) -> bool:
        """Connect to an existing Browserbase session"""
        try:
            await self.start()
            
            print(f"[DEBUG] Connecting to existing session {session_id}")
            print(f"[DEBUG] Connection URL: {connection_url}")
            
            # Store session info first
            self.sessions[session_id] = {
                'session': None,
                'browser': None,
                'context': None,
                'page': None,
                'connection_url': connection_url
            }
            
            # Try to connect to the existing session
            browser = await self._playwright.chromium.connect_over_cdp(connection_url)
            print(f"[DEBUG] Playwright connected successfully")
            
            # Get or create context and page like Athena Intelligence
            contexts = browser.contexts
            if contexts and len(contexts) > 0:
                context = contexts[0]
                pages = context.pages
                page = pages[0] if pages and len(pages) > 0 else await context.new_page()
            else:
                context = await browser.new_context()
                page = await context.new_page()
            
            self.sessions[session_id].update({
                'browser': browser,
                'context': context,
                'page': page
            })
            
            # Ensure we are on Google before returning (like Athena Intelligence)
            await self._ensure_on_google(page)
            
            print(f"[DEBUG] Session {session_id} connected successfully")
            return True
            
        except Exception as e:
            print(f"[DEBUG] Failed to connect to session {session_id}: {str(e)}")
            return False
    
    async def _ensure_connected(self, session_id: str) -> bool:
        """Ensure we're connected to the session"""
        print(f"[DEBUG] Ensuring connection for session {session_id}")
        
        # Check if session exists in memory first
        if session_id not in self.sessions:
            print(f"[DEBUG] Session {session_id} not found in controller memory")
            
            # Since frontend now sends session ID, we can try to get session info from Browserbase API
            try:
                print(f"[DEBUG] Attempting to fetch session {session_id} info from Browserbase API")
                session_info = self._fetch_session_from_api(session_id)
                if session_info:
                    print(f"[DEBUG] Found session {session_id} in Browserbase, attempting to connect")
                    return await self.connect_to_existing_session(session_id, session_info['connection_url'])
            except Exception as e:
                print(f"[DEBUG] Failed to fetch session {session_id} from API: {str(e)}")
            
            print(f"[DEBUG] Session {session_id} not found")
            return False
        
        session = self.sessions[session_id]
        
        # Check session age (Browserbase sessions have timeouts)
        created_at = session.get('created_at', 0)
        current_time = time.time()
        
        # Only check age if we have a valid created_at timestamp
        if created_at > 0:
            age_minutes = (current_time - created_at) / 60
            if age_minutes > 300:  # 5 hours timeout (adjust based on your session config)
                print(f"[DEBUG] Session {session_id} too old ({age_minutes:.1f} minutes), removing")
                del self.sessions[session_id]
                self._remove_session_from_cache(session_id)
                return False
            print(f"[DEBUG] Session {session_id} age: {age_minutes:.1f} minutes")
        else:
            print(f"[DEBUG] Session {session_id} has no created_at timestamp, skipping age check")
        
        # Check if already connected and alive
        if session.get('browser') and session.get('page'):
            try:
                # Quick connectivity test
                title = await session['page'].title()
                print(f"[DEBUG] Connection alive, page title: {title}")
                return True
            except Exception as e:
                print(f"[DEBUG] Connection test failed: {str(e)}")
                # Clear dead connection references
                session['browser'] = None
                session['context'] = None  
                session['page'] = None
        
        # Try to reconnect if we have the connection URL
        connection_url = session.get('connection_url')
        if not connection_url:
            print(f"[DEBUG] No connection URL for session {session_id}")
            return False
        
        print(f"[DEBUG] Attempting to reconnect to session {session_id}")
        return await self.connect_to_existing_session(session_id, connection_url)
    
    async def close_session(self, session_id: str):
        """Close a browser session"""
        if session_id in self.sessions:
            try:
                session = self.sessions[session_id]
                if session.get('browser'):
                    await session['browser'].close()
                del self.sessions[session_id]
                # Remove from cache too
                self._remove_session_from_cache(session_id)
                print(f"[DEBUG] Closed session {session_id}")
            except Exception as e:
                print(f"[DEBUG] Error closing session {session_id}: {str(e)}")
        else:
            # Even if not in memory, remove from cache
            self._remove_session_from_cache(session_id)
    
    async def navigate(self, session_id: str, url: str) -> Dict[str, Any]:
        """Navigate to a URL"""
        if not await self._ensure_connected(session_id):
            return {'success': False, 'error': 'Session not found or connection failed'}
        
        try:
            page = self.sessions[session_id]['page']
            print(f"[DEBUG] Navigating to {url}")
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            title = await page.title()
            current_url = page.url
            print(f"[DEBUG] Navigation successful: {title}")
            return {
                'success': True,
                'url': current_url,
                'title': title
            }
        except Exception as e:
            print(f"[DEBUG] Navigation failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def click(self, session_id: str, selector: str) -> Dict[str, Any]:
        """Click an element"""
        if not await self._ensure_connected(session_id):
            return {'success': False, 'error': 'Session not found or connection failed'}
        
        try:
            page = self.sessions[session_id]['page']
            print(f"[DEBUG] Clicking element: {selector}")
            await page.click(selector, timeout=10000)
            print(f"[DEBUG] Click successful")
            return {'success': True, 'clicked': selector}
        except Exception as e:
            print(f"[DEBUG] Click failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def type_text(self, session_id: str, selector: str, text: str) -> Dict[str, Any]:
        """Type text into an element"""
        if not await self._ensure_connected(session_id):
            return {'success': False, 'error': 'Session not found or connection failed'}
        
        try:
            page = self.sessions[session_id]['page']
            print(f"[DEBUG] Typing '{text}' into {selector}")
            await page.fill(selector, text)
            print(f"[DEBUG] Type successful")
            return {'success': True, 'typed': text, 'selector': selector}
        except Exception as e:
            print(f"[DEBUG] Type failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def screenshot(self, session_id: str, full_page: bool = False) -> Dict[str, Any]:
        """Take a screenshot"""
        if not await self._ensure_connected(session_id):
            return {'success': False, 'error': 'Session not found or connection failed'}
        
        try:
            page = self.sessions[session_id]['page']
            print(f"[DEBUG] Taking screenshot (full_page={full_page})")
            screenshot_bytes = await page.screenshot(full_page=full_page)
            import base64
            screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
            print(f"[DEBUG] Screenshot successful ({len(screenshot_base64)} chars)")
            return {
                'success': True,
                'screenshot': f'data:image/png;base64,{screenshot_base64}'
            }
        except Exception as e:
            print(f"[DEBUG] Screenshot failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def get_content(self, session_id: str) -> Dict[str, Any]:
        """Get page content"""
        if not await self._ensure_connected(session_id):
            return {'success': False, 'error': 'Session not found or connection failed'}
        
        try:
            page = self.sessions[session_id]['page']
            print(f"[DEBUG] Getting page content")
            content = {
                'title': await page.title(),
                'url': page.url,
                'html': await page.content(),
                'text': await page.inner_text('body')
            }
            print(f"[DEBUG] Content retrieved: {content['title']}")
            return {'success': True, 'content': content}
        except Exception as e:
            print(f"[DEBUG] Get content failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def wait_for(self, session_id: str, selector: str = None, timeout: int = 5000) -> Dict[str, Any]:
        """Wait for an element or timeout"""
        if not await self._ensure_connected(session_id):
            return {'success': False, 'error': 'Session not found or connection failed'}
        
        try:
            page = self.sessions[session_id]['page']
            if selector:
                print(f"[DEBUG] Waiting for selector: {selector}")
                await page.wait_for_selector(selector, timeout=timeout)
                print(f"[DEBUG] Selector found")
                return {'success': True, 'found': selector}
            else:
                print(f"[DEBUG] Waiting {timeout}ms")
                await asyncio.sleep(timeout / 1000)
                return {'success': True, 'waited': timeout}
        except Exception as e:
            print(f"[DEBUG] Wait failed: {str(e)}")
            return {'success': False, 'error': str(e)}

# Global instance
browser_controller = BrowserbaseController()

