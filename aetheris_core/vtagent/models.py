# models.py for vtagent app in Aetheris
from django.db import models


class NewsSource(models.Model):
    CATEGORY_CHOICES = [
        ('cybersecurity', 'Cybersecurity'),
        ('tech-news', 'Tech News'),
        ('gov', 'Government'),
        ('vendor', 'Vendor'),
        ('research', 'Research'),
        ('other', 'Other'),
    ]

    CRAWLER_TYPE_CHOICES = [
        ('scrapy', 'Scrapy'),
        ('bs4', 'BeautifulSoup'),
    ]

    name = models.CharField(max_length=255)
    url = models.URLField(unique=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    crawler_type = models.CharField(max_length=10, choices=CRAWLER_TYPE_CHOICES, default='scrapy')
    is_active = models.BooleanField(default=True)
    crawl_code = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class RawArticle(models.Model):
    SOURCE_TYPE_CHOICES = [
        ('scrapy', 'Scrapy'),
        ('bs4', 'BeautifulSoup'),
    ]

    source = models.ForeignKey(NewsSource, on_delete=models.CASCADE)
    source_type = models.CharField(max_length=10, choices=SOURCE_TYPE_CHOICES)
    title = models.TextField()
    url = models.URLField(unique=True)
    published = models.CharField(max_length=100, blank=True)
    content = models.TextField()
    author = models.CharField(max_length=255, blank=True)
    tags = models.JSONField(default=list, blank=True)
    section = models.CharField(max_length=255, blank=True)
    scraped_at = models.DateTimeField(auto_now_add=True)
    errors = models.JSONField(default=list, blank=True)

    def __str__(self):
        return self.title[:80]


class ClassifiedArticle(models.Model):
    CLASSIFIER_CHOICES = [
        ('ml', 'Machine Learning'),
        ('gemini', 'Google Gemini'),
        ('openai', 'OpenAI'),
    ]

    url = models.URLField()
    title = models.TextField()
    source = models.CharField(max_length=255)
    published = models.CharField(max_length=100, blank=True)
    classification_source = models.CharField(max_length=10, choices=CLASSIFIER_CHOICES)
    VT_PrimaryType = models.JSONField(default=list, blank=True)
    VT_Subtype = models.JSONField(default=list, blank=True)
    Industry = models.JSONField(default=list, blank=True)
    Platform = models.JSONField(default=list, blank=True)
    Severity = models.JSONField(default=list, blank=True)     # critical, high, etc.
    Impact = models.JSONField(default=list, blank=True)       # data breach, etc.
    Actor = models.JSONField(default=list, blank=True)        # cybercriminal, insider
    Origin = models.JSONField(default=list, blank=True)       # internal, external
    Compliance = models.JSONField(default=list, blank=True)
    raw_content = models.TextField()
    processed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.classification_source.upper()} | {self.title[:80]}"

from vtagent.models import RawArticle

class GeneratedTaxonomyLabel(models.Model):
    # === 🔹 Article Association ===
    raw_article = models.ForeignKey(RawArticle, on_delete=models.CASCADE, null=True, blank=True)
    record_id = models.CharField(max_length=100, null=True, blank=True)
    classification_source = models.CharField(max_length=500, blank=True)
    labels_generated_at = models.DateTimeField(auto_now_add=True)

    # === 🔹 NEW: Data Classification Tracking ===
    data_source = models.CharField(max_length=500, blank=True)  # e.g., RawArticle, CMDB, ADUser
    data_origin = models.CharField(max_length=500, blank=True)  # e.g., Django, FAISS, Hybrid

    # === 🔹 CMDB-Derived Context ===
    platform = models.JSONField(default=list, null=True, blank=True)
    software = models.JSONField(default=list, null=True, blank=True)
    software_version = models.CharField(max_length=500, null=True, blank=True)
    hardware_vendor = models.CharField(max_length=500, null=True, blank=True)
    connectivity = models.CharField(max_length=500, null=True, blank=True)
    network_zone = models.CharField(max_length=100, null=True, blank=True)

    # === 🔹 Asset-Level Intelligence ===
    os = models.CharField(max_length=500, null=True, blank=True)
    os_version = models.CharField(max_length=500, null=True, blank=True)
    security_software = models.CharField(max_length=500, null=True, blank=True)
    ip_address = models.GenericIPAddressField(max_length=500, null=True, blank=True)

    # === 🔹 Employee & AD Context ===
    country = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    business_unit = models.CharField(max_length=100, null=True, blank=True)
    department = models.CharField(max_length=100, null=True, blank=True)
    security_posture = models.CharField(max_length=500, null=True, blank=True)

    # === 🔹 Inferred Threat Taxonomy ===
    severity = models.JSONField(default=list, null=True, blank=True)
    impact = models.JSONField(default=list, null=True, blank=True)
    actor = models.JSONField(default=list, null=True, blank=True)
    origin = models.JSONField(default=list, null=True, blank=True)
    compliance = models.JSONField(default=list, null=True, blank=True)

    # === 🔹 Threat Intelligence & TTPs ===
    threat_stage = models.CharField(max_length=500, null=True, blank=True)
    initial_access_method = models.CharField(max_length=500, null=True, blank=True)
    payload_type = models.CharField(max_length=500, null=True, blank=True)
    mitre_tactics = models.JSONField(default=list, null=True, blank=True)
    impact_area = models.JSONField(default=list, null=True, blank=True)

    # === 🔹 Detection & Response Context ===
    detection_vector = models.CharField(max_length=500, null=True, blank=True)
    reported_by = models.CharField(max_length=500, null=True, blank=True)
    response_action = models.TextField(null=True, blank=True)

    # === 🔹 Backlink to Specific Asset/User ===
    cmdb_item = models.ForeignKey('syntheticcmdb.ConfigurationItem', null=True, blank=True, on_delete=models.SET_NULL)
    ad_user = models.ForeignKey('syntheticad.ADUser', null=True, blank=True, on_delete=models.SET_NULL)
    employee = models.ForeignKey('syntheticemployees.Employee', null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"TaxonomyLabel #{self.id}"


