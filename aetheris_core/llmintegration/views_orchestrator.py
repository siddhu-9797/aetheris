# llmintegration/views_orchestrator.py

from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .contextual_query_pipeline import build_gemini_prompt_and_response



@csrf_exempt
def query_llm_view(request):
    if request.method == "POST":
        prompt = request.POST.get("prompt", "")
        if not prompt:
            return render(request, "llmintegration/llm_chat.html", {"error": "No prompt provided."})

        try:
            response = build_gemini_prompt_and_response(prompt)
            return render(request, "llmintegration/llm_chat.html", {
                "prompt": prompt,
                "response": response
            })
        except Exception as e:
            return render(request, "llmintegration/llm_chat.html", {"error": str(e)})

    return render(request, "llmintegration/llm_chat.html")
