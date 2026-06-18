# academic/views.py
from django.shortcuts import render
from django.db import transaction
from django.http import HttpResponse
from django.contrib.auth import get_user_model

from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser

import tablib

from .admin import CourseResource, RoomResource, DepartmentResource, BatchResource
from user_api.admin import UserResource

from .models import (
    Department, Semester, Course, TimeSlot, RoutineEntry, Room, 
    RoomType, RoomSubType, Day
)
from .utils import generate_routine_algorithm, rollback_routine_algorithm
from .serializers import (
    DepartmentSerializer, SemesterSerializer, CourseSerializer, 
    TimeSlotSerializer, RoutineEntrySerializer, RoomSerializer
)
from user_api.permissions import IsAdminUser

User = get_user_model()

# ==============================================================================
# ROUTINE CONFLICT CHECKER (Helper Function)
# ==============================================================================
def check_routine_conflict(day_id, time_slot_id, room_id, course, exclude_entry_ids=None):
    """
    Ei function check korbe oi din, oi time e room, teacher ba batch er kono clash ase kina.
    exclude_entry_ids e je ID gulo thakbe, taderke check theke baad dibe.
    """
    base_query = RoutineEntry.objects.filter(
        day_id=day_id, 
        time_slot_id=time_slot_id, 
        is_active=True,
        is_cancelled=False
    )
    
    # Ekhane main update ta kora hoyeche (id__in use kore eksathe ekadhik class baad dewa)
    if exclude_entry_ids:
        base_query = base_query.exclude(id__in=exclude_entry_ids)

    # 1. Room Conflict Check
    if base_query.filter(room_id=room_id).exists():
        return "Error: Ei somoy ei Room ti already booked!"

    # 2. Teacher Conflict Check
    if course.teacher and base_query.filter(course__teacher=course.teacher).exists():
        return f"Error: {course.teacher.username} sir er ei somoy onno ekta class ase!"

    # 3. Batch/Semester Conflict Check
    if base_query.filter(course__department=course.department, course__semester=course.semester).exists():
        return f"Error: Ei batch er students der ei somoy already arekta class ase!"

    return None

# ==============================================================================
# Model ViewSets (Updated for Soft Delete: is_active=True)
# ==============================================================================
class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.filter(is_active=True)
    serializer_class = DepartmentSerializer
    permission_classes = [IsAdminUser]

class SemesterViewSet(viewsets.ModelViewSet):
    queryset = Semester.objects.filter(is_active=True).order_by('order')
    serializer_class = SemesterSerializer
    permission_classes = [IsAdminUser]

class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.filter(is_active=True)
    serializer_class = CourseSerializer
    permission_classes = [IsAdminUser]

class TimeSlotViewSet(viewsets.ModelViewSet):
    # TimeSlot doesn't inherit TimeStampedModel in our current design, so no is_active filter needed
    queryset = TimeSlot.objects.all().order_by('start_time')
    serializer_class = TimeSlotSerializer
    permission_classes = [IsAdminUser]

class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.filter(is_active=True)
    serializer_class = RoomSerializer
    permission_classes = [IsAdminUser]


# ==============================================================================
# ROUTINE GENERATION & MANAGEMENT APIs
# ==============================================================================
class GenerateRoutineView(APIView):
    permission_classes = [IsAdminUser]
    
    def post(self, request):
        department_id = request.data.get('department_id')
        semester_id = request.data.get('semester_id')
        ignore_warnings = request.data.get('ignore_warnings', False)
        
        if isinstance(ignore_warnings, str):
            ignore_warnings = ignore_warnings.lower() == 'true'
        
        if not department_id:
            return Response(
                {"status": "error", "message": "department_id is required."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            department = Department.objects.get(id=department_id, is_active=True)
            
            if semester_id:
                Semester.objects.get(id=semester_id, is_active=True)
            
            result = generate_routine_algorithm(
                department_id=department.id, 
                semester_id=semester_id, 
                ignore_warnings=ignore_warnings
            )
            
            if result.get("status") == "Warning":
                return Response(result, status=status.HTTP_409_CONFLICT)
            elif result.get("status") == "Locked":
                return Response(result, status=status.HTTP_403_FORBIDDEN)
            elif result.get("status") == "Error":
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response(result, status=status.HTTP_200_OK)
            
        except Department.DoesNotExist:
            return Response(
                {"status": "error", "message": "Department not found or is inactive."}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Semester.DoesNotExist:
            return Response(
                {"status": "error", "message": "Semester not found or is inactive."}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"status": "error", "message": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RollbackRoutineView(APIView):
    permission_classes = [IsAdminUser]
    
    def post(self, request):
        department_id = request.data.get('department_id')
        if not department_id:
            return Response({"status": "error", "message": "department_id is required."}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            department = Department.objects.get(id=department_id, is_active=True)
            result = rollback_routine_algorithm(department.id)
            return Response(result)
            
        except Department.DoesNotExist:
            return Response({"status": "error", "message": "Department not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RoutineListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        queryset = RoutineEntry.objects.filter(is_active=True)
    
        if user.role == 'TEACHER':
            queryset = queryset.filter(course__teacher=user)
          
        elif user.role == 'STUDENT':
            if user.department and user.semester:
                queryset = queryset.filter(
                    course__department=user.department,
                    course__semester=user.semester
                )
            else:
                return Response({"error": "Student profile incomplete"}, status=status.HTTP_400_BAD_REQUEST)
      
        day = request.query_params.get('day')
        department_id = request.query_params.get('department_id')
        semester_id = request.query_params.get('semester_id')

        if day:
            queryset = queryset.filter(day_id=day)
        if department_id:
            queryset = queryset.filter(course__department_id=department_id)
        if semester_id:
            queryset = queryset.filter(course__semester_id=semester_id)

        queryset = queryset.order_by('day__order', 'time_slot__start_time')
        serializer = RoutineEntrySerializer(queryset, many=True)
        return Response(serializer.data)
    

class TeacherCancelClassView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        
        if getattr(user, 'role', '') != 'TEACHER':
            return Response({"error": "Only teachers can cancel classes."}, status=status.HTTP_403_FORBIDDEN)

        routine_id = request.data.get('routine_id')
        cancel_message = request.data.get('cancel_message')

        if not routine_id:
            return Response({"error": "routine_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not cancel_message:
            return Response({"error": "cancel_message is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            routine = RoutineEntry.objects.get(id=routine_id, is_active=True)
            
            if routine.course.teacher != user:
                return Response({"error": "You can only cancel your own classes."}, status=status.HTTP_403_FORBIDDEN)

            routine.is_cancelled = True
            routine.cancel_message = cancel_message
            routine.save()

            return Response({
                "status": "Success",
                "message": f"Class '{routine.course.course_name}' has been cancelled successfully."
            })

        except RoutineEntry.DoesNotExist:
            return Response({"error": "Routine entry not found or inactive."}, status=status.HTTP_404_NOT_FOUND)


class ManualRoutineUpdateView(APIView):
    # permission_classes = [IsAdminUser]

    def put(self, request, entry_id):
        try:
            entry = RoutineEntry.objects.get(id=entry_id)
        except RoutineEntry.DoesNotExist:
            return Response({"error": "Routine entry found hoyni!"}, status=status.HTTP_404_NOT_FOUND)

        new_day_id = request.data.get('day_id', entry.day.id)
        new_time_slot_id = request.data.get('time_slot_id', entry.time_slot.id)
        new_room_id = request.data.get('room_id', entry.room.id if entry.room else None)

        conflict_msg = check_routine_conflict(new_day_id, new_time_slot_id, new_room_id, entry.course, exclude_entry_ids=[entry.id])
        
        if conflict_msg:
            return Response({"status": "error", "message": conflict_msg}, status=status.HTTP_400_BAD_REQUEST)

        entry.day_id = new_day_id
        entry.time_slot_id = new_time_slot_id
        entry.room_id = new_room_id
        entry.save()

        return Response({"status": "success", "message": "Routine successfully update kora hoyeche!"})


class RoutineSwapView(APIView):
    # permission_classes = [IsAdminUser]

    def post(self, request):
        entry1_id = request.data.get('entry1_id')
        entry2_id = request.data.get('entry2_id')

        if not entry1_id or not entry2_id:
            return Response({"error": "Duti routine entry er ID dite hobe."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            entry1 = RoutineEntry.objects.get(id=entry1_id)
            entry2 = RoutineEntry.objects.get(id=entry2_id)
        except RoutineEntry.DoesNotExist:
            return Response({"error": "Kono ekte routine entry pawa jayni."}, status=status.HTTP_404_NOT_FOUND)

        # Cross-Conflict Check (Duijonkei ignore korbo check korar somoy)
        ignore_ids = [entry1.id, entry2.id]
        
        # LOGIC: Entry 1 jacche Entry 2 er time e, kintu ROOM ar COURSE nijertai thakbe
        conflict1 = check_routine_conflict(
            day_id=entry2.day.id, 
            time_slot_id=entry2.time_slot.id, 
            room_id=entry1.room.id if entry1.room else None, 
            course=entry1.course, 
            exclude_entry_ids=ignore_ids
        )
        
        # LOGIC: Entry 2 jacche Entry 1 er time e, kintu ROOM ar COURSE nijertai thakbe
        conflict2 = check_routine_conflict(
            day_id=entry1.day.id, 
            time_slot_id=entry1.time_slot.id, 
            room_id=entry2.room.id if entry2.room else None, 
            course=entry2.course, 
            exclude_entry_ids=ignore_ids
        )

        if conflict1 or conflict2:
            return Response({
                "status": "error", 
                "message": "Swap kora jabe na, karon conflict ache!",
                "details": {"entry1_issue": conflict1, "entry2_issue": conflict2}
            }, status=status.HTTP_400_BAD_REQUEST)

        # =========================================================
        # THE MAGIC FIX: Swap ONLY Time & Day (Container), Not Content
        # =========================================================
        with transaction.atomic():
            # Shudhu day ar time ta temporary save korlam
            temp_day = entry1.day
            temp_time = entry1.time_slot
            
            # Entry 1 er vitor Entry 2 er time ar day bosiye dilam
            entry1.day = entry2.day
            entry1.time_slot = entry2.time_slot
            entry1.save()

            # Entry 2 er vitor Entry 1 er ager time ar day bosiye dilam
            entry2.day = temp_day
            entry2.time_slot = temp_time
            entry2.save()

        return Response({"status": "success", "message": "Duti class er shudhu somoy (Time & Day) successfully swap kora hoyeche!"})
# ==============================================================================
# DYNAMIC EXCEL IMPORT & EXPORT APIs (Master API)
# ==============================================================================

RESOURCE_MAP = {
    'user': UserResource,
    'course': CourseResource,
    'room': RoomResource,
    'department': DepartmentResource,
    'batch': BatchResource,
}

class ExcelImportView(APIView):
    permission_classes = [IsAdminUser]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        model_name = request.data.get('model_name')
        excel_file = request.FILES.get('file')

        if not model_name or not excel_file:
            return Response(
                {"error": "model_name and file are required in form-data."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        model_name = model_name.lower()
        if model_name not in RESOURCE_MAP:
            return Response(
                {"error": f"Invalid model_name. Allowed options: {list(RESOURCE_MAP.keys())}"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            dataset = tablib.Dataset()
            dataset.load(excel_file.read(), format='xlsx')

            resource_class = RESOURCE_MAP[model_name]
            resource = resource_class()

            result = resource.import_data(dataset, dry_run=True)

            if result.has_errors() or result.has_validation_errors():
                error_details = []
                
                for error in result.row_errors():
                    error_details.append(f"Row {error[0]}: {str(error[1].error)}")
                    
                for invalid_row in result.invalid_rows:
                    error_details.append(f"Row {invalid_row.number}: {invalid_row.error_dict}")

                return Response({
                    "status": "error", 
                    "message": "Data validation failed! Please check your Excel file.", 
                    "details": error_details
                }, status=status.HTTP_400_BAD_REQUEST)

            resource.import_data(dataset, dry_run=False)
            return Response({
                "status": "success", 
                "message": f"{model_name.capitalize()} data imported successfully!"
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ExcelExportView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        model_name = request.query_params.get('model_name')

        if not model_name:
            return Response(
                {"error": "model_name is required as a query parameter."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        model_name = model_name.lower()
        if model_name not in RESOURCE_MAP:
            return Response(
                {"error": f"Invalid model_name. Allowed options: {list(RESOURCE_MAP.keys())}"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            resource_class = RESOURCE_MAP[model_name]
            resource = resource_class()
            dataset = resource.export()

            response = HttpResponse(
                dataset.xlsx, 
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="{model_name}_backup.xlsx"'
            return response

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)