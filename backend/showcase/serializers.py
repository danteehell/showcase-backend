from rest_framework import serializers
from .models import *
from users.models import Specialty


class ProjectListItemSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source='get_type_display')
    class Meta:
        model = ProjectListItem
        fields = ['type', 'text']


class ProjectSerializer(serializers.ModelSerializer):
    curator = serializers.SerializerMethodField()
    theme = serializers.CharField(source='theme.name', default=None)
    specialties = serializers.SlugRelatedField(many=True, read_only=True, slug_field='name')
    day_of_week = serializers.CharField(source='shedule.day_of_week', default=None)
    campus = serializers.CharField(source='campus.name', default=None)
    courses = serializers.SlugRelatedField(many=True, read_only=True, slug_field='name')
    difficulty = serializers.CharField(source='difficulty.name', default=None)
    partner = serializers.CharField(source='partner.name', default=None)
    
    tasks = serializers.SerializerMethodField()
    technologies = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            'id', 'title', 'theme', 'specialties', 'campus', 'courses', 'day_of_week',
            'difficulty', 'partner', 'curator', 'internship', 'spots_remaining', 
            'short_description', 'long_description', 'is_active', 'created_at', 'updated_at',
            'tasks', 'technologies'
        ]
        
    def get_curator(self, obj):
        if obj.curator:
            return obj.curator.get_full_name()
        return None

    def get_tasks(self, obj):
        items = obj.list_items.filter(type='tasks')
        return [item.text for item in items]

    def get_technologies(self, obj):
        items = obj.list_items.filter(type='technology')
        return [item.text for item in items]


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