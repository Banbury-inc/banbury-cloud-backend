from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import os
import json
import urllib.request
import urllib.parse
import time
import base64
import asyncio
from typing import Dict, Any, Optional
from .browser_controller_v3 import browser_controller

@csrf_exempt
@require_http_methods(["POST"])
def create_session(request):
	try:
		project_id = os.environ.get('BROWSERBASE_PROJECT_ID')
		if not project_id:
			return JsonResponse({ 'error': 'Browserbase project ID not configured' }, status=500)

		try:
			body = json.loads(request.body.decode('utf-8') or '{}')
		except Exception:
			body = {}
		
		start_url = body.get('startUrl') or 'https://www.google.com'
		print(f"Creating session with start URL: {start_url}")
		
		# Use the browser controller to create session with SDK
		loop = asyncio.new_event_loop()
		asyncio.set_event_loop(loop)
		
		try:
			session_result = loop.run_until_complete(
				browser_controller.create_and_connect_session(project_id, start_url)
			)
			
			if not session_result.get('success'):
				error_msg = session_result.get('error', 'Failed to create session')
				print(f"Session creation failed: {error_msg}")
				return JsonResponse({
					'error': error_msg,
					'success': False,
					'message': 'Session not found or connection failed'
				}, status=500)
			
			session_id = session_result['id']
			print(f"Session {session_id} created successfully")
			
			# Verify session was saved to cache
			cache_data = browser_controller._load_session_from_cache(session_id)
			if cache_data:
				print(f"✅ Session {session_id} successfully saved to cache")
			else:
				print(f"❌ Session {session_id} NOT found in cache after creation!")
			
			# Get debug URLs using the REST API
			api_key = os.environ.get('BROWSERBASE_API_KEY')
			debug_data = {}
			if session_id and api_key:
				debug_url = f'https://api.browserbase.com/v1/sessions/{session_id}/debug'
				debug_req = urllib.request.Request(debug_url, method='GET')
				debug_req.add_header('x-bb-api-key', api_key)
				try:
					with urllib.request.urlopen(debug_req, timeout=10) as debug_resp:
						debug_body = debug_resp.read()
						debug_data = json.loads(debug_body.decode('utf-8'))
				except Exception as e:
					print(f"Failed to get debug URLs: {e}")
			
			# Return session data
			response_data = {
				'id': session_id,
				'connectUrl': session_result.get('connection_url'),
				'automation_connected': True,
				'status': 'RUNNING'
			}
			
			# Add debug URLs if available
			if 'debuggerFullscreenUrl' in debug_data:
				response_data['embedUrl'] = debug_data['debuggerFullscreenUrl']
				response_data['viewerUrl'] = debug_data['debuggerFullscreenUrl']
			elif 'debuggerUrl' in debug_data:
				response_data['embedUrl'] = debug_data['debuggerUrl']
				response_data['viewerUrl'] = debug_data['debuggerUrl']
			
			return JsonResponse(response_data, status=200)
			
		finally:
			loop.close()
			
	except Exception as e:
		print(f"Error creating session: {e}")
		return JsonResponse({ 'error': str(e) }, status=500)



@csrf_exempt
@require_http_methods(["POST"])
def navigate(request):
	"""Navigate to a URL in an existing Browserbase session"""
	try:
		body = json.loads(request.body.decode('utf-8'))
		session_id = body.get('sessionId')
		url = body.get('url')
		
		if not session_id:
			return JsonResponse({'error': 'sessionId is required'}, status=400)
		if not url:
			return JsonResponse({'error': 'url is required'}, status=400)
		
		# Use Playwright to navigate
		loop = asyncio.new_event_loop()
		asyncio.set_event_loop(loop)
		result = loop.run_until_complete(browser_controller.navigate(session_id, url))
		
		return JsonResponse(result)
		
	except Exception as e:
		return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def click(request):
	"""Click an element in a Browserbase session"""
	try:
		body = json.loads(request.body.decode('utf-8'))
		session_id = body.get('sessionId')
		selector = body.get('selector')
		
		if not session_id:
			return JsonResponse({'error': 'sessionId is required'}, status=400)
		if not selector:
			return JsonResponse({'error': 'selector is required'}, status=400)
		
		# Use Playwright to click
		loop = asyncio.new_event_loop()
		asyncio.set_event_loop(loop)
		result = loop.run_until_complete(browser_controller.click(session_id, selector))
		
		return JsonResponse(result)
		
	except Exception as e:
		return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def type_text(request):
	"""Type text into an input field"""
	try:
		body = json.loads(request.body.decode('utf-8'))
		session_id = body.get('sessionId')
		selector = body.get('selector')
		text = body.get('text', '')
		
		if not session_id:
			return JsonResponse({'error': 'sessionId is required'}, status=400)
		if not selector:
			return JsonResponse({'error': 'selector is required'}, status=400)
		
		# Use Playwright to type text
		loop = asyncio.new_event_loop()
		asyncio.set_event_loop(loop)
		result = loop.run_until_complete(browser_controller.type_text(session_id, selector, text))
		
		return JsonResponse(result)
		
	except Exception as e:
		return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def screenshot(request):
	"""Take a screenshot of the current page"""
	try:
		body = json.loads(request.body.decode('utf-8'))
		session_id = body.get('sessionId')
		full_page = body.get('fullPage', False)
		
		if not session_id:
			return JsonResponse({'error': 'sessionId is required'}, status=400)
		
		# Use Playwright to take a screenshot
		loop = asyncio.new_event_loop()
		asyncio.set_event_loop(loop)
		result = loop.run_until_complete(browser_controller.screenshot(session_id, full_page))
		
		return JsonResponse(result)
		
	except Exception as e:
		return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt  
@require_http_methods(["POST"])
def get_content(request):
	"""Get the current page content/HTML"""
	try:
		body = json.loads(request.body.decode('utf-8'))
		session_id = body.get('sessionId')
		
		if not session_id:
			return JsonResponse({'error': 'sessionId is required'}, status=400)
		
		# Use Playwright to get content
		loop = asyncio.new_event_loop()
		asyncio.set_event_loop(loop)
		result = loop.run_until_complete(browser_controller.get_content(session_id))
		
		return JsonResponse(result)
		
	except Exception as e:
		return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def wait_for(request):
	"""Wait for an element or a specific amount of time"""
	try:
		body = json.loads(request.body.decode('utf-8'))
		session_id = body.get('sessionId')
		selector = body.get('selector')
		timeout = body.get('timeout', 5000)  # Default 5 seconds
		
		if not session_id:
			return JsonResponse({'error': 'sessionId is required'}, status=400)
		
		# Use Playwright to wait
		loop = asyncio.new_event_loop()
		asyncio.set_event_loop(loop)
		result = loop.run_until_complete(browser_controller.wait_for(session_id, selector, timeout))
		
		return JsonResponse(result)
		
	except Exception as e:
		return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def list_sessions(request):
	"""List all active browser sessions"""
	try:
		sessions = []
		for session_id, session_data in browser_controller.sessions.items():
			sessions.append({
				'id': session_id,
				'connected': bool(session_data.get('browser')),
				'connect_url': session_data.get('connect_url', '')[:50] + '...' if session_data.get('connect_url') else None
			})
		
		return JsonResponse({
			'success': True,
			'sessions': sessions,
			'count': len(sessions)
		})
		
	except Exception as e:
		return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def check_session(request):
	"""Check if a session exists and test connection"""
	try:
		body = json.loads(request.body.decode('utf-8'))
		session_id = body.get('sessionId')
		
		if not session_id:
			return JsonResponse({'error': 'sessionId is required'}, status=400)
		
		print(f"Checking session {session_id}")
		
		# Use the same logic as _ensure_connected to check cache
		if session_id not in browser_controller.sessions:
			print(f"Session {session_id} not found in controller memory, checking cache...")
			cache_data = browser_controller._load_session_from_cache(session_id)
			if not cache_data:
				print(f"Session {session_id} not found in cache either")
				return JsonResponse({
					'success': False,
					'exists': False,
					'message': f'Session {session_id} not found in controller or cache'
				})
			# Session exists in cache but not in memory
			session_data = cache_data
			in_cache_only = True
		else:
			session_data = browser_controller.sessions[session_id]
			in_cache_only = False
		
		# Check session age
		import time
		current_time = time.time()
		created_at = session_data.get('created_at', 0)
		age_minutes = (current_time - created_at) / 60 if created_at else 0
		
		response = {
			'success': True,
			'exists': True,
			'in_memory': not in_cache_only,
			'in_cache_only': in_cache_only,
			'connected': bool(session_data.get('browser')) if not in_cache_only else False,
			'has_page': bool(session_data.get('page')) if not in_cache_only else False,
			'has_connection_url': bool(session_data.get('connection_url')),
			'age_minutes': round(age_minutes, 2),
			'session_id': session_id
		}
		
		print(f"Session check result: {response}")
		return JsonResponse(response)
		
	except Exception as e:
		print(f"Error checking session: {str(e)}")
		return JsonResponse({'error': str(e)}, status=500)