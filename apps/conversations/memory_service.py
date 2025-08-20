import os
import json
import hashlib
from datetime import datetime
from typing import Optional, List, Dict, Any


# Try multiple possible import paths for the Zep client
ZepClientClass = None  # type: ignore
ZepMessageClass = None  # type: ignore
try:
	from zep_cloud import Zep as _Zep
	from zep_cloud.types import Message as _ZepMessage
	ZepClientClass = _Zep
	ZepMessageClass = _ZepMessage
except Exception:
	try:
		from zep_cloud.client import Zep as _Zep
		from zep_cloud.types import Message as _ZepMessage
		ZepClientClass = _Zep
		ZepMessageClass = _ZepMessage
	except Exception:
		try:
			from zep import Zep as _Zep
			ZepClientClass = _Zep
		except Exception:
			ZepClientClass = None  # SDK not available; we'll operate in Mongo-only mode
			ZepMessageClass = None

from .models import Memory as MongoMemory

def _json_safe(value: Any) -> Any:
	"""Convert value to a JSON-serializable structure."""
	if value is None or isinstance(value, (str, int, float, bool)):
		return value
	if isinstance(value, dict):
		return {str(k): _json_safe(v) for k, v in value.items()}
	if isinstance(value, (list, tuple, set)):
		return [_json_safe(v) for v in value]
	# Fallback: stringify unknown objects
	return str(value)


def _build_zep_message(name: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> Any:
	"""Construct a Zep SDK Message or a compatible dict if the class isn't available."""
	metadata = metadata or {}
	if ZepMessageClass is not None:
		try:
			return ZepMessageClass(name=name, role=role, content=content, metadata=metadata)
		except Exception:
			pass
	# Fallback to dict structure expected by API
	return {"name": name, "role": role, "content": content, "metadata": metadata}


class EnhancedMemoryService:
	"""Enhanced memory service with optional Zep Cloud integration"""
	
	def __init__(self):
		self.zep_api_key = 'z_1dWlkIjoiNGM2YzZkNjEtODY1Ni00ZjY3LWE4YzgtY2MyYzI1YzVlNjczIn0.af1wRMsgNmxIskCgjEMdbI31kU0ATizP-_oRi7lBvbwpQgUg3NntBHPnq75jX0aMDWaNxWLIso_FqMmwQZD1ZQ'
		self.mem0_api_key = os.getenv('MEM0_API_KEY')
		self.zep_group_id = os.getenv('ZEP_GROUP_ID')
		self.zep_client = None
		
		if self.zep_api_key and ZepClientClass is not None:
			try:
				self.zep_client = ZepClientClass(api_key=self.zep_api_key)  # type: ignore[arg-type]
			except Exception:
				self.zep_client = None
	
	def is_zep_enabled(self) -> bool:
		"""Check if Zep Cloud is enabled"""
		return self.zep_client is not None
	
	def setup_zep_ontology(self) -> bool:
		"""Set up the ontology for Zep Cloud"""
		if not self.is_zep_enabled():
			return False
			
		try:
			# Best-effort; ignore if SDK does not support this method
			if hasattr(self.zep_client, "graph") and hasattr(self.zep_client.graph, "set_entity_types"):
				self.zep_client.graph.set_entity_types({  # type: ignore[union-attr]
					"entities": {
						"Company": {
							"name": 'Company',
							"description": 'A business organization',
							"attributes": {
								"name": { "type": 'string', "description": 'Company name' },
								"industry": { "type": 'string', "description": 'Industry sector' },
								"size": { "type": 'string', "description": 'Company size' },
								"website": { "type": 'string', "description": 'Company website' },
								"description": { "type": 'string', "description": 'Company description' },
							},
						},
						"Person": {
							"name": 'Person',
							"description": 'An individual person',
							"attributes": {
								"name": { "type": 'string', "description": 'Person name' },
								"role": { "type": 'string', "description": 'Job role or title' },
								"company": { "type": 'string', "description": 'Associated company' },
								"email": { "type": 'string', "description": 'Email address' },
								"phone": { "type": 'string', "description": 'Phone number' },
								"expertise": { "type": 'array', "description": 'Areas of expertise' },
							},
						},
					},
				})
			return True
		except Exception:
			return False
	
	def ensure_zep_user(self, username: str, email: str = None, first_name: str = None, last_name: str = None) -> Optional[Any]:
		"""Ensure a user exists in Zep Cloud and return the user object"""
		if not self.is_zep_enabled():
			return None
			
		try:
			zep_user_id = username
			# Try to get existing user
			if hasattr(self.zep_client, "user") and hasattr(self.zep_client.user, "get"):
				try:
					user = self.zep_client.user.get(user_id=zep_user_id)  # type: ignore[union-attr]
					return user
				except Exception:
					pass
			# Create if not found
			if hasattr(self.zep_client, "user") and hasattr(self.zep_client.user, "add"):
				user = self.zep_client.user.add(  # type: ignore[union-attr]
					user_id=zep_user_id,
					email=email,
					first_name=first_name,
					last_name=last_name,
				)
				return user
			return None
		except Exception:
			return None

	def ensure_zep_session(self, username: str, session_id: str) -> bool:
		"""Ensure a Zep session exists for the user; create it if missing (best-effort)."""
		if not self.is_zep_enabled():
			return False
		
		try:
			# Try multiple approaches for session/thread creation
			created = False
			
			# Approach 1: Try memory interface (legacy)
			if hasattr(self.zep_client, "memory"):
				mem = self.zep_client.memory  # type: ignore[assignment]
				# Check if session exists
				if hasattr(mem, "get_session"):
					try:
						existing = mem.get_session(session_id=session_id, user_id=username)  # type: ignore[union-attr]
						if existing:
							return True
					except Exception:
						pass
				
				# Try to create session via memory interface
				for create_name in ["add_session", "create_session", "upsert_session", "open_session"]:
					if hasattr(mem, create_name):
						try:
							create_fn = getattr(mem, create_name)
							create_fn(session_id=session_id, user_id=username)  # type: ignore[misc]
							created = True
							break
						except Exception:
							continue
			
			# Approach 2: Try thread interface (v3)
			if not created and hasattr(self.zep_client, "thread"):
				thr = self.zep_client.thread  # type: ignore[assignment]
				# Check if thread exists
				if hasattr(thr, "get"):
					try:
						existing = thr.get(thread_id=session_id)  # type: ignore[union-attr]
						if existing:
							# Even if thread exists, try to create/associate session
							created = True  # Mark as created since thread exists
					except Exception:
						pass
				
				# Try to create thread
				for create_name in ["create", "add", "upsert", "open"]:
					if hasattr(thr, create_name):
						try:
							create_fn = getattr(thr, create_name)
							# Try with just thread_id first
							try:
								create_fn(thread_id=session_id)  # type: ignore[misc]
								created = True
								break
							except Exception:
								# Try with user context if required by SDK
								create_fn(thread_id=session_id, user_id=username)  # type: ignore[misc]
								created = True
								break
						except Exception:
							continue
			
			# Approach 3: Try threads interface (alternative v3 naming)
			if not created and hasattr(self.zep_client, "threads"):
				thr = self.zep_client.threads  # type: ignore[assignment]
				# Check if thread exists
				if hasattr(thr, "get"):
					try:
						existing = thr.get(thread_id=session_id)  # type: ignore[union-attr]
						if existing:
							created = True  # Mark as created since thread exists
					except Exception:
						pass
				
				# Try to create thread
				for create_name in ["create", "add", "upsert", "open"]:
					if hasattr(thr, create_name):
						try:
							create_fn = getattr(thr, create_name)
							# Try with just thread_id first
							try:
								create_fn(thread_id=session_id)  # type: ignore[misc]
								created = True
								break
							except Exception:
								# Try with user context if required by SDK
								create_fn(thread_id=session_id, user_id=username)  # type: ignore[misc]
								created = True
								break
						except Exception:
							continue
			
			# Approach 4: Always try to create a session via memory interface (even if thread exists)
			if hasattr(self.zep_client, "memory"):
				mem = self.zep_client.memory  # type: ignore[assignment]
				for create_name in ["add_session", "create_session", "upsert_session", "open_session"]:
					if hasattr(mem, create_name):
						try:
							create_fn = getattr(mem, create_name)
							create_fn(session_id=session_id, user_id=username)  # type: ignore[misc]
							created = True
							break
						except Exception:
							continue
			
			# Approach 5: Fallback - try to create by adding a message
			if not created:
				# Try memory interface
				if hasattr(self.zep_client, "memory"):
					mem = self.zep_client.memory  # type: ignore[assignment]
					for msg_name in ["add_messages", "append", "create_messages"]:
						if hasattr(mem, msg_name):
							try:
								msg_fn = getattr(mem, msg_name)
								msg_fn(session_id=session_id, messages=[{"role": "user", "content": "", "metadata": {"_init": True}}])  # type: ignore[misc]
								created = True
								break
							except Exception:
								continue
				
				# Try thread interface
				if not created and hasattr(self.zep_client, "thread"):
					thr = self.zep_client.thread  # type: ignore[assignment]
					if hasattr(thr, "add_messages"):
						try:
							msg = _build_zep_message(name=username, role="user", content="", metadata={"_init": True})
							thr.add_messages(thread_id=session_id, messages=[msg])  # type: ignore[union-attr]
							created = True
						except Exception:
							pass
			
			# Verify creation if possible
			if hasattr(self.zep_client, "thread") and hasattr(self.zep_client.thread, "get"):
				try:
					ver = self.zep_client.thread.get(thread_id=session_id)  # type: ignore[union-attr]
					return True if ver else created
				except Exception:
					return created
			elif hasattr(self.zep_client, "memory") and hasattr(self.zep_client.memory, "get_session"):
				try:
					ver = self.zep_client.memory.get_session(session_id=session_id, user_id=username)  # type: ignore[union-attr]
					return True if ver else created
				except Exception:
					return created
			
			return created
		except Exception:
			# Best-effort: do not fail the caller if session creation is flaky
			return False
	
	def ensure_zep_thread(self, username: str, thread_id: str) -> bool:
		"""Ensure a Zep v3 thread exists, creating it if the SDK exposes a create/add method. Best-effort."""
		if not self.is_zep_enabled():
			return False
		try:
			if hasattr(self.zep_client, "thread"):
				thr = self.zep_client.thread  # type: ignore[assignment]
				# Try to get
				if hasattr(thr, "get"):
					try:
						thr.get(thread_id=thread_id)  # type: ignore[union-attr]
						return True
					except Exception:
						pass
					# Try to create using common method names
					for create_name in ["create", "add", "upsert", "open"]:
						if hasattr(thr, create_name):
							try:
								create_fn = getattr(thr, create_name)
								# Try with just thread_id first
								try:
									create_fn(thread_id=thread_id)  # type: ignore[misc]
								except Exception:
									# Try with user context if required by SDK
									user_id = username
									create_fn(thread_id=thread_id, user_id=user_id)  # type: ignore[misc]
								return True
							except Exception:
								continue
				# If no thread interface, rely on add_messages to implicitly create
			return True
		except Exception:
			return True

	def store_memory_enhanced(
		self,
		username: str,
		content: str,
		memory_type: str = "general",
		session_id: str = "default",
		metadata: Dict[str, Any] = None,
		use_zep: bool = True
	) -> Dict[str, Any]:
		"""Store memory with enhanced Zep Cloud integration"""
		# Always store in MongoDB for backward compatibility
		mongo_result = MongoMemory.store_memory(username, content, memory_type, session_id, metadata)
		
		zep_info: Dict[str, Any] = {"enabled": self.is_zep_enabled(), "stored_graph": False, "stored_memory": False}
		if use_zep and self.is_zep_enabled():
			try:
				# Ensure user and thread best-effort
				self.ensure_zep_user(username)
				self.ensure_zep_session(username, session_id)
				self.ensure_zep_thread(username, session_id)
				# Add to Zep graph (optional, v3 signature typically does not take data_type)
				if hasattr(self.zep_client, "graph") and hasattr(self.zep_client.graph, "add"):
					zep_user_id = self.get_zep_user_id(username)
					try:
						self.zep_client.graph.add(user_id=zep_user_id, data=content)  # type: ignore[union-attr]
						zep_info["stored_graph"] = True
					except Exception as e_graph:
						zep_info["graph_error"] = str(e_graph)
				# Primary: Zep v3 thread.add_messages per docs
				attempts: List[Dict[str, Any]] = []
				attempts: List[Dict[str, Any]] = []
				# Build both role variants to match SDK expectations
				msg_user = _build_zep_message(name=username, role="user", content=content, metadata=metadata)
				msg_human = _build_zep_message(name=username, role="human", content=content, metadata=metadata)
				# Try thread API first (v3)
				for client_attr in ["thread", "threads"]:
					if hasattr(self.zep_client, client_attr):
						thr = getattr(self.zep_client, client_attr)
						if hasattr(thr, "add_messages"):
							try:
								res = thr.add_messages(thread_id=session_id, messages=[msg_user], return_context=True)
								attempts.append({"method": f"{client_attr}.add_messages(user)", "ok": True, "result": str(getattr(res, "__dict__", res))})
								zep_info["stored_memory"] = True
								zep_info["episode_ids"] = getattr(res, "episode_uuids", None) or getattr(res, "episodes", None)
								zep_info["context"] = getattr(res, "context", None)
								break
							except Exception as e_user:
								attempts.append({"method": f"{client_attr}.add_messages(user)", "ok": False, "error": str(e_user)})
								try:
									res2 = thr.add_messages(thread_id=session_id, messages=[msg_human], return_context=True)
									attempts.append({"method": f"{client_attr}.add_messages(human)", "ok": True, "result": str(getattr(res2, "__dict__", res2))})
									zep_info["stored_memory"] = True
									zep_info["episode_ids"] = getattr(res2, "episode_uuids", None) or getattr(res2, "episodes", None)
									zep_info["context"] = getattr(res2, "context", None)
									break
								except Exception as e_human:
									attempts.append({"method": f"{client_attr}.add_messages(human)", "ok": False, "error": str(e_human)})
						# Break outer loop if stored
						if zep_info.get("stored_memory"):
							break

				# Fallback to legacy memory API only if thread API failed
				if not zep_info["stored_memory"] and hasattr(self.zep_client, "memory"):
					mem = self.zep_client.memory  # type: ignore[assignment]
					msg_payload = {"role": 'user', "content": content, "metadata": metadata or {}}
					for method_name in ["add", "add_messages", "append", "create_messages"]:
						if hasattr(mem, method_name):
							method = getattr(mem, method_name)
							try:
								res = method(session_id=session_id, messages=[msg_payload])  # type: ignore[misc]
								attempts.append({"method": f"memory.{method_name}(session_id,messages)", "ok": True, "result": str(getattr(res, "__dict__", res))})
								zep_info["stored_memory"] = True
								break
							except Exception as e1:
								attempts.append({"method": f"memory.{method_name}(session_id,messages)", "ok": False, "error": str(e1)})
				# Verify by fetching thread info if possible
				if hasattr(self.zep_client, "thread") and hasattr(self.zep_client.thread, "get"):
					try:
						thr = self.zep_client.thread.get(thread_id=session_id)  # type: ignore[union-attr]
						zep_info["thread_exists"] = True
						zep_info["thread"] = str(getattr(thr, "__dict__", thr))
					except Exception as e_thr:
						zep_info["thread_exists"] = False
						zep_info["thread_error"] = str(e_thr)
				zep_info["memory_attempts"] = attempts
			except Exception as e:
				zep_info["error"] = str(e)
		
		return {
			"success": True,
			"memory_id": mongo_result.get("memory_id"),
			"message": "Memory stored in MongoDB" + (" and Zep" if zep_info.get("stored_memory") else ""),
			"zep": zep_info,
		}
	
	def search_memories_enhanced(
		self,
		username: str,
		query: str,
		session_id: str = "default",
		limit: int = 10,
		memory_type: str = None,
		use_zep: bool = True,
		scope: str = "nodes",
		reranker: str = "cross_encoder"
	) -> Dict[str, Any]:
		"""Search memories with enhanced Zep Cloud integration"""
		print(f"Search memories: username={username}, query={query}, session_id={session_id}, use_zep={use_zep}")
		# Get MongoDB results
		mongo_result = MongoMemory.search_memories(username, query, session_id, limit, memory_type)
		
		# If Zep is enabled and requested, also search in Zep Cloud
		if use_zep and self.is_zep_enabled():
			try:
				# Get the correct Zep user ID
				zep_user_id = self.get_zep_user_id(username)
				
				zep_result = None
				
				# Try v3 thread search first
				if hasattr(self.zep_client, "thread") and hasattr(self.zep_client.thread, "search"):
					try:
						print(f"Trying v3 thread search: thread_id={session_id}, query={query[:255]}")
						zep_result = self.zep_client.thread.search(  # type: ignore[union-attr]
							thread_id=session_id,
							query=query[:255],
							limit=limit,
						)
						print(f"V3 thread search result: {zep_result}")
					except Exception as e:
						print(f"V3 thread search failed: {e}")
						zep_result = None
				
				# Fallback to v2 graph search
				if zep_result is None and hasattr(self.zep_client, "graph") and hasattr(self.zep_client.graph, "search"):
					try:
						print(f"Trying v2 graph search: user_id={zep_user_id}, query={query[:255]}, scope={scope}")
						zep_result = self.zep_client.graph.search(  # type: ignore[union-attr]
							user_id=zep_user_id,
							query=query[:255],
							scope=scope,
							limit=limit,
							reranker=reranker,
						)
						print(f"V2 graph search result: {zep_result}")
					except Exception as e:
						print(f"V2 graph search failed: {e}")
						zep_result = None

				combined_result: Dict[str, Any] = {
					"success": True,
					"mongo_memories": [],
					"zep_facts": [],
					"zep_entities": [],
					"count": 0,
				}
				
				# Process Zep search results
				if zep_result:
					print(f"Processing Zep result: {zep_result}")
					print(f"Zep result type: {type(zep_result)}")
					print(f"Zep result attributes: {dir(zep_result)}")
					
					# Try to extract v3 thread search results
					if hasattr(zep_result, 'messages'):
						messages = getattr(zep_result, 'messages', []) or []
						for message in messages:
							content = getattr(message, 'content', '')
							role = getattr(message, 'role', 'user')
							message_metadata = getattr(message, 'metadata', {}) or {}
							
							combined_result["zep_facts"].append({
								"fact": f"{role}: {content}",
								"confidence": 1.0,
								"score": 1.0,
								"created_at": getattr(message, 'created_at', ''),
								"uuid": getattr(message, 'uuid_', ''),
								"labels": [role, "message"],
								"attributes": _json_safe(message_metadata),
								"domain": message_metadata.get('domain', ''),
								"expertise_level": message_metadata.get('expertise_level', ''),
								"source": "zep_v3_thread"
							})
							combined_result["count"] += 1
					
					# Try to extract v2 graph search results
					elif hasattr(zep_result, 'edges') or hasattr(zep_result, 'nodes'):
						# Extract facts from Zep results
						if hasattr(zep_result, 'edges'):
							for edge in getattr(zep_result, 'edges', []) or []:
								# Extract all available attributes
								edge_attributes = getattr(edge, 'attributes', {}) or {}
								edge_labels = getattr(edge, 'labels', []) or []
								
								combined_result["zep_facts"].append({
									"fact": getattr(edge, 'fact', ''),
									"confidence": getattr(edge, 'score', 0) or 0,
									"score": getattr(edge, 'score', 0) or 0,
									"created_at": getattr(edge, 'created_at', ''),
									"graph_id": getattr(edge, 'graph_id', ''),
									"labels": edge_labels,
									"attributes": _json_safe(edge_attributes),
									"domain": edge_attributes.get('domain', ''),
									"expertise_level": edge_attributes.get('expertise_level', ''),
									"source": "zep_v2_graph"
								})
								combined_result["count"] += 1
						# Extract entities from Zep results
						if hasattr(zep_result, 'nodes'):
							for node in getattr(zep_result, 'nodes', []) or []:
								# Extract all available attributes
								node_attributes = getattr(node, 'attributes', {}) or {}
								node_labels = getattr(node, 'labels', []) or []
								
								combined_result["zep_entities"].append({
									"id": getattr(node, 'uuid_', ''),
									"name": getattr(node, 'name', ''),
									"type": node_labels[0] if node_labels else 'entity',
									"summary": getattr(node, 'summary', ''),
									"score": getattr(node, 'score', 0) or 0,
									"created_at": getattr(node, 'created_at', ''),
									"graph_id": getattr(node, 'graph_id', ''),
									"labels": node_labels,
									"attributes": _json_safe(node_attributes),
									"source": "zep_v2_graph"
								})
								combined_result["count"] += 1
				# Only include stringified raw for safety
				combined_result["zep_raw"] = str(zep_result)
				print(f"Final combined result: {combined_result}")
				return combined_result
			except Exception as e:
				return {
					"success": True,
					"mongo_memories": mongo_result.get("memories", []),
					"zep_facts": [],
					"zep_entities": [],
					"count": len(mongo_result.get("memories", [])),
					"zep_error": str(e),
				}
		return mongo_result
	
	def get_zep_user_id(self, username: str) -> Optional[str]:
		"""Get the Zep user ID for a given username"""
		if not self.is_zep_enabled():
			return None
		try:
			user = self.ensure_zep_user(username)
			if user:
				# Try to get the Zep user ID from the user object
				zep_user_id = getattr(user, 'user_id', None) or getattr(user, 'uuid_', None) or username
				return zep_user_id
			return username
		except Exception:
			return username

	def extract_entities_from_graph(self, username: str, limit: int = 50) -> List[Dict[str, Any]]:
		"""Extract entities from the Zep knowledge graph"""
		if not self.is_zep_enabled():
			return []
		try:
			zep_user_id = self.get_zep_user_id(username)
			entities = []
			
			# Try to get entities from the graph
			if hasattr(self.zep_client, "graph") and hasattr(self.zep_client.graph, "search"):
				try:
					# Search for all entities (nodes) in the graph
					result = self.zep_client.graph.search(  # type: ignore[union-attr]
						user_id=zep_user_id,
						query="",  # Empty query to get all entities
						scope="nodes",
						limit=limit,
						reranker="cross_encoder",
					)
					
					if result and hasattr(result, 'nodes'):
						nodes = getattr(result, 'nodes', []) or []
						for node in nodes:
							# Extract all available attributes
							node_attributes = getattr(node, 'attributes', {}) or {}
							node_labels = getattr(node, 'labels', []) or []
							
							entities.append({
								"id": getattr(node, 'uuid_', ''),
								"name": getattr(node, 'name', ''),
								"type": node_labels[0] if node_labels else 'entity',
								"summary": getattr(node, 'summary', ''),
								"score": getattr(node, 'score', 0) or 0,
								"created_at": getattr(node, 'created_at', ''),
								"graph_id": getattr(node, 'graph_id', ''),
								"labels": node_labels,
								"attributes": _json_safe(node_attributes),
								"source": "zep_graph"
							})
					
				except Exception:
					pass
			
			# If no entities found, try to extract from thread messages
			if not entities:
				messages = self.get_thread_messages(username, "assistant_ui", limit)
				
				# Simple entity extraction from message content
				extracted_entities = {}
				for msg in messages:
					content = msg.get('content', '').lower()
					
					# Look for common entity patterns
					if 'name is' in content or 'called' in content:
						# Extract person names
						import re
						name_patterns = [
							r'name is (\w+)',
							r'called (\w+)',
							r'(\w+) is my',
							r'(\w+) has',
						]
						for pattern in name_patterns:
							matches = re.findall(pattern, content)
							for match in matches:
								if len(match) > 2:  # Filter out short matches
									extracted_entities[match] = {
										"type": "Person",
										"source": "message_extraction"
									}
					
					# Look for company/organization mentions
					if 'company' in content or 'work at' in content or 'job at' in content:
						company_patterns = [
							r'work at (\w+)',
							r'job at (\w+)',
							r'company (\w+)',
						]
						for pattern in company_patterns:
							matches = re.findall(pattern, content)
							for match in matches:
								if len(match) > 2:
									extracted_entities[match] = {
										"type": "Company",
										"source": "message_extraction"
									}
				
				# Convert extracted entities to standard format
				for name, info in extracted_entities.items():
					entities.append({
						"id": f"extracted_{name.lower()}",
						"name": name,
						"type": info["type"],
						"summary": f"Extracted from conversation: {name}",
						"attributes": {"source": info["source"]},
						"source": "message_extraction"
					})
			
			return entities
		except Exception:
			return []

	def get_zep_users(self, username: str = None, limit: int = 50) -> List[Dict[str, Any]]:
		"""Get all Zep users"""
		if not self.is_zep_enabled():
			return []
		try:
			users = []
			
			# Since we're using Zep v2 API, we need to get users individually
			# For now, let's get the current user and any other users we can find
			
			# Method 1: Try to get current user from memory interface (v2)
			if username and hasattr(self.zep_client, "memory") and hasattr(self.zep_client.memory, "get_user"):
				try:
					# Try to get user by username
					user = self.zep_client.memory.get_user(user_id=username)  # type: ignore[union-attr]
					if user:
						users.append({
							"id": getattr(user, 'user_id', username),
							"uuid": getattr(user, 'uuid_', ''),
							"email": getattr(user, 'email', username),
							"first_name": getattr(user, 'first_name', ''),
							"last_name": getattr(user, 'last_name', ''),
							"created_at": getattr(user, 'created_at', ''),
							"updated_at": getattr(user, 'updated_at', ''),
							"session_count": getattr(user, 'session_count', 0),
							"metadata": _json_safe(getattr(user, 'metadata', {})),
						})
				except Exception:
					pass
			
			# Method 2: Try user interface (v2/v3)
			if username and hasattr(self.zep_client, "user") and hasattr(self.zep_client.user, "get"):
				try:
					user = self.zep_client.user.get(user_id=username)  # type: ignore[union-attr]
					if user:
						users.append({
							"id": getattr(user, 'user_id', username),
							"uuid": getattr(user, 'uuid_', ''),
							"email": getattr(user, 'email', username),
							"first_name": getattr(user, 'first_name', ''),
							"last_name": getattr(user, 'last_name', ''),
							"created_at": getattr(user, 'created_at', ''),
							"updated_at": getattr(user, 'updated_at', ''),
							"session_count": getattr(user, 'session_count', 0),
							"metadata": _json_safe(getattr(user, 'metadata', {})),
						})
				except Exception:
					pass
			
			# Method 3: Try v3 methods as fallback
			if not users and hasattr(self.zep_client, "user") and hasattr(self.zep_client.user, "list"):
				try:
					user_list = self.zep_client.user.list(limit=limit)  # type: ignore[union-attr]
					if user_list:
						for user in user_list:
							users.append({
								"id": getattr(user, 'user_id', ''),
								"uuid": getattr(user, 'uuid_', ''),
								"email": getattr(user, 'email', ''),
								"first_name": getattr(user, 'first_name', ''),
								"last_name": getattr(user, 'last_name', ''),
								"created_at": getattr(user, 'created_at', ''),
								"updated_at": getattr(user, 'updated_at', ''),
								"session_count": getattr(user, 'session_count', 0),
								"metadata": _json_safe(getattr(user, 'metadata', {})),
							})
				except Exception:
					pass
			
			return users
		except Exception:
			return []

	def get_thread_messages(self, username: str, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
		"""Get all messages from a Zep thread"""
		if not self.is_zep_enabled():
			return []
		try:
			zep_user_id = self.get_zep_user_id(username)
			messages = []
			
			# Try v3 thread interface
			if hasattr(self.zep_client, "thread") and hasattr(self.zep_client.thread, "get"):
				try:
					thread = self.zep_client.thread.get(thread_id=session_id)  # type: ignore[union-attr]
					if hasattr(thread, 'messages'):
						thread_messages = getattr(thread, 'messages', []) or []
						for msg in thread_messages[-limit:]:
							messages.append({
								"content": getattr(msg, 'content', ''),
								"role": getattr(msg, 'role', 'user'),
								"name": getattr(msg, 'name', ''),
								"created_at": getattr(msg, 'created_at', ''),
								"uuid": getattr(msg, 'uuid_', ''),
							})
				except Exception:
					pass
			
			# Try v2 memory interface as fallback
			if not messages and hasattr(self.zep_client, "memory") and hasattr(self.zep_client.memory, "get_session"):
				try:
					session = self.zep_client.memory.get_session(session_id=session_id, user_id=zep_user_id)  # type: ignore[union-attr]
					if hasattr(session, 'messages'):
						session_messages = getattr(session, 'messages', []) or []
						for msg in session_messages[-limit:]:
							messages.append({
								"content": getattr(msg, 'content', ''),
								"role": getattr(msg, 'role', 'user'),
								"name": getattr(msg, 'name', ''),
								"created_at": getattr(msg, 'created_at', ''),
								"uuid": getattr(msg, 'uuid_', ''),
							})
				except Exception:
					pass
			
			return messages
		except Exception:
			return []

	def get_memory_context(
		self,
		username: str,
		session_id: str,
		messages: List[Dict[str, Any]] = None,
		limit: int = 10
	) -> Optional[str]:
		"""Get memory context for a conversation"""
		if not self.is_zep_enabled():
			return None
		try:
			zep_user_id = self.get_zep_user_id(username)
			context = None
			if hasattr(self.zep_client, "memory") and hasattr(self.zep_client.memory, "get_session"):
				context = self.zep_client.memory.get_session(  # type: ignore[union-attr]
					session_id=session_id,
					user_id=zep_user_id,
				)
			if context and getattr(context, 'messages', None):
				context_string = "Previous conversation context:\n\n"
				for message in context.messages[-limit:]:
					role = "User" if getattr(message, 'role', '') == "user" else "Assistant"
					context_string += f"{role}: {getattr(message, 'content', '')}\n\n"
				return context_string
			return None
		except Exception:
			return None


# Global instance
memory_service = EnhancedMemoryService()
