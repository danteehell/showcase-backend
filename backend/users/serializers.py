from rest_framework import serializers

from .models import (
    User,
    StudentProfile,
    CuratorProfile,
    Specialty,
    Faculty,
    Partner,
    PartnerRepresentative,
)


class StudentSpecialtySerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialty
        fields = ["id", "code", "name"]


class StudentProfileSerializer(serializers.ModelSerializer):
    group = serializers.CharField(
        source="group.name",
        read_only=True,
        allow_null=True,
    )
    specialty = StudentSpecialtySerializer(
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = StudentProfile
        fields = ["group", "course", "specialty"]


class CuratorProfileSerializer(serializers.ModelSerializer):
    department = serializers.CharField(
        source="department.name",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = CuratorProfile
        fields = ["department"]


class DirectionSpecialtySerializer(serializers.ModelSerializer):
    faculty = serializers.CharField(
        source="faculty.name",
        read_only=True,
    )

    class Meta:
        model = Specialty
        fields = ["id", "code", "name", "faculty"]


class FacultySerializer(serializers.ModelSerializer):
    class Meta:
        model = Faculty
        fields = ["id", "name"]


class PartnerRepresentativeSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="partner.id", read_only=True)
    name = serializers.CharField(source="partner.name", read_only=True)
    short_name = serializers.CharField(
        source="partner.short_name",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = PartnerRepresentative
        fields = ["id", "name", "short_name"]

class PartnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Partner
        fields = [
            "id",
            "name",
            "short_name",
            "website",
            "email",
            "phone",
            "contact_person",
            "is_curator_contact",
            "additional_contact",
            "internship",
        ]

class UserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    role_display = serializers.SerializerMethodField()
    profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "middle_name",
            "role",
            "role_display",
            "profile",
        ]
        read_only_fields = fields

    def get_role(self, obj):
        return "admin" if obj.is_admin() else obj.role

    def get_role_display(self, obj):
        return "Начальник ЦПД" if obj.is_admin() else obj.get_role_display()

    def get_profile(self, obj):
        if obj.is_admin():
            return None

        if obj.is_student():
            profile = getattr(obj, "student_profile", None)

            return (
                StudentProfileSerializer(profile).data
                if profile
                else None
            )

        if obj.is_curator():
            profile = getattr(obj, "curator_profile", None)

            return (
                CuratorProfileSerializer(profile).data
                if profile
                else None
            )

        if obj.is_direction_head():
            specialties = obj.headed_specialties.all()

            return {
                "specialties": DirectionSpecialtySerializer(
                    specialties,
                    many=True,
                ).data
            }

        if obj.is_dean():
            faculties = obj.dean_of_faculties.all()

            return {
                "faculties": FacultySerializer(
                    faculties,
                    many=True,
                ).data
            }

        if obj.is_partner():
            representatives = obj.partner_roles.select_related("partner")

            return {
                "partners": PartnerRepresentativeSerializer(
                    representatives,
                    many=True,
                ).data
            }

        return None