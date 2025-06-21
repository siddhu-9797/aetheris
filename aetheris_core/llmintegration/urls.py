from django.urls import path
from . import views, views_orchestrator, views_dashboard, views_similarity, views_anomaly

urlpatterns = [
    # Chat interface
    path("chat/", views.llm_chat_view, name="llm_chat_view"),

    # API endpoint for raw Aetheris LLM prompt
    path("api/llm/", views.gemini_prompt_api_view, name="aetheris_llm_api"),

    # Dashboard
    path("dashboard/", views_dashboard.llm_dashboard_view, name="llm_dashboard"),

    #FAISS similarity reports
    path("similarity-dashboard/", views_similarity.similarity_dashboard_view, name="llm_similarity_dashboard"),

    #FAISS Anamolies reports
    path("anomalies/", views_anomaly.anomaly_dashboard_view, name="llm_anomalies_dashboard"),
]
