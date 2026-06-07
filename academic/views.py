from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

# Room মডেলটি ইম্পোর্ট করা হয়েছে (ভবিষ্যতে RoomViewSet বানানোর জন্য কাজে লাগবে)
from .models import Department, Semester, Course, TimeSlot, RoutineEntry, Room 
from .utils import generate_routine_algorithm
from .serializers import (
    DepartmentSerializer, SemesterSerializer, CourseSerializer, 
    TimeSlotSerializer, RoutineEntrySerializer
)
from user_api.permissions import IsAdminUser


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsAdminUser]

class SemesterViewSet(viewsets.ModelViewSet):
    queryset = Semester.objects.all().order_by('order')
    serializer_class = SemesterSerializer
    permission_classes = [IsAdminUser]

class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsAdminUser]

class TimeSlotViewSet(viewsets.ModelViewSet):
    queryset = TimeSlot.objects.all().order_by('start_time')
    serializer_class = TimeSlotSerializer
    permission_classes = [IsAdminUser]


# আপডেটেড GenerateRoutineView: এখন এটি department_id ইনপুট হিসেবে নেবে
class GenerateRoutineView(APIView):
    permission_classes = [IsAdminUser]
    
    def post(self, request):
        department_id = request.data.get('department_id')
        
        if not department_id:
            return Response({"status": "error", "message": "department_id is required. Please select a department."}, status=400)
            
        try:
            # চেক করা হচ্ছে ডিপার্টমেন্টটি আসলেই আছে কিনা
            department = Department.objects.get(id=department_id)
            
            # অ্যালগরিদমে department.id পাস করা হচ্ছে
            result = generate_routine_algorithm(department.id)
            return Response(result)
            
        except Department.DoesNotExist:
            return Response({"status": "error", "message": "Department not found."}, status=404)
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=500)


# আপডেটেড RoutineListView
class RoutineListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        queryset = RoutineEntry.objects.all()
    
        if user.role == 'TEACHER':
            queryset = queryset.filter(course__teacher=user)
          
        elif user.role == 'STUDENT':
            if user.department and user.semester:
                queryset = queryset.filter(
                    course__department=user.department,
                    course__semester=user.semester
                )
            else:
                return Response({"error": "Student profile incomplete"}, status=400)
      
        day = request.query_params.get('day')
        if day:
            queryset = queryset.filter(day=day)

        # অ্যাডমিন চাইলে নির্দিষ্ট ডিপার্টমেন্টের রুটিন ফিল্টার করে দেখতে পারবে
        department_id = request.query_params.get('department_id')
        if department_id:
            queryset = queryset.filter(course__department_id=department_id)

        queryset = queryset.order_by('day', 'time_slot__start_time')

        serializer = RoutineEntrySerializer(queryset, many=True)
        return Response(serializer.data)
    



# RoomViewSet নতুন যোগ করা হলো
from .serializers import RoomSerializer

class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    permission_classes = [IsAdminUser]