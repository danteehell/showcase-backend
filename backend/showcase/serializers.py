from rest_framework import serializers
from .models import *
from users.models import Specialty


class ProjectApplicationSerializer(serializers.ModelSerializer):
    applicant_email = serializers.ReadOnlyField(source='applicant.email')
    
    specialties = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Specialty.objects.all(), required=False
    )

    class Meta:
        model = ProjectApplication
        fields = [
            'id', 'applicant', 'applicant_email', 'status', 
            'rejection_reason_choice', 'rejection_reason_text',
            'title', 'relevance', 'problem', 'goal', 'tasks', 'expected_result',
            'specialties', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'applicant', 'status', 'rejection_reason_choice', 'rejection_reason_text', 
            'created_at', 'updated_at'
        ]

class ProjectListItemSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source='get_type_display')
    class Meta:
        model = ProjectListItem
        fields = ['type', 'text']


class ProjectSerializer(serializers.ModelSerializer):
    curator = serializers.SerializerMethodField()
    theme = serializers.CharField(source='theme.name', default=None)
    specialties = serializers.SlugRelatedField(many=True, read_only=True, slug_field='name')
    campus = serializers.CharField(source='campus.name', default=None)
    courses = serializers.SlugRelatedField(many=True, read_only=True, slug_field='name')
    difficulty = serializers.CharField(source='difficulty.name', default=None)
    partner = serializers.CharField(source='partner.name', default=None)
    
    technologies = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            'id', 'title', 'short_description', 'relevance', 'problem', 'goal', 
            'tasks', 'expected_result', 'theme', 'specialties', 'campus', 'courses', 
            'difficulty', 'partner', 'curator', 'internship', 'spots_remaining', 
            'is_active', 'created_at', 'updated_at', 'technologies'
        ]
        
    def get_curator(self, obj):
        if obj.curator:
            return obj.curator.get_full_name()
        return None

    def get_technologies(self, obj):
        return [item.text for item in obj.list_items.all() if item.type == 'technologies']

class FilterOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FilterOption
        fields = ['id', 'name']


class FilterCategorySerializer(serializers.ModelSerializer):
    options = FilterOptionSerializer(many=True, read_only=True)
    
    class Meta:
        model = FilterCategory
        fields = ['id', 'name', 'options'] 


class PartnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Partner
        fields = ['name', 'website']