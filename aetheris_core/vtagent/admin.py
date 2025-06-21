# admin.py for vtagent
from django.contrib import admin
from django.urls import path, reverse
from django.utils.html import format_html
from django.shortcuts import redirect
from django.contrib import messages
from django.conf import settings
from import_export.admin import ExportMixin

from django.http import HttpResponseRedirect
import subprocess
import os

from .models import NewsSource, RawArticle, ClassifiedArticle, GeneratedTaxonomyLabel
from .CrawlDispatcher import crawl_news_source

import sys
#print(f"Django is using Python interpreter: {sys.executable}")

@admin.register(NewsSource)
class NewsSourceAdmin(ExportMixin, admin.ModelAdmin):
    list_display = ("name", "category", "crawler_type", "is_active", "created_at", "scrapy_button", "bs4_button", "both_button")
    list_filter = ("category", "crawler_type", "is_active")
    search_fields = ("name", "url")

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("crawl_scrapy/<int:source_id>/", self.admin_site.admin_view(self.crawl_scrapy), name="vtagent_newssource_crawl_scrapy"),
            path("crawl_bs4/<int:source_id>/", self.admin_site.admin_view(self.crawl_bs4), name="vtagent_newssource_crawl_bs4"),
            path("crawl_both/<int:source_id>/", self.admin_site.admin_view(self.crawl_both), name="vtagent_newssource_crawl_both"),
        ]
        return custom_urls + urls

    def scrapy_button(self, obj):
        url = reverse("admin:vtagent_newssource_crawl_scrapy", args=[obj.id])
        return format_html('<a class="button" href="{}">Use Scrapy</a>', url)
    scrapy_button.short_description = "Scrapy"
    scrapy_button.allow_tags = True

    def bs4_button(self, obj):
        url = reverse("admin:vtagent_newssource_crawl_bs4", args=[obj.id])
        return format_html('<a class="button" href="{}">Use BS4</a>', url)
    bs4_button.short_description = "BS4"
    bs4_button.allow_tags = True

    def both_button(self, obj):
        url = reverse("admin:vtagent_newssource_crawl_both", args=[obj.id])
        return format_html('<a class="button" href="{}">Use Both</a>', url)
    both_button.short_description = "Both"
    both_button.allow_tags = True

    def crawl_scrapy(self, request, source_id):
        return self._crawl_dispatch(request, source_id, use_scrapy=True)

    def crawl_bs4(self, request, source_id):
        return self._crawl_dispatch(request, source_id, use_bs4=True)

    def crawl_both(self, request, source_id):
        return self._crawl_dispatch(request, source_id, use_scrapy=True, use_bs4=True)

    def _crawl_dispatch(self, request, source_id, use_scrapy=False, use_bs4=False):
        try:
            source = NewsSource.objects.get(pk=source_id)
            count, errors = crawl_news_source(source, use_scrapy=use_scrapy, use_bs4=use_bs4)
            
            # Filter out timeout errors from display
            filtered_errors = []
            for error in errors:
                if "timed out after" not in str(error) and "UNIQUE constraint failed" not in str(error):
                    filtered_errors.append(error)
            
            # Auto-vectorize and classify new articles if any were crawled
            if count > 0:
                try:
                    # Step 1: Vectorization
                    self.message_user(request, f"Crawled {count} articles. Starting vectorization...", messages.INFO)
                    vectorize_result = self._auto_vectorize_articles()
                    
                    # Step 2: ML Classification
                    self.message_user(request, "Vectorization complete. Starting ML classification...", messages.INFO)
                    ml_result = self._auto_ml_classify_articles()
                    
                    # Step 3: LLM Classification
                    self.message_user(request, "ML classification complete. Starting LLM analysis (this may take a few minutes)...", messages.INFO)
                    llm_result = self._auto_classify_articles(count)
                    
                    # Final success
                    self.message_user(request, f"🎉 Complete pipeline finished! Crawled {count} articles with full ML & LLM classification.", messages.SUCCESS)
                except Exception as ve:
                    self.message_user(request, f"Crawled {count} articles but post-processing failed: {str(ve)}", messages.WARNING)
            else:
                self.message_user(request, "No new articles found to crawl", messages.INFO)
                
            if filtered_errors:
                # Show only first few errors to avoid overwhelming
                error_summary = filtered_errors[:3]
                if len(filtered_errors) > 3:
                    error_summary.append(f"... and {len(filtered_errors) - 3} more errors")
                self.message_user(request, f"Crawl completed with some issues: {error_summary}", messages.WARNING)
                
        except NewsSource.DoesNotExist:
            self.message_user(request, f"News source with ID {source_id} not found", messages.ERROR)
        except Exception as e:
            self.message_user(request, f"Crawl failed: {str(e)}", messages.ERROR)
        # Redirect back to the NewsSource changelist
        from django.urls import reverse
        return redirect(reverse('admin:vtagent_newssource_changelist'))
    
    def _auto_vectorize_articles(self):
        """Auto-vectorize articles after crawling"""
        import subprocess
        import sys
        from django.conf import settings
        
        # BASE_DIR points to /Users/sid/.../aetheris/, so we need aetheris_core/vtagent/
        script_path = os.path.join(settings.BASE_DIR, "aetheris_core", "vtagent", "vectorize_articles.py")
        
        # Debug: Check if script exists
        if not os.path.exists(script_path):
            raise Exception(f"Vectorization script not found at: {script_path}")
        
        # Change to the correct working directory
        old_cwd = os.getcwd()
        try:
            os.chdir(os.path.join(settings.BASE_DIR, "aetheris_core"))
            result = subprocess.run([sys.executable, script_path], capture_output=True, text=True)
        finally:
            os.chdir(old_cwd)
        
        if result.returncode != 0:
            raise Exception(f"Vectorization failed: {result.stderr}")
        
        # Return success message
        return f"Vectorized articles: {result.stdout.strip()}"
    
    def _auto_classify_articles(self, article_count):
        """Auto-generate taxonomy labels for new articles"""
        import subprocess
        import sys
        from django.conf import settings
        
        # Set max articles to process only the new ones
        script_path = os.path.join(settings.BASE_DIR, "aetheris_core", "llmintegration", "generate_article_labels_llm.py")
        
        # Temporarily update the script to process only new articles
        env = os.environ.copy()
        env['MAX_ARTICLES'] = str(min(article_count, 10))  # Limit to avoid timeout
        
        result = subprocess.run([sys.executable, script_path], 
                              capture_output=True, text=True, env=env, timeout=600)  # 10 minute timeout
        
        if result.returncode != 0:
            raise Exception(f"LLM classification failed: {result.stderr}")
        
        return f"LLM analysis completed successfully"
    
    def _auto_ml_classify_articles(self):
        """Auto-run ML classification for articles"""
        import subprocess
        import sys
        from django.conf import settings
        
        # Run the simple ML classification script (faster, no transformers)
        script_path = os.path.join(settings.BASE_DIR, "aetheris_core", "vtagent", "simple_ml_classifier.py")
        
        # Check if script exists
        if not os.path.exists(script_path):
            raise Exception(f"ML classification script not found at: {script_path}")
        
        # Change to correct working directory
        old_cwd = os.getcwd()
        try:
            os.chdir(os.path.join(settings.BASE_DIR, "aetheris_core"))
            result = subprocess.run([sys.executable, script_path], 
                                  capture_output=True, text=True, timeout=180)  # 3 minute timeout
        finally:
            os.chdir(old_cwd)
        
        if result.returncode != 0:
            raise Exception(f"ML classification failed: {result.stderr}")
        
        return f"ML classified articles successfully"

@admin.register(RawArticle)
class RawArticleAdmin(ExportMixin, admin.ModelAdmin):
    list_display = ['id', 'title', 'source', 'published']
    change_list_template = "admin/rawarticle_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("vectorize/", self.admin_site.admin_view(self.vectorize_articles), name="vectorize_raw_articles"),
        ]
        return custom_urls + urls

    def vectorize_articles(self, request):
        try:
            import sys
            from django.conf import settings

            # Build absolute paths
            venv_python = os.path.join(settings.BASE_DIR, "venv", "Scripts", "python.exe")
            script_path = os.path.join(settings.BASE_DIR, "aetheris_core", "vtagent", "FAISS_Vectorizer.py")

            # NEW: DEBUG PRINT TO CHECK PATHS
            print(f"[DEBUG] Interpreter path: {venv_python}")
            print(f"[DEBUG] Script path: {script_path}")

            # NEW: Check if both paths exist before proceeding
            if not os.path.isfile(venv_python):
                raise FileNotFoundError(f"Python interpreter not found at: {venv_python}")
            if not os.path.isfile(script_path):
                raise FileNotFoundError(f"Script not found at: {script_path}")

            # Run subprocess
            result = subprocess.run([venv_python, script_path], capture_output=True, text=True)

            if result.returncode == 0:
                self.message_user(request, "Raw Articles vectorized successfully.", messages.SUCCESS)
            else:
                self.message_user(request, f"Vectorization failed: {result.stderr}", messages.ERROR)

        except Exception as e:
            self.message_user(request, f"Exception during vectorization: {e}", messages.ERROR)

        return HttpResponseRedirect("../")



@admin.register(ClassifiedArticle)
class ClassifiedArticleAdmin(ExportMixin, admin.ModelAdmin):
    list_display = ("title", "classification_source", "source", "published", "processed_at")
    list_filter = ("classification_source", "processed_at")
    search_fields = ("title", "url", "VT_PrimaryType", "VT_Subtype", "Platform", "Industry")

    change_list_template = "admin/classified_article_changelist.html"

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path("classify/", self.admin_site.admin_view(classify_raw_articles_view), name="classify_raw_articles"),
        ]
        return custom_urls + urls


    def classify_articles(self, request):
        try:
            from .VTAggregatorAgent_ML_ZS import classify_raw_articles
            count, errors = classify_raw_articles()
            if errors:
                self.message_user(request, f"Classified with warnings: {errors}", messages.WARNING)
            else:
                self.message_user(request, f"Classified {count} new articles", messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"Classification failed: {str(e)}", messages.ERROR)
        return redirect("..")

def classify_raw_articles_view(request):
    try:
        # Run classification script
        python_executable = sys.executable  # Points to the currently running virtualenv's Python
        script_path = os.path.join(settings.BASE_DIR, "vtagent", "VTAggregatorAgent_ML_ZS.py")
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
        )
        
        output = result.stdout + "\n" + result.stderr

        if result.returncode == 0:
            messages.success(request, "Raw Articles classified successfully.")
        else:
            messages.error(request, f"Classification script failed:\n{output}")

    except Exception as e:
        messages.error(request, f"Error during classification: {str(e)}")

    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/admin/"))



@admin.register(GeneratedTaxonomyLabel)
class GeneratedTaxonomyLabelAdmin(ExportMixin, admin.ModelAdmin):
    list_display = ['id', 'get_raw_article_id', 'classification_source', 'get_article_title', 'data_origin']
    readonly_fields = ['get_article_content']
    search_fields = ("article__title", "article__url")
    list_filter = ('data_source', 'data_origin', "platform", "country", 'classification_source')

    def get_article_title(self, obj):
        return obj.raw_article.title if hasattr(obj.raw_article, 'title') else f"Article {obj.raw_article.id}"

    def get_article_content(self, obj):
        return obj.raw_article.content
    get_article_content.short_description = "Raw Article Content"

    def get_raw_article_id(self, obj):
        return obj.raw_article.id if obj.raw_article else "—"
    get_raw_article_id.short_description = 'Raw Article ID'
    get_raw_article_id.admin_order_field = 'raw_article__id'


    def get_article_title(self, obj):
        if obj.raw_article:
            return obj.raw_article.title
        return "—"
    get_article_title.short_description = 'Raw Article Title'


    def get_article_content(self, obj):
        if obj.raw_article:
            return obj.raw_article.content
        return "—"
    get_article_content.short_description = "Raw Article Content"

