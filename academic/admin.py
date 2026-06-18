# academic/admin.py
from django.contrib import admin
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from import_export.admin import ImportExportModelAdmin
from django.contrib.auth import get_user_model

from .models import (
    Day, TimeSlot, RoomType, RoomSubType, Department, 
    Semester, Batch, Room, Course, RoutineEntry, 
    BatchTimeConstraint, SystemSetting, RoutineBackup
)

User = get_user_model()

# ==============================================================================
# PROFESSIONAL RESOURCES (Magic of Natural Keys for Excel)
# ==============================================================================

class DepartmentResource(resources.ModelResource):
    class Meta:
        model = Department
        skip_unchanged = True
        import_id_fields = ('name',)

class BatchResource(resources.ModelResource):
    # ID এর বদলে ডিপার্টমেন্ট এবং সেমিস্টারের নাম দিয়ে ম্যাচ করবে
    department = fields.Field(
        column_name='department',
        attribute='department',
        widget=ForeignKeyWidget(Department, 'name')
    )
    current_semester = fields.Field(
        column_name='current_semester',
        attribute='current_semester',
        widget=ForeignKeyWidget(Semester, 'name')
    )

    class Meta:
        model = Batch
        import_id_fields = ('name',)
        skip_unchanged = True
        report_skipped = True
        fields = ('id', 'name', 'department', 'current_semester', 'status', 'is_active')

class CourseResource(resources.ModelResource):
    # ID এর বদলে ডিপার্টমেন্টের নাম, সেমিস্টারের নাম এবং টিচারের ইউজারনেম দিয়ে ম্যাচ করবে
    department = fields.Field(
        column_name='department',
        attribute='department',
        widget=ForeignKeyWidget(Department, 'name')
    )
    semester = fields.Field(
        column_name='semester',
        attribute='semester',
        widget=ForeignKeyWidget(Semester, 'name')
    )
    teacher = fields.Field(
        column_name='teacher',
        attribute='teacher',
        widget=ForeignKeyWidget(User, 'username')
    )

    class Meta:
        model = Course
        import_id_fields = ('course_code',)
        skip_unchanged = True
        report_skipped = True

class RoomResource(resources.ModelResource):
    department = fields.Field(
        column_name='department',
        attribute='department',
        widget=ForeignKeyWidget(Department, 'name')
    )
    room_type = fields.Field(
        column_name='room_type',
        attribute='room_type',
        widget=ForeignKeyWidget(RoomType, 'name')
    )

    class Meta:
        model = Room
        import_id_fields = ('room_number',)
        skip_unchanged = True
        report_skipped = True

# ==============================================================================
# IMPORT/EXPORT ADMIN CLASSES
# ==============================================================================
@admin.register(Department)
class DepartmentAdmin(ImportExportModelAdmin):
    resource_class = DepartmentResource
    list_display = ('name', 'is_active', 'created_at')
    search_fields = ('name',)
    list_filter = ('is_active',)

@admin.register(Semester)
class SemesterAdmin(ImportExportModelAdmin):
    list_display = ('name', 'order', 'is_active')
    ordering = ('order',)

@admin.register(Batch)
class BatchAdmin(ImportExportModelAdmin):
    resource_class = BatchResource
    list_display = ('name', 'department', 'current_semester', 'status', 'is_active')
    list_filter = ('department', 'status', 'is_active')
    search_fields = ('name',)

@admin.register(Room)
class RoomAdmin(ImportExportModelAdmin):
    resource_class = RoomResource
    list_display = ('room_number', 'capacity', 'room_type', 'department', 'is_active')
    list_filter = ('room_type', 'department', 'is_active')
    search_fields = ('room_number',)

@admin.register(Course)
class CourseAdmin(ImportExportModelAdmin):
    resource_class = CourseResource
    list_display = ('course_code', 'course_name', 'credits', 'course_type', 'department', 'teacher', 'is_active')
    list_filter = ('department', 'semester', 'course_type', 'is_active')
    search_fields = ('course_name', 'course_code', 'teacher__username')

@admin.register(RoutineEntry)
class RoutineEntryAdmin(ImportExportModelAdmin):
    list_display = ('get_day_name', 'time_slot', 'get_course_name', 'group_name', 'get_department', 'get_room_number', 'get_teacher', 'is_cancelled', 'is_active')
    list_filter = ('day', 'course__department', 'course__semester', 'is_cancelled', 'is_active')
    search_fields = ('course__course_code', 'room__room_number')

    def get_day_name(self, obj): return obj.day.name if obj.day else "N/A"
    get_day_name.short_description = 'Day'

    def get_course_name(self, obj): return obj.course.course_name
    get_course_name.short_description = 'Course'

    def get_department(self, obj): return obj.course.department.name
    get_department.short_description = 'Department'

    def get_room_number(self, obj): return obj.room.room_number if obj.room else "N/A"
    get_room_number.short_description = 'Room No'

    def get_teacher(self, obj): return obj.course.teacher.username if obj.course.teacher else "N/A"
    get_teacher.short_description = 'Teacher'

@admin.register(BatchTimeConstraint)
class BatchTimeConstraintAdmin(ImportExportModelAdmin):
    list_display = ('department', 'semester', 'day', 'time_slot', 'constraint_type', 'is_active')

admin.site.register(Day)
admin.site.register(TimeSlot)
admin.site.register(RoomType)
admin.site.register(RoomSubType)

# ==============================================================================
# SECURE/READ-ONLY ADMIN CLASSES
# ==============================================================================
@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'last_updated')
    
    def has_add_permission(self, request):
        if self.model.objects.exists():
            return False
        return super().has_add_permission(request)

@admin.register(RoutineBackup)
class RoutineBackupAdmin(admin.ModelAdmin):
    list_display = ('department', 'created_at')
    readonly_fields = ('department', 'created_at', 'backup_data')
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False