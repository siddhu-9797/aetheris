from django.urls import path
from . import views, views_orchestrator, views_dashboard

urlpatterns = [
    # Chat interface
    path("chat/", views.llm_chat_view, name="llm_chat_view"),

    # API endpoint for raw Gemini prompt
    path("api/gemini/", views.gemini_prompt_api_view, name="gemini_prompt_api"),

    # Dashboard
    path("dashboard/", views_dashboard.llm_dashboard_view, name="llm_dashboard"),
]
