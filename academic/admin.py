from django.contrib import admin
from .models import Department, Semester, Course, TimeSlot, RoutineEntry

admin.site.register(Department)
admin.site.register(Semester)
admin.site.register(TimeSlot)

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('course_code', 'course_name', 'credits', 'course_type', 'department', 'semester', 'teacher')
    list_filter = ('department', 'semester', 'course_type', 'teacher')
    search_fields = ('course_name', 'course_code')




@admin.register(RoutineEntry)
class RoutineEntryAdmin(admin.ModelAdmin):
    
    list_display = ('day', 'time_slot', 'get_course_name', 'get_department', 'get_semester', 'get_room_number', 'get_teacher')
    
    list_filter = ('day', 'course__department', 'course__semester', 'course__teacher')
    
    
     
    # def course_info(self, obj):
    #     return f"{obj.course.course_name} ({obj.course.course_type})"
    
    # def teacher_info(self, obj):
    #     return obj.course.teacher.username if obj.course.teacher else "-"
    
    def get_course_name(self, obj):
        return obj.course.course_name
    get_course_name.short_description = 'Course'

    def get_department(self, obj):
        return obj.course.department.name
    get_department.short_description = 'Department'

    def get_semester(self, obj):
        return obj.course.semester.name
    get_semester.short_description = 'Semester'

    def get_room_number(self, obj):
        return obj.course.room_number
    get_room_number.short_description = 'Room No'

    def get_teacher(self, obj):
        return obj.course.teacher.username if obj.course.teacher else "N/A"
    get_teacher.short_description = 'Teacher'