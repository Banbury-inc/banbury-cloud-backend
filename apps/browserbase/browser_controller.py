"""
Browser controller using Playwright to connect to Browserbase sessions
"""
import asyncio
import json
from typing import Dict, Any, Optional
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
import logging

logger = logging.getLogger(__name__)

class BrowserbaseController:
    """Controller for automating Browserbase sessions using Playwright"""
    
    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self._playwright = None
        self._running = False
    
    async def start(self):
        """Start the Playwright instance"""
        if not self._running:
            self._playwright = await async_playwright().start()
            self._running = True
    
    async def stop(self):
        """Stop the Playwright instance and close all sessions"""
        if self._running:
            for session_id in list(self.sessions.keys()):
                await self.close_session(session_id)
            await self._playwright.stop()
            self._running = False
    
    async def connect_to_session(self, session_id: str, ws_endpoint: str) -> bool:
        """Connect to a Browserbase session using its WebSocket endpoint"""
        try:
            await self.start()
            
            print(f"[DEBUG] Attempting to connect to session {session_id}")
            print(f"[DEBUG] WebSocket endpoint: {ws_endpoint}")
            
            # Store the WebSocket endpoint even if connection fails initially
            self.sessions[session_id] = {
                'ws_endpoint': ws_endpoint,
                'browser': None,
                'context': None,
                'page': None
            }
            
            # Try to connect to the browser
            try:
                print(f"[DEBUG] Connecting to Playwright CDP at {ws_endpoint}")
                # Connect to the browser using the WebSocket endpoint
                browser = await self._playwright.chromium.connect_over_cdp(ws_endpoint)
                print(f"[DEBUG] Successfully connected to browser")
                
                # Get the default context and page
                contexts = browser.contexts
                print(f"[DEBUG] Found {len(contexts)} contexts")
                
                if contexts:
                    context = contexts[0]
                    pages = context.pages
                    print(f"[DEBUG] Found {len(pages)} pages in context")
                    page = pages[0] if pages else await context.new_page()
                else:
                    print(f"[DEBUG] No contexts found, creating new context")
                    context = await browser.new_context()
                    page = await context.new_page()
                
                self.sessions[session_id].update({
                    'browser': browser,
                    'context': context,
                    'page': page
                })
                
                print(f"[DEBUG] Session {session_id} fully connected")
                logger.info(f"Connected to Browserbase session {session_id}")
                return True
            except Exception as e:
                print(f"[DEBUG] Initial connection failed for session {session_id}: {str(e)}")
                logger.warning(f"Initial connection failed for session {session_id}: {str(e)}. Will retry on demand.")
                return True  # Return True so session is stored for later retry
            
        except Exception as e:
            print(f"[DEBUG] Failed to setup session {session_id}: {str(e)}")
            logger.error(f"Failed to setup session {session_id}: {str(e)}")
            return False
    
    async def _ensure_connected(self, session_id: str) -> bool:
        """Ensure we're connected to the session, reconnecting if necessary"""
        print(f"[DEBUG] _ensure_connected called for session {session_id}")
        print(f"[DEBUG] Available sessions: {list(self.sessions.keys())}")
        
        if session_id not in self.sessions:
            print(f"[DEBUG] Session {session_id} not found in sessions")
            return False
        
        session = self.sessions[session_id]
        print(f"[DEBUG] Session data: browser={session.get('browser') is not None}, page={session.get('page') is not None}")
        
        # Check if already connected
        if session.get('browser') and session.get('page'):
            try:
                # Test if connection is still alive
                title = await session['page'].title()
                print(f"[DEBUG] Connection alive, page title: {title}")
                return True
            except Exception as e:
                print(f"[DEBUG] Connection test failed: {str(e)}")
                # Connection lost, need to reconnect
                pass
        
        # Try to connect/reconnect
        ws_endpoint = session.get('ws_endpoint')
        if not ws_endpoint:
            print(f"[DEBUG] No WebSocket endpoint stored for session {session_id}")
            return False
        
        print(f"[DEBUG] Attempting to reconnect to {ws_endpoint}")
        try:
            browser = await self._playwright.chromium.connect_over_cdp(ws_endpoint)
            print(f"[DEBUG] Reconnection successful")
            
            contexts = browser.contexts
            if contexts:
                context = contexts[0]
                pages = context.pages
                page = pages[0] if pages else await context.new_page()
            else:
                context = await browser.new_context()
                page = await context.new_page()
            
            session.update({
                'browser': browser,
                'context': context,
                'page': page
            })
            
            print(f"[DEBUG] Session {session_id} reconnected successfully")
            logger.info(f"Reconnected to session {session_id}")
            return True
        except Exception as e:
            print(f"[DEBUG] Failed to reconnect to session {session_id}: {str(e)}")
            logger.error(f"Failed to reconnect to session {session_id}: {str(e)}")
            return False
    
    async def close_session(self, session_id: str):
        """Close a browser session"""
        if session_id in self.sessions:
            try:
                session = self.sessions[session_id]
                await session['browser'].close()
                del self.sessions[session_id]
                logger.info(f"Closed session {session_id}")
            except Exception as e:
                logger.error(f"Error closing session {session_id}: {str(e)}")
    
    async def navigate(self, session_id: str, url: str) -> Dict[str, Any]:
        """Navigate to a URL"""
        if not await self._ensure_connected(session_id):
            return {'success': False, 'error': 'Session not found or connection failed'}
        
        try:
            page = self.sessions[session_id]['page']
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            return {
                'success': True,
                'url': page.url,
                'title': await page.title()
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def click(self, session_id: str, selector: str) -> Dict[str, Any]:
        """Click an element"""
        if not await self._ensure_connected(session_id):
            return {'success': False, 'error': 'Session not found or connection failed'}
        
        try:
            page = self.sessions[session_id]['page']
            await page.click(selector, timeout=10000)
            return {'success': True, 'clicked': selector}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def type_text(self, session_id: str, selector: str, text: str) -> Dict[str, Any]:
        """Type text into an element"""
        if not await self._ensure_connected(session_id):
            return {'success': False, 'error': 'Session not found or connection failed'}
        
        try:
            page = self.sessions[session_id]['page']
            await page.fill(selector, text)
            return {'success': True, 'typed': text, 'selector': selector}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def screenshot(self, session_id: str, full_page: bool = False) -> Dict[str, Any]:
        """Take a screenshot"""
        if not await self._ensure_connected(session_id):
            return {'success': False, 'error': 'Session not found or connection failed'}
        
        try:
            page = self.sessions[session_id]['page']
            screenshot_bytes = await page.screenshot(full_page=full_page)
            import base64
            screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
            return {
                'success': True,
                'screenshot': f'data:image/png;base64,{screenshot_base64}'
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def get_content(self, session_id: str) -> Dict[str, Any]:
        """Get page content"""
        if not await self._ensure_connected(session_id):
            return {'success': False, 'error': 'Session not found or connection failed'}
        
        try:
            page = self.sessions[session_id]['page']
            content = {
                'title': await page.title(),
                'url': page.url,
                'html': await page.content(),
                'text': await page.inner_text('body')
            }
            return {'success': True, 'content': content}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def wait_for(self, session_id: str, selector: str = None, timeout: int = 5000) -> Dict[str, Any]:
        """Wait for an element or timeout"""
        if not await self._ensure_connected(session_id):
            return {'success': False, 'error': 'Session not found or connection failed'}
        
        try:
            page = self.sessions[session_id]['page']
            if selector:
                await page.wait_for_selector(selector, timeout=timeout)
                return {'success': True, 'found': selector}
            else:
                await asyncio.sleep(timeout / 1000)
                return {'success': True, 'waited': timeout}
        except Exception as e:
            return {'success': False, 'error': str(e)}

# Global instance with session persistence
browser_controller = BrowserbaseController()

# Session registry to persist session info across requests
SESSION_REGISTRY = {}
