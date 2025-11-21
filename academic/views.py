from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Department, Semester, Course, TimeSlot, RoutineEntry

from .utils import generate_routine_algorithm

from .models import Department, Semester, Course, TimeSlot, RoutineEntry
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



    
    



class GenerateRoutineView(APIView):
    permission_classes = [IsAdminUser]
    def post(self, request):
        try:
            result = generate_routine_algorithm()
            return Response(result)
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=500)

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

       
        queryset = queryset.order_by('day', 'time_slot__start_time')

        serializer = RoutineEntrySerializer(queryset, many=True)
        return Response(serializer.data)