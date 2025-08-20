import os
import json
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
		self.zep_api_key = os.getenv('ZEP_API_KEY')
		self.mem0_api_key = os.getenv('MEM0_API_KEY')
		self.zep_client = None
		
		if self.zep_api_key and ZepClientClass is not None:
			try:
				self.zep_client = ZepClientClass(api_key=self.zep_api_key)  # type: ignore[arg-type]
			except Exception:
				self.zep_client = None
	
	def is_zep_enabled(self) -> bool:
		"""Check if Zep Cloud is enabled"""
		return self.zep_client is not None
	
	def generate_zep_user_id(self, username: str, workspace_id: str = "default") -> str:
		"""Generate a Zep user ID from username and workspace"""
		return f"{workspace_id}_{username}"
	
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
		"""Ensure a user exists in Zep Cloud"""
		if not self.is_zep_enabled():
			return None
			
		try:
			zep_user_id = self.generate_zep_user_id(username)
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
		"""Best-effort: use get_session if available; otherwise rely on thread.add_messages to create implicitly."""
		if not self.is_zep_enabled():
			return False
		try:
			zep_user_id = self.generate_zep_user_id(username)
			# Some SDKs only expose thread APIs in v3; prefer thread.get if available
			if hasattr(self.zep_client, "thread") and hasattr(self.zep_client.thread, "get"):
				try:
					self.zep_client.thread.get(thread_id=session_id)  # type: ignore[union-attr]
					return True
				except Exception:
					# Let add_messages create it implicitly
					return True
			# Legacy memory API fallback (no-op)
			return True
		except Exception:
			return True
	
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
									user_id = self.generate_zep_user_id(username)
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
				self.ensure_zep_thread(username, session_id)
				# Add to Zep graph (optional, v3 signature typically does not take data_type)
				if hasattr(self.zep_client, "graph") and hasattr(self.zep_client.graph, "add"):
					user_id = self.generate_zep_user_id(username)
					try:
						self.zep_client.graph.add(user_id=user_id, data=content)  # type: ignore[union-attr]
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
		# Get MongoDB results
		mongo_result = MongoMemory.search_memories(username, query, session_id, limit, memory_type)
		
		# If Zep is enabled and requested, also search in Zep Cloud
		if use_zep and self.is_zep_enabled():
			try:
				# Prefer searching by thread (session) or hashed user bound to thread
				used_user_id = None
				used_strategy = None
				search_user_id = None
				if hasattr(self.zep_client, "thread") and hasattr(self.zep_client.thread, "get"):
					try:
						thr = self.zep_client.thread.get(thread_id=session_id)  # type: ignore[union-attr]
						# Try common locations for the associated user id
						search_user_id = getattr(thr, 'user_id', None)
						if not search_user_id:
							user_obj = getattr(thr, 'user', None)
							if user_obj is not None:
								search_user_id = getattr(user_obj, 'uuid', None) or getattr(user_obj, 'id', None) or getattr(user_obj, 'user_id', None)
					except Exception:
						pass

				zep_result = None
				if hasattr(self.zep_client, "graph") and hasattr(self.zep_client.graph, "search"):
					# Attempt 1: by thread_id if supported
					try:
						zep_result = self.zep_client.graph.search(  # type: ignore[union-attr]
							thread_id=session_id,
							query=query[:255],
							scope=scope,
							limit=limit,
							reranker=reranker,
						)
						used_strategy = "thread_id"
					except Exception:
						zep_result = None
					# Attempt 2: by hashed user bound to thread
					if zep_result is None and search_user_id:
						try:
							zep_result = self.zep_client.graph.search(  # type: ignore[union-attr]
								user_id=str(search_user_id),
								query=query[:255],
								scope=scope,
								limit=limit,
								reranker=reranker,
							)
							used_user_id = str(search_user_id)
							used_strategy = "thread_user_id"
						except Exception:
							zep_result = None
					# Attempt 3: fallback to our generated user id
					if zep_result is None:
						try:
							fallback_user = self.generate_zep_user_id(username)
							zep_result = self.zep_client.graph.search(  # type: ignore[union-attr]
								user_id=fallback_user,
								query=query[:255],
								scope=scope,
								limit=limit,
								reranker=reranker,
							)
							used_user_id = fallback_user
							used_strategy = "fallback_user_id"
						except Exception:
							zep_result = None
				combined_result: Dict[str, Any] = {
					"success": True,
					"mongo_memories": [],
					"zep_facts": [],
					"zep_entities": [],
					"count": 0,
					"used_user_id": used_user_id,
					"used_strategy": used_strategy,
				}
				# Extract facts from Zep results
				if zep_result and hasattr(zep_result, 'edges'):
					for edge in getattr(zep_result, 'edges', []) or []:
						combined_result["zep_facts"].append({
							"fact": getattr(edge, 'fact', ''),
							"confidence": getattr(edge, 'score', 0) or 0,
							"source": "zep_cloud"
						})
						combined_result["count"] += 1
				# Extract entities from Zep results
				if zep_result and hasattr(zep_result, 'nodes'):
					for node in getattr(zep_result, 'nodes', []) or []:
						combined_result["zep_entities"].append({
							"id": getattr(node, 'uuid_', ''),
							"name": getattr(node, 'name', ''),
							"type": (getattr(node, 'labels', []) or ['entity'])[0],
							"summary": getattr(node, 'summary', ''),
							"attributes": _json_safe(getattr(node, 'attributes', {})),
						})
						combined_result["count"] += 1
				# Only include stringified raw for safety
				combined_result["zep_raw"] = str(zep_result)
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
			zep_user_id = self.generate_zep_user_id(username)
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
