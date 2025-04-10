# views.py

import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from llmintegration.contextual_query_pipeline import build_gemini_prompt_and_response
from llmintegration.llm_utils import call_gemini

# UI-based Chat View
@csrf_exempt
def llm_chat_view(request):
    if "history" not in request.session:
        request.session["history"] = []

    if request.method == "POST":
        user_input = request.POST.get("user_input")
        gemini_response = build_gemini_prompt_and_response(user_input)

        request.session["history"].append({"role": "chat-user", "text": user_input})
        request.session["history"].append({"role": "chat-bot", "text": gemini_response})
        request.session.modified = True

    return render(request, "llmintegration/llm_chat.html", {
        "history": request.session.get("history", [])
    })


# JSON API endpoint for Gemini prompt
@csrf_exempt
def gemini_prompt_api_view(request):
    if request.method == "POST":
        try:
            body = json.loads(request.body)
            prompt = body.get("prompt", "")

            if not prompt:
                return JsonResponse({"error": "Prompt cannot be empty"}, status=400)

            response = call_gemini(prompt)
            return JsonResponse({"response": response})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Only POST allowed"}, status=405)