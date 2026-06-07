from rest_framework import serializers

# নতুন Room মডেলটি ইম্পোর্ট করা হলো
from .models import Department, Semester, Course, TimeSlot, RoutineEntry, Room

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'name']

class SemesterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Semester
        fields = ['id', 'name', 'order']

# ১. নতুন RoomSerializer তৈরি করা হলো
class RoomSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    
    class Meta:
        model = Room
        fields = ['id', 'room_number', 'capacity', 'room_type', 'sub_category', 'department', 'department_name']

class CourseSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.username', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    semester_name = serializers.CharField(source='semester.name', read_only=True)
    
    # ফ্রন্টএন্ডের সুবিধার্থে অ্যাডমিন ফিক্সড রুমের নাম দেখার জন্য (ঐচ্ছিক)
    fixed_room_number = serializers.CharField(source='fixed_room.room_number', read_only=True)

    class Meta:
        model = Course
        # room_number বাদ দেওয়া হয়েছে এবং নতুন ফিল্ডগুলো যোগ করা হয়েছে
        fields = [
            'id', 'course_code', 'course_name', 'student_count',
            'credits', 'course_type', 'sub_category',
            'teacher', 'teacher_name',
            'department', 'department_name',
            'semester', 'semester_name',
            'fixed_room', 'fixed_room_number', 'fixed_day', 'fixed_time_slot'
        ]

class TimeSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeSlot
        fields = ['id', 'start_time', 'end_time']

class RoutineEntrySerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source='course.course_name', read_only=True)
    course_code = serializers.CharField(source='course.course_code', read_only=True)

    teacher_name = serializers.SerializerMethodField()
    department_name = serializers.SerializerMethodField()
    semester_name = serializers.SerializerMethodField()
    
    # ২. room_number এখন course.room_number এর বদলে room.room_number থেকে আসবে
    room_number = serializers.CharField(source='room.room_number', read_only=True)
    
    start_time = serializers.TimeField(source='time_slot.start_time', read_only=True)
    end_time = serializers.TimeField(source='time_slot.end_time', read_only=True)
    credits = serializers.IntegerField(source='course.credits', read_only=True)

    class Meta:
        model = RoutineEntry
        fields = [
            'id', 
            'day', 
            'start_time', 
            'end_time',
            'course_name', 
            'course_code', 
            'credits',       
            'teacher_name', 
            'department_name', 
            'semester_name', 
            'room_number' # আপডেটেড
        ]

    def get_teacher_name(self, obj):
        return obj.course.teacher.username if obj.course.teacher else "No Teacher"

    def get_department_name(self, obj):
        return obj.course.department.name if obj.course.department else "N/A"

    def get_semester_name(self, obj):
        return obj.course.semester.name if obj.course.semester else "N/A"