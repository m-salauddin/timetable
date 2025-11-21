# academic/serializers.py

from rest_framework import serializers



from .models import Department, Semester, Course, TimeSlot, RoutineEntry

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'name']

class SemesterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Semester
        fields = ['id', 'name', 'order']

        
        
class CourseSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.username', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    semester_name = serializers.CharField(source='semester.name', read_only=True)

    class Meta:
        model = Course
        fields = [
            'id', 'course_code', 'course_name', 'room_number',
            'credits', 'course_type', # নতুন ফিল্ড
            'teacher', 'teacher_name',
            'department', 'department_name',
            'semester', 'semester_name'
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
    room_number = serializers.CharField(source='course.room_number', read_only=True)
    
    start_time = serializers.TimeField(source='time_slot.start_time', read_only=True)
    end_time = serializers.TimeField(source='time_slot.end_time', read_only=True)

    class Meta:
        model = RoutineEntry
        fields = [
            'id', 
            'day', 
            'start_time', 
            'end_time',
            'course_name', 
            'course_code', 
            'teacher_name', 
            'department_name', 
            'semester_name', 
            'room_number'
        ]


    def get_teacher_name(self, obj):
       
        return obj.course.teacher.username if obj.course.teacher else "No Teacher"

    def get_department_name(self, obj):
        return obj.course.department.name if obj.course.department else "N/A"

    def get_semester_name(self, obj):
        return obj.course.semester.name if obj.course.semester else "N/A" 
  