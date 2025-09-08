from django.urls import path
from . import views

urlpatterns = [
    path("save/", views.save_conversation, name="save_conversation"),
    path("list/", views.get_conversations, name="get_conversations"),
    path("admin/list/", views.get_all_conversations_admin, name="get_all_conversations_admin"),
    path("admin/users/", views.get_conversation_users_admin, name="get_conversation_users_admin"),
    path("<str:conversation_id>/", views.get_conversation, name="get_conversation"),
    path("<str:conversation_id>/delete/", views.delete_conversation, name="delete_conversation"),
    path("<str:conversation_id>/title/", views.update_conversation_title, name="update_conversation_title"),
    path("<str:conversation_id>/update/", views.update_conversation, name="update_conversation"),
    
    # Memory endpoints
    path("memory/store/", views.store_memory, name="store_memory"),
    path("memory/search/", views.search_memories, name="search_memories"),
    path("memory/list/", views.get_memories, name="get_memories"),
    path("memory/<str:memory_id>/delete/", views.delete_memory, name="delete_memory"),
    path("memory/delete-session/", views.delete_memories_by_session, name="delete_memories_by_session"),
    path("memory/cleanup/", views.cleanup_old_memories, name="cleanup_old_memories"),
    
    # Enhanced Memory endpoints with Zep Cloud integration
    path("memory/enhanced/store/", views.store_memory_enhanced, name="store_memory_enhanced"),
    path("memory/enhanced/search/", views.search_memories_enhanced, name="search_memories_enhanced"),
    path("memory/context/", views.get_memory_context, name="get_memory_context"),
    path("memory/conversation/", views.add_conversation_to_memory, name="add_conversation_to_memory"),
    path("memory/status/", views.get_memory_status, name="get_memory_status"),
    
    # Knowledge Graph endpoints
    path("knowledge/graph/", views.get_knowledge_graph, name="get_knowledge_graph"),
    path("knowledge/search/", views.search_knowledge_graph, name="search_knowledge_graph"),
    path("knowledge/entity/add/", views.add_entity_to_graph, name="add_entity_to_graph"),
    path("knowledge/fact/add/", views.add_fact_to_graph, name="add_fact_to_graph"),
    path("knowledge/document/add/", views.add_document_to_graph, name="add_document_to_graph"),
]
