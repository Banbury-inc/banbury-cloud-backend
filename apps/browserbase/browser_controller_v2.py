"""
Browser controller using the official Browserbase SDK with Playwright
"""
import asyncio
import json
import os
from typing import Dict, Any, Optional
from browserbase import Browserbase
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
import logging

logger = logging.getLogger(__name__)

class BrowserbaseController:
    """Controller for automating Browserbase sessions using official SDK + Playwright"""
    
    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self._playwright = None
        self._running = False
        self._bb = None
    
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
    
    async def connect_to_session(self, session_id: str, connect_url: str) -> bool:
        """Connect to a Browserbase session using Playwright"""
        try:
            await self.start()
            
            print(f"[DEBUG] Connecting to Browserbase session {session_id}")
            print(f"[DEBUG] Connect URL: {connect_url}")
            
            # Store session info
            self.sessions[session_id] = {
                'connect_url': connect_url,
                'browser': None,
                'context': None,
                'page': None,
                'bb_session': None
            }
            
            # Connect using Playwright
            try:
                print(f"[DEBUG] Connecting Playwright to {connect_url}")
                browser = await self._playwright.chromium.connect_over_cdp(connect_url)
                print(f"[DEBUG] Playwright connected successfully")
                
                # Get or create context and page
                contexts = browser.contexts
                if contexts:
                    context = contexts[0]
                    pages = context.pages
                    page = pages[0] if pages else await context.new_page()
                    print(f"[DEBUG] Using existing context with {len(pages)} pages")
                else:
                    print(f"[DEBUG] Creating new context")
                    context = await browser.new_context()
                    page = await context.new_page()
                
                self.sessions[session_id].update({
                    'browser': browser,
                    'context': context,
                    'page': page
                })
                
                print(f"[DEBUG] Session {session_id} connected successfully")
                return True
                
            except Exception as e:
                print(f"[DEBUG] Playwright connection failed: {str(e)}")
                # Store for later retry
                return True
            
        except Exception as e:
            print(f"[DEBUG] Failed to setup session {session_id}: {str(e)}")
            return False
    
    async def _ensure_connected(self, session_id: str) -> bool:
        """Ensure we're connected to the session, reconnecting if necessary"""
        print(f"[DEBUG] Ensuring connection for session {session_id}")
        
        if session_id not in self.sessions:
            print(f"[DEBUG] Session {session_id} not found")
            return False
        
        session = self.sessions[session_id]
        
        # Check if already connected
        if session.get('browser') and session.get('page'):
            try:
                title = await session['page'].title()
                print(f"[DEBUG] Connection alive, page title: {title}")
                return True
            except Exception as e:
                print(f"[DEBUG] Connection test failed: {str(e)}")
        
        # Try to reconnect
        connect_url = session.get('connect_url')
        if not connect_url:
            print(f"[DEBUG] No connect URL for session {session_id}")
            return False
        
        try:
            print(f"[DEBUG] Reconnecting to {connect_url}")
            browser = await self._playwright.chromium.connect_over_cdp(connect_url)
            
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
            
            print(f"[DEBUG] Successfully reconnected to session {session_id}")
            return True
        except Exception as e:
            print(f"[DEBUG] Reconnection failed: {str(e)}")
            return False
    
    async def close_session(self, session_id: str):
        """Close a browser session"""
        if session_id in self.sessions:
            try:
                session = self.sessions[session_id]
                if session.get('browser'):
                    await session['browser'].close()
                del self.sessions[session_id]
                print(f"[DEBUG] Closed session {session_id}")
            except Exception as e:
                print(f"[DEBUG] Error closing session {session_id}: {str(e)}")
    
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

